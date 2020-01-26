import asyncio
import json
import zlib
import uuid
import multiprocessing

from base64 import urlsafe_b64encode, urlsafe_b64decode
from collections import deque
from datetime import datetime
from expiringdict import ExpiringDict

from dnslib import DNSRecord, RR, QTYPE, RCODE, CLASS, TXT, A
from dnslib.server import BaseResolver

from app.interfaces.c2_passive_interface import C2Passive


class DNS(C2Passive):
    """
    DNS C2 channel

    :param services: Object services
    :type services: object
    :param config: Configuration file
    :type config: dict
    """
    def __init__(self, services, config):
        super().__init__(config=config)
        self.contact_svc = services.get('contact_svc')
        self.file_svc = services.get('file_svc')
        self.logger = self.file_svc.create_logger('DNSService')
        self.resolver = C2Resolver(self.contact_svc, self.logger, self.file_svc, '')
        self.config = config['config']

    async def start(self):
        """
        Starts DNS C2 loop and UDP datagram endpoint
        """
        loop = asyncio.get_event_loop()
        laddr = self.config['listen']['address']
        lport = self.config['listen']['port']
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPAsyncDNSHandler(self.resolver),
            local_addr=(laddr, lport)
        )

    def valid_config(self):
        """
        Determine if module configuration is valid.

        :return: Status of valid configuration
        :rtype: bool
        """
        if 'listen' in self.config:
            keys = self.config['listen'].keys()
            return ('address' in keys and 'port' in keys)
        return False


