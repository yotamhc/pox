#!/usr/bin/env python
# Nom nom nom nom

# TODO: there is currently a dependency on the order of initialization of
# client and server... . for example:

#  $ pox.py nom_client nom_server    # blocks indefinitely

# whereas

#  $ pox.py nom_server nom_client    # works

from pox.core import core, UpEvent
from pox.lib.revent.revent import EventMixin
import pox.messenger.messenger as messenger
import pox.topology.topology as topology

import sys
import threading
import signal
import time
import copy
import socket

class DistributedController(EventMixin, topology.Controller):
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
  def __init__(self, name):
    """
    Note that server may be a direct reference to the NomServer (for simulation), or a Pyro4 proxy
    (for emulation)
    
    pre: name is unique across the network
    """
    EventMixin.__init__(self)
    topology.Controller.__init__(self, name)
    self.name = name
    self.log = core.getLogger(name)
    self.topology = None
    
    self._server_connection = None
    self._queued_commits = []
    
    # For simulation. can't connect to NomServer until the Messenger is listening to new connections
    # TODO: for emulation, this should be removed / refactored -- just assume that the NomServer machine is up
    core.messenger.addListener(messenger.MessengerListening, self._register_with_server)
    
  def _register_with_server(self, event):
    sock = socket.socket()
    # TODO: don't assume localhost -> should point to machine NomServer is running on
    sock.connect(("localhost",7790))
    self._server_connection = messenger.TCPMessengerConnection(socket = sock)
    self._server_connection.addListener(messenger.MessageReceived, self._handle_MessageReceived)
    self._server_connection.send({"nom_server_handshake":self.name})
    # Answer comes back asynchronously as a call to nom_update
    self._server_connection.send({"get":None})
    
  def _handle_MessageReceived (self, event, msg):
    if event.con.isreadable():
      r = event.con.read()
      self.log.debug("-%s" % str(r))
      if type(r) is not dict:
        self.log.warn("message was not a dict!")
        return
      if "nom_update" in r:
        self.nom_update(r["nom_update"])
    else:
      self.log.debug("- conversation finished")

  def nom_update(self, topology):
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
    self.log.info("Updating nom from %s to %s " % (self.topology, topology))
    self.topology = topology
    # Register subclass' event handlers
    self.listenTo(topology, "topology")
    # TODO: react to the change in the topology, by firing queued events to 
    # subclass' ?
    return True

  def commit_nom_change(self):
    self.log.debug("Committing NOM update")
    if self._server_connection:
      self._server_connection.send({"put":self.topology})
    else:
      self.log.debug("Queuing nom commit")
      self._queued_commits.append(copy.deepcopy(self.topology))
    
    # TODO: need to commit nom changes whenever the learning switch updates its state...
  