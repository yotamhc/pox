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


from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.openflow import PacketIn
from pox.topology.topology import Switch, Entity
from pox.lib.revent import *

log = core.getLogger()

class Controller (EventMixin):
  """
  Generic Controller Application Superclass. Loads up topology and
  registers subclasse's handlers with topology et al.
  """
  
  # The set of components we depend on. These must be loaded before we can begin.
  _wantComponents = set(['topology'])
  
  def __init__(self):
    if not core.resolveComponents(self, self._wantComponents):
      # If dependencies aren't loaded, register event handlers for ComponentRegistered
      self.listenTo(core)
  
  def _handle_ComponentRegistered (self, event):
    """ Checks whether the newly registered component is one of our dependencies """
    if core.resolveComponents(self, self._wantComponents):
      # Note that core.resolveComponents registers our event handlers with the dependencies
      return EventRemove
  