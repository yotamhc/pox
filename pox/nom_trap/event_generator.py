
from pox.openflow import PacketIn
from pox.openflow.libopenflow_01 import ofp_packet_in
from pox.lib.packet.ethernet import *
from pox.lib.packet.ipv4 import *
from pox.lib.packet.icmp import *

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
    # randomly choose an in port. TODO: factor choosing a random elt out
    rand_index = self.random.randint(0,len(switch.ports)-1)
    in_port = switch.ports[switch.ports.keys()[rand_index]] # .number?
    e = ethernet()
    # TODO: need a better way to create random MAC addresses
    e.src = EthAddr(struct.pack("Q",self.random.randint(1,0xFF))[:6])
    e.dst = in_port.hwAddr
    e.type = ethernet.IP_TYPE
    ipp = ipv4()
    ipp.protocol = ipv4.ICMP_PROTOCOL
    ipp.srcip = IPAddr(self.random.randint(0,0xFFFFFFFF))
    ipp.dstip = IPAddr(self.random.randint(0,0xFFFFFFFF))
    ping = icmp()
    ping.type = TYPE_ECHO_REQUEST
    ping.payload = "PingPing" * 6
    ipp.payload = ping
    e.payload = ipp
    
    buffer_id = self.random.randint(0,0xFFFFFFFF)
    reason = None
    
    pkt = ofp_packet_in(data = e.pack(),
                        in_port = in_port.number,
                        buffer_id = buffer_id,
                        reason = reason)
    
    return PacketIn(switch, pkt)