import socket
import netaddr

from eventlet import semaphore
from ryu.lib import hub
from ryu.lib.hub import Timeout
from ryu.base import app_manager
from ryu.controller import handler
from ryu.services.protocols.ldp import event as ldp_event
from ryu.services.protocols.ldp.interface import LDPInterface 
from ryu.services.protocols.ldp import ldp_util
from ryu.services.protocols.ldp.peer import Peer

from ryu.lib.packet import ldp
from ryu.lib.packet.ldp import LDPMessage

class LDPManager(app_manager.RyuApp):
    @staticmethod
    def _instance_name(router_id, label_space_id):
        return 'lsr-%s:%s' % (router_id, label_space_id)

    def __init__(self, *args, **kwargs):
        super(LDPManager, self).__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs
        self.name = ldp_event.LDP_MANAGER_NAME
        self.shutdown = hub.Queue()
        self.interfaces = {}
        self.peers = {} #key peer router_id 
        self.config = None
        self.register_observer(ldp_event.EventLDPStateChanged,
                               self.name)
        self.register_observer(ldp_event.EventLDPMessageReceived,
                               self.name)
        #self.session_thread = hub.spawn(self._session_thread)

    def start(self):
        t = hub.spawn(self._shutdown_loop)
        super(LDPManager, self).start()
        return t

    @handler.set_ev_cls(ldp_event.EventLDPConfigRequest)
    def config_request_handler(self, ev):
        self.config = ev.config
        iface_conf = ev.interface
        interface = self._new_interface(iface_conf, self.config)
        self.interfaces[iface_conf.device_name] = interface
        #TODO: delay timer
        interface.start()
        rep = ldp_event.EventLDPConfigReply(self._instance_name(self.config.router_id, self.config.label_space_id),
            interface, self.config)
        self.reply_to_request(ev, rep)

    @handler.set_ev_cls(ldp_event.EventHelloReceived)
    def hello_received(self, ev):
        router_id = ev.router_id
        packet = ev.packet
        peer = self.peers.get(router_id, None)
        if peer is not None:
            peer.reset_hold_timer()
        else:
            msg, rest = LDPMessage.parser(packet)
            peer_router_id = msg.header.router_id
            trans_addr = LDPMessage.retrive_tlv(ldp.LDP_TLV_IPV4_TRANSPORT_ADDRESS, msg)
            peer = Peer(self, peer_router_id, trans_addr, self.config)
            self.peers[router_id] = peer
            is_active = ldp_util.from_inet_ptoi(peer_router_id) < \
                ldp_util.from_inet_ptoi(self.config.router_id)
            hub.spawn(self._session_thread, is_active, peer)

    @handler.set_ev_cls(ldp_event.EventLDPStateChanged)
    def ldp_state_change(self, ev):
        print 'state_change:%s' % (ev.new_state)

    @handler.set_ev_cls(ldp_event.EventLDPMessageReceived)
    def ldp_recv_msg(self, ev):
        print 'receive:%s' % (ev.msg)

    @handler.set_ev_cls(ldp_event.EventLDPSendMessage)
    def ldp_send_message(self, ev):
        msg = ev.msg
        router_id = ev.router_id
        peer = self.peers[router_id]
        peer.send_msg(msg.serialize())

    def _new_interface(self, iface_conf, conf):
        server = DiscoverServer(iface_conf.ip_address)
        interface = LDPInterface(self, server, conf)
        return interface

    def _shutdown_loop(self):
        app_mgr = app_manager.AppManager.get_instance()
        while self.is_active or not self.shutdown.empty():
            instance = self.shutdown.get()
            app_mgr.uninstantiate(instance.name)
            app_mgr.uninstantiate(instance.monitor_name)
            del self._instances[instance.name]

    def _session_thread(self, is_active, peer):
        bind_addr = (self.config.router_id, LDP_DISCOVERY_PORT)
        if is_active:
            bind_addr = (self.config.router_id, 0)
        sess = SessionServer(bind_addr)
        sess.start(is_active, (peer.trans_addr.addr, LDP_DISCOVERY_PORT),
                peer.conn_handle)

    def start_discover(self):
        pass

    def start_listen(self):
        pass

ALL_ROUTER = '224.0.0.2'
LDP_DISCOVERY_PORT = 646
DEFAULT_CONN_TIMEOUT = 30

class SessionServer(object):

    def __init__(self, bind_address):
        sock = socket.socket(socket.AF_INET, 
            socket.SOCK_STREAM)
        if bind_address is not None:
            sock.bind(bind_address)
        self._socket = sock

    def start(self, is_active, peer_addr, conn_handle):
        if is_active:
            with Timeout(DEFAULT_CONN_TIMEOUT, socket.error):
                self._socket.connect(peer_addr)
            hub.spawn(conn_handle, self._socket, True)
        else:
            self._socket.listen(50)
            hub.spawn(self._listen_loop, conn_handle)

    def _listen_loop(self, conn_handle):
        while True:
            sock, client_address = self._socket.accept()
            hub.spawn(conn_handle, sock, False)

class DiscoverServer(object):

    def __init__(self, iface):
        self.write_lock = semaphore.Semaphore()
        sock = socket.socket(socket.AF_INET, 
            socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET,
             socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_IP,
            socket.IP_MULTICAST_LOOP, 0)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET,
                socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            socket.inet_aton(ALL_ROUTER) + socket.inet_aton(iface))
        sock.setsockopt(socket.SOL_IP,
             socket.IP_MULTICAST_IF,
             socket.inet_aton(iface))
        sock.bind((ALL_ROUTER, LDP_DISCOVERY_PORT))
        self.socket = sock

    def start(self, handler):
        hub.spawn(self._recv_loop, handler)

    def sendto(self, *args):
        self.write_lock.acquire()
        try:
            self.socket.sendto(*args)
        finally:
            self.write_lock.release()

    def _recv_loop(self, handler):
        while True:
            data, addr = self.socket.recvfrom(8192)
            hub.spawn(handler, data, addr)

class LDPStatistics(object):
    """"""
