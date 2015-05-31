from ryu.lib import addrconv
from ryu.controller import event
from ryu.controller import handler

LDP_STATE_NON_EXISTENT = 'existent'
LDP_STATE_INITIAL = 'initial' ,
LDP_STATE_OPEN_SENT = 'open_sent',
LDP_STATE_OPEN_REC = 'open_rec'
LDP_STATE_OPERATIONAL = 'operational'

LDP_MANAGER_NAME = 'LDPManager'

class LDPConfig(object):
    def __init__(self, router_id='0.0.0.0', label_space_id=0,
        ldp_port=646, hold_time=15, keep_alive=180,
        start_delay=0):
        assert router_id is not None
        super(LDPConfig, self).__init__()
        self.router_id = router_id
        self.label_space_id = label_space_id
        self.hold_time = hold_time
        self.keep_alive = keep_alive
        self.ldp_port = ldp_port
        self.start_delay = start_delay

    def __eq__(self, other):
        return (self.router_id == other.router_id and
                self.label_space_id == other.label_space_id and
                self.hold_time == other.hold_time and
                self.keep_alive == other.keep_alive and
                self.ldp_port == other.ldp_port and
                self.start_delay == other.start_delay)

    def __hash__(self):
        hash((self.router_id, self.label_space_id,
              self.iface, self.hold_time,
              map(addrconv.ip_text_to_bin, self.router_id),
              self.hold_time, self.keep_alive,
              self.ldp_port, self.start_delay))

class LDPInterfaceConf(object):
    def __init__(self, primary_ip_address, device_name):
        self.ip_address = primary_ip_address
        self.device_name = device_name

    def __str__(self):
        return '%s<%s, %s>' % (
            self.__class__.__name__,
            self.ip_address, self.device_name)

    def __eq__(self, other):
        return (self.ip_address == other.ip_address and
                self.device_name == other.device_name)

    def __hash__(self):
        return hash((addrconv.ip_text_to_bin(self.ip_address),
            self.device_name))


class EventLDPConfigRequest(event.EventRequestBase):
    def __init__(self, interface, config):
        super(EventLDPConfigRequest, self).__init__()
        self.dst = LDP_MANAGER_NAME
        self.interface = interface
        self.config = config

class EventLDPConfigReply(event.EventReplyBase):
    def __init__(self, instance_name, interface, config):
        # dst = None. dst is filled by app_base.RyuApp#reply_to_request()
        super(EventLDPConfigReply, self).__init__(None)
        self.instance_name = instance_name  # None means failure
        self.interface = interface
        self.config = config

class EventLDPStateChanged(event.EventBase):
    """
    Event that this VRRP Router changed its state.
    """
    def __init__(self, instance_name, peer,
                 old_state, new_state):
        super(EventLDPStateChanged, self).__init__()
        self.instance_name = instance_name
        self.peer = peer
        self.old_state = old_state
        self.new_state = new_state

class EventLDPMessageReceived(event.EventBase):
    """
    Event LDP Message Received
    """
    def __init__(self, instance_name, msg):
        super(EventLDPMessageReceived, self).__init__()
        self.instance_name = instance_name
        self.msg = msg

class EventHelloReceived(event.EventBase):
    def __init__(self, router_id, packet):
        super(EventHelloReceived, self).__init__()
        self.router_id = router_id
        self.packet = packet

class EventLDPSendMessage(event.EventBase):
    def __init__(self, peer_lsr_id, msg):
        super(EventLDPSendMessage, self).__init__()
        self.peer_lsr_id = peer_lsr_id
        self.msg = msg

handler.register_service('ryu.services.protocols.ldp.manager')
