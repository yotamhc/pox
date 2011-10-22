def launch ():
  import nom_client
  # import cached_nom ???
  from pox.core import core
  import Pyro4
  server = Pyro4.Proxy("PYRONAME:nom_server.nom_server")
  # Note: to run with a server other than NomServer, pass 
  # in None. e.g.:
  #   $ ./pox.py nom_client server=None
  # What I really want to do is specifiy the core component name on the
  # command line, e.g., 
  #   $ ./pox.py nom_client server='core.components["NomTrap"]'
  # but I believe that would require an `eval`
  core.registerNew(nom_client.NomClient, server)
