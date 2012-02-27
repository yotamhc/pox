#!/usr/bin/python

from pox.debugger.debugger import FuzzTester
import pox.debugger.topology_generator as default_topology
from pox.debugger.io_worker import *
from experiment_config_lib import *
from pox.lib.recoco.recoco import Scheduler

import sys
import string
import subprocess
import argparse

# We use python as our DSL for specifying experiment configuration  
# The module can define the following functions:
#   controllers(command_line_args=[]) => returns a list of pox.debugger.experiment_config_info.ControllerInfo objects
#   switches()                        => returns a list of pox.debugger.experiment_config_info.Switch objects

# TODO: merge with Mininet
parser = argparse.ArgumentParser(description="Run a debugger experiment. Note: must precede controller args with --")
parser.add_argument("--config_file", help='optional experiment config file to load')
parser.add_argument('controller_args', metavar='controller arg', nargs='*',
                   help='arguments to pass to the controller(s)')
args = parser.parse_args()
  
if args.config_file:
  config = __import__(args.config_file)
else:
  config = object()

if hasattr(config, 'controllers'):
  controllers = config.controllers(args.controller_args)
else:
  controllers = [Controller(args.controller_args)] 

# Boot the controllers
for c in controllers:
  command_line_args = map(lambda(x): string.replace(x, "__port__", str(c.port)),
                      map(lambda(x): string.replace(x, "__address__", str(c.address)), c.cmdline))
  subprocess.Popen(command_line_args)
  
io_loop = RecocoIOLoop()

#if hasattr(config, 'switches'):
#  switches = config.switches()
#else:
#  switches = []
# HACK
(panel, switch_impls) = default_topology.populate(controllers, io_loop.create_deferred_worker_for_socket)
  
scheduler = Scheduler()
scheduler.schedule(io_loop)

# TODO: allow user to configure the fuzzer parameters, e.g. drop rate
debugger = FuzzTester()
debugger.start(panel, switch_impls)
