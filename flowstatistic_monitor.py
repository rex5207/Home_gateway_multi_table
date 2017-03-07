from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.topology.api import get_switch
from ryu.controller.event import EventBase
from ryu.lib import hub
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.app.ofctl.api import get_datapath

from config import forwarding_config,qos_config
from models import flow
from qos import App_UpdateEvent

import logging


class flowstatistic_monitor(app_manager.RyuApp):

    _EVENTS = [App_UpdateEvent]

    def __init__(self, *args, **kwargs):
        """Initial Setting method."""
        super(flowstatistic_monitor, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        logging.getLogger("requests").setLevel(logging.WARNING)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.monitor_thread = hub.spawn(self._monitor, datapath)

    def _monitor(self, datapath):
        while True:
            key_set = forwarding_config.flow_list.keys()
            for key in key_set:
                flow = forwarding_config.flow_list[key]
                if flow.exist == 0:
                    forwarding_config.flow_list.pop(key)
                else:
                    forwarding_config.flow_list[key].exist = 0
            parser = datapath.ofproto_parser
            req = parser.OFPFlowStatsRequest(datapath)
            datapath.send_msg(req)
            ev = App_UpdateEvent('Update rate for app')
            self.send_event_to_observers(ev)
            hub.sleep(1)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        for stat in body:
            if stat.table_id != 3:
                continue
            if stat.match.get('eth_type') == ether.ETH_TYPE_IP:
                key_tuples = str(ev.msg.datapath.id)\
                             + '' or stat.match.get('eth_src')\
                             + stat.match.get('eth_dst')\
                             + stat.match.get('ipv4_src')\
                             + stat.match.get('ipv4_dst')\
                             + str(stat.match.get('ip_proto'))

                if stat.match.get('ip_proto') == inet.IPPROTO_TCP:
                    key_tuples += str(stat.match.get('tcp_src')) + str(stat.match.get('tcp_dst'))

                    if forwarding_config.flow_list.get(key_tuples) is None:
                        flow_value = flow.Flow(ev.msg.datapath.id,
                                               stat.match.get('eth_src'),
                                               stat.match.get('eth_dst'),
                                               stat.match.get('ipv4_src'),
                                               stat.match.get('ipv4_dst'),
                                               stat.match.get('ip_proto'),
                                               stat.match.get('tcp_src'),
                                               stat.match.get('tcp_dst'),
                                               stat.byte_count, 1)
                        flow_value.rate_calculation()
                        forwarding_config.flow_list.update({key_tuples: flow_value})
                    else:
                        flow_value = forwarding_config.flow_list.get(key_tuples)
                        flow_value.byte_count_1 = flow_value.byte_count_2
                        flow_value.byte_count_2 = stat.byte_count
                        flow_value.rate_calculation()
                        flow_value.exist = 1

                elif stat.match.get('ip_proto') == inet.IPPROTO_UDP:
                    key_tuples += str(stat.match.get('udp_src'))\
                                      + str(stat.match.get('udp_dst'))
                    if forwarding_config.flow_list.get(key_tuples) is None:
                        flow_value = flow.Flow(ev.msg.datapath.id,
                                               stat.match.get('eth_src'),
                                               stat.match.get('eth_dst'),
                                               stat.match.get('ipv4_src'),
                                               stat.match.get('ipv4_dst'),
                                               stat.match.get('ip_proto'),
                                               stat.match.get('udp_src'),
                                               stat.match.get('udp_dst'),
                                               stat.byte_count, 1)
                        flow_value.rate_calculation()
                        forwarding_config.flow_list.update({key_tuples: flow_value})
                    else:
                        flow_value = forwarding_config.flow_list.get(key_tuples)
                        flow_value.byte_count_1 = flow_value.byte_count_2
                        flow_value.byte_count_2 = stat.byte_count
                        flow_value.rate_calculation()
                        flow_value.exist = 1
