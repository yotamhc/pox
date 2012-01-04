#!/usr/bin/env python
# Nom nom nom nom

# TODO: there is currently a dependency on the order of initialization of
# client and server... . for example:

#  $ pox.py nom_client nom_server    # blocks indefinitely

# whereas

#  $ pox.py nom_server nom_client    # works

from pox.core import core, UpEvent
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *
from pox.lib.recoco.recoco import *

from pox.controllers.pyro4_daemon_loop import PyroLoop

import sys
import threading
import signal
import time

import Pyro4
import Pyro4.util

sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()
 
class DistributedController(EventMixin):
  """
  Keeps a copy of the Nom in its cache. Arbitrary controller applications
  can be implemented on top of NomClient through inheritance. Mutating calls to 
  self.nom transparently write-through to the NomServer

  Visually,  NomClient's connect to the NomServer through
  the following interfaces:

  ==========================                            ==========================
  |    NomClient           |                            |    NomServer           |
  |                        |   any mutating operation   |                        |
  |                        |  -------------------->     |server.put(nom)         |
  |                        |                            |                        |
  |          client.       |   cache invalidation, or   |                        |
  |            update_nom()|   network event            |                        |
  |                        |   <-------------------     |                        |
  ==========================                            ==========================
  """
  def __init__(self, server):
    """
    Note that server may be a direct reference to the NomServer (for simulation), or a Pyro4 proxy
    (for emulation)
    """
    self.server = server
    self.topology = None
    daemon = Pyro4.Daemon()
    self.uri = daemon.register(self)
    PyroLoop(daemon)
    
    # Can't register with server until Core is up (TODO: since...)
    # pre: core isn't already up
    core.addListener(UpEvent, self._register_with_server)

  def _register_with_server(self, event):
    log.debug("self.server %s" % self.server)
    self.server.register_client(self)
    log.debug("registered with NomServer")
    self.nom = self.server.get()
    log.debug("Fetched nom from nom_server")

  # This should really be handler for an Event defined by pox.core
  def update_nom(self, topology):
    """
    According to Scott's philosophy of SDN, a control application is a
    function: F(view) => configuration

    This method is the entry point for the POX platform to update the
    view. 

    The POX platform may invoke it in two situations:
      i.  NomServer will invalidate this client's cache in the
          case where another client modifies its copy of the NOM

      ii. Either POX or this client (should) register this method as a
          handler for network events.
    """
    log.info("Updating nom from %s to %s " % (self.topology, topology))
    self.topology = topology
    # Register subclass' event handlers
    self.listenTo(topology)
    # TODO: react to the change in the topology, by firing queued events to 
    # subclass' ?
    return True