class C2Resolver(BaseResolver):
    def __init__(self, contact_svc, log, file_svc, suffix=''):
        self.contact_svc = contact_svc
        self.log = log
        self.file_svc = file_svc
        self.suffix = '54ndc47.%s' % suffix
        self.transmissions = {}
        self.cache = ExpiringDict(max_len=100000, max_age_seconds=100)
        self.response_handler_lock = multiprocessing.Lock()
        pass

    async def handle_message(self, paw, req_type, data):
        """
        Handle requests depending on their request type.

        :param req_type: Request type
        :type req_type: int
        :param data: Request data
        :type data: dict
        :return: Return dictionary from message processing function
        :rtype: dict
        """
        data = json.loads(data)
        ret = None
        success = False
        if req_type == 1:
            success, ret = await self._get_instructions(data)
        elif req_type == 2:
            success, ret = await self._parse_results(data)
        elif req_type == 3:
            success, ret = await self._download_file(data)
        elif req_type == 4:
            success, ret = await self._upload_file(paw, data)
        else:
            success, ret = False, "Invalid request type"
        return success, ret

    async def resolve(self, request, handler):
        """
        Receives a parsed DNSRecord, determines the logic depending on the request name, and execute the corresponding logic
        required to process the data properly.
        """
        answers = []
        data = request.q.qname
        if data.matchSuffix('ping.%s' % self.suffix):
            # PING command
            answers.append(self._generate_rr(request.q.qname, 'A', "80.79.78.71"))
        elif data.matchSuffix(self.suffix):
            data = data.stripSuffix(self.suffix)  # 41414140.01.s.<paw>.
            data_arr = str(data).split('.')[:-1]  # [41414140, 01, s, <paw>]
            paw = data_arr.pop()  # [41414140, 01, s]  # Agent PAW
            command = data_arr.pop()  # [41414140, 01]

            if command == 's':
                req_type = int(data_arr.pop())  # [41414140]
                response = await self.start_transmission(paw, req_type)
                answers.append(self._generate_rr(request.q.qname, 'TXT', response))

            elif command == 'd':  # [length of transmission, req type, transmission id, ]
                # COMPLETE TRANSMISSION COMMAND
                tid = data_arr.pop()  # [length of transmission, command]
                req_type = int(data_arr.pop())  # [length of transmission]
                tid_cache_expected = int(data_arr.pop())  # []

                response = await self.finish_transmission(tid, req_type, tid_cache_expected)
                answers.append(self._generate_rr(request.q.qname, 'TXT', response))

            elif command == 'c':  # [base64 data, seq number, req type, transmission id, ]
                # APPEND TRANSMISSION DATA COMMAND
                tid = data_arr.pop()  # [base64 data, seq, req, ]
                req_type = int(data_arr.pop())  # [base64 data, seq, ]
                seq_num = int(data_arr.pop())  # [base64 data, ]
                data = data_arr.pop()

                try:
                    self.transmissions[tid].add_data(data, seq_num)
                    answers.append(self._generate_rr(request.q.qname, 'A', '41.41.41.41'))
                except KeyError:
                    self.log.warning('Client attempted to append data to a non-existent transmission')
                    reply = request.reply()
                    reply.header.rcode = RCODE.NXDOMAIN
                    return reply

            elif command == 'r':  # [seq number, req type, transmission id]
                # CHUNK TRANSMISSION RESPONSE RECEIVE
                tid = data_arr.pop()  # [seq num, req type]
                req_type = int(data_arr.pop())
                seq_num = int(data_arr.pop())

                if not len(self.transmissions[tid].response):
                    self.log.warning('Chunked response requested but transmission doesn\'t have a response')
                    reply = request.reply()
                    reply.header.rcode = RCODE.NXDOMAIN
                    return reply

                transmission_resp = self.transmissions[tid].response
                data = transmission_resp.popleft()
                answers.append(self._generate_rr(request.q.qname, 'TXT', data))

            elif command == 'rd':  # [req type, transmission id]
                # CHUNK TRANSMISSION COMPLETE COMMAND
                tid = data_arr.pop()
                del self.transmissions[tid]

                answers.append(self._generate_rr(request.q.qname, 'A', '41.41.41.41'))
            else:
                reply = request.reply()
                reply.header.rcode = RCODE.NXDOMAIN
                return reply
        return self._generate_response(request, answers)

    async def start_transmission(self, paw, req_type):
        """
        Instantiate a transmission object and return a DNS response indicating
        that the system is ready for data transfers.

        :param paw: Agent PAW
        :type paw: str
        :param req_type: Request type
        :type req_type: int
        :return: Returns JSON dictionary
        """
        tid = uuid.uuid4().hex[-8:]
        self.transmissions[tid] = C2Transmission(tid, paw, req_type)

        response = dict(success=True, tid=tid)
        return self.chunk_string(self.encode_string(json.dumps(response)))

    async def finish_transmission(self, tid, req_type, expected_length):
        """
        Finalize a transmission object and return any response data in the object.
        If there the response data is greater than 2 TXT strings in length, the
        response will be chunked to ensure that the DNS packet is below the max
        size.
        If the response data is less than 2 TXT strings, the response is returned
        and the object is deleted.
        If the transmission length does not match the length of the received data
        array, the function returns an error indicating a transmission mismatch.

        :param tid: Transmission ID
        :type tid: str
        :param req_type: Request Type
        :type req_type: int
        :param expected_length: Expected transmission length
        :type expected_length: int
        :return: Response data, chunked response message, or transmission error
        :rtype: list
        """
        transmission = self.transmissions.get(tid)

        if not transmission:
            response = dict(success=False, error='Attempted to end transmission that didn\'t exist')
            return self.chunk_string(self.encode_string(json.dumps(response)))

        if transmission.end(expected_length):
            data = self.decode_bytes(transmission.final_contents)
            success, result = await self.handle_message(transmission.paw, req_type, data)
            response = dict(success=success, data=result)
            response = self.chunk_string(self.encode_string(json.dumps(response)))
            if len(response) > 2:
                # data needs to be chunked due to DNS UDP packet size limitations
                self.transmissions[tid].response = deque(self.chunk_data_for_packets(response, 2))
                chunk_msg = dict(success=success, chunked=True, total_chunks=len(self.transmissions[tid].response))
                return self.chunk_string(self.encode_string(json.dumps(chunk_msg)))
            else:
                del self.transmissions[tid]
                return response
        else:
            response = dict(success=False, error='Transmission length mismatch')
            return self.chunk_string(self.encode_string(json.dumps(response)))

    @staticmethod
    def decode_bytes(s):
        """
        Receives a zlib compressed base64 string and returns the plaintext.

        :param s: Zlib compressed, base64 encoded string
        :type s: str
        :return: plaintext
        :rtype: str
        """
        return str(zlib.decompress(urlsafe_b64decode(s)).decode().replace('\n', ''))

    @staticmethod
    def decode_raw(s):
        """
        Receives a zlib compressed base64 string and returns raw bytes

        """
        return zlib.decompress(urlsafe_b64decode(s))

    @staticmethod
    def encode_string(s):
        """
        Receives a plaintext string, zlib compresses it, and encodes it into a base64 string.

        :param s: plaintext string
        :type s: str
        :return: Zlib compressed, base64 encoded string
        :rtype: str
        """
        if isinstance(s, str):
            s = s.encode()
        return str(urlsafe_b64encode(zlib.compress(s, 9)).decode())

    @staticmethod
    def chunk_string(s, n=150):
        """
        Takes a string and splits it into x chunks of n length. The default is 150 to safely account for DNS overhead.

        :param s: string
        :type s: str
        :param n: Number of characters per chunk
        :type n: int
        :return: Array of n-length chunks of original string
        :rtype: list
        """
        return [s[i:i+n] for i in range(0, len(s), n)]

    @staticmethod
    def chunk_data_for_packets(data, chunk_size):
        """
        Takes a list of string chunks and creates a list of `chunk_size` lists from the original data.

        :param data: list of string chunks
        :type data: list
        :param chunk_size: number of string chunks per data chunk
        :type chunk_size: int
        :return: List of `chunk_size` lists from original string chunk list.
        """
        ret = []
        while len(data) > 0:
            ret.append(data[:chunk_size])
            del data[:chunk_size]
        return ret

    """ PRIVATE """

    async def _get_instructions(self, data):
        agent = await self.contact_svc.handle_heartbeat(**data)
        instructions = await self.contact_svc.get_instructions(data['paw'])
        response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
        return True, response

    async def _parse_results(self, data):
        """
        Results command logic

        :param data: Client result data
        :return: Status of saving results
        """
        data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = await self.contact_svc.save_results(data['id'], data['output'], data['status'], data['pid'])

        return True, status

    async def _download_file(self, data):
        """
        Reads a file from `file_svc` and returns response to the client.

        :param data: Client file request data
        :return: Response with file payload that is zlib compressed and base64 encoded.
        """
        try:
            _, req_file, _ = await self.file_svc.get_file(data)
            req_file = self.encode_string(req_file)
            return True, req_file
        except FileNotFoundError as e:
            return False, str(e)

    async def _upload_file(self, paw, data):
        """
        Save file from client.

        :param data: Client save request `{"filename": "foo.bar", "contents": ""}`
        :return: Status of saving file
        """
        try:
            if 'filename' in data and 'contents' in data:
                target_dir = await self.file_svc.create_exfil_sub_directory(data.get('X-Request-ID', paw))
                contents = self.decode_raw(data['contents'])
                await self.file_svc.save_file(data['filename'], contents, target_dir)
                return True, dict()
        except Exception as e:
            return False, str(e)

    def _generate_rr(self, qname, rrtype, data):
        """
        Generates a DNS RR answer.

        :param qname: DNS query name
        :param rrtype: DNS query type
        :param data: Arbitary data to put into the record
        :return: DNS RR answer or None if rrtype is not accounted for
        :rtype: dnslib.RR or None
        """
        if rrtype == "TXT":
            return RR(rname=qname, rtype=QTYPE.TXT, rclass=CLASS.IN, ttl=0, rdata=TXT(data))
        elif rrtype == "A":
            return RR(rname=qname, rtype=QTYPE.A, rclass=CLASS.IN, ttl=1, rdata=A(data))
        else:
            return None

    def _generate_response(self, request, rrs):
        """
        Generates a reply to the request with any input RR answers.

        :param request: DNSRecord request
        :param rrs: Array of RR answers
        :return: DNSRecord DNS reply
        """
        resp = request.reply()
        if isinstance(rrs, list):
            for rr in rrs:
                resp.add_answer(rr)
        else:
            resp.add_answer(rrs)
        return resp


