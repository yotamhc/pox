"""
This module mocks out openflow switches. 

This is only for simulation, not emulation. For simluation, we run everything
in the same process, and mock out switch behavior. This way it's super easy
to track the state of the system at any point in time (total ordering of events).

Eventually, we want to test the entire stack. We're also going to want to
allow for the possibility of consistency bugs, which will imply separate
processes. To emulate, we'll want to :
    - Boot up MiniNet with some open v switches
    - inject randomly generated traffic to the switches themselves. This brings up two questions:
        * Is it possible to package a MiniNet VM as part of POX? That would
          go against the grain of POX's python-only, pre-packaged everything
          philosophy.
        * Can this module successfully interpose on all messages between vswitches
          and the control application?
"""

from pox.openflow.topology import *
from pox.openflow.switch_impl import SwitchImpl
from pox.openflow.of_01 import Connection
from pox.core import core

log = core.getLogger()

# TODO: model hosts in the network!

class MockSocket(object):
  """ 
  Send bytes directly from object to object, rather than opening a real socket
  
  Requires that both ends of the socket maintain a Connection object
  """
  def __init__(self, receiver_connection=None):
    self.receiver_connection = receiver_connection
    # Single element queue
    self.read_buffer = "" 
    # In case the user tries to send() before receiver_connection is set. This
    # is a bit of a hack around for a mutual dependency between sender and receiver
    # sockets when trying to initialize new connections.
    self.send_queue = []  
    
  def set_receiver_connection(self, receiver_connection):
    self.receiver_connection = receiver_connection
    for unsent_msg in self.send_queue:
      self.send(unsent_msg)
      
    self.send_queue = []
    
  def send(self, msg):
    msg_len = len(msg)
    # TODO: let fuzzer interpose on this transfer, to delay or drop packets
    if self.receiver_connection is None:
      # receiver_connection hasn't been set yet
      self.send_queue.append(msg) 
      return msg_len # Fake it -- pretend we sent the message already
      
    # Push the bits
    self.receiver_connection.sock.read_buffer = msg
    # Cause them to read the bits
    self.receiver_connection.read()
    return msg_len
    
  def recv(self, len):
    msg = self.read_buffer
    self.read_buffer = ""
    return msg
  
  def shutdown(self, sig=None):
    pass
  
  def close(self):
    pass
  
  def fileno(self):
    return -1
  
class MockOpenFlowSwitch (OpenFlowSwitch):
  """
  NOTE: /not/ a mock switch implementation, only a mock NOM entity.
        For the mock switch implementation we use pox.openflow.switch_impl
  """
  def __init__ (self, dpid, ofp_phy_ports):
    OpenFlowSwitch.__init__(self, dpid)
    self.failed = False
    # Instantiate the Switch Implementation here. We don't use self.switch_impl
    # to communicate directly with the switch, rather, we go through a Connection
    # object as in the normal OpenFlowSwitch implementation.
    self.name = "switch#%d" % dpid
    self.switch_impl = SwitchImpl(dpid, MockSocket(), name=self.name, ports=ofp_phy_ports)
    self.connect(self.switch_impl)
    
  def connect(self, switch_impl):
    # Note that OpenFlowSwitch._setConnection won't be called externally,
    # (at least in simulation mode), since pox.core isn't raising any
    # ConnectionUp events. To make sure that self.capabilities et al are 
    # set properly, instead instantiate our own Connection object here.
    # Instantiating a Connection object will cause a ofp_hello message to 
    # be sent to the MockSwitchImpl. When the MockSwitchImpl replies, the
    # Connection will send a features request. Upon receiving the features
    # request, we call OpenFlowSwitch._setConnection to set
    # self.capabilities et al as usual.
    
    # In case we are re-connecting with the switch, double check 
    # that switch_impl.socket.receiver_connection is None
    switch_impl._connection.sock.receiver_connection = None
    # This will initiate the handshake
    connection = Connection(MockSocket(switch_impl._connection))
    # Since switch_impl.socket.receiver_connection hasn't been set, 
    # switch_impl will not immediately reply to the OFP_HELLO. This gives us
    # the opportunity to register a ConnectionUp handler before the handshake
    # is complete. 
    connection.addListener(ConnectionUp, self._handle_ConnectionUp)
    # Now set switch_impl.socket.receiver_connection to us
    switch_impl._connection.sock.set_receiver_connection(connection)
    # Now the handshake should complete (instantaneously)

  def _handle_ConnectionUp(self, event):    
    self._setConnection(event.connection, event.ofp) 
    
  def fail(self):
    if self.failed:
      log.warn("Switch already failed")
    self.failed = True
    # TODO: depending on the type of failure, a real switch failure
    # might not lead to an immediate disconnect
    self._connection.disconnect()
    
  def recover(self):
    if not self.failed:
      log.warn("Switch already up")
    self.failed = False
    self.connect(self.switch_impl)
    
class Link():
  """
  Temporary stand in for Murphy's graph-library for the NOM.
   
  Note: Directed!
  """
  def __init__(self, start_switch_impl, start_port, end_switch_impl, end_port):
    self.start_switch_impl = start_switch_impl
    self.start_port = start_port
    self.end_switch_impl = end_switch_impl
    self.end_port = end_port
          
class Message (object):
  """ So we can track a message throughout the network """
  def __init__(self, msg):
    self.in_transit = False
    self.delayed_rounds = 0
    self.msg = msg
