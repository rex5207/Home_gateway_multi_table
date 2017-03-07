#!/ bin/bash
#ryu-manager base.py service_control.py firewall.py qos.py forwarding.py dhcp.py nat.py flowstatistic_monitor.py --wsapi-port 7777 --ofp-tcp-listen-port 6666
ryu-manager qos.py forwarding.py flowstatistic_monitor.py --wsapi-port 7777 --ofp-tcp-listen-port 6666
