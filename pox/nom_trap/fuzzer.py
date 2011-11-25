#!/usr/bin/env python
# Nom nom nom nom

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *

from pox.topology.topology import Topology

import sys
import threading
import signal
import subprocess
import socket
import time

log = core.getLogger()

class FuzzTester (Topology):
    """
    This is part of a testing framework for controller applications. It 
    acts as a replacement for pox.topology.
    
    Given a set of event handlers (registered by a controller application),
    it will inject intelligently chosen mock events (and observe
    their responses?)
    """
    def __init__(self):
      pass 
       
    def switchjoin_registration(self, handler):
      """
      Feed test_noms to the client (event handlers!), and log the results.
     
      TODO: I'm pretty sure we're going to need a reference to the client
      itself, not just its handler...    
      """
      pass
                   
                   
if __name__ == "__main__":
  pass
