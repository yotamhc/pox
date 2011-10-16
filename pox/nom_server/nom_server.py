#!/usr/bin/env python
# Nom nom nom nom

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *

import Pyro4
import Pyro4.util
import sys
import threading
import signal
import subprocess
import socket

from cached_nom import CachedNom

sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()

# TODO: there are currently issues with catching SIGTERM... as a result, pox doesn't
# shutdown properly... This is a known issue with threading.Thread.

class NomServer:
    """
    The Nom "database". Keeps a copy of the Nom in memory, as well as a list
    of all registered clients. When a client calls NomServer.put(),
    invalidates + updates the caches of all registered clients
    """
    def __init__(self):
        def fork_name_server():
            """Fork a python process to run the name server"""

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
                    log.warn("name_serving_runnging? exception: %s" % e)
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
        self.registered = set()

        nom_server = self

        class DaemonThread(threading.Thread):
            """serveSimple() does not return, so we spawn a new thread"""
            def run(self):
                # Start the Pyro event loop
                Pyro4.Daemon.serveSimple(
                    {
                        nom_server: "nom_server.nom_server"
                    },
                    ns=True
                )

        self.daemon_thread = DaemonThread()
        self.daemon_thread.start()
            
    def register_client(self, client_uri):
        log.info("register %s" % client_uri)
        client = Pyro4.Proxy(client_uri)
        self.registered.add(client)

    # def unregister_client? TODO

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
