import numpy as np
import multiprocessing as MP
import time

  
def worker_heiter(id, secret, q_request, q_reply):
    import modules_JH
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
    danger_list = []#verzeichnis der Intruder
    D = 2 #Durchmesser der Pucks
    amax = 100.
        
    for i in range(n_pucks):#initiale Abfrage aller Pucks zu beginn der Sim.
        q_request.put('GET_PUCK', i,id)
        puck = q_reply.get()[1]#geht das so?
        if puck.is_alive() == False:
            continue
        if puck.get_name()== 'heiter':
            me = puck                #speichert mich gesondert als 'me' ab
            continue
        p_list = [puck.get_id(), puck.get_position(), puck.get_velocity(), \
                  puck.get_acceleration(), puck.get_time(), puck.is_alive()]
        pucks(i = p_list)
        
    for i in range(len(pucks)):#Prüft welche Pucks gefährlich werden könnten und setzt diese auf die danger_list
        tca = Tca(me.get_position(),pucks(i[1]),me.get_velocity(),pucks(i[2]))
        if tca < 10:#random Zahl -> testen
            danger_list.append(pucks(i))
            if Dtca_abs(tca,me.get_position(), pucks(i[1]), me.get_velocity(),\
                        pucks(i[2])) < 1.1 * D:
                resacc = Res_acc(tca,me.get_position(), pucks(i[1]),\
                                 me.get_velocity(),pucks(i[2]))
                q_request.put('SET_ACCELERATION', resacc, secret, id)
                #time.sleep(2/50) #-> dann kann man halt in der Zeit nichts anderes machen -> threading, asyncio
                q_request.put('SET_ACCELERATION', 0, secret, id)
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen

    while True:#dauerhafte checks der priorisierten pucks und aller anderen
        prio_check()
        time.sleep(5/50)
        prio_check()
        time.sleep(5/50)
        rest_check()
        time.sleep(5/50)

        
###############################################################################Ablage von vermutlich unnötigem                
while True:#dauernde checks
    for i  in range(len(danger_list)):#check der gefährder, timing fehlt
        q_request.put('GET_PUCK', danger_list[i[0]], id)
        puck = q_reply.get()[1]
        if puck.is_alive() == False:
            continue
        tca = Tca(me.get_position(),puck.get_position(),me.get_velocity(),puck.get_velocity())
        if tca >= 10:
            danger_list.remove[i]
            continue
        else:
            if Dtca_abs(tca,me.get_position(), puck.get_position(), me.get_velocity(),\
                        puck.get_velocity()) < 1.1 * D:
                resacc = Res_acc(tca,me.get_position(), pucks(i[1]),\
                                 me.get_velocity(),pucks(i[2]))
                q_request.put('SET_ACCELERATION', resacc, secret, id)
                #time.sleep(2/50??) #-> dann kann man halt in der Zeit nichts anderes machen -> threading, asyncio
                q_request.put('SET_ACCELERATION', 0, secret, id)
                danger_list.remove[i] #den Puck für den ausgewichen wurde streichen          
  
#auch: reflexion an rand checken
#geschwindigkeit nach Ausweichen checken und ggf. anderes Ausweichen       