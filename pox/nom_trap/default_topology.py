#!/usr/bin/env python
# Nom nom nom nom

'''
If the user does not specify a topology to test on, use this default:

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

def populate(topology):
  # TODO: Do we need to simulate a port to the controller?
  ports = []
  num_ports = 6
  # Ox00000000 is reserved, so start at Ox00000001
  for i in range(0, num_ports):
    addr = 0x000000000001
    wrapper = EthAddr(addr)
    ofp_port = ofp_phy_port()
    ofp_port.port_no = i # Does this have to start from 0?
    ofp_port.hw_addr = wrapper
    ports.append(OpenFlowPort(ofp_port))
    addr += 0x000000000001

  switch1 = MockOpenFlowSwitch(dpid = 1)
  switch2 = MockOpenFlowSwitch(dpid = 2)
  switch3 = MockOpenFlowSwitch(dpid = 3)
  
  for switch in [switch1, switch2, switch3]:
    topology.addEntity(switch)