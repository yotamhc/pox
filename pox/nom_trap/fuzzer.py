#!/usr/bin/env python
# Nom nom nom nom

# TODO: future feature: colored cli prompts to make packets vs. crashes
#       vs. whatever easy to distinguish

# TODO: rather than just prompting "Continue to next round? [Yn]", allow
#       the user to examine the state of the network interactively (i.e.,
#       provide them with the normal POX cli + the simulated events

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *

from pox.topology.topology import *
from pox.openflow.libopenflow_01 import ofp_action_output
import pox.nom_trap.default_topology as default_topology
from fuzzer_entities import *
from event_generator import EventGenerator

import sys
import threading
import signal
import subprocess
import socket
import time
import random
import os

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
    def __init__(self):
      Topology.__init__(self)
      self.listenTo(core)
      self.core_up = False
      
      # List of the event handlers we are waiting before starting the fuzzer
      # loop. Values of the dict will be set to the event handler.
      self._required_event_handlers = {
        SwitchJoin : None,
      }
     
      self.running = False
      
      # TODO: make it easier for client to tweak these
      self.failure_rate = 0.5
      self.recovery_rate = 0.5
      self.drop_rate = 0.5
      self.delay_rate = 0.5
      self.of_message_generation_rate = 0.5
      
      # Logical time (round #) for the simulation execution
      self.logical_time = 0
      # TODO: take a timestep parameter for how long
      # each logical timestep should last?
      
      # TODO: allow the user to specify a topology
      # The next line should cause the client to register additional
      # handlers on switch entities
      default_topology.populate(self)
      
      # events for this round
      self.sorted_events = []
      self.in_transit_messages = set()
      self.dropped_messages = set()
      self.failed_switches = set()
      self.failed_controllers = set()
      self.cancelled_timeouts = set() # ?
      
      # Statistics to print on exit
      self.packets_sent = 0
      
      # Make execution deterministic to allow the user to easily replay
      self.seed = 0.0
      self.random = random.Random(self.seed)
      self.event_generator = EventGenerator(self.random)
      
      # TODO: future feature: log all events, and allow user to (interactively)
      # replay the execution
      # self.replay_logger = ReplayLogger()
      # Write the seed out to the replay log as the first 4 bytes
      
      # TODO: future feature: allow the user to interactively choose the order
      # events occur for each round, whether to delay, drop packets, fail nodes,
      # etc. 
      # self.failure_lvl = [
      #   NOTHING,    # Everything is handled by the random number generator
      #   CRASH,      # The user only controls node crashes and restarts
      #   DROP,       # The user also controls message dropping
      #   DELAY,      # The user also controls message delays
      #   EVERYTHING  # The user controls everything, including message ordering
      # ]  
      
    def _handle_GoingUpEvent(self, going_up_event):
      log.debug("going up event!")
      self.core_up = True
      if self._ready_to_start():
        self.start()
      
    def event_handler_registered(self, event_type, handler):
      """ 
      A client just registered an event handler on us
      
      TODO: I'm pretty sure we're going to need a reference to the client
      itself, not just its handler
      """
      log.debug("event handler registered %s %s" % (str(event_type), str(handler)))
      
      if event_type in self._required_event_handlers:
        self._required_event_handlers[event_type] = handler
        
      if self._ready_to_start():
        self.start()
      
    def _ready_to_start(self):
      if None in self._required_event_handlers.values():
        return False
      
      if not self.core_up:
        return False
      
      return True
    
    def start(self):
      """
      Start the fuzzer loop!
      """
      # TODO: I need to interpose on all client calls to recoco Timeouts or
      # other blocking tasks... we're just running in an infinite loop here, and
      # won't be yielding to recoco. We don't need the default of_01_Task, since
      # we're simulating all of our own network elements
      log.debug("Starting fuzz loop")
      
      self.running = True
      
      while(self.running):
        self.logical_time += 1
        self.trigger_events()
        print("Round %d completed." % self.logical_time)
        answer = raw_input('Continue to next round? [Yn]')
        if answer != '' and answer.lower() != 'y':
          self.stop()
          
        # TODO: print out the state of the network at each timestep? Take a
        # verbose flag..
        
    def stop(self):
      self.running = False
      print "Fuzzer stopping..."
      print "Total rounds completed: %d" % self.logical_time
      print "Total packets sent: %d" % self.packets_sent
      os.sys.exit()
      
    # ============================================ #
    #     Bookkeeping methods                      #
    # ============================================ #
    def all_switches(self):
      """ Return all switches currently registered """
      return self.getEntitiesOfType(MockOpenFlowSwitch)
    
    def crashed_switches(self):
      """ Return the switches which are currently down """
      return filter(lambda switch : switch.failed, self.all_switches())
    
    def live_switches(self):
      """ Return the switches which are currently up """
      return filter(lambda switch : not switch.failed, self.all_switches())
    
    # ============================================ #
    #      Methods to trigger events               #
    # ============================================ #
    def trigger_events(self):
      self.check_in_transit()
      self.check_crashes()
      self.check_timeouts()
      self.fuzz_traffic()

    def check_in_transit(self):
      # Decide whether to delay, drop, or deliver packets
      # TODO: interpose on connection objects to grab their messages
      # TODO: track messages from switch to switch, not just switch to controller
      # REVIEW: are these (a) /OF control plane messages/ or (b) packets/? 
      # if (b) name accordingly
      # if (a) AFAIK, OF control plane should never be dropped, so not sure if the functionality is needed here.
      # This the delaying models switch specific queuing, it should maybe be implemented by the switch?
      for msg in self.in_transit_messages:
        if self.random.random() < self.delay_rate:
          # Delay the message
          msg.delayed_rounds += 1
        elif self.random.random() < self.drop_rate:
          # Drop the message
          # TODO: Don't drop TCP messages... that would just be silly.
          self.dropped_messages.add(msg)
          self.in_transit_messages.remove(msg)
        else:
          # TODO: deliver the message
          pass
    
    def check_crashes(self):
      # Decide whether to crash or restart switches, links and controllers
      def crash_switches():
        crashed = set()
        for switch in self.live_switches():
          if self.random.random() < self.failure_rate:
            log.info("Crashing switch %s" % str(switch))
            switch.fail()
            crashed.add(switch)
        return crashed
            
      def restart_switches(crashed_this_round):
        for switch in self.crashed_switches():
          if switch in crashed_this_round:
            continue
          if self.random.random() < self.recovery_rate:
            log.info("Rebooting switch %s" % str(switch))
            switch.recover()

      def cut_links():
        pass

      def repair_links():
        pass

      def crash_controllers():
        pass

      def restart_controllers():
        pass
            
      crashed = crash_switches()
      restart_switches(crashed)
      cut_links()
      repair_links()
      crash_controllers()
      restart_controllers()

    def check_timeouts(self):
      # Interpose on timeouts
      pass
    
    def fuzz_traffic(self):
      # randomly generate messages from switches
      # TODO: future feature: trace-driven packet generation
      for switch in self.live_switches():
        if self.random.random() < self.of_message_generation_rate:
          log.debug("triggering a random event")
          # trigger a random event handler.
          # TODO: trigger more than one in a given round?
          num_relevant_event_types = len(switch._eventMixin_handlers)
          if num_relevant_event_types == 0:
            log.debug("No registered event handlers for switch %s found" % str(switch))
            continue
          event_type = self.random.choice(switch._eventMixin_handlers.keys())
          event = self.event_generator.generate(event_type, switch)
          handlers = switch._eventMixin_handlers[event_type]
          # TODO: we need a way to distinguish client handler's from other
          # handlers. For now just assume that the first one is the client's.
          # handlers are tuples: (priority, handler, once, eid)
          handler = handlers[0][1]
          handler(event) 
          
    # TODO: do we need to define more event types? e.g., packet delivered,
    # controller crashed, etc. An alternative might be to just generate
    # sensible traffic, and let the switch raise its own events.
    
    def dump_csv(self):
      """
      For each switch in the network, dump it's Flow Table in csv format, 
      for consumption by Anteater
      
      Returns a hash from switch_impl -> csv output
      """
      switch_impl2csv = {}
      def switch_csv(switch):
        """ Dump the Flow Table for a single switch """
        # TODO: implement this as a method on SwitchImpl! Will need a mapping
        #       of port -> next hop IP address
        #
        #       Only problem with putting it in SwitchImpl is that port -> next hop IP
        #       assumes that the switch works at Layer 3...
        lines = []
        for entry in switch.table._table:
          match, _, actions = entry 
           
          dst, prefix = match.get_nw_dst()
          if dst is None:
            dst = "0.0.0.0"
          full_dst = '/'.join((str(dst), str(prefix)))
          
          # Default drop (no output action specified)
          output_interface = "drop"
          gateway = "DIRECT"
          
          for action in actions:
            # TODO: assume that there is only one ofp_action_output in the list of actions?
            if type(action) == ofp_action_output:
              port_no = action.port
              port = switch.ports[port_no]
              port_name = port.name
              if port_name == "":
                port_name = "eth%d" % port_no
              output_interface = port_name
              gateway = switch.outgoing_links[port].end_port.ip_addr
                      
          # TODO: figure out what tags are used for in Anteater
          tags = "O"
      
          csv = ','.join((full_dst, gateway, output_interface, tags))
          lines.append(csv)
          
        # Now manually add in loopback devices
        for port in switch.ports.values():
          csv = "%s/32,DIRECT,loopback 1,O" % str(port.ip_addr)
          lines.append(csv)
        
        # TODO: problem! Anteater assumes destination-based routing. OpenFlow is
        # (source, destination)-based routing.
        return "\n".join(lines)
      
      # Now, get a csv string for each switch
      for switch in self.getEntitiesOfType(MockOpenFlowSwitch):
        # TODO: don't assume that the switch has a reference to the implementation! For emulation, will need 
        #       to fetch table of the implementation through a more realistic means
        switch_impl = switch.switch_impl
        csv_output = switch_csv(switch_impl)
        switch_impl2csv[switch_impl] = csv_output
      
      return switch_impl2csv  
        
if __name__ == "__main__":
  pass
