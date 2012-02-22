'''
Created on Aug 13, 2011

@author: peymankazemian
'''
from pox.lib.headerspace.headerspace.tf import *
from pox.lib.headerspace.headerspace.hs import *
from pox.lib.headerspace.NSDI_examples.emulated_tf import *
from pox.lib.headerspace.config_parser.helper import dotted_ip_to_int

rtr_names = ["bbra_rtr",
             "bbrb_rtr",
             "boza_rtr",
             "bozb_rtr",
             "coza_rtr",
             "cozb_rtr",
             "goza_rtr",
             "gozb_rtr",
             "poza_rtr",
             "pozb_rtr",
             "roza_rtr",
             "rozb_rtr",
             "soza_rtr",
             "sozb_rtr",
             "yoza_rtr",
             "yozb_rtr",
             ]

def load_stanford_backbone_ntf():
    emul_tf = emulated_tf(3)
    i = 0
    for rtr_name in rtr_names:
        f = TF(1)
        f.load_object_from_file("tf_stanford_backbone/%s.tf"%rtr_name)
        f.activate_hash_table([15,14])
        emul_tf.append_tf(f)
        i = i+1
    return emul_tf

def load_stanford_backbone_ttf():
    f = TF(1)
    f.load_object_from_file("tf_stanford_backbone/backbone_topology.tf")
    return f

def load_stanford_backbone_port_to_id_map():
    f = open("tf_stanford_backbone/port_map.txt",'r')
    id_to_name = {}
    map = {}
    rtr = ""
    for line in f:
        if line.startswith("$"):
            rtr = line[1:].strip()
            map[rtr] = {}
        elif line != "":
            tokens = line.strip().split(":")
            map[rtr][tokens[0]] = int(tokens[1])
            id_to_name[tokens[1]] = "%s-%s"%(rtr,tokens[0])
    return (map,id_to_name)
            
def add_internet(ntf,ttf,port_map,cs,campus_ip_list):
    '''
    Campus IP list is a list of (ip address,subnet mask) for each IP subnet on campus
    '''
    s = TF(cs.HS_FORMAT()["length"]*2)
    s.set_prefix_id("internet")
    for entry in campus_ip_list:
        match = byte_array_get_all_x(cs.HS_FORMAT()["length"]*2)
        cs.set_field(match,'ip_dst',dotted_ip_to_int(entry[0]),32-entry[1])
        rule = TF.create_standard_rule([0], match, [0], None, None, "", [])
        s.add_fwd_rule(rule)
    ntf.append_tf(s)
    
    bbra_internet_port1 = port_map["bbra_rtr"]["te1/1"]
    bbra_internet_port2 = port_map["bbra_rtr"]["te7/4"]
    bbrb_internet_port1 = port_map["bbrb_rtr"]["te1/4"]
    bbrb_internet_port2 = port_map["bbrb_rtr"]["te7/3"]
    rule = TF.create_standard_rule([bbra_internet_port1], None,[0], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([bbra_internet_port2], None,[0], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([bbrb_internet_port1], None,[0], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([bbrb_internet_port2], None,[0], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([0], None,[bbra_internet_port1], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([0], None,[bbra_internet_port2], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([0], None,[bbrb_internet_port1], None, None, "", [])
    ttf.add_link_rule(rule)
    rule = TF.create_standard_rule([0], None,[bbrb_internet_port2], None, None, "", [])
    ttf.add_link_rule(rule)
    

        