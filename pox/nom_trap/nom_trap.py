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
  This is the interposition layer of the pox testing framework
  It interposes on on pox.topology to inject mock events into
  controller applications.
  
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
    
  # If you want to do something special with the event handler registation, 
  # define a method here rather than None
  _relevant_EventTypes = {
    SwitchJoin : None,
    SwitchLeave : None,
    HostJoin : None,
    HostLeave : None,
    EntityJoin : None,
    EntityLeave : None
  }
  
  def __init__(self):
    # We wait for the client to register themselves with us
    self.fuzzer = FuzzTester()
 
  def addListener (self, eventType, handler, once=False, weak=False, priority=None, byName=False):  
    """ Interpose on addListener to notify our fuzzer when to start """
    # TODO: pretty sure we're going to need a reference to the client, not
    # just its handler. Add an extra arg to addListener?
    log.debug("addListener called, handler=%s" % str(handler))
    """
    We overwrite this method so that we are notified when a client
    registers a handler
    """
    Topology.addListener(self.fuzzer, eventType, handler, once, weak, priority, byName)
    
    if eventType in self._relevant_EventTypes:
      if self._relevant_EventTypes[eventType] is None:
        self.fuzzer.event_handler_registered(eventType, handler)
      else:
        self._relevant_EventTypes[eventType](eventType, handler)
        
  def __getattr__( self, name ):
    """
    Delegate unknown attributes to fuzzer (we just interpose)
    """
    return getattr( self.fuzzer, name )
      
if __name__ == "__main__":
  pass
