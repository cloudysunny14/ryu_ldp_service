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

from ryu.lib.packet.ldp import LDPHello
from ryu.lib.packet.ldp import CommonHelloParameter
from ryu.lib.packet.ldp import IPv4TransportAddress
from ryu.services.protocols.ldp.event import EventHelloReceived
from ryu.services.protocols.ldp.ldp_util import EventletIOFactory

#TODO: separete common static value
ALL_ROUTERS = '224.0.0.2'
LDP_DISCOVERY_PORT = 646

class LDPInterface(object):

    def __init__(self, app, discovery_server, config):
        self.discovery_server =  discovery_server
        self.app = app
        self.state = None
        self.config = config
        self.hello_msg = self._generate_hello_msg(config)
        self._hello_timer = EventletIOFactory.create_looping_call(self.send_hello)

    def _generate_hello_msg(self, config):
        router_id = config.router_id
        hold_time = config.hold_time
        tlvs = [CommonHelloParameter(hold_time=hold_time,
                t_bit=0, r_bit=0),
                IPv4TransportAddress(addr=router_id)]
        msg = LDPHello(router_id=router_id, msg_id=0,
                tlvs=tlvs)
        return msg

    def start(self):
        self.discovery_server.start(self._recv_handler)
        self._hello_timer.start(self.config.hold_time/3)

    def _recv_handler(self, packet, addr):
        ev = EventHelloReceived(self, packet)
        self.app.send_event(self.app.name, ev)

    def send_hello(self):
        self.discovery_server.sendto(self.hello_msg.serialize(),
                (ALL_ROUTERS, LDP_DISCOVERY_PORT))
