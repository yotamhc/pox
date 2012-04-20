# Copyright 2012 James McCauley
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
from pox.lib.revent import *
from collections import defaultdict
from pox.openflow.discovery import Discovery
from pox.lib.util import dpidToStr

log = core.getLogger()
"""
Demonstrates the spanning tree module so that the L2 switch
works decently on topologies with loops.
"""
all_links = {}
     
class LXbars(object):
  def __init__(self, id, controller):
    self.id = id
    self.switches = {}
    self.internal_links = set()
    self.controller = controller
    self.external_links = set()
  def add_switch(self, switch):
    log.debug(str.format("Added {0} to {1}", switch.dpid, self.id)) 
    self.switches[switch] = switch
  def add_link(self, link):
    assert(link.dpid1 in self.switches or link.dpid2 in self.switches)
    if link.dpdid1 in self.switches and link.dpdid2 in self.switches:
      if link not in self.internal_links:
        self.internal_links.add(link)
    else:
      if link not in self.external_links:
        internal_dpid = (link.dpid1 if link.dpid1 in self.switches else link.dpid2)
        external_dpid = (link.dpid1 if link.dpid1 not in self.switches else link.dpid2)
        internal_port = (link.port1 if link.dpid1 in self.switches else link.port2)
        label = self.controller.LXBarLabelForExternalPort(external_dpid)
        external_links.add((internal_dpid, internal_port, label))
class Switch(object):
  def __init__(self, dpid, connection):
    self.dpid = dpid
    self.connection = connection
class Controller(EventMixin):
  def __init__(self, filename):
    self.lxbars = {}
    self.switch_to_lxbar = {}
    self.switches = {}
    if filename is not None:
      import json
      from os.path import expanduser
      jsonf = open(expanduser(args.filename))
      objs = json.load(jsonf)
      for lxbar in objs['lxbs']:
        self.lxbars[int(lxbar)] = LXbars(lxbar, self)
      for switch in objs['switches'].iteritems():
        self.switch_to_lxbar[int(switch[0])] = int(switch[1])
    else:
      self.lxbars[1] = LXbars(1, self)
    self.listenTo(core.openflow)
    core.openflow_discovery.addListenerByName("LinkEvent", self._handle)
  def _handle_ConnectionUp (self, event):
    dpid = event.dpid
    if dpid not in self.switches:
      self.switches[dpid] = Switch(dpid, event.connection)
      lxbar = (self.switch_to_lxbar[dpid] if dpid in self.switch_to_lxbar else 1)
      self.lxbars[lxbar].add_switch(self.switches[dpid])
    else:
      self.switches[dpid].connection = event.connection
  def _handle(self, event):
    def normalize(link):
      return (link if link.dpid1 < link.dpid2 else Discovery.Link(link.dpid2, link.port2, link.dpid1, link.port1))
    link = normalize(event.link)
    if link not in all_links:
      all_links[link] = 0
      lxbar1 = (self.switch_to_lxbar[link.dpid1] if link.dpid1 in self.switch_to_lxbar else 1)
      lxbar2 = (self.switch_to_lxbar[link.dpid2] if link.dpid2 in self.switch_to_lxbar else 1)
      self.lxbars[lxbar1].add_link(link)
      self.lxbars[lxbar2].add_link(link)
      print str.format("Total links = {0}", len(all_links))
  def LXBarLabelForExternalPort(self, dpid):
      return (self.switch_to_lxbar[dpid] if dpid in self.switch_to_lxbar else 1)
def launch (filename=None):
  from pox.core import core
  import pox.openflow.discovery
  pox.openflow.discovery.launch()
  core.registerNew(Controller, filename)
