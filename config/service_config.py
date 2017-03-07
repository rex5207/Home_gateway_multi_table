# Define rule priority of each service
service_priority = {
    'service_control': 65530,
    # firewall
    'firewall': 65500,
    # qos
    'app_rate_limit': 100,
    'host_rate_limit': 10,
    # forwarding
    'forwarding': 5,
    # nat/dhcp
    'dhcp': 100,
    'nat': 10,
    # next in all table
    'goto_table': 0,
    # packet_in in last table
    'packet_in': 1
}

# Define which table service applied rule into
service_sequence = {
    'nat_ingress': 0,  # outside-to-inside
    'firewall': 1,
    'qos': 2,
    'forwarding': 3,
    'nat_egress': 4,   # inside-to-outside
    'dhcp': 4,
    'packet_in': 3,    # last table
}

# service enable or disable
service_status = {
    'firewall': True,
    'qos': True,
    'nat': True,
    'dhcp': True,
    'forwarding': True
}
