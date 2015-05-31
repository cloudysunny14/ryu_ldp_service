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

"""
sample router manager.
(un-)instantiate routers
Usage example:
PYTHONPATH=. ./bin/ryu-manager --verbose \
             ryu.services.protocols.vrrp.manager \
             ryu.services.protocols.vrrp.dumper \
             ryu.services.protocols.vrrp.sample_manager
"""
from ryu.lib import hub
from ryu.base import app_manager
from ryu.services.protocols.ldp import ldp_api
from ryu.services.protocols.ldp import event as ldp_event

class SampleManager(app_manager.RyuApp):

    def __init__(self, *args, **kwargs):
        super(SampleManager, self).__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs

        self._instances = {}

    def start(self):
        hub.spawn(self._main)

    def _main(self):
        interface = ldp_event.LDPInterfaceConf(
            primary_ip_address='10.1.1.1', device_name='eth0')
        config = ldp_event.LDPConfig(router_id='1.1.1.1',
            ldp_port=646)
        ldp_api.ldp_config(self, interface, config)

