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
import time

from pox.nom_server.nom_server import NomServer
from pox.nom_server.nom_server import CachedNom

sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()

class NomTrap(NomServer):
    """
    This is a testing framework for controller applications (specifically
    those that inherit from NomClient)

    We can think of the controller application as a function:
        F(view) => configuration

    This property allows us to treat the controller application as a black box:
    we feed it (intelligently chosen) views, and observe the configuration it
    produces without having to worry about the actual logic that the
    application executes internally.
   
    Normally NomClient's connects to a centrallized database (NomServer)
    through the following interfaces:

    ==========================                            ==========================
    |    NomClient           |                            |    NomServer           |
    |                        |   any mutating operation   |                        |
    |                        |  -------------------->     |server.put(nom)         |
    |                        |                            |                        |
    |          client.       |   cache invalidation, or   |                        |
    |            update_nom()|   network event            |                        |
    |                        |   <-------------------     |                        |
    ==========================                            ==========================

    A NomTrap severs these connections, and articifically:
       i.) Calls client.update_nom() with intellegintly chosen views

       ii.) Logs all resulting mutating operations on the Nom, and associates them with
           the original input views

    This allows us to build up a database of:
       F(view) => configuration

    mappings for the client, which we can later use to test invariants.
    """

    _core_name = "NomServer" # we want to be core.NomServer

    def __init__(self):
        # don't call super constructor, since we don't care about Pyro4

        # Don't make the CachedNom server reference a proxy, since we're
        # ignoring Pyro4
        self.nom = CachedNom(self)
        # for now, only one client will register
        self.registered = []
        # the nom currently being fed to the client
        self.pending_nom = None
        # the client(s?) under test
        self.test_client = None

        # results returned by the client, of the form:
        #      { input nom => [output nom1, output nom2, ...] }
        # normally there will be a single output nom, but the client may execute
        # several mutating operations on the input nom, so we log them all
        self.inputnom_2_outputnoms = {}

    def register_client(self, client):
        log.debug("register, nom_trap: %s" % client)
        if len(self.registered) >= 1:
            raise RuntimeError("NomTraps currently only support one client")

        # Don't bother creating a Pyro4 Proxy -- just keep a local reference to the
        # client
        self.registered.append(client)
        self.test_client = client
 
    def exercise_client(self, input_noms):
        """
        Feed test_noms to the client, and log the results. test_noms can be either a list
        or a generator that returns Nom objects on each next() call. Note that
        the Noms don't have to be CachedNom objects -- they could be arbitrary
        objects, so long as the NomClient can interact with them in the
        standardized way (yet to be defined).
        """
        if self.test_client == None:
            raise RuntimeError("Test client has not yet registered")
        
        for nom in input_noms:
            self.pending_nom = nom
            self.test_client.update_nom(nom)
            # TODO: how do we know when the client has finished updating?
            #       it may execute multiple mutating operations as a result of
            #       feeding in the test nom... for now, just sleep for 10
            #       seconds
            time.sleep(10)

    def put(self, nom):
        """
        Log the nom output value, and associate it with the current test nom

        Then invalidate the client's cache as normal
        """
        log.debug("put, nom = ", nom)
        if self.pending_nom not in self.inputnom_2_outputnoms:
            # Does python have a default hash value equivalent? 
            # In ruby: hash = Hash.new { |h,k| h[k] = [] }
            self.inputnom_2_outputnoms[self.pending_nom] = []

        self.inputnom_2_outputnoms[self.pending_nom].append(nom)

        NomServer.put(self, nom)
            
if __name__ == "__main__":
    from pox.nom_server.nom_server import CachedNom

    trap = NomTrap()
    # wait for the client to connect
    while not trap.registered:
        log.debug("Waiting for client to connect...")
        trap.exercise_client([CachedNom(trap)])
        time.sleep(1)