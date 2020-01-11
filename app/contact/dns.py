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
from dnslib.server import DNSServer, BaseResolver

from app.interfaces.c2_passive_interface import C2Passive


class UDPAsyncDNSHandler(asyncio.DatagramProtocol):
    udplen = 0

    def __init__(self, resolver):
        self.loop = asyncio.get_event_loop()
        self.protocol = None
        self.resolver = resolver

    def connection_made(self, transport):
        self.transport = transport

    async def dns_work(self, request, addr):
        """
        Process data with the resolver and generate a response
        for the client
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
        """
        self.protocol = "udp"
        request = DNSRecord.parse(data)
        asyncio.create_task(self.dns_work(request, addr))


class C2Transmission(object):
    """
    C2Transmission

    Maintains the state of an existing transmission communications.
    """

    def __init__(self, id):
        self.id = id
        self.data = dict()
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


class C2Resolver(BaseResolver):
    def __init__(self, contact_svc, suffix=''):
        self.contact_svc = contact_svc
        self.suffix = '54ndc47.%s' % suffix
        self.transmissions = {}
        self.cache = ExpiringDict(max_len=100000, max_age_seconds=100)
        self.response_handler_lock = multiprocessing.Lock()
        pass

    @staticmethod
    def decode_bytes(s):
        return str(zlib.decompress(urlsafe_b64decode(s)).decode().replace('\n', ''))

    @staticmethod
    def encode_string(s):
        return str(urlsafe_b64encode(zlib.compress(s.encode(), 9)).decode())

    @staticmethod
    def chunk_string(s, n=150):
        return [s[i:i+n] for i in range(0, len(s), n)]

    @staticmethod
    def chunk_data_for_packets(data, chunk_size):
        ret = []
        while len(data) > 0:
            ret.append(data[:chunk_size])
            del data[:chunk_size]
        return ret

    async def handle_message(self, req_type, data):
        data = json.loads(data)
        ret = None
        if req_type == 1:
            ret = await self._get_instructions(data)
        elif req_type == 2:
            ret = await self._parse_results(data)
        else:
            ret = dict(success=False, error='Invalid request type')
        return ret

    async def resolve(self, request, handler):
        """
        Receives a parsed DNSRecord, determines the logic depending on the request name, and execute the corresponding logic
        required to process the data properly.
        """
        data = request.q.qname
        if data.matchSuffix('ping.%s' % self.suffix):
            # PING command
            return self._generate_response(request, self._generate_rr(request.q.qname, 'A', "80.79.78.71"))
        elif data.matchSuffix(self.suffix):
            data = data.stripSuffix(self.suffix)  # 41414140.01.s.<paw>.
            data_arr = str(data).split('.')[:-1]  # [41414140, 01, s, <paw>]

            paw = data_arr.pop()  # [41414140, 01, s]
            command = data_arr.pop()  # [41414140, 01]
            if command == 's':  # [41414140]
                # START TRANSMISSION COMMAND
                tid = uuid.uuid4().hex[-8:]
                self.transmissions[tid] = C2Transmission(tid)
                # generate response with TXT record and transmission ID
                response = dict(success=True, tid=tid)
                response = self.chunk_string(self.encode_string(json.dumps(response)))
                return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', response))

            elif command == 'd':  # [length of transmission, req type, transmission id, ]
                # COMPLETE TRANSMISSION COMMAND
                tid = data_arr.pop()  # [length of transmission, command]
                transmission = self.transmissions.get(tid)

                if not transmission:
                    response = dict(success=False, error='Attempted to end transmission that didn\'t exist')
                    response = self.chunk_string(self.encode_string(json.dumps(response)))
                    return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', response))

                req_type = int(data_arr.pop())  # [length of transmission]
                tid_cache_expected = int(data_arr.pop())  # []

                if transmission.end(tid_cache_expected):
                    data = self.decode_bytes(transmission.final_contents)
                    result = await self.handle_message(req_type, data)

                    response = dict(success=True, data=result)
                    response = self.chunk_string(self.encode_string(json.dumps(response)))
                    if len(response) > 2:
                        # data needs to be chunked
                        self.transmissions[tid].response = deque(self.chunk_data_for_packets(response, 2))
                        print(self.transmissions[tid].response)
                        chunk_msg = dict(success=True, chunked=True, total_chunks=len(self.transmissions[tid].response))
                        chunk_msg = self.chunk_string(self.encode_string(json.dumps(chunk_msg)))
                        return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', chunk_msg))
                    else:
                        del self.transmissions[tid]
                        return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', response))
                else:
                    response = dict(success=False, error='Transmission length mismatch')
                    response = self.chunk_string(self.encode_string(json.dumps(response)))
                    return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', response))

            elif command == 'c':  # [base64 data, seq number, req type, transmission id, ]
                # APPEND TRANSMISSION DATA COMMAND
                tid = data_arr.pop()  # [base64 data, seq, req, ]
                req_type = int(data_arr.pop())  # [base64 data, seq, ]
                seq_num = int(data_arr.pop())  # [base64 data, ]
                data = data_arr.pop()

                try:
                    self.transmissions[tid].add_data(data, seq_num)
                    return self._generate_response(request, self._generate_rr(request.q.qname, 'A', '41.41.41.41'))
                except KeyError:
                    # tried to add data to nonexistent transmission
                    return self._generate_response(request, self._generate_rr(request.q.qname, 'A', '255.255.255.255'))

            elif command == 'r':  # [seq number, req type, transmission id]
                # CHUNK TRANSMISSION RESPONSE RECEIVE
                tid = data_arr.pop()  # [seq num, req type]
                req_type = int(data_arr.pop())
                seq_num = int(data_arr.pop())
                print("r data %s" % self.transmissions[tid].response)
                print("seq num %d, len %d" % (seq_num, len(self.transmissions[tid].response)))

                if not len(self.transmissions[tid].response):
                    reply = request.reply()
                    reply.header.rcode = RCODE.NXDOMAIN
                    return reply

                transmission_resp = self.transmissions[tid].response
                data = transmission_resp.popleft()

                return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', data))

            elif command == 'rd':  # [req type, transmission id]
                # CHUNK TRANSMISSION COMPLETE COMMAND
                tid = data_arr.pop()
                del self.transmissions[tid]

                return self._generate_response(request, self._generate_rr(request.q.qname, 'A', '41.41.41.41'))
            else:
                reply = request.reply()
                reply.header.rcode = RCODE.NXDOMAIN
                return reply

    """ PRIVATE """

    async def _get_instructions(self, data):
        agent = await self.contact_svc.handle_heartbeat(**data)
        instructions = await self.contact_svc.get_instructions(data['paw'])
        response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
        return response

    async def _parse_results(self, data):
        """
        Results command logic

        :param: data Client result data
        :return: Status of saving results
        """
        data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = await self.contact_svc.save_results(data['id'], data['output'], data['status'], data['pid'])

        return status

    def _generate_rr(self, qname, rrtype, data):
        """
        Generates a DNS RR answer.

        :param: qname DNS query name
        :param: rrtype DNS query type
        :param: data Arbitary data to put into the record
        :return: dnslib.RR DNS RR answer
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

        :param: request DNSRecord request
        :param: rrs Array of RR answers
        :return: DNSRecord DNS reply
        """
        resp = request.reply()
        if isinstance(rrs, list):
            for rr in rrs:
                resp.add_answer(rr)
        else:
            resp.add_answer(rrs)
        return resp


class DNS(C2Passive):

    def __init__(self, services, config):
        super().__init__(config=config)
        self.contact_svc = services.get('contact_svc')
        self.resolver = C2Resolver(self.contact_svc, '')
        self.udp_server = DNSServer(self.resolver, port=5353)

    async def start(self):
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPAsyncDNSHandler(self.resolver),
            local_addr=('127.0.0.1', 5353)
        )

    def valid_config(self):
        return True

    """ PRIVATE """

    async def _start_dns_server(self):
        pass

    async def _ping(self, request):
        pass

    async def _instructions(self, request):
        pass

    async def _results(self, request):
        pass
