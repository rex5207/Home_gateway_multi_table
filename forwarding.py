import json
from webob import Response
from ryu.base import app_manager
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.topology.api import get_switch, get_host
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.lib.packet import lldp
from ryu.lib.packet import dhcp
from ryu.lib import mac

from config import service_config, forwarding_config
from helper import ofp_helper
from models.member import Member


class L2Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(L2Switch, self).__init__(*args, **kwargs)
        self.switches = {}
        self.topology_api_app = self
        self.table_id = service_config.service_sequence['forwarding']
        self.service_priority = service_config.service_priority['forwarding']
        self.goto_table_priority = service_config.service_priority['goto_table']

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser


        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        self.add_table_miss_flow(datapath, 0, match, actions)
        # # Table Miss, forward packet to next table
        # match = parser.OFPMatch()
        # ofp_helper.add_flow_goto_next(datapath, table_id=self.table_id,
        #                               priority=self.goto_table_priority, match=match)


    def add_table_miss_flow(self, datapath, priority, match, actions,
                        buffer_id=None):
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        ofp_helper.add_flow_goto_next(datapath, 0, self.goto_table_priority, match)

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,table_id=1,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,table_id=1,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if not service_config.service_status['forwarding']:
            return

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        # retrieve packet
        pkt = packet.Packet(msg.data)
        pkt_eth = pkt.get_protocols(ethernet.ethernet)[0]
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_arp = pkt.get_protocol(arp.arp)
        pkt_lldp = pkt.get_protocol(lldp.lldp)
        pkt_dhcp = pkt.get_protocol(dhcp.dhcp)

        if pkt_lldp:
            # ignore lldp packet
            return

        if pkt_dhcp:
            for options in pkt_dhcp.options.option_list:
                if(options.tag == 12):
                    if forwarding_config.member_list.get(pkt_dhcp.chaddr) is not None:
                        member = forwarding_config.member_list.get(pkt_dhcp.chaddr)
                    else:
                        forwarding_config.member_list.setdefault(pkt_dhcp.chaddr,
                                                                 Member(pkt_dhcp.chaddr))
                        forwarding_config.member_list[pkt_dhcp.chaddr].datapath = datapath
                        forwarding_config.member_list[pkt_dhcp.chaddr].port = in_port
                    forwarding_config.member_list[pkt_dhcp.chaddr].hostname = options.value
            if service_config.service_status['dhcp']:
                # if dhcp enabled, forwarding should not handle
                return

        if pkt_arp or pkt_eth.dst not in forwarding_config.member_list:
            self._handle_arp(msg, in_port, pkt_eth, pkt_arp)
        elif pkt_ipv4:
            if pkt_eth.dst == mac.BROADCAST_STR:
                self._broadcast_pkt(msg, in_port)
            elif (pkt_ipv4.dst == '255.255.255.255') or (pkt_ipv4.dst == '0.0.0.0'):
                self._broadcast_pkt(msg, in_port)
            else:
                self._handle_ipv4(msg, in_port, pkt, pkt_eth, pkt_ipv4)

    def _handle_arp(self, msg, in_port, pkt_eth, pkt_arp):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        eth_dst = pkt_eth.dst
        eth_src = pkt_eth.src
        dpid = datapath.id

        # update member(host) in member_list
        member_list = forwarding_config.member_list
        member_list.setdefault(eth_src, Member(eth_src))
        member_list[eth_src].datapath = datapath
        member_list[eth_src].port = in_port

        if eth_dst not in member_list:
            self._broadcast_pkt(msg, in_port)
        else:
            out_port = member_list[eth_dst].port
            actions = [parser.OFPActionOutput(out_port)]
            ofp_helper.send_packet_out(msg, in_port, actions)

    def _handle_ipv4(self, msg, in_port, pkt, pkt_ethernet, pkt_ipv4):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        eth_dst = pkt_ethernet.dst
        eth_src = pkt_ethernet.src

        # update ip info for members in member_list
        member_list = forwarding_config.member_list
        dst_member = member_list[eth_dst]
        dst_member.ip = pkt_ipv4.dst
        if member_list.get(eth_src) is not None:
            src_member = member_list[eth_src]
            src_member.ip = pkt_ipv4.src
        out_port = dst_member.port

        # install layer4 flow for statitic
        actions = [parser.OFPActionOutput(out_port)]
        actions_back = [parser.OFPActionOutput(in_port)]
        if pkt_ipv4.proto == inet.IPPROTO_TCP:
            pkt_tcp = pkt.get_protocol(tcp.tcp)
            match = parser.OFPMatch(eth_src=pkt_ethernet.src,
                                    eth_dst=pkt_ethernet.dst,
                                    eth_type=ether.ETH_TYPE_IP,
                                    ipv4_src=pkt_ipv4.src,
                                    ipv4_dst=pkt_ipv4.dst,
                                    ip_proto=pkt_ipv4.proto,
                                    tcp_src=pkt_tcp.src_port,
                                    tcp_dst=pkt_tcp.dst_port)
            match_back = parser.OFPMatch(eth_src=pkt_ethernet.dst,
                                         eth_dst=pkt_ethernet.src,
                                         eth_type=ether.ETH_TYPE_IP,
                                         ipv4_src=pkt_ipv4.dst,
                                         ipv4_dst=pkt_ipv4.src,
                                         ip_proto=pkt_ipv4.proto,
                                         tcp_src=pkt_tcp.dst_port,
                                         tcp_dst=pkt_tcp.src_port)
        elif pkt_ipv4.proto == inet.IPPROTO_UDP:
            pkt_udp = pkt.get_protocol(udp.udp)
            match = parser.OFPMatch(eth_src=pkt_ethernet.src,
                                    eth_dst=pkt_ethernet.dst,
                                    eth_type=ether.ETH_TYPE_IP,
                                    ipv4_src=pkt_ipv4.src,
                                    ipv4_dst=pkt_ipv4.dst,
                                    ip_proto=pkt_ipv4.proto,
                                    udp_src=pkt_udp.src_port,
                                    udp_dst=pkt_udp.dst_port)
            match_back = parser.OFPMatch(eth_src=pkt_ethernet.dst,
                                         eth_dst=pkt_ethernet.src,
                                         eth_type=ether.ETH_TYPE_IP,
                                         ipv4_src=pkt_ipv4.dst,
                                         ipv4_dst=pkt_ipv4.src,
                                         ip_proto=pkt_ipv4.proto,
                                         udp_src=pkt_udp.dst_port,
                                         udp_dst=pkt_udp.src_port)
        else:
            match = parser.OFPMatch(eth_src=pkt_ethernet.src,
                                    eth_dst=pkt_ethernet.dst,
                                    eth_type=ether.ETH_TYPE_IP,
                                    ipv4_src=pkt_ipv4.src,
                                    ipv4_dst=pkt_ipv4.dst)
            match_back = parser.OFPMatch(eth_src=pkt_ethernet.dst,
                                         eth_dst=pkt_ethernet.src,
                                         eth_type=ether.ETH_TYPE_IP,
                                         ipv4_src=pkt_ipv4.dst,
                                         ipv4_dst=pkt_ipv4.src)
        ofp_helper.add_flow(datapath, table_id=1,
                                      priority=self.service_priority, match=match,
                                      actions=actions, idle_timeout=10)
        ofp_helper.add_flow(datapath, table_id=1,
                                      priority=self.service_priority, match=match_back,
                                      actions=actions_back, idle_timeout=10)
        ofp_helper.send_packet_out(msg, in_port, actions)

    def _broadcast_pkt(self, msg, in_port):
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]
        ofp_helper.send_packet_out(msg, in_port, actions)

    # @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    # def port_status_handler(self, ev):
    #     msg = ev.msg
    #     dp = msg.datapath
    #     ofp = dp.ofproto
    #
    #     if msg.reason == ofp.OFPPR_ADD:
    #         reason = 'ADD'
    #     elif msg.reason == ofp.OFPPR_DELETE:
    #         reason = 'DELETE'
    #     elif msg.reason == ofp.OFPPR_MODIFY:
    #         reason = 'MODIFY'
    #     else:
    #         reason = 'unknown'
    #
    #     self.logger.debug('OFPPortStatus received: reason=%s desc=%s',
    #                       reason, msg.desc)
