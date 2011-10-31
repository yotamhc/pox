t = core.components['NomTrap']
c = core.components['NomClient']

t.registered
t.test_client
from pox.nom_server.cached_nom import CachedNom
t.exercise_client([CachedNom(t)])
