import struct
import socket
import random


class FakeSwitch(object):
    HEADER_FORMAT = '!BBHI'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    OF_HELLO = 0

    def __init__(self, controller, port=6633, dpid=None):
        if dpid:
            self.dpid = dpid
        else:
            self.dpid = random.randrange(1<<64)

        self.sock = socket.socket()
        self.sock.connect((controller, port))

        self.send_hello()
        self.recv_loop()

    def send_packet(self, of_type, payload):
        version = 1
        tid = 0

        length = self.HEADER_SIZE + len(payload)
        message = struct.pack(self.HEADER_FORMAT, version, of_type, length, tid)
        message += payload

        self.sock.send(message)

    def recv_loop(self):
        while 1:
            header = self.sock.recv(self.HEADER_SIZE)
            version, type_, length, tid = struct.unpack(
                self.HEADER_FORMAT, header)
            payload = self.sock.recv(length - self.HEADER_SIZE)

            # TODO: do something

    def send_hello(self):
        self.send_packet(self.OF_HELLO, '')
