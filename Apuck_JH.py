import numpy as np
import multiprocessing as MP
import time
import modules_JH

  
def worker_heiter(id, secret, q_request, q_reply):
    #1. Initialisieren des Pucks und erfassen der Parameter
    q_request.put('SET_NAME', 'heiter', secret, id)
    q_request.put('GET_SIZE', id)
    q_request.put('GET_BOX', id)
    
    nameok = q_reply.get()
    if nameok[1] == None:
        raise ValueError("Setting name failed")
    n_pucks = q_reply.get()[1]
    simbox = q_reply.get()[1]
    box_xmin = simbox.xmin
    box_xmax = simbox.xmax
    box_ymin = simbox.ymin
    box_ymax = simbox.ymax
    
    pucks = dict()#Zentrales Verzeichnis der Pucks
        
    for i in range(n_pucks):#initiale Abfrage aller Pucks zu beginn der Sim.
        q_request.put('GET_PUCK', i,id)
        puck = q_reply.get()[1]
        if puck.is_alive() == False:
            continue
        p_list = [puck.get_id(), puck.get_position(), puck.get_velocity(), \
                  puck.get_acceleration(), puck.get_time(), puck.is_alive()]
        pucks(i = p_list)
        
        
        
        
        
        