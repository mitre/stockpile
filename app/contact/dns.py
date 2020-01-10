import asyncio
import json
import zlib
import uuid
import multiprocessing

from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
from expiringdict import ExpiringDict

from dnslib import DNSRecord, RR, QTYPE, RCODE, CLASS, TXT, A
from dnslib.server import DNSServer, BaseResolver

from app.interfaces.c2_passive_interface import C2Passive


class UDPAsyncDNSHandler(object):
    udplen = 0

    def __init__(self, resolver):
        self.loop = asyncio.get_event_loop()
        self.protocol = None
        self.resolver = resolver

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.protocol = "udp"
        request = DNSRecord.parse(data)
        reply = asyncio.create_task(self.resolver.resolve(request, self))
        asyncio.wait_for(reply, 10)

        rdata = reply.result().pack()
        if self.udplen and len(rdata) > self.udplen:
            truncated_reply = reply.truncate()
            rdata = truncated_reply.pack()

        self.transport.sendto(rdata, addr)
        print(reply)


class C2Transmission(object):
    def __init__(self, id):
        self.id = id
        self.data = dict()
        self.final_contents = ""
        self.response = []

    def add_data(self, data, idx):
        if idx not in self.data:
            self.data[idx] = data

    def end(self, final_length):
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

    def handle_message(self, req_type, data):
        data = json.loads(data)
        ret = None
        if req_type == 1:
            print(data)
            ret = self._get_instructions(data)
        elif req_type == 2:
            ret = self._parse_results(data)
        else:
            ret = dict(success=False, error='Invalid request type')
        return ret

    async def resolve(self, request, handler):
        data = request.q.qname
        print(data)
        if data.matchSuffix('ping.%s' % self.suffix):
            return self._ping(request)
        elif data.matchSuffix(self.suffix):
            data = data.stripSuffix(self.suffix)  # 41414140.01.s.<paw>.
            data_arr = str(data).split('.')[:-1]  # [41414140, 01, s, <paw>]

            paw = data_arr.pop()  # [41414140, 01, s]
            command = data_arr.pop()  # [41414140, 01]
            if command == 's':  # [41414140]
                tid = uuid.uuid4().hex[-8:]
                self.transmissions[tid] = C2Transmission(tid)
                # generate response with TXT record and transmission ID
                response = dict(success=True, tid=tid)
                response = self.chunk_string(self.encode_string(json.dumps(response)))
                return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', response))

            elif command == 'd':  # [length of transmission, req type, transmission id, ]
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
                    result = self.handle_message(req_type, data)

                    response = dict(success=True, data=result)
                    response = self.chunk_string(self.encode_string(json.dumps(response)))
                    if len(response) > 2:
                        # data needs to be chunked
                        self.transmissions[tid].response = self.chunk_data_for_packets(response, 2)
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

                # generate response with TXT and instructions
            elif command == 'c':  # [base64 data, seq number, req type, transmission id, ]
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
                data = transmission_resp.pop(0)

                return self._generate_response(request, self._generate_rr(request.q.qname, 'TXT', data))

            elif command == 'rd':  # [req type, transmission id]
                tid = data_arr.pop()
                del self.transmissions[tid]

                return self._generate_response(request, self._generate_rr(request.q.qname, 'A', '41.41.41.41'))
            else:
                reply = request.reply()
                reply.header.rcode = RCODE.NXDOMAIN
                return reply

    """ PRIVATE """

    def _ping(self, request):
        return self._generate_response(request, self._generate_rr(request.q.qname, 'A', "80.79.78.71"))

    async def _get_instructions(self, data):
        agent = await self.contact_svc.handle_heartbeat(**data)
        instructions = await self.contact_svc.get_instructions(data['paw'])
        response = dict(sleep=await agent.calculate_sleep(), instructions=instructions)
        return response

    async def _parse_results(self, data):
        data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = await self.contact_svc.save_results(data['id'], data['output'], data['status'], data['pid'])

        return status

    def _parse_data(self, qname):
        json_str = self.contact_svc.decode_bytes(str(qname))
        try:
            return json.loads(json_str)
        except ValueError:
            return None

    def _generate_rr(self, qname, rrtype, data):
        if rrtype == "TXT":
            return RR(rname=qname, rtype=QTYPE.TXT, rclass=CLASS.IN, ttl=0, rdata=TXT(data))
        elif rrtype == "A":
            return RR(rname=qname, rtype=QTYPE.A, rclass=CLASS.IN, ttl=1, rdata=A(data))
        else:
            return None

    def _generate_response(self, request, rrs):
        resp = request.reply()
        print(type(resp))
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
        try:
            await asyncio.sleep(3600)
        finally:
            transport.close()

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
