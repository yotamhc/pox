def launch ():
  import nom_client
  # import cached_nom ???
  from pox.core import core
  core.registerNew(nom_client.NomClient)
