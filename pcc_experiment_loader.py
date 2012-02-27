from pox.debugger.debugger import FuzzTester
import pox.debugger.topology_generator as default_topology
from pox.debugger.io_worker import *
from experiment_config_info import *
from pox.lib.recoco.recoco import Scheduler

import sys
import os

if len(sys.argv) < 1:
  print >>sys.stderr, "Usage: %s <experiment config file> <arguments to pass to pox children>"
  sys.exit()
  
# We use python as our DSL for specifying experiment configuration  
# The module can define the following functions:
#   controllers(command_line_args=[]) => returns a list of pox.debugger.experiment_config_info.ControllerInfo objects
#   switches()                        => returns a list of pox.debugger.experiment_config_info.Switch objects

# TODO: merge with Mininet

remaining_cmd_line_args = sys.argv[1:]
config = __import__(sys.argv[0])

if hasattr(config, 'controllers'):
  controllers = config.controllers(remaining_cmd_line_args)
else:
  controllers = [Controller(remaining_cmd_line_args)] 

# Boot the controllers
for c in controllers:
  os.system(map(lambda x: x.replace("__port__", c.port).replace("__address__", c.address), c.cmdline))
  
io_loop = RecocoIOLoop()

#if hasattr(config, 'switches'):
#  switches = config.switches()
#else:
#  switches = []
# HACCELK
(panel, switch_impls) = default_topology.populate(controllers, io_loop.create_worker_for_socket)
  
scheduler = Scheduler()
scheduler.schedule(io_loop)

# TODO: allow user to configure the fuzzer parameters, e.g. drop rate
debugger = FuzzTester()
debugger.start(panel, switch_impls)
