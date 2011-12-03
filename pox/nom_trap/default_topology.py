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
  # TODO: Do we need to simulate a port to the controller?
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
    ports.append(OpenFlowPort(ofp_port))
    addr += 1

  switches = []
  for switch_num in range(0, num_switches):
    switches.append(MockOpenFlowSwitch(switch_num))
    # Load up ports
    for port_no in range(0, ports_per_switch):
      port = ports[(switch_num*ports_per_switch)+port_no]
      switches[switch_num].ports[port.number] = port
      # TODO: set switch.switch_impl.ports too!
  
  for switch in switches:
    topology.addEntity(switch)