class UDPAsyncDNSHandler(asyncio.DatagramProtocol):
    """
    Handles UDP datagrams received by the socket and sends them for resolver processing.

    :param resolver: DNS resolver object
    :type resolver: C2Resolver
    """
    udplen = 0

    def __init__(self, resolver):
        """Constructor method
        """
        self.resolver = resolver

    def connection_made(self, transport):
        self.transport = transport

    async def dns_work(self, request, addr):
        """
        Process data with the resolver and generate a response
        for the client

        :param request: DNS request message
        :type request: dnslib.DNSRecord
        :param addr: Source address
        """
        reply = await self.resolver.resolve(request, self)
        rdata = reply.pack()
        if self.udplen and len(rdata) > self.udplen:
            truncated_reply = reply.truncate()
            rdata = truncated_reply.pack()

        self.transport.sendto(rdata, addr)

    def datagram_received(self, data, addr):
        """
        Process a datagram received from the UDP socket

        :param data: Raw data from the datagram endpoint
        :type data: bytes
        :param addr: Source address
        :type addr: bytes
        """
        request = DNSRecord.parse(data)
        asyncio.create_task(self.dns_work(request, addr))


class C2Transmission(object):
    """
    C2Transmission
    Maintains the state of an existing transmission communications.

    :param id: Transmission ID
    :type id: str
    """

    def __init__(self, id, paw, req_type):
        """Constructor Method
        """
        self.id = id
        self.data = dict()
        self.paw = paw
        self.req_type = req_type
        self.final_contents = ""
        self.response = None

    def add_data(self, data, idx):
        """
        Adds data to an existing transmission if the indexed chunk does not already exist in the transmission.
        """
        if idx not in self.data:
            self.data[idx] = data

    def end(self, final_length):
        """
        Finalizes an existing transmission and concatenates all the data into the final contents.

        Returns successfully if all sequential chunks up to `final_length` are present.
        """
        if all(k in self.data for k in range(final_length)):
            for i in range(final_length):
                self.final_contents += self.data[i]
            return True
        else:
            return False
