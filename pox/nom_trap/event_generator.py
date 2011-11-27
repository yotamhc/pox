
from pox.openflow import PacketIn
from pox.openflow.libopenflow_01 import ofp_packet_in
import pox.lib.packet.ethernet as ethernet

class EventGenerator (object):
  """
  Generate sensible randomly generated (openflow) events 
  """
  
  def __init__(self, random):
    self.random = random
    
    self._event_generators = {
      PacketIn : self.packet_in
    }
    
  def generate(self, eventType, switch):
    if eventType not in self._event_generators:
      raise "Unknown event type %s" % str(eventType)
    
    return self._event_generators[eventType](switch)
       
  def packet_in(self, switch):
    # TODO: generate the data to put in the packet in message. Need a notion
    # of valid ethernet addresses within the network 
    data = ethernet()
    # randomly choose an in port. TODO: factor choosing a random elt out
    rand_index = self.random.randint(0,len(switch.ports)-1)
    in_port = switch.ports[switch.ports.keys()[rand_index]]
    buffer_id = -1
    reason = None
    pkt = ofp_packet_in(data = data,
                        in_port = in_port,
                        buffer_id = buffer_id,
                        reason = reason)
    
    return PacketIn(switch, pkt)