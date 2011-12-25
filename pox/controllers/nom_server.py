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
import threading
import signal
import subprocess
import socket



sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()

# TODO: there are currently issues with catching SIGTERM... as a result, pox doesn't
# shutdown properly... This is a known issue with threading.Thread. We should
# switch to recoco.

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
    |          client.       |   cache invalidation, or   |                        |
    |            update_nom()|   network event            |                        |
    |                        |   <-------------------     |                        |
    ==========================                            ==========================
    """
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
        self.nom = CachedNom(server_proxy)
        self.registered = []

        daemon = Pyro4.Daemon()
        self.uri = daemon.register(self)
        # register with name server
        ns = Pyro4.naming.locateNS()
        ns.register("nom_server.nom_server", self.uri)
        PyroLoop(daemon)

    def register_client(self, client):
        log.info("register %s" % client.uri)
        client = Pyro4.Proxy(client.uri)
        self.registered.append(client)

    def unregister_client(self, client):
        pass

    def get(self):
        log.info("get")
        return self.nom

    def put(self, val):
        log.info("put %s" % val)
        self.nom = val
        for client in self.registered:
            client.update_nom(val)
            log.info("invalidating/updating %s" % client)
            
if __name__ == "__main__":
    nom = NomServer()
    nom.daemon_thread.join()
    
    
def launch():
  from pox.core import core
  core.registerNew(NomServer)

