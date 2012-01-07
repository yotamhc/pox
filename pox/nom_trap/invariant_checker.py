
from pox.core import core
from pox.openflow.libopenflow_01 import * 
from fuzzer_entities import *
  
import xml.etree.ElementTree as ET 
import os
import glob

log = core.getLogger("invariant_checker")

class InvariantChecker():
  def __init__(self, topology):
    self.topology = topology
    current_dir = os.getcwd()
    self.jruby_path = current_dir + "/pox/lib/anteater/jruby-1.6.5/bin/jruby"
    self.library_path = current_dir + "/pox/lib/anteater/build/lib/Ruby"
    self.solver_path = current_dir + "/pox/lib/anteater/src/tools/scripts/Makefile.solve"
    
    # Individual invariant checks
    self.loop_detector = current_dir + "/pox/lib/anteater/src/tools/loop-detector.rb"
    self.consistency_detector = current_dir + "/pox/lib/anteater/src/tools/consistency-checker.rb"
    self.blackhole_detector = current_dir +  "/pox/lib/anteater/src/tools/packet-loss.rb"
    # TODO: where is the connectedness detector script?
    self.connectivity_detector = None
    
    # Set up environment variables
    os.environ['ANTEATER_BUILD_DIR'] = current_dir + "/pox/lib/anteater/build"
    os.environ['ANTEATER_SRC_DIR'] = current_dir +  "/pox/lib/anteater/src"
    os.environ['LLVM_BIN_DIR'] = current_dir + "/pox/lib/anteater/dist/bin"
    os.environ['LD_LIBRARY_PATH'] = current_dir + "/pox/lib/anteater/build/lib/Core:$LD_LIBRARY_PATH"
    os.environ['JRUBY_OPTS']="--server --1.9 -J-Xmx16384m -J-Djruby.compile.fastest=true -J-Djruby.compile.frameless=true -J-Djruby.compile.positionless=true -J-Djruby.compile.fastops=true -J-Djruby.compile.fastcase=true -J-Djruby.compile.lazyHandles=true"
    os.environ['RUBY_EXECUTABLE'] = current_dir + "/pox/lib/anteater/jruby-1.6.5/bin/jruby"
    
  # --------------------------------------------------------------#
  #                    Invariant checks                           #
  # --------------------------------------------------------------#
  def check_loops(self):
    return self._run_anteater_script(self.loop_detector, "lc-base")
    
  def check_blackholes(self):
    return self._run_anteater_script(self.blackhole_detector, "pl-base")
    
  def check_connectivity(self):
    return self._run_anteater_script(self.connectivity_detector, "lc-base")
  
  def check_routing_consistency(self):
    # TODO: this takes a list as a second parameter. I think the list might be consistency constraints
    return self._run_anteater_script(self.consistency_detector, "cfc-base")
    
  def _run_anteater_script(self, script, output_prefix):
    log.debug("Snapshotting FIBs...")
    fib_manifest = self.generate_fib_manifest() 
    log.debug("Generating contraints...")
    cmd = ' '.join((self.jruby_path, '-I', self.library_path, script, fib_manifest))
    log.debug(cmd)
    os.system(cmd)
    log.debug("Invoking solver...")
    cmd = ' '.join(("make", "-f", self.solver_path, "BC_SRCS=%s.bc" % output_prefix))
    log.debug(cmd)
    os.system(cmd)
    # TODO: try catch block
    output_reader = open("%s.result" % output_prefix, 'r')
    result = output_reader.readline().strip()
    output_reader.close()
    log.debug("Cleaning up files...")
    for extension in ["*fib", "manifest.xml", "*bc", "*result"]:
      output_files = glob.glob(extension) 
      for output_file in output_files:
        os.remove(output_file)
    # TODO: if not sat, help the user find the problem somehow? ;)
    return result
      
      
  # --------------------------------------------------------------#
  #                    FIB Snapshot                               #
  # --------------------------------------------------------------#
  def dump_csv(self):
    """
    For each switch in the network, dump it's Flow Table in csv format, 
    for consumption by Anteater
    
    Returns a hash from switch_impl -> csv output
    """
    switch_impl2csv = {}
    
    def switch_csv(switch):
      """ Dump the Flow Table for a single switch """
      # TODO: implement this as a method on SwitchImpl! Will need a mapping
      #       of port -> next hop IP address
      #
      #       Only problem with putting it in SwitchImpl is that port -> next hop IP
      #       assumes that the switch works at Layer 3...
      lines = []
      for entry in switch.table._table:
        match, _, actions = entry 
         
        dst, prefix = match.get_nw_dst()
        if dst is None:
          dst = "0.0.0.0"
        full_dst = '/'.join((str(dst), str(prefix)))
        
        # Default drop (no output action specified)
        output_interface = "drop"
        gateway = "DIRECT"
        
        for action in actions:
          # TODO: assume that there is only one ofp_action_output in the list of actions?
          if type(action) == ofp_action_output:
            port_no = action.port
            port = switch.ports[port_no]
            port_name = port.name
            if port_name == "":
              port_name = "eth%d" % port_no
            output_interface = port_name
            gateway = switch.outgoing_links[port].end_port.ip_addr
                    
        # TODO: figure out what tags are used for in Anteater
        tags = "O"
    
        csv = ','.join((full_dst, gateway, output_interface, tags))
        lines.append(csv)
        
      # Now manually add in loopback devices
      for port in switch.ports.values():
        csv = "%s/32,DIRECT,loopback 1,O" % str(port.ip_addr)
        lines.append(csv)
      
      # TODO: problem! Anteater assumes destination-based routing. OpenFlow is
      # (source, destination)-based routing.
      return "\n".join(lines)
    
    # Now, get a csv string for each switch
    for switch in self.topology.getEntitiesOfType(MockOpenFlowSwitch):
      # TODO: don't assume that the switch has a reference to the implementation! For emulation, will need 
      #       to fetch table of the implementation through a more realistic means
      switch_impl = switch.switch_impl
      csv_output = switch_csv(switch_impl)
      switch_impl2csv[switch_impl] = csv_output
    
    return switch_impl2csv  
  
  def generate_fib_manifest(self):
    """ Generate an XML manifest file for Anteater consumption """
    switch_impl2csv = self.dump_csv()
    root = ET.Element("manifest")
    data = ET.SubElement(root, "data")
    for switch in switch_impl2csv.keys():
      node = ET.SubElement(data, "node")
      node.set("name", switch.name)
      fib_output_name = "%s.fib" % switch.name
      node.set("file", fib_output_name)
      fib_csv = switch_impl2csv[switch] 
      log.debug("writing out %s..." % fib_output_name)
      f = open(fib_output_name, 'w')
      f.write(fib_csv)
      f.close()
      
    tree = ET.ElementTree(root)   
    output_name = "manifest.xml"
    tree.write(output_name)
    return output_name
