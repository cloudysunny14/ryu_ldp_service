# Copyright (C) 2014 Kiyonari Harigae <lakshmi at cloudysunny14 org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import logging
import traceback
import struct
import abc
import six
from eventlet import semaphore
from ryu.lib import hub
from ryu.services.protocols.ldp import event as ldp_event
from ryu.services.protocols.ldp.ldp_util import EventletIOFactory

from ryu.lib.packet import ldp
from ryu.lib.packet.ldp import LDPMessage
LOG = logging.getLogger('ldp.Peer')

LDP_MIN_MSG_LEN = 10

@six.add_metaclass(abc.ABCMeta)
class LDPState(object):
    def __init__(self, peer):
        super(LDPState, self).__init__()
        self.peer = peer

    @abc.abstractmethod
    def action(self):
        pass

    @abc.abstractmethod
    def new_state(self):
        pass

    @abc.abstractmethod
    def state(self):
        pass

class LDPStateNonExistent(LDPState):
    def action(self):
        pass

    def new_state(self):
        return ldp_event.LDP_STATE_INITIAL

    def state(self):
        return ldp_event.LDP_STATE_NON_EXISTENT

class LDPActiveStateInitial(LDPState):
    def action(self):
        self.peer.send_init()

    def new_state(self):
        return ldp_event.LDP_STATE_OPEN_SENT

    def state(self):
        return ldp_event.LDP_STATE_INITIAL

class LDPPassiveStateInitial(LDPState):
    def action(self):
        pass

    def new_state(self):
        return ldp_event.LDP_STATE_OPEN_REC

    def state(self):
        return ldp_event.LDP_STATE_INITIAL

class LDPStateOpenSent(LDPState):
    def action(self):
        self.peer.send_keepalive()
        self.peer.start_keepalive_timeout()

    def new_state(self):
        return ldp_event.LDP_STATE_OPERATIONAL

    def state(self):
        return ldp_event.LDP_STATE_OPEN_SENT

class LDPStateOpenRec(LDPState):
    def action(self):
        self.peer.send_init()
        self.peer.send_keepalive()
        self.peer.start_keepalive_timeout()
        pass

    def new_state(self):
        return ldp_event.LDP_STATE_OPERATIONAL

    def state(self):
        return ldp_event.LDP_STATE_OPEN_REC

class LDPStateOperational(LDPState):
    def action(self):
        pass

    def new_state(self):
        return ldp_event.LDP_STATE_NON_EXISTENT

    def state(self):
        return ldp_event.LDP_STATE_OPERATIONAL

