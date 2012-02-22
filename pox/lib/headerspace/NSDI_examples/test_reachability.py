'''
Created on Aug 14, 2011

@author: peymankazemian
'''
from NSDI_examples.load_stanford_backbone import *
from config_parser.cisco_router_parser import ciscoRouter
from headerspace.hs import *
from time import time, clock

ntf = load_stanford_backbone_ntf()
ttf = load_stanford_backbone_ttf()
(port_map,port_reverse_map) = load_stanford_backbone_port_to_id_map()
cs = ciscoRouter(1)
#add_internet(ntf,ttf,port_map,cs,[("171.64.0.0",14),("128.12.0.0",16)])

all_x = byte_array_get_all_x(ciscoRouter.HS_FORMAT()["length"]*2)
hs = headerspace(ciscoRouter.HS_FORMAT()["length"]*2)
cs.set_field(all_x, "ip_dst", dotted_ip_to_int("10.0.0.0"), 24)
hs.add_hs(all_x)
port_id = port_map["goza_rtr"]["te3/3"]
st = time()
res = ntf.T(hs,port_id)
ntf.remove_duplicates(res)
en = time()
print "TIME: %d"%(en-st)
print len(res)

'''
print "----------------------"
for (h,p) in res:
    print "(%s,%s)"%(h,port_reverse_map["%d"%p[0]])
'''

linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked) 

tmp = []
st = time()
for (h,ports) in linked:
    for p in ports:
        h.self_diff()
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
en = time()
print "TIME: %d"%(en-st)
res = tmp
#ntf.remove_duplicates(res)
print len(res)
'''
print "----------------------"
for (h,p) in res:
    print "(%s,%s)"%(h,port_reverse_map["%d"%p[0]])
'''
linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked) 

tmp = []
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
res = tmp
ntf.remove_duplicates(res)
print len(res)
'''
print "----------------------"
for (h,p) in res:
    print "(%s,%s)"%(h,port_reverse_map["%d"%p[0]])
'''
linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked)

tmp = []
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
res = tmp
ntf.remove_duplicates(res)
print len(res)
'''
print "----------------------"
for (h,p) in res:
    print "(%s,%s)"%(h,port_reverse_map["%d"%p[0]])
'''
linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked)

tmp = []
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
res = tmp
ntf.remove_duplicates(res)
print len(res)

linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked)

tmp = []
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
res = tmp
ntf.remove_duplicates(res)
print len(res)

linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked)

tmp = []
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
res = tmp
ntf.remove_duplicates(res)
print len(res)


linked = []
for (h,ports) in res:
    for p in ports:
        linked.extend(ttf.T(h,p))
print len(linked)

tmp = []
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
    #print len(tmp)
res = tmp
ntf.remove_duplicates(res)
print len(res)
'''
for (h,p) in res:
    print "(%s,%s)"%(h,p)
'''
'''
(h,ports) = res[245]
print h
print ports
linked =  ttf.T(h, ports[0])
print linked
tmp= [ ]
for (h,ports) in linked:
    for p in ports:
        tmp.extend(ntf.T(h,p))
for (h,p) in tmp:
    print "(%s,%s)"%(h,p)
'''
