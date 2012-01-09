def launch (num_controllers=1):
  import fuzzer
  from pox.core import core
  core.registerNew(fuzzer.FuzzTester, num_controllers)
