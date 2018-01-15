import threading
import networkx as nx
import random
import json

class OpticalRouterInTheSky:
    """
    A centralized optical router that knows the entire topology and find
    optical paths between domains/nodes/hosts
    """
    # TODO: Need to synchronize this class
    
    def __init__(self, topo):
        self.topo = topo
        self.paths = dict()
        self.lock = threading.Lock()
        
    def create_path_fixed_lambda(self, src_name, dst_name, path_name=None):
        with self.lock:
            # Find a new path
            p = self.topo.find_path_fixed_lambda(src_name, dst_name)
            if p is None: return None
            if path_name is not None:
                p.name = path_name
        
            # Register path
            self.topo.register_optical_path(p)
            self.paths[p.name] = p
        
            return p

    def create_path_variable_lambda(self, src_name, dst_name, path_name=None):
        with self.lock:
            # Find a new path
            p = self.topo.find_path(src_name, dst_name)
            if p is None: return None
            if path_name is not None:
                p.name = path_name
        
            # Register path
            self.topo.register_optical_path(p)
            self.paths[p.name] = p
        
            return p
        
    def delete_path(self, path_name):
        with self.lock:
            if path_name not in self.paths:
                return False
            p = self.paths[path_name]
            self.topo.unregister_optical_path(p)
            del self.paths[path_name]
            return True
        
class OpticalPort(object):
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr
        self.class_name = self.__class__.__name__

    def __str__(self):
        return '[ %s: %s (addr: %s) ]' % (self.__class__.__name__, self.name, self.addr)
    

class DomainPort(OpticalPort):
    def __init__(self, name, addr):
        super(DomainPort, self).__init__(name, addr)
    

class HostPort(OpticalPort):
    def __init__(self, name, addr):
        super(HostPort, self).__init__(name, addr)


class OpticalAddress:
    def __init__(self, str):
        self.str = str
        
    def __str__(self):
        return str
    
    
class OpticalPathEdge:
    def __init__(self, optical_link, lamb):
        self.optical_link = optical_link
        self.lamb = lamb    


class OpticalPath:
    def __init__(self, name, edges):
        self.name = name
        self.edges = edges


class OpticalLink:
    """
    Representaion of a single optical edge
    """
    def __init__(self, src_port, dst_port, lambdas):
        self.src_port = src_port
        self.dst_port = dst_port
        self.lambdas = lambdas[:]
        self.used_lambdas = dict()

    def _register_path(self, path_name, lamb):
        if lamb not in self.lambdas:
            return False
        
        self.lambdas.remove(lamb)
        self.used_lambdas[path_name] = lamb
        return True
        
    def _unregister_path(self, path_name):
        if path_name not in self.used_lambdas:
            return False
        
        lamb = self.used_lambdas[path_name]
        self.lambdas.append(lamb)
        return True
        

class OpticalTopo:
    """
    An optical topology of nodes with multiple ports, and outgoing edges from
    specific ports.
    The topo class can provide same-frequency paths by managing a different
    graph for each frequency.
    Currently this class only allows one link between two nodes.
    """
    def __init__(self, optical_links):
        self.optical_links = dict() # to find specific edge (with port info) between nodes
        self.g = nx.Graph() # underlying graph of nodes (without port info)
        self.fg = dict() # a dict lambda -> graph per lambda
        self.fg_removed = dict()
        
        for e in optical_links:
            if e.src_port.name not in self.optical_links:
                self.optical_links[e.src_port.name] = dict()
            self.optical_links[e.src_port.name][e.dst_port.name] = e
            self.g.add_nodes_from([ e.src_port.name, e.dst_port.name ])
            self.g.add_edge(e.src_port.name, e.dst_port.name, optical_link=e)
            
            for l in e.lambdas:
                if l not in self.fg:
                    self.fg[l] = nx.Graph()
                    self.fg_removed[l] = dict()
                self.fg[l].add_nodes_from([ e.src_port.name, e.dst_port.name ])
                self.fg[l].add_edge(e.src_port.name, e.dst_port.name, optical_link=e, l=l)
                
    
    def get_edge(self, src_name, dst_name):
        if src_name in self.optical_links and dst_name in self.optical_links[src_name]:
            return self.optical_links[src_name][dst_name]
        return None
        
    def _register_lambda(self, optical_link, lamb):
        self.fg[lamb].remove_edge(optical_link.src_port.name, optical_link.dst_port.name)
        self.fg_removed[lamb][optical_link] = { 'optical_link': optical_link, 'l': lamb }
    
    def _unregister_lambda(self, optical_link, lamb):
        e = self.fg_removed[lamb][optical_link]
        del self.fg_removed[lamb][optical_link]
        self.fg[lamb].add_edge(optical_link.src_port.name, optical_link.dst_port.name, e)
        
    def register_optical_path(self, optical_path):
        # this method works on OpticalPath containing OpticalPathEdge edges
        for e in optical_path.edges:
            self._register_lambda(e.optical_link, e.lamb)
            e.optical_link._register_path(optical_path.name, e.lamb)
    
    def unregister_optical_path(self, optical_path):
        # this method works on OpticalPath containing OpticalPathEdge edges
        for e in optical_path.edges:
            self.unregister_lambda(e.optical_link, e.lamb)
            e.optical_link._unregister_path(optical_path.name, e.lamb)
        
    def _name_path(self, edges):
        first = edges[0].src_port.name
        last = edges[len(edges) - 1].dst_port.name
        rand = random.randint(65536)
    
    def _node_path_to_edges(self, p, lamb=None):
        # translates a path of nodes to an OpticalPath, where a lambda is assigned for
        # each edge. May return None if no lambda is available on one of the links
        result = []
        last = None
        for node in p:
            if last is None:
                last = node
                continue
            else:
                if last not in self.optical_links or node not in self.optical_links[last]: 
                    return None
                e = self.optical_links[last][node]
                if lamb is None:
                    if len(e.lambdas) > 0:
                        lamb = e.lambdas[0]
                    else:
                        return None
                result.append(OpticalPathEdge(e, lamb))
                last = node
        
        return OpticalPath(self._name_path(result), result)

    def find_path(self, src_name, dst_name, avoid=None):
        # finds a path of ports (edges) from src node to dst node, with variable lambda
        # returns an OpticalPath object
        # avoid - a list of edges to avoid
        
        if avoid is None:
            ps = self.g.all_shortest_paths(source=src_name, target=dst_name)
            for p in ps:
                res = self._node_path_to_edges(p)
                if res is not None:
                    return res
            return None
        else:
            # requested to avoid specific edges
            s_avoid = set(avoid)
            ps = self.g.all_shortest_paths(source=src_name, target=dst_name)
            if ps in None or len(ps) == 0: return None
            for p in ps:
                ep = self._node_path_to_edges(p)
                if ep is not None and s_avoid.isdisjoint(ep):
                    return ep
            return None
        
    def find_path_fixed_lambda(self, src_name, dst_name):
        # Returns a path with a fixed lambda
        # returns an OpticalPath object
        for lamb in self.fg:
            p = self.fg[lamb].shortest_path(source=src_name, target=dst_name)
            if p is not None:
                return self._node_path_to_edges(p, lamb)
        return None


