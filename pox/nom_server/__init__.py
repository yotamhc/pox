def launch ():
  import nom_server
  import nom_trap
  import cached_nom
  from pox.core import core
  # TODO: how do I invoke NomTrap from pox.py?
  #core.registerNew(nom_server.NomServer)
  core.registerNew(nom_trap.NomTrap)
