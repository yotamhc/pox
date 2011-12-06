def launch ():
  import nom_trap
  from pox.core import core
  core.registerNew(nom_trap.NomTrap)
