#!/usr/bin/env pethon
# Nom nom nom nom

# TODO: there is currently a dependency on the order of initialization of
# client and server... . for example:

#  $ pox.py nom_client nom_server    # blocks indefinitely

# whereas

#  $ pox.py nom_server nom_client    # works


from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *
from pox.lib.recoco.recoco import *

import sys
import threading
import signal
import time

import Pyro4
import Pyro4.util

sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()

class DaemonLoop (Task):
    """
    Recoco Task for the Pyro4 event loop

    TODO: there should be an event loop construct in pox so that I don't
    have to deal with Select
    """
    def __init__(self, daemon):
        Task.__init__(self)
        
        self.daemon = daemon
        self.daemon_sockets = set(daemon.sockets)
        
        # When core goes up, make sure to schedule ourselves
        core.addListener(pox.core.GoingUpEvent, self.start)

    def start(self, event):
        Task.start(self)

    def run(self):
        while core.running:
            rlist,_,_ = yield Select(self.daemon_sockets, [], [], 3)
            events = []
            for read_sock in rlist:
                if read_sock in self.daemon_sockets:
                    events.append(read_sock)
    
            if events:
                self.daemon.events(events)

class NomClient:
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
    def __init__(self, server=core.components['NomServer']):
        self.server = server
        daemon = Pyro4.Daemon()
        self.uri = daemon.register(self)
        DaemonLoop(daemon) 
        
        self.server.register_client(self)
        log.debug("registered with NomServer")
        self.nom = self.server.get()
        log.debug("Fetched nom from nom_server")

    def update_nom(self, nom):
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
        log.info("Updating nom from %s to %s " % (self.nom, nom))
        self.nom = nom
        return True
        # TODO: react to the change in the NOM

def main():
    import time
    import random

    def sigint_handler(signum, frame):
        import os
        os._exit(signum)

    signal.signal(signal.SIGINT, sigint_handler)

    nom_client = NomClient()
    time.sleep(2)

    while True:
        # test read operation
        nom_client.nom.items()
        # test write operation 
        nom_client.nom[random.randint(0,100)] = random.randint(0,100)
        time.sleep(random.randint(0,4))

if __name__ == "__main__":
    main()
