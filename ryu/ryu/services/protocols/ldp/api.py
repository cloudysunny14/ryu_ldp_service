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
