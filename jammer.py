import struct
import socket
import random
import logging


class FakeSwitch(object):
    HEADER_FORMAT = '!BBHI'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    OF_HELLO = 0
    OF_FEATUERS_REQUEST = 5
    OF_FEATURES_REPLY = 6

    def __init__(self, controller, port=6633, dpid=None):
        if dpid:
            self.dpid = dpid
        else:
            self.dpid = random.randrange(1<<64)

        self.sock = socket.socket()
        self.sock.connect((controller, port))

    def send_packet(self, of_type, tid=0, payload=''):
        version = 1
        tid = 0

        length = self.HEADER_SIZE + len(payload)
        message = struct.pack(self.HEADER_FORMAT, version, of_type, length, tid)
        message += payload

        self.sock.send(message)

    def start(self):
        self.send_hello()
        while 1:
            self.proc_step()

    def proc_step(self):
        header = self.sock.recv(self.HEADER_SIZE)
        version, type_, length, tid = struct.unpack(
            self.HEADER_FORMAT, header)
        payload = self.sock.recv(length - self.HEADER_SIZE)

        if type_ == self.OF_HELLO:
            pass
        elif type_ == self.OF_FEATUERS_REQUEST:
            self.send_features_reply(tid, payload)
        else:
            logging.warning('Unknown type: {0}'.format(type_))

    def send_hello(self):
        self.send_packet(self.OF_HELLO, '')

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
