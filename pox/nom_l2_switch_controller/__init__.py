# Copyright 2011 James McCauley
#
# This file is part of POX.
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX.  If not, see <http://www.gnu.org/licenses/>.

"""
This package contains a nom-based L2 learning switch.
"""

def launch (debug=False, distributed=False):
  # TODO: need a more transparent mechanism for specifying the debug flag...
  """
  Starts a NOM-based L2 learning switch, along with the discovery and topology modules
  """
  if type(distributed) == bool and distributed:
    distributed = 1
  elif type(distributed) == str:
    distributed = int(distributed)
  
  if not debug and not distributed:
    import pox.topology
    pox.topology.launch() 
    import pox.openflow.discovery
    pox.openflow.discovery.launch()
    import pox.openflow.topology
    pox.openflow.topology.launch()
    
  from pox.core import core
  if not distributed:
    import nom_l2_switch_controller
    core.registerNew(nom_l2_switch_controller.nom_l2_switch_controller)
  else:
    import pox.controllers.nom_server
    core.registerNew(pox.controllers.nom_server.NomServer)
    import distributed_nom_l2_switch_controller
    # server = Pyro4.Proxy("PYRONAME:nom_server.nom_server")
    #server = core.components['NomServer'] # TODOC: for simulation, just grab a direct reference
    # TODO: convert `distributed` to an integer
    for id in range(0, distributed):
      # TODO: no sure if I should be registering these with core
      # (name conflict, and not suitable for emulation with true distrbuted controller)
      # for now this is just to keep the controllers from being garbage collected
      name = "controller#%d" % id
      core.register(name, distributed_nom_l2_switch_controller.nom_l2_switch_controller(name))
      