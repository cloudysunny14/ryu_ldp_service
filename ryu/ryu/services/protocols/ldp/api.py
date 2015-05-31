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

from ryu.base import app_manager
from ryu.services.protocols.ldp import event as ldp_event 


def ldp_config(app, interface, config):
    """create an instance.
    returns EventVRRPConfigReply(instance.name, interface, config)
    on success.
    returns EventVRRPConfigReply(None, interface, config)
    on failure.
    """
    config_request = ldp_event.EventLDPConfigRequest(interface, config)
    config_request.sync = True
    return app.send_request(config_request)

app_manager.require_app('ryu.services.protocols.ldp.manager', api_style=True)
