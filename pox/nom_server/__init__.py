def launch ():
  import nom_server
  import cached_nom
  from pox.core import core
  core.registerNew(nom_server.NomServer)
