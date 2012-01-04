#!/usr/bin/env python
# Nom nom nom nom

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *

from pox.controllers.pyro4_daemon_loop import PyroLoop
from pox.controllers.cached_nom import CachedNom

import Pyro4
import Pyro4.util
import sys
import signal
import subprocess
import socket


sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()

class NomServer:
  """
  The Nom "database". Keeps a copy of the Nom in memory, as well as a list
  of all registered clients. When a client calls NomServer.put(),
  invalidates + updates the caches of all registered clients

  Visually,  NomClient's connect to the NomServer through
  the following interfaces:

  ==========================                            ==========================
  |    NomClient           |                            |    NomServer           |
  |                        |   any mutating operation   |                        |
  |                        |  -------------------->     |server.put(nom)         |
  |                        |                            |                        |
  |          client.       |                            |                        |
  |            update_nom()|    cache invalidation      |                        |
  |                        |   <-------------------     |                        |
  ==========================                            ==========================
  """
  
  # The set of components we depend on. These must be loaded before we can begin.
  _wantComponents = set(['topology'])
  
  def __init__(self):
    def fork_name_server():
      """
      Fork a python process to run the name server
      
      NOTE: to avoid having to fork every time you run pox, open a
      separate terminal and run:
        $ python -m Pyro4.naming
      """
      def name_server_already_running():
        """check if the pyro4 name server is already running"""
        log.info("checking if name server is already running...")
        s = socket.socket()
        name_server_hostname = "localhost"
        name_server_port = 9090
        try:
          s.connect((name_server_hostname, name_server_port)) 
          return True
        except Exception, e:
          log.warn("name_server already running? exception: %s" % e)
          return False

      if not name_server_already_running():
        log.info("booting name server...")

        subprocess.Popen(
          "python -m Pyro4.naming",
          shell=True,
        )

    fork_name_server()

    # Clients call server.get() for their reference to the CachedNom
    # The CachedNom's reference to the NomServer should be 
    # a Proxy, not the full object (`self`)
    server_proxy = Pyro4.Proxy("PYRONAME:nom_server.nom_server")
    # don't wait for a response from `put` calls
    server_proxy._pyroOneway.add("put")
    self.registered = []

    daemon = Pyro4.Daemon()
    self.uri = daemon.register(self)
    # register with name server
    ns = Pyro4.naming.locateNS()
    ns.register("nom_server.nom_server", self.uri)
    PyroLoop(daemon)
    
    # TODO: the following code is highly redundant with controller.rb
    self.topology = None
    if not core.resolveComponents(self, self._wantComponents):
      # If dependencies aren't loaded, register event handlers for ComponentRegistered
      self.listenTo(core)
  
  def _handle_ComponentRegistered (self, event):
    """ Checks whether the newly registered component is one of our dependencies """
    if core.resolveComponents(self, self._wantComponents):
      # Note that core.resolveComponents registers our event handlers with the dependencies
      # TODO: add a named field for every component in  _wantComponents
      self.topology = core.components['topology'] 

  def register_client(self, client):
    log.info("register %s" % client.uri)
    client = Pyro4.Proxy(client.uri)
    self.registered.append(client)

  def unregister_client(self, client):
    pass

  def get(self):
    log.info("get")
    return self.topology

  def put(self, val):
    log.info("put %s" % val)
    self.topology = val
    for client in self.registered:
      # TODO: clone val?
      client.update_nom(val)
      log.info("invalidating/updating %s" % client)
          
def launch():
  from pox.core import core
  core.registerNew(NomServer)