def read_topology_file(path):
    try:
        f = open(path, 'r')
        links = json.load(f, cls=TopoJsonDecoder)
        return OpticalTopo(links)
    finally:
        f.close()
        
        

class DefaultJsonEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


class TopoJsonDecoder(json.JSONEncoder):
    def decode(self, s):
        lst = json.loads(s)
        res = []
        for o in lst:
            # o is a link json
            link = self.decode_link(o)
            res.append(link)
        return res
    
    def decode_link(self, obj):
        src_port = self.decode_port(obj['src_port'])
        dst_port = self.decode_port(obj['dst_port'])
        lambdas = obj['lambdas']
        
        link = OpticalLink(src_port, dst_port, lambdas)
        return link
        
    def decode_port(self, obj):
        name = obj['name']
        addr = obj['addr']
        class_name = obj['class_name']
        
        if class_name == 'HostPort':
            return HostPort(name, addr)
        elif class_name == 'DomainPort':
            return DomainPort(name, addr)
        else:
            return None


def create_sample_topology_file(path):
    """
    Creates and stores a sample topology file for testing purposes.
    The topology is:
    
    +----+     1+----------+2            1+----------+2     +----+
    | h1 +------+ Domain A +--------------+ Domain B +------+ h2 |
    +----+      +----+-----+              +----+-----+      +----+
                     \3                        /3
                      \                       /
                       \   1+----------+2    /
                        \---+ Domain C +----/
                            +----+-----+
                                 |3
                                 |
                               +-+--+
                               | h3 |
                               +----+
    """
    dpA = [None]
    dpB = [None]
    dpC = [None]
    for i in range(1,4):
        dpA.append(DomainPort('A:' + str(i),'a' + str(i)))
        dpB.append(DomainPort('B:' + str(i),'b' + str(i)))
        dpC.append(DomainPort('C:' + str(i),'c' + str(i)))

    h1 = HostPort('H1:1', 'h1')
    h2 = HostPort('H2:1', 'h2')
    h3 = HostPort('H3:1', 'h3')
    
    lambdas = [1,2,3,4,5,6,7,8,9,10]
    
    h1link = OpticalLink(h1, dpA[1], lambdas)
    h2link = OpticalLink(h2, dpB[2], lambdas)
    h3link = OpticalLink(h3, dpC[3], lambdas)
    
    a2blink = OpticalLink(dpA[2], dpB[1], lambdas)
    a2clink = OpticalLink(dpA[3], dpC[1], lambdas)
    b2clink = OpticalLink(dpB[3], dpC[2], lambdas)
    
    links = [ h1link, h2link, h3link, a2blink, a2clink, b2clink ]
    try:
        f = open(path, 'w')
        json.dump(links, f, cls=DefaultJsonEncoder)
        return True
    except:
        return False
    finally:
        f.close()



if __name__ == '__main__':
    # Test code
    #create_sample_topology_file('topology')
    topo = read_topology_file('topology')
    oris = OpticalRouterInTheSky(topo)
