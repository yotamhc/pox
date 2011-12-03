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
  """ Send bytes directly from object to object, rather than opening a real socket """
  def __init__(self, receiver):
    self.receiver = receiver
    self.read_buffer = "" # Single element queue
    
  def send(self, msg):
    # TODO: let fuzzer interpose on this transfer, to delay or drop packets
    # Push the bits
    self.receiver.connection.sock.read_buffer = msg
    # Cause them to read the message
    self.receiver.connection.read()
    return len(msg)
    
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
  def __init__ (self, dpid):
    OpenFlowSwitch.__init__(self, dpid)
    self.failed = False
    # Instantiate the Switch Implementation here
    self.switch_impl = SwitchImpl(dpid, MockSocket(self), ports=[])
    self.connect()
    
  def connect(self):
    # Note that OpenFlowSwitch._setConnection won't be called externally,
    # (at least in simulation mode), since pox.core isn't raising any
    # ConnectionUp events. To make sure that self.capabilities et al are 
    # set properly, instead instantiate our own Connection object here.
    # Instantiating a Connection object will case a ofp_hello message to 
    # be sent to the MockSwitchImpl. When the MockSwitchImpl replies, the
    # Connection will send a features request. Upon receiving the features
    # request, we call OpenFlowSwitch._setConnection to set
    # self.capabilities et al as usual.
    connection = Connection(MockSocket(self.switch_impl))
    # Since the socket transfers occur immediately, it should be the case
    # that the handshake has already completed by this point:
    #     self                                       switch
    #                   -> hello
    #                   <- hello
    #                   -> feature request
    #                   <- feature reply
    #                   -> barrier request
    #                   <- barrier in
    # 
    # There is a problem with this... namely, Connection will already have raised
    # the ConnectionUp event with the corresponding feature reply message.
    # Essentially, the problem is that before we have a change to register an event
    # handler, the event will already have been triggered. I can think of a few potential
    # solutions to this issue:
    #   i.    Fabricate a feature_reply (+easy to do since we have a reference to switch_impl)
    #   ii.   Add a random timeout to MockSocket delivery (+more realistic, -concurrency issues)
    #   iii.  Add an "predefined event handler list" argument to OpenFlowSwitch.__init__ (-awkward)
    #   iv.   Add a primitive to EventMixin to ensure that all previously triggered events are executed
    #         for newly registered event handlers (+may solve other event handler registration ordering
    #         issues in POX, -requires a lot of state)
    #
    # For now, we'll go with option i. 
    fabricated_features_msg = self.switch_impl._generate_features_message()
    self._setConnection(connection, fabricated_features_msg)
    
  def fail(self):
    if self.failed:
      log.warn("Switch already failed")
    self.failed = True
    self._connection.disconnect()
    
  def recover(self):
    if not self.failed:
      log.warn("Switch already up")
    self.failed = False
    self.connect()
    
class Link():
  """ Punt on Murphy's graph-library for the NOM """
  pass
          
class Message (object):
  """ So we can track a message throughout the network """
  def __init__(self, msg):
    self.in_transit = False
    self.delayed_rounds = 0
    self.msg = msg
