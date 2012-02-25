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

from pox.openflow.libopenflow_01 import ofp_action_output
import pox.debugger.topology_generator as topology_generator
from pox.debugger.debugger_entities import *
from event_generator import EventGenerator
from invariant_checker import InvariantChecker

import sys
import threading
import signal
import subprocess
import socket
import time
import random
import os

log = core.getLogger("debugger")

class msg():
  BEGIN = '\033[1;'
  END = '\033[1;m'

  GRAY, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, CRIMSON = map(lambda num: str(num) + "m", range(30, 39))
  B_GRAY, B_RED, B_GREEN, B_YELLOW, B_BLUE, B_MAGENTA, B_CYAN, B_WHITE, B_CRIMSON =  map(lambda num: str(num) + "m", range(40, 49))

  @staticmethod
  def interactive(message):
    # todo: would be nice to simply give logger a color arg, but that doesn't exist...
    print msg.BEGIN + msg.WHITE + message + msg.END

  @staticmethod
  def event(message):
    print msg.BEGIN + msg.CYAN + message + msg.END

  @staticmethod
  def raw_input(message):
    prompt = msg.BEGIN + msg.WHITE + message + msg.END
    return raw_input(prompt)

  @staticmethod
  def success(message):
    print msg.BEGIN + msg.B_GREEN + msg.BEGIN + msg.WHITE + message + msg.END

  @staticmethod
  def fail(message):
    print msg.BEGIN + msg.B_RED + msg.BEGIN + msg.WHITE + message + msg.END

class FuzzTester (EventMixin):
  # TODO: future feature: split this into Manager superclass and
  # simulator, emulator subclasses. Use vector clocks to take
  # consistent snapshots of emulated network
  
  # TODO: do we need to define more event types? e.g., packet delivered,
  # controller crashed, etc. An alternative might be to just generate
  # sensible traffic, and let the switch raise its own events. 
  
  _core_name = "debugger"

  _wantComponents = ["topology", "openflow_topology"]

  """
  This is part of a testing framework for controller applications. It
  acts as a replacement for pox.topology.

  Given a set of event handlers (registered by a controller application),
  it will inject intelligently chosen mock events (and observe
  their responses?)
  """
  def __init__(self, num_controllers):
    self.num_controllers = num_controllers

    self.core_up = False
    self.listenTo(core)
    if not core.listenToDependencies(self, self._wantComponents):
      self.topology = None
      log.debug("still waiting for my required components: %s"% repr(self._wantComponents))
    else:
      self.topology = core.topology
      log.debug("ready on initialization")

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
    self.invariant_checker = InvariantChecker(self)

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

  def _handle_ComponentRegistered (self, event):
    """
    A component was registered with pox.core. If we were dependent on it,
    check again if all of our dependencies are now satisfied so we can boot.
    """
    if core.listenToDependencies(self, self._wantComponents):
      self.topology = core.topology
      log.info("initialization completed")
      return EventRemove

  def _handle_GoingUpEvent(self, going_up_event):
    log.debug("going up event!")
    self.core_up = True
    if self._ready_to_start():
      self.start()
    else:
      log.debug("Core is up, but not all controllers registered. Waiting..")
      self.update_listener = self.topology.addListener(Update, self._handle_topology_update)

  def _handle_topology_update(self, update_event):
    log.debug("update event. checking if we're ready...")
    if self._ready_to_start():
      self.topology.removeListener(self.update_listener)
      self.start()

  def _ready_to_start(self):
    controllers = self.topology.getEntitiesOfType(Controller, True)
    if len(controllers) < self.num_controllers:
      log.debug("_ready_to_start: waiting for %d controllers, have so far: %s" % (self.num_controllers, str(controllers)) )
      return False

    handshake_pending_controllers = filter(lambda c: not c.handshake_complete, controllers)
    if len(handshake_pending_controllers) > 0:
      log.debug("_ready_to_start: controllers with pending handshake: " + str(handshake_pending_controllers))
      return False

    if not self.core_up:
      log.debug("_ready_to_start: Core not yet up")
      return False

    # TODO: need a mechanism for signaling  when the distributed controller handshake has completed

    return True

  def start(self):
    """
    Start the fuzzer loop!
    """
    log.debug("Starting fuzz loop")

    # TODO: allow the user to specify a topology
    # The next line should cause the client to register additional
    # handlers on switch entities
    (self.panel, self.switches) = topology_generator.populate()

    self.loop()

  def loop(self):
    self.logical_time += 1
    self.trigger_events()
    msg.event("Round %d completed." % self.logical_time)
    # TODO: print out the state of the network at each timestep? Take a
    # verbose flag..
    self.invariant_check_prompt()
    answer = msg.raw_input('Continue to next round? [Yn]').strip()
    if answer != '' and answer.lower() != 'y':
      self.stop()
    else:
      # loop again!
      core.callLater(self.loop)

  def stop(self):
    self.running = False
    msg.event("Fuzzer stopping...")
    msg.event("Total rounds completed: %d" % self.logical_time)
    msg.event("Total packets sent: %d" % self.packets_sent)
    os._exit(0)

  # ============================================ #
  #     Bookkeeping methods                      #
  # ============================================ #
  def all_switches(self):
    """ Return all switches currently registered """
    return self.switches

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
          msg.event("Crashing switch %s" % str(switch))
          switch.fail()
          crashed.add(switch)
      return crashed

    def restart_switches(crashed_this_round):
      for switch in self.crashed_switches():
        if switch in crashed_this_round:
          continue
        if self.random.random() < self.recovery_rate:
          msg.event("Rebooting switch %s" % str(switch))
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
        # FIXME do something smarter here than just generate packet ins
        log.debug("triggering a random event")
        # event_type = self.random.choice(switch._eventMixin_handlers.keys()) 
        event_type = PacketIn
        # Generates a
        self.event_generator.generate(event_type, switch)

  def invariant_check_prompt(self):
    answer = msg.raw_input('Check Invariants? [Ny]')
    if answer != '' and answer.lower() != 'n':
      msg.interactive("Which one?")
      msg.interactive("  'l' - loops")
      msg.interactive("  'b' - blackholes")
      msg.interactive("  'r' - routing consistency")
      msg.interactive("  'c' - connectivity")
      answer = msg.raw_input("  ")
      result = None
      if answer.lower() == 'l':
        result = self.invariant_checker.check_loops()
      elif answer.lower() == 'b':
        result = self.invariant_checker.check_blackholes()
      elif answer.lower() == 'r':
        result = self.invariant_checker.check_routing_consistency()
      elif answer.lower() == 'c':
        result = self.invariant_checker.check_connectivity()
      else:
        log.warn("Unknown input...")

      if not result:
        return
      elif result == "sat":
        msg.success("Invariant holds!")
      else:
        msg.fail("Invariant violated!")




if __name__ == "__main__":
  pass
