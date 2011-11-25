#!/usr/bin/env python
# Nom nom nom nom

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *
from pox.topology.topology import *
from pox.nom_trap.fuzzer import FuzzTester

import sys
import threading
import subprocess
import socket
import time

log = core.getLogger()

class NomTrap (EventMixin):
  """
  This is a testing framework for controller applications. It interposes on
  on pox.topology to inject mock events into controller applications.
  
  We can think of the controller application as a function:
      F(view) => configuration

  This property allows us to treat the controller application as a black box:
  we feed it (intelligently chosen) views, and observe the configuration it
  produces without having to worry about the actual logic that the
  application executes internally.
  
  This allows us to build up a database of:
     F(view) => configuration

  mappings for the client, which we can later (or concurrently) use to test
  invariants.
  """
    
  # we want to be core.topology, so that we can interpose transparently
  _core_name = "topology"
  
  def notify_SwitchJoin_registration(self, handler):
    """ Someone just registered a handler for SwitchJoin """
    log.debug("SwitchJoin handler registered")
    self.fuzzer.switchjoin_registration(handler)
   
  # The event types we want to be notified of listener registrations for
  _relevant_EventTypes = {
    SwitchJoin : notify_SwitchJoin_registration,
    SwitchLeave : None,
    HostJoin : None,
    HostLeave : None,
    EntityJoin : None,
    EntityLeave : None
  }
  
  def __init__(self):
    # We wait for the client to register themselves with us
    self.fuzzer = FuzzTester()
    # alternatively, delegate all missing attributes to self.fuzzer?
    self._eventMixin_events = self.fuzzer._eventMixin_events

  def addListener (self, eventType, handler, once=False, weak=False, priority=None, byName=False):  
    log.debug("addListener called, handler=%s" % str(handler))
    """
    We overwrite this method so that we are notified when a client
    registers a handler
    """
    if eventType in self._relevant_EventTypes:
      # For now, we assume that the client was the one registering the handler...
      # TODO: add an argument to addListener which is a reference to the registrator?
      self._relevant_EventTypes[eventType](self, handler)
      
    EventMixin.addListener(self, eventType, handler, once, weak, priority, byName)
  
if __name__ == "__main__":
 pass
