"""
This module mocks out openflow switches. 

It just occurred to me that we don't really want to mock out network elements...
Ultimately, our goal is to test the entire stack! So really, we should be using 
MiniNet to boot open v switches, and then inject randomly generated traffic to the 
switches themselves. This brings up two questions:
  - Is it possible to package a MiniNet VM as part of POX? That would
    go against the grain of POX's python-only, pre-packaged everything
    philosophy.
  - Can this module successfully interpose on all messages between vswitches
    and the control application?
"""

from pox.openflow.topology import *
from pox.openflow.of_01 import Connection
from pox.core import core

log = core.getLogger()

# TODO: model hosts in the network!

class MockConnection (Connection):
  """
  A mock connection to a switch
  
  TODO: This is the wrong layer of abstraction to be mocking out...
        what we really want is a "Forwarding Engine" abstraction that models
        the flow tables of the switch. The client shouldn't have to send any
        messages at all.
  """
  def __init__ (self, switch):
    self.switch = switch
    self.data_sent = []
    Connection.__init__(self, None)
    
  # Overwrite all of the following entries so we don't 
  # try to invoke methods on self.sock
  def fileno (self):
    return -1

  def disconnect(self, hard = True):
    self.disconnected = True
    
  def reconnect(self):
    self.disconnected = False 
  
  def send (self, data):
    log.debug("Client sending data %s on switch %s" % (str(data), str(self.switch)))
    
    if self.disconnected:
      log.warn("Switch disconnected, not delivering message")
      return
    
    # TODO: make this do something. We should have a separate forwarding engine entity
    self.data_sent.append(data)

  def read (self):
    return []

  def __str__ (self):
    return "[MockCon " + str(self.ID) + "/" + str(self.dpid) + "]"

class MockOpenFlowSwitch (OpenFlowSwitch):
  """
  NOTE: /not/ a mock switch implementation, only a mock NOM entity.
        For the mock switch implementation we use pox.lib.pylibopenflow.switch
  """
  def __init__ (self, dpid):
    OpenFlowSwitch.__init__(self, dpid)
    # TODO: the self param should really be a reference to pylibopenflow.switch
    self.connection = MockConnection(self)
    self.failed = False
    # TODO: set ports?
    
  def fail(self):
    if self.failed == True:
      log.warn("Switch already failed")
    self.failed = True
    self.connection.disconnect()
    
  def recover(self):
    if not self.failed:
      log.warn("Switch already up")
    self.failed = False
    self.connection.reconnect()
    
    
class Message (object):
  """ So we can track a message throughout the network """
  def __init__(self, msg):
    self.in_transit = False
    self.delayed_rounds = 0
