#!/usr/bin/env python
# Nom nom nom nom

'''
If the user does not specify a topology to test on, use by default a full mesh
of switches. For example, with N = 3:

              controller
 
     switch1-(1)------------(3)--switch2
        \                       /
        (2)                   (4)
          \                   /
           \                 / 
            \               /
             (6)-switch3-(5)
            
TODO: should this topology include Hosts as well?
'''

from pox.nom_trap.fuzzer_entities import *
from pox.openflow.libopenflow_01 import ofp_phy_port
import pox.topology.topology as topology
from pox.controllers.distributed_controller import DistributedController
from socket import *

class Cycler():
  """
  Abstraction for cycling through the given list circularly:
  
  c = Cycler([1,2,3])
  while True:
    print c.next()
  """
  def __init__(self, arr):
    self._list = list(arr)
    self._current_index = 0 
    
  def next(self):
    if len(self._list) == 0:
      return None
    
    element = self._list[self._current_index]
    self._current_index += 1
    self._current_index %= len(self._list)
    return element

def populate(topology, num_switches=3):
  # TODO: Do we need to simulate (designate) a port to the controller?
  # TODO: use only topology Controllers for emulation (have switches connect directly rather than
  #       creating an [unserializable] socket here)
  #controllers = Cycler(topology.getEntitiesOfType(topology.Controller))
  
  # HACK: For simulation, get a direct reference to the controllers via core.components, and
  #       inject the MockOpenFlowSwitch objects directly into the controller's cached NOM
  controllers = []
  for name in core.components.keys():
    if name.find("controller") != -1:
      controllers.append(core.components[name])
  controllers = Cycler(controllers)
  
  # Every switch has a link to every other switch, for N*(N-1) total ports
  ports_per_switch = num_switches - 1
  total_ports = num_switches * ports_per_switch
  # We start at 0x000000000001, since 0x000000000000 is reserved
  port_nos_iterator = xrange(1, total_ports+1).__iter__()
  
  # Initialize switches
  switches = []
  for switch_num in range(0, num_switches):
    ports_for_switch = []
    for _ in range(0, ports_per_switch):
      # Define Port
      ofp_port = ofp_phy_port()
      port_no = port_nos_iterator.next()
      ofp_port.port_no = port_no
      eth_addr_num = port_no
      # We need 6 bytes -- Q is a long long, which is 8 bytes. So we cut off at 6 /before reversing/
      # TODO: on Mac OSX, the bytes are swapped (e.g. 05:00:00:00:00:00). So I reverse it
      raw_addr = struct.pack("=Q", eth_addr_num)[:6][::-1]
      ofp_port.hw_addr = EthAddr(raw_addr)
      # HACK: ports don't normally have an IP address associated with them in 
      # a hardcoded way like this. But, it makes life easier for Anteater output
      ip_addr_num = port_no
      ofp_port.ip_addr = inet_ntoa(struct.pack('=L',ntohl(ip_addr_num)))
      ports_for_switch.append(ofp_port)
      
    # Instantiate NOM Switch (which instantiates the SwitchImpl)
    parent_controller = controllers.next()
    switch = MockOpenFlowSwitch(switch_num, ports_for_switch, parent_controller.name)
    
    # HACK: externally define a new field in SwitchImpl
    #       port -> Link
    switch.switch_impl.outgoing_links = {}
    
    # HACK: insert the MockOpenFlowSwitch directly into controller's NOM. We'll also
    # add a copy to the master NOM here.
    if isinstance(parent_controller, DistributedController):
      parent_controller.topology.addEntity(switch)
      
    switches.append(switch)
    
  if len(switches) != num_switches:
    raise AssertionError("len(switches) != num_switches. Was %d" % len(switches))
    
  connected_ports = set()
  for switch in switches:
    # Now "connect" the ports. 
    switch_impl = switch.switch_impl
    
    if len(switch_impl.ports) != ports_per_switch:
      raise AssertionError("len(switch_impl.ports) != ports_per_switch")
    
    # Find switches that we haven't connected to yet
    already_connected_neighbor_impls = set(map(lambda l: l.end_switch_impl, switch_impl.outgoing_links.values()))
    all_neighbor_impls = map(lambda s: s.switch_impl, filter(lambda s: s != switch, switches))
    unconnected_neighbor_impls = filter(lambda n: n not in already_connected_neighbor_impls, all_neighbor_impls) 
    
    for other_switch_impl in unconnected_neighbor_impls:
      our_port = filter(lambda p: p not in connected_ports, switch_impl.ports.values())[0]
      neighbor_port = filter(lambda p: p not in connected_ports, other_switch_impl.ports.values())[0]
        
      # Now we have two ports that haven't been connected yet
      connected_ports.add(our_port)
      connected_ports.add(neighbor_port)
        
      # Add a link switch -> other
      switch2other = Link(switch_impl, our_port, other_switch_impl, neighbor_port)
      switch_impl.outgoing_links[our_port] = switch2other      
        
      # Add a link other -> switch
      other2switch = Link(other_switch_impl, neighbor_port, switch_impl, our_port)
      other_switch_impl.outgoing_links[neighbor_port] = other2switch
      
  if len(connected_ports) != total_ports:
    raise AssertionError("len(connected_ports != total_ports). Was %d. Connected ports: %s" % (len(connected_ports), str(connected_ports)))
      
  # Now add switches to the master Topology copy
  for switch in switches:
    topology.addEntity(switch)