class Peer(object):
    @staticmethod
    def _instance_name(router_id, label_space_id):
        return 'lsr-%s:%s' % (router_id, label_space_id)

    _ACTIVE_STATE_MAP = {
        ldp_event.LDP_STATE_NON_EXISTENT: LDPStateNonExistent,
        ldp_event.LDP_STATE_INITIAL: LDPActiveStateInitial,
        ldp_event.LDP_STATE_OPEN_SENT: LDPStateOpenSent,
        ldp_event.LDP_STATE_OPEN_REC: LDPStateOpenRec,
        ldp_event.LDP_STATE_OPERATIONAL: LDPStateOperational,
    }
    _PASSIVE_STATE_MAP = {
        ldp_event.LDP_STATE_NON_EXISTENT: LDPStateNonExistent,
        ldp_event.LDP_STATE_INITIAL: LDPPassiveStateInitial,
        ldp_event.LDP_STATE_OPEN_REC: LDPStateOpenRec,
        ldp_event.LDP_STATE_OPERATIONAL: LDPStateOperational
    }

    def __init__(self, app, peer_router_id, trans_addr, conf):
        self._app = app
        self.peer_router_id = peer_router_id
        self.trans_addr = trans_addr
        self.state = ldp_event.LDP_STATE_NON_EXISTENT
        self.name = self._instance_name(peer_router_id, 0)
        self._conf = conf
        self._socket = None
        self._recv_buff = ''
        self._state_map = {}
        self._state_instance = None
        self._send_lock = semaphore.Semaphore()
        self._keepalive_send_timer = \
            EventletIOFactory.create_looping_call(self._send_keepalive)
        self._keepalive_timeout_timer = \
            EventletIOFactory.create_looping_call(self.keepalive_timeout)
        self._keepalive_time = 0
        self._msg_id = 0

    def send_event_to_observers(self, ev):
        self._app.send_event_to_observers(ev)

    def conn_handle(self, socket, is_active):
        if is_active:
            self._state_map = self._ACTIVE_STATE_MAP
        else:
            self._state_map = self._PASSIVE_STATE_MAP
        self._socket = socket
        self.state_change(ldp_event.LDP_STATE_INITIAL)
        hub.spawn(self._recv_loop)

    def send_init(self):
        keepalive_time = self._conf.keep_alive
        # TODO: params are to be configurable
        tlvs = [ldp.CommonSessionParameters(proto_ver=1, keepalive_time=keepalive_time,
                pvlim=0, max_pdu_len=0, receiver_lsr_id=self.peer_router_id,
                receiver_label_space_id=0, a_bit=0, d_bit=0)]
        msg = ldp.LDPInit(router_id = self._conf.router_id, msg_id = self._msg_id,
            tlvs = tlvs)
        self.send_msg(msg)

    def send_keepalive(self):
        self._keepalive_send_timer.start(self._keepalive_time / 3)

    def _send_keepalive(self):
        msg = ldp.LDPKeepAlive(router_id=self._conf.router_id, msg_id = self._msg_id,
            tlvs=[])
        self.send_msg(msg)

    def keepalive_timeout(self):
        print 'timeout'

    def reset_hold_timer(self):
        pass
        #self._hello_timer.reset()

    def start_keepalive_timeout(self):
        self._keepalive_timeout_timer.start(self._keepalive_time, now=False)

    def state_change(self, new_state):
        if self.state == new_state:
            return
        old_state = self.state
        self.state = new_state
        self.state_impl = self._state_map[new_state](self)
        state_changed = ldp_event.EventLDPStateChanged(
            self.name, self, old_state, new_state)
        self.send_event_to_observers(state_changed)
        self.state_impl.action()

    def _recv_loop(self):
        required_len = LDP_MIN_MSG_LEN
        conn_lost_reason = "Connection lost as protocol is no longer active"
        try:
            while True:
                next_bytes = self._socket.recv(required_len)
                if len(next_bytes) == 0:
                    print 'peer closed'
                    conn_lost_reason = 'Peer closed connection'
                    break
                self.data_received(next_bytes)
        except socket.error as err:
            conn_lost_reason = 'Connection to peer lost: %s.' % err
        except ldp.LdpExc as ex:
            conn_lost_reason = 'Connection to peer lost, reason: %s.' % ex
        except Exception as e:
            LOG.debug(traceback.format_exc())
            conn_lost_reason = str(e)
        finally:
            self.connection_lost(conn_lost_reason)

    def data_received(self, next_bytes):
        try:
            self._data_received(next_bytes)
        except ldp.LdpExc as exc:
            if exc.SEND_ERROR:
                self.send_notification(exc.CODE, exc.SUB_CODE)
            else:
                self._socket.close()
            raise exc

    def _data_received(self, next_bytes):
        # Append buffer with received bytes.
        self._recv_buff += next_bytes

        while True:
            if len(self._recv_buff) < LDP_MIN_MSG_LEN:
                return
            version, pdu_len, router_id, label_space_id \
                = Peer.parse_msg_header(
                    self._recv_buff[:LDP_MIN_MSG_LEN])
            # RFC
            buf_len = len(self._recv_buff) - 4
            if buf_len < pdu_len:
                return
            #TODO: t
            try:
                include_header = (pdu_len > LDP_MIN_MSG_LEN)
                while True:
                    msg, rest = LDPMessage.parser(self._recv_buff, include_header)
                    self._handle_msg(msg)
                    self._recv_buff = rest
                    if len(rest) <= LDP_MIN_MSG_LEN: break
                    include_header = False
                # If we have a valid bgp message we call message handler.
            except KeyError:
                return

    def _handle_msg(self, msg):
        msg_type = msg.type
        # state change by msg type
        # if initial recv, call then and current state change call
        state_change = True
        if msg_type == ldp.LDP_MSG_INIT:
            if self.state != ldp_event.LDP_STATE_INITIAL:
                # TODO: Notify
                pass
            self._handle_init(msg)
        elif msg_type == ldp.LDP_MSG_KEEPALIVE:
            if self.state == ldp_event.LDP_STATE_OPERATIONAL:
                state_change = False
            elif self.state != ldp_event.LDP_STATE_OPEN_REC:
                # TODO: Notiy
                pass
        elif msg_type == ldp.LDP_MSG_NOTIFICATION:
            if self.state != ldp_event.LDP_STATE_OPERATIONAL:
                #TODO: Notify
                pass
        else:
            state_change = False

        if state_change:
            new_state = self.state_impl.new_state()
            self.state_change(new_state)
        else:
            msg_recv = ldp_event.EventLDPMessageReceived(
                self.name, msg)
            self.send_event_to_observers(msg_recv)

    def _handle_init(self, msg):
        tlv = LDPMessage.retrive_tlv(ldp.LDP_TLV_COMMON_SESSION_PARAMETERS, msg)
        if self._conf.keep_alive < tlv.keepalive_time:
            self._keepalive_time = self._conf.keepalive
        else:
            self._keepalive_time = tlv.keepalive_time

    @staticmethod
    def parse_msg_header(buff):
        return struct.unpack('!HH4sH', buff)

    def send_msg(self, msg):
        self._msg_id += 1
        self._send_with_lock(msg)

    def _send_with_lock(self, msg):
        self._send_lock.acquire()
        try:
            self._socket.sendall(msg.serialize())
        finally:
            self._send_lock.release()

    def connection_lost(self, reason):
        """Stops all timers and notifies peer that connection is lost.
        """
