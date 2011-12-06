#!/usr/bin/env python
# Nom nom nom nom

'''
If the user does not specify a topology to test on, use by default a full mesh
of switches. For example, with N = 3:

              controller
 
     switch1----------------switch2
        \                   /
         \                 /
          \               / 
           \             /
            -- switch3--
            
TODO: should this topology include Hosts as well?
'''

from pox.nom_trap.fuzzer_entities import *
from pox.openflow.libopenflow_01 import ofp_phy_port

def populate(topology, num_switches=3):
  # TODO: Do we need to simulate (designate) a port to the controller?
  ports = []
  # Every switch has a link to every other switch, for N*(N-1) total ports
  ports_per_switch = num_switches - 1
  total_ports = num_switches * ports_per_switch
  # Ox000000000000 is reserved, so start at Ox000000000001
  addr = 1
  for port_no in range(0, total_ports):
    ofp_port = ofp_phy_port()
    ofp_port.port_no = port_no
    # repeat the addr value in each of the 6 bytes
    raw_addr = struct.pack("Q", addr)[:6] 
    ofp_port.hw_addr = EthAddr(raw_addr)
    ports.append(ofp_port)
    addr += 1

  switches = []
  for switch_num in range(0, num_switches):
    first_port_index = switch_num*ports_per_switch
    ports_for_switch = ports[first_port_index : first_port_index+ports_per_switch]
    switches.append(MockOpenFlowSwitch(switch_num, ports_for_switch))
      
  for switch in switches:
    topology.addEntity(switch)