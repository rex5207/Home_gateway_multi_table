def add_flow(datapath, table_id, priority, match, actions,
             idle_timeout=0, buffer_id=None):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser

    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                         actions)]
    if buffer_id:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                buffer_id=buffer_id,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    else:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    datapath.send_msg(mod)


def del_flow(datapath, table_id, priority, match):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    mod = parser.OFPFlowMod(datapath=datapath,
                            command=ofproto.OFPFC_DELETE_STRICT,
                            out_port=ofproto.OFPP_ANY,
                            out_group=ofproto.OFPG_ANY,
                            priority=priority,
                            match=match,
                            table_id=table_id)
    datapath.send_msg(mod)


def add_flow_with_next(datapath, table_id, priority, match, actions,
                       idle_timeout=0, buffer_id=None):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    next_table = table_id + 1

    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
            parser.OFPInstructionGotoTable(next_table)]
    if buffer_id:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                buffer_id=buffer_id,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    else:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    datapath.send_msg(mod)


def add_flow_goto_next(datapath, table_id, priority, match,
                       idle_timeout=0, buffer_id=None):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    next_table = table_id + 1

    inst = [parser.OFPInstructionGotoTable(next_table)]
    if buffer_id:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                buffer_id=buffer_id,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    else:
        mod = parser.OFPFlowMod(datapath=datapath,
                                idle_timeout=idle_timeout,
                                priority=priority,
                                match=match,
                                table_id=table_id,
                                instructions=inst)
    datapath.send_msg(mod)


def add_flow_rate_limit(datapath, table_id, priority, match, meter_id,
                        idle_timeout=0, buffer_id=None):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    next_table = table_id + 1
    command = ofproto.OFPFC_ADD
    if meter_id == -1:
        actions = []  # drop
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    elif meter_id == 0:
        inst = [parser.OFPInstructionGotoTable(next_table)]
    else:
        inst = [parser.OFPInstructionMeter(meter_id),
                parser.OFPInstructionGotoTable(next_table)]

    if buffer_id:
        mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id, command=command,
                                buffer_id=buffer_id, priority=priority, match=match,
                                idle_timeout=idle_timeout, instructions=inst)
    else:
        mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id, command=command,
                                priority=priority, idle_timeout=idle_timeout,
                                match=match, instructions=inst)
    datapath.send_msg(mod)


def send_packet_out(msg, in_port, actions):
    datapath = msg.datapath
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    data = None
    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
        data = msg.data
    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                              in_port=in_port, actions=actions, data=data)
    datapath.send_msg(out)


def add_meter(datapath, bandwidth, id):
    parser = datapath.ofproto_parser
    ofproto = datapath.ofproto

    command = ofproto.OFPMC_ADD
    band = parser.OFPMeterBandDrop(rate=bandwidth, burst_size=1024)
    req = parser.OFPMeterMod(datapath, command, ofproto.OFPMF_KBPS, id, [band])
    datapath.send_msg(req)


def del_meter(datapath, bandwidth, id):
    parser = datapath.ofproto_parser
    ofproto = datapath.ofproto

    command = ofproto.OFPMC_DELETE
    band = parser.OFPMeterBandDrop(rate=bandwidth, burst_size=1024)
    req = parser.OFPMeterMod(datapath, command, ofproto.OFPMF_KBPS, id, [band])
    datapath.send_msg(req)


def mod_meter(datapath, bandwidth, id):
    parser = datapath.ofproto_parser
    ofproto = datapath.ofproto

    command = ofproto.OFPMC_MODIFY
    band = parser.OFPMeterBandDrop(rate=bandwidth, burst_size=1024)
    req = parser.OFPMeterMod(datapath, command, ofproto.OFPMF_KBPS, id, [band])
    datapath.send_msg(req)
