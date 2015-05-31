# Copyright (C) 2013,2014 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2013,2014 YAMAMOTO Takashi <yamamoto at valinux co jp>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from time import time
from nose.tools import eq_
from ryu.lib.packet import lsp_ping 


class Test_lsp_ping(unittest.TestCase):
    """ Test case for ryu.lib.packet.lsp_ping
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_mpls_echo_request_ipv4pre(self):
        sub_tlvs = [lsp_ping.IPv4PrefixTLV(prefix='1.1.1.1', prefix_len=32)]
        tlvs = [lsp_ping.TargetFecStack(sub_tlvs=sub_tlvs)]
        msg = lsp_ping.MPLSEcho(type=lsp_ping.MPLS_ECHO_REQUEST,
            reply_mode=lsp_ping.MPLS_REPLY_MODE_UDP_PACKET,
            senders_handle=1, sequence_num=1, timestamp_sent=time(), tlvs=tlvs)
        binmsg = msg.serialize()
        msg2, rest = lsp_ping.MPLSEcho.parser(binmsg)
        eq_(str(msg), str(msg2))
        eq_(rest, '')


