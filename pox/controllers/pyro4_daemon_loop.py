from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *
from pox.lib.recoco.recoco import *

class PyroLoop (Task):
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

