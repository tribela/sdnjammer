import logging
import random
import socket
import struct


class FakeSwitch(object):
    HEADER_FORMAT = '!BBHI'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    OF_HELLO = 0
    OF_ECHO_REQUEST = 2
    OF_ECHO_REPLY = 3
    OF_FEATUERS_REQUEST = 5
    OF_FEATURES_REPLY = 6

    def __init__(self, controller, port=6633, dpid=None):
        if dpid:
            self.dpid = dpid
        else:
            self.dpid = random.randrange(1 << 64)

        self.controller = controller
        self.port = port

        self.connected = False
        self.registered = False

    def connect(self):
        if not self.connected:
            self.sock = socket.socket()
            self.sock.connect((self.controller, self.port))

    def close(self):
        self.sock.close()

    def start(self):
        self.register()
        while 1:
            self.proc_step()

    def register(self):
        self.connect()
        self.send_hello()
        while not self.registered:
            self.proc_step()

    def send_packet(self, of_type, tid=0, payload=''):
        version = 1
        tid = 0

        length = self.HEADER_SIZE + len(payload)
        message = struct.pack(self.HEADER_FORMAT,
                              version, of_type, length, tid)
        message += payload

        self.sock.send(message)

    def proc_step(self):
        header = self.sock.recv(self.HEADER_SIZE)
        version, type_, length, tid = struct.unpack(
            self.HEADER_FORMAT, header)

        more_bytes = length - self.HEADER_SIZE
        if more_bytes:
            payload = self.sock.recv(more_bytes)
        else:
            payload = ''

        if type_ == self.OF_HELLO:
            logging.debug('HELLO!')
        elif type_ == self.OF_ECHO_REPLY:
            logging.debug('Echo reply: {0}'.format(payload))
        elif type_ == self.OF_FEATUERS_REQUEST:
            self.send_features_reply(tid, payload)
        else:
            logging.warning('Unknown type: {0}, payload: {1}'.format(
                type_, payload.encode('hex')))

    def send_hello(self):
        self.send_packet(self.OF_HELLO)

    def send_echo_request(self, data):
        self.send_packet(self.OF_ECHO_REQUEST, payload=data)

    def send_features_reply(self, tid, params):
        payload_format = '!QIBxxxII'

        buffer_size = 255
        number_of_tables = 0
        sw_capablity_flags = 0x00000000
        action_capablity_flags = 0x00000000

        payload = struct.pack(
            payload_format,
            self.dpid, buffer_size, number_of_tables,
            sw_capablity_flags, action_capablity_flags)

        self.send_packet(self.OF_FEATURES_REPLY, tid, payload)
        self.registered = True


def by_connection_reset(host, port, count):
    for i in xrange(count):
        dpid = i + 1
        sw = FakeSwitch(host, port, dpid=dpid)
        sw.connect()
        sw.send_hello()
        sw.send_features_reply(0, '')


def by_duplicated_dpid(host, port, count):
    switches = []
    for i in range(count):
        dpid = i + 1
        sw = FakeSwitch(host, port, dpid=dpid)
        sw.connect()
        sw.register()
        switches.append(sw)

    for sw in switches:
        sw.close()
