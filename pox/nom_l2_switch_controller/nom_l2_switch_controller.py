# Copyright 2011 James McCauley
#
# This file is part of POX.
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX.  If not, see <http://www.gnu.org/licenses/>.

"""
This is a prototype control application written on top of the (substrate) NOM. 

It converts NOM switch entities into LearningSwitches.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.openflow import PacketIn
from pox.topology.topology import Switch
from pox.lib.revent import *

log = core.getLogger()

# Note that control applications are /stateless/; they are simply a function:
#    f(view) -> configuration
#
# The view is encapsulated in the NOM, and the configuration results from manipulating
# NOM entities.
#
# To ensure statelesness (order-independence), the application must never instantiate its own
# objects. Instead, it must "fold in" any needed state into the NOM. The platform itself is in
# charge of managing the NOM.
# 
# To "fold in" state, the application must declare a user-defined NOM entity. The entities
# encapsulate:
#   i.    State (e.g., self.mac2port = {})
#   ii.   Behavior (i.e. event handlers, such as def _handle_PacketIn() below)
#
# This is an example of a user-defined NOM entity.
class LearningSwitch (EventMixin):
  """
  The learning switch "brain" associated with a single OpenFlow switch.

  When we see a packet, we'd like to output it on a port which will eventually
  lead to the destination.  To accomplish this, we build a table that maps
  addresses to ports.

  We populate the table by observing traffic.  When we see a packet from some
  source coming from some port, we know that source is out that port.

  When we want to forward traffic, we look up the destination in our table.  If
  we don't know the port, we simply send the message out all ports except the
  one it came in on.  (In the presence of loops, this is bad!).

  In short, our algorithm looks like this:

  For each new flow:
  1) Use source address and port to update address/port table
  2) Is destination multicast?
     Yes:
        2a) Flood the packet
     No:
        2b) Port for destination address in our address/port table?
           No:
             2ba) Flood the packet
          Yes:
             2bb1) Install flow table entry in the switch so that this flow
                   goes out the appropriate port
             2bb2) Send buffered packet out appropriate port
  """
  def __init__ (self, switch):
    """
    Initialize the NOM Wrapper for Switch Entities
    
    switch - the NOM switch entity to wrap
    """
    self.switch = switch

    # We define our own state
    self.macToPort = {}

    # We also define our behavior by registering an event handler (_handle_PacketIn)
    self.listenTo(switch)

  def _handle_PacketIn (self, packet_in_event):
    """ Event handler for PacketIn events: run the learning switch algorithm """
    log.debug("PacketIn_handler! packet_in_event: %s" % (str(packet_in_event)))
    
    def flood ():
      """ Floods the packet """
      # TODO: there should really be a static method in pox.openflow that constructs this
      # this packet for us.
      msg = of.ofp_packet_out()
      msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      msg.buffer_id = packet_in_event.ofp.buffer_id
      msg.in_port = packet_in_event.port
      self.switch.send(msg)

    packet = packet_in_event.parse()
    self.macToPort[packet.src] = packet_in_event.port # 1
    if packet.dst.isMulticast():
      flood() # 2a
    else:
      if packet.dst not in self.macToPort:
        log.debug("port for %s unknown -- flooding" % (packet.dst,))
        flood() # 2ba
      else:
        # 2bb
        port = self.macToPort[packet.dst]
        log.debug("installing flow for %s.%i -> %s.%i" %
                  (packet.src, packet_in_event.port, packet.dst, port))
        # TODO: there should really be a static method in pox.openflow that constructs this
        # this packet for us.
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = 10
        msg.hard_timeout = 30
        msg.actions.append(of.ofp_action_output(port = port))
        msg.buffer_id = packet_in_event.ofp.buffer_id
        self.switch.send(msg)

# In addition to declaring the user-defined NOM entity, the application must tell the platform
# how and when to instantiate these NOM entities. We do this with the following controller:
class nom_l2_switch_controller (EventMixin):
  """ Controller that treats the network as a set of learning switches """
  
  # The set of components we depend on. These must be loaded before we can begin.
  _wantComponents = set(['topology'])

  def __init__ (self):
    """ Initializes the l2 switch controller component """
    log.debug("nom_l2_switch_controller booting...")
    
    if not core.resolveComponents(self, self._wantComponents):
      # If dependencies aren't loaded, register event handlers for ComponentRegistered
      self.listenTo(core)
  
  def _handle_ComponentRegistered (self, event):
    """ Checks whether the newly registered component is one of our dependencies """
    if core.resolveComponents(self, self._wantComponents):
      self._registerWrapper()
      return EventRemove
    
  def _registerWrapper(self):
    """
    Tell the platform how to instantiate DumbSwitch NOM entities
    
    pre: pox.topology is registered with the pox.core 
    """
    topology = core.components['topology']
    # This says: whenever a Switch object is instantiated in the NOM, wrap it with
    # a LearningSwitch object. 
    topology.registerWrapper(Switch, LearningSwitch) 