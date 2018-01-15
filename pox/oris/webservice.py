# Copyright 2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A simple JSON-RPC-ish web service for interacting with OpenFlow.

This is not incredibly robust or performant or anything.  It's a demo.
It's derived from the of_service messenger service, so see it for some
more details.  Also, if you add features to this, please think about
adding them to the messenger service too.

Current commands include:
  set_table
    Sets the flow table on a switch.
    dpid - a string dpid
    flows - a list of flow entries
  get_switch_desc
    Gets switch details.
    dpid - a string dpid
  get_flow_stats
    Get list of flows on table.
    dpid - a string dpid
    match - match structure (optional, defaults to match all)
    table_id - table for flows (defaults to all)
    out_port - filter by out port (defaults to all)
  get_switches
    Get list of switches and their basic info.

Example - Make a hub:
curl -i -X POST -d '{"method":"set_table","params":{"dpid":
 "00-00-00-00-00-01","flows":[{"actions":[{"type":"OFPAT_OUTPUT",
 "port":"OFPP_ALL"}],"match":{}}]}}' http://127.0.0.1:8000/OF/
"""

import sys
from pox.core import core
from pox.web.jsonrpc import JSONRPCHandler, make_error
import threading

import oris

log = core.getLogger()

TOPOLOGY_FILE = 'topology'

class ORISRequestHandler(JSONRPCHandler):
    def _exec_create_path_fixed_lambda(self, src_name, dst_name, path_name=None):
        res = self.args['oris'].create_path_fixed_lambda(src_name, dst_name, path_name)
        if res is None:
            # return an error message
            pass
        else:
            return res
        
    def _exec_create_path_variable_lambda(self, src_name, dst_name, path_name=None):
        res = self.args['oris'].create_path_variable_lambda(src_name, dst_name, path_name)
        if res is None:
            # return an error message
            pass
        else:
            return res

    def _exec_delete_path(self, path_name):
        res = self.args['oris'].delete_path(path_name)
        if res is None:
            # return an error message
            pass
        else:
            return res
        

def launch (username='', password=''):
  def _launch ():
    topo = oris.read_topology_file(TOPOLOGY_FILE)
    if topo is None:
      log.error('Failed to read topology file')

    oris = OpticalRouterInTheSky(topo)
    
    cfg = {}
    if len(username) and len(password):
      cfg['auth'] = lambda u, p: (u == username) and (p == password)
      cfg['oris'] = oris
    core.WebServer.set_handler("/oris/",ORISRequestHandler,cfg,True)

  core.call_when_ready(_launch, ["WebServer","oris"],
                       name = "oris.webservice")
