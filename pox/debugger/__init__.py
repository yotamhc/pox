def launch (num_controllers=1):
  import debugger
  from pox.core import core
  core.registerNew(debugger.FuzzTester, num_controllers)
