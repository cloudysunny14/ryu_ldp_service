# Copyright (C) 2014 Stratosphere Inc.
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

"""
Usage example

1. Run this application:
$ wsdump.py ws://127.0.0.1:8080/ldp_manager/ws
$ {"jsonrpc": "2.0", "id": 1, "method": "get_arp_table", "params" : {}}
...
"""  # noqa

from ryu.base import app_manager
from ryu.controller import handler
from ryu.app.wsgi import (
    rpc_public,
    WebSocketRPCServer,
    ControllerBase,
    WSGIApplication,
    websocket,
)
from ryu.services.protocols.ldp import event as ldp_event

WEBSOCKET_LDP_RPC_APP_INSTANCE_NAME = 'websocket_ldp_rpc_app'

class WebSocketLdp(app_manager.RyuApp):
    _CONTEXTS = {
        'wsgi': WSGIApplication,
    }

    def __init__(self, *args, **kwargs):
        super(WebSocketLdp, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(
            WebSocketLdpController,
            data={WEBSOCKET_LDP_RPC_APP_INSTANCE_NAME: self},
        )
        self._ws_manager = wsgi.websocketmanager
        self._peers = {}
        self._peer_id = 0

    @handler.set_ev_cls(ldp_event.EventLDPPeerAdd)
    def peer_add(self, ev):
        peer_id = ev.peer_id
        pass

    @rpc_public('manager.start')
    def manager_start(self):
        pass

    @rpc_public('adver.send_address')
    def send_address(self, ):
        pass

    @rpc_public('adver.send_label_mapping')
    def send_label_mapping(self, prefix, label):
      return {'prefix': prefix, 'label': label}

    @rpc_public('adver.send_label_request')
    def send_label_request(self):
        pass

    @rpc_public('oper.notification')
    def send_notification(self):
        pass

    @rpc_public('show.ldp_neighbor')
    def show_ldp_neighbor(self):
        pass

class WebSocketLdpController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(WebSocketLdpController, self).__init__(
            req, link, data, **config)
        self.app = data[WEBSOCKET_LDP_RPC_APP_INSTANCE_NAME]

    @websocket('ldp_manager', '/ldp/ws')
    def _websocket_handler(self, ws):
        rpc_client = WebSocketRPCServer(ws, self.app)
        rpc_client.serve_forever()
