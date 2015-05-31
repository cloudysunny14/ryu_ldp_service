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

import unittest
from nose.tools import eq_
from nose.tools import ok_

from ryu.lib.packet import ldp
from ryu.lib.packet import afi
from ryu.lib.packet import safi


class Test_ldp(unittest.TestCase):
    """ Test case for ryu.lib.packet.bgp
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_hello(self):
        tlvs = [ldp.CommonHelloParameter(hold_time = 15, t_bit = 0,
                r_bit = 0), ldp.IPv4TransportAddress(addr='1.1.1.1')]
        msg = ldp.LDPHello(router_id = '1.1.1.1', msg_id = 0, tlvs = tlvs)
        binmsg = msg.serialize()
        msg2, rest = ldp.LDPMessage.parser(binmsg)
        eq_(str(msg), str(msg2))
        eq_(rest, '')

    def test_init(self):
        tlvs = [ldp.CommonSessionParameters(proto_ver=1, keepalive_time=15,
                pvlim=0, max_pdu_len=0, receiver_lsr_id='2.2.2.2',
                receiver_label_space_id=0, a_bit=0, d_bit=0)]
        msg = ldp.LDPInit(router_id = '1.1.1.1', msg_id = 0, tlvs = tlvs)
        binmsg = msg.serialize()
        msg2, rest = ldp.LDPMessage.parser(binmsg)
        eq_(str(msg), str(msg2))
        eq_(rest, '')

    def test_keepalive(self):
        msg = ldp.LDPKeepAlive(router_id='1.1.1.1', msg_id = 1, tlvs=[])
        binmsg = msg.serialize()
        msg2, rest = ldp.LDPMessage.parser(binmsg)
        eq_(str(msg), str(msg2))
        eq_(rest, '')

    def test_address_message(self):
        addrs= ['1.1.1.1', '2.2.2.2', '3.3.3.3']
        address_list = ldp.AddressList(address_family=1, addresses=addrs)
        msg = ldp.LDPAddress(router_id='1.1.1.1',msg_id = 2, tlvs=[address_list])
        binmsg = msg.serialize()
        msg2, rest = ldp.LDPMessage.parser(binmsg)
        eq_(str(msg), str(msg2))
        eq_(rest, '')

    def test_label_mapping(self):
        fec_elements = [ldp.PrefixFecElement(address_type=1, element_len=32, prefix='2.2.2.2')]
        tlvs = [ldp.Fec(fec_elements=fec_elements), ldp.GenericLabel(label=1000)]
        msg = ldp.LDPLabelMapping(router_id='1.1.1.1',msg_id = 2, tlvs=tlvs)
        binmsg = msg.serialize()
        print ''.join('{:02x}'.format(x) for x in binmsg)
        msg2, rest = ldp.LDPMessage.parser(binmsg)
        print msg2
        eq_(str(msg), str(msg2))
        eq_(rest, '')

    def test_sequencial_message(self):
        addrs= ['1.1.1.1', '2.2.2.2', '3.3.3.3']
        address_list = ldp.AddressList(address_family=1, addresses=addrs)
        msg = ldp.LDPAddress(router_id='1.1.1.1',msg_id = 2, tlvs=[address_list])
        binmsg = msg.serialize()
        print ''.join('{:02x}'.format(x) for x in binmsg)
        fec_elements = [ldp.PrefixFecElement(address_type=1, element_len=32, prefix='2.2.2.2')]
        tlvs = [ldp.Fec(fec_elements=fec_elements), ldp.GenericLabel(label=1000)]
        msg2 = ldp.LDPLabelMapping(router_id='1.1.1.1',msg_id = 2, tlvs=tlvs)
        binmsg = binmsg + msg2.serialize(include_header=False)
        print ''.join('{:02x}'.format(x) for x in binmsg)
        msg3, rest = ldp.LDPMessage.parser(binmsg)
        eq_(str(msg), str(msg3))
        print ''.join('{:02x}'.format(x) for x in rest)
        msg4, rest = ldp.LDPMessage.parser(rest, include_header=False)
        eq_(str(msg2), str(msg4))
        eq_(rest, '')

    def test_notification(self):
        tlvs = [ldp.Status(u_bit=0, f_bit=0, status_code=ldp.LDP_STATUS_HOLD_TIMER_EXPIRED, message_id=1, message_type=0)]
        msg = ldp.LDPNotification(router_id='1.1.1.1',msg_id = 2, tlvs=tlvs)
        binmsg = msg.serialize()
        msg2, rest = ldp.LDPMessage.parser(binmsg)
        eq_(str(msg), str(msg2))
        eq_(rest, '')

