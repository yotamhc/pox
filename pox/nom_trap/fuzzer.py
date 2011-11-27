#!/usr/bin/env python
# Nom nom nom nom

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *

from pox.topology.topology import *
import pox.nom_trap.default_topology as default_topology

import sys
import threading
import signal
import subprocess
import socket
import time
import random

log = core.getLogger()

class FuzzTester (Topology):
    # TODO: future feature: split this into Manager superclass and
    # simulator, emulator subclasses. Use vector clocks to take
    # consistent snapshots of emulated network
    """
    This is part of a testing framework for controller applications. It 
    acts as a replacement for pox.topology.
    
    Given a set of event handlers (registered by a controller application),
    it will inject intelligently chosen mock events (and observe
    their responses?)
    """
    
    # When the client registers an event handler, replace the value with
    # a reference to it, rather than None. Will start when no None values
    # remain
    _required_event_handlers = {
       SwitchJoin : None
    }
    
    def __init__(self):
      Topology.__init__(self)
     
      self.running = False
      
      # TODO: make it easier for client to tweak these
      self.failure_rate = 0.0
      self.recovery_rate = 0.0
      self.drop_rate = 0.0
      self.delay_rate = 0.0
      
      # Logical time for the simulation execution
      self.logical_time = 0
      # TODO: take a timestep parameter for how long
      # each logical timestep should last?
      
      # TODO: allow the user to specify a topology
      # This should cause the client to register additional handlers on
      # switch entities
      default_topology.populate(self)
      
      self.sorted_events = []
      self.in_transit_messages = []
      self.failed_switches = []
      self.failed_controllers = []
      self.delated_messages = []
      self.dropped_messages = []
      # self.canceled_timeouts = [] ?
      
      # Statistics to print on exit
      self.packets_sent = 0
      
      # Make execution deterministic to allow the user to easily replay
      self.seed = 0.0
      self.random = random.Random(self.seed)
      
      # TODO: future feature: log all events, and allow user to (interactively)
      # replay the execution
      # self.replay_logger = ReplayLogger()
      # Write the seed out to the replay log as the first 4 bytes
      
      # TODO: future feature: allow the user to interactively choose the order
      # events occur for each round, whether to delay, drop packets, fail nodes,
      # etc. 
      # FailureLvl [
      #   NOTHING,    // Everything is handled by the random number generator
      #   CRASH,      // The user only controls node crashes and restarts
      #   DROP,      // The user also controls message dropping
      #   DELAY,      // The user also controls message delays
      #   EVERYTHING    // The user controls everything, including message ordering
      # ]  
      
    def event_handler_registered(self, event_type, handler):
      """ 
      A client just registered an event handler on us
      
      TODO: I'm pretty sure we're going to need a reference to the client
      itself, not just its handler
      """
      
      log.debug("event handler registered %s %s" % (str(event_type), str(handler)))
      
      if self.ready_to_start(event_type, handler):
        self.start()
      
    def ready_to_start(self, event_type, handler):
      if event_type in self._required_event_handlers:
        self._required_event_handlers[event_type] = handler
        
      if None in self._required_event_handlers.values():
        return False
      
      return True
    
    def start(self):
      """
      Start the fuzzer loop!
      """
      # TODO: I need to interpose on all client calls to recoco Timeouts or
      # other block tasks... we're just running in an infinite loop here, and
      # won't be yielding to recoco. We don't need of_01_Task, since we're 
      # simulating all of our own network elements
      
      log.debug("Starting fuzz loop")
      
      while(self.running):
        self.logical_time += 1
        self.trigger_events()
        break
        
    def stop(self):
      self.running = False
      # TODO; print out statistics
      
    # ============================================ #
    #      Methods to trigger events               #
    # ============================================ #
    def check_in_transit(self):
      # Decide whether to delay, drop packets
      pass
    
    def check_crash(self):
      # Decide whether to crash, restart switches, controllers
      pass
    
    def check_timeouts(self):
      # Interpose on timeouts
      pass
    
    def trigger_events(self):
      self.check_in_transit()
      self.check_crash()
      self.check_timeouts()
      # TODO: print out the state of the network at each timestep?
    
    # TODO: do we need to define more event types? e.g., packet delivered,
    # controller crashed, etc.
 
    def send_packet(self, msg):
      pass
    
    def deliver_packet(self, msg):
      pass
      
    # ============================================ #
    #      Methods to crash or restart nodes       #
    # ============================================ #
    def crash_switch(self, dpid):
      pass
    
    def restart_switch(self, dpid):
      pass
    
    def cut_link(self, link):
      pass
   
    def repair_link(self, link):
      pass
  
    def crash_controller(self, id):
      pass
     
    def restart_controller(self, id):
      pass
         
if __name__ == "__main__":
  pass
