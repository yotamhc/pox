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
This is a prototype control application written on top of the (substrate) NOM. 

It converts NOM switch entities into LearningSwitches.
"""

from pox.core import core
from pox.controllers.distributed_controller import DistributedController
from learning_switch import LearningSwitch

log = core.getLogger()

# In addition to declaring the user-defined NOM entity, the application must tell the platform
# how and when to instantiate these NOM entities. We do this with the following controller:
class nom_l2_switch_controller (DistributedController):
  """ Controller that treats the network as a set of learning switches """

  def __init__ (self, server):
    """ Initializes the l2 switch controller component """
    DistributedController.__init__(self, server)
    log.debug("nom_l2_switch_controller booting...")
   
  def _handle_topology_SwitchJoin(self, switchjoin_event):
    """ Convert switches into Learning Switches """
    log.debug("Switch Join! %s " % switchjoin_event)
    self.topology.addEntity(LearningSwitch(switchjoin_event.switch))
    