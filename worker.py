import numpy as np
import multiprocessing as MP
import time
#import modules_JH

vmax = 42.
amax = 100 #steht später im Worker

def r_of_t(r_now, v_now, a_now, t):
    r_t = r_now + v_now*t + 0.5*a_now*(t**2)
    return r_t
  
def Tca (r_self, r_enemy, v_self, v_enemy):
    
    tca = -1*(((np.dot((r_enemy - r_self),v_enemy - \
            v_self)))/(np.dot((v_enemy- v_self),\
                             (v_enemy - v_self))))
    return tca

def Dtca_abs (tca, r_self, r_enemy, v_self, v_enemy):
    
    dtca = np.linalg.norm((r_enemy- r_self)- ((v_enemy- v_self)*(np.dot(\
            (r_enemy-r_self),(v_enemy-v_self)))/(np.dot((v_enemy-v_self),\
            (v_enemy-v_self)))))
    return dtca

def Dtca_vec (tca, r_self, r_enemy, v_self, v_enemy):
    dtca = ((r_enemy- r_self)- ((v_enemy- v_self)*np.dot(\
            (r_enemy-r_self),(v_enemy-v_self))/(np.dot((v_enemy-v_self),\
            (v_enemy-v_self)))))
    return dtca
    

def Res_acc (tca,  r_self, r_enemy, v_self, v_enemy):#TBD: check von V nach dem Manöver
    R_puck = 1.
    r_tca_self = r_of_t(r_self, v_self,np.array([0,0]), tca)
    r_tca_enemy = r_of_t(r_enemy, v_enemy, np.array([0,0]), tca)
    r_tca = r_tca_enemy - r_tca_self
    res_acc = 2*(2*R_puck - r_tca)*(tca**(-2))
    if v_self+res_acc >= vmax:
        max_acc = vmax-v_self
        return max_acc #dann für länger laufen lassen! Check im Programm dazu einbauen!
    if np.linalg.norm(res_acc) > amax:
        return amax
    return res_acc

def danger_check(r_self, r_enemy, v_self, v_enemy):
    tca = Tca(r_self, r_enemy, v_self, v_enemy)
    if tca <= 2.0 and Dtca_abs(tca, r_self, r_enemy, v_self, v_enemy) <= 2.5:  #random Zeitwert. Einheit? Passt das? Testen
        return True
    else:
        return False

def check_rebound(r,v,box_x_min, box_x_max, box_y_min, box_y_max, steps):
    for i in range(steps):
        x_next = r[0]+v[0]
        y_next = r[1]+v[1]
        if x_next<box_x_min or x_next > box_x_max:
            return x_next
        if y_next < box_y_min or y_next > box_y_max:
            return y_next
        r[0] = x_next
        r[1] = y_next
    return False

    
def prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd):#übergabe aller variablen als Args
    for i  in range(len(danger_list)-1):#check der gefährder, timing fehlt, -1 für keyError?
        q_request.put(('GET_PUCK', danger_list[i-1][0], idd))
        #try:
        #    puck = q_reply.get(timeout=2)[1]  #vermeidet deadlock
        #except q_reply.Empty:
        #    print("Keine Antwort in der Queue erhalten.")
        puck = q_reply.get()[1]
        if type(puck) !='puck_server.Puck_Server' :#sicherstellen, dass nicht eine andere reply verwendet wird die noch da ist
            continue
        if puck.is_alive() == False:
            continue
        tca = Tca(me.get_position(),puck.get_position(),me.get_velocity(),puck.get_velocity())
        if tca >= (11/50):
            danger_list.pop(i)
            continue
        else:
            if Dtca_abs(tca,me.get_position(), puck.get_position(), me.get_velocity(),\
                        puck.get_velocity()) < 1.1 * D:
                resacc = Res_acc(tca,me.get_position(), pucks[i][1],\
                                 me.get_velocity(),pucks[i][2])
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                #time.sleep(2/50??) #-> dann kann man halt in der Zeit nichts anderes machen -> threading, asyncio
                q_request.put(('SET_ACCELERATION', 0, secret, idd))
                danger_list.pop(i) #den Puck für den ausgewichen wurde streichen
                
def rest_check(pucks, me, danger_list, D, q_request, secret, idd):
    for i in pucks:
        tca = Tca(me.get_position(),pucks[i][1],me.get_velocity(),pucks[i][2])
        if tca < (11/50):#random Zahl -> testen
            danger_list.append(pucks[i])
            if Dtca_abs(tca,me.get_position(), pucks[i][1], me.get_velocity(),\
                        pucks[i][2]) < 1.1 * D:
                resacc = Res_acc(tca,me.get_position(), pucks[i][1],\
                                 me.get_velocity(),pucks[i][2])
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                #time.sleep(2/50) #-> dann kann man halt in der Zeit nichts anderes machen
                q_request.put(('SET_ACCELERATION', 0, secret, idd))
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen     
  
def worker_heiter(idd, secret, q_request, q_reply):
    #import modules_JH
    #1. Initialisieren des Pucks und erfassen der Parameter
    q_request.put(('SET_NAME', 'Jakob Heiter', secret, idd))
    q_request.put(('GET_SIZE', idd))
    q_request.put(('GET_BOX', idd))
    
    nameok = q_reply.get()
    if nameok[1] == None:
        raise ValueError("Setting name failed")
    n_pucks = q_reply.get()[1]
    simbox = q_reply.get()[1]#für Reflexionscheck
    box_xmin = simbox.xmin
    box_xmax = simbox.xmax
    box_ymin = simbox.ymin
    box_ymax = simbox.ymax
    
    pucks = dict()#Zentrales Verzeichnis der Pucks
    danger_list = []#verzeichnis der Intruder
    D = 2 #Durchmesser der Pucks
    amax = 100.
    vmax = 42.
        
    for i in range(n_pucks):#initiale Abfrage aller Pucks zu beginn der Sim.
        q_request.put(('GET_PUCK', i,idd))
        puck = q_reply.get()[1]#geht das so?, sonst: q_reply.get([1])
        if puck.is_alive() == False:
            continue
        if puck.get_name()== 'Jakob Heiter':
            me = puck                #speichert mich gesondert als 'me' ab
            continue
        p_list = [puck.get_id(), puck.get_position(), puck.get_velocity(), \
                  puck.get_acceleration(), puck.get_time(), puck.is_alive()]
        pucks[i] = p_list
        
    for i in pucks:#Prüft welche Pucks gefährlich werden könnten und setzt diese auf die danger_list
        tca = Tca(me.get_position(),pucks[i][1],me.get_velocity(),pucks[i][2])
        if tca < 1.5:#random Zahl -> testen: <2.5!
            danger_list.append(pucks[i])
            if Dtca_abs(tca,me.get_position(), pucks[i][1], me.get_velocity(),\
                        pucks[i][2]) < 1.1 * D:
                resacc = Res_acc(tca,me.get_position(), pucks[i][1],\
                                 me.get_velocity(),pucks[i][2])
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                q_request.put(('SET_ACCELERATION', 0, secret, idd))
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen

    while True:#dauerhafte checks der priorisierten pucks und aller anderen
        prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd)
        time.sleep(5/50)
        prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd)
        time.sleep(5/50)
        rest_check(pucks, me, danger_list, D, q_request, secret, idd)
        time.sleep(5/50)

        
###############################################################################Ablage von vermutlich unnötigem                
#while True:#dauernde checks
#    for i  in range(len(danger_list)):#check der gefährder, timing fehlt
#        q_request.put('GET_PUCK', danger_list[i[0]], id)
#        puck = q_reply.get()[1]
#        if puck.is_alive() == False:
#            continue
#        tca = Tca(me.get_position(),puck.get_position(),me.get_velocity(),puck.get_velocity())
#        if tca >= 10:
#            danger_list.remove[i]
#            continue
#        else:
#            if Dtca_abs(tca,me.get_position(), puck.get_position(), me.get_velocity(),\
#                        puck.get_velocity()) < 1.1 * D:
#                resacc = Res_acc(tca,me.get_position(), pucks(i[1]),\
#                                 me.get_velocity(),pucks(i[2]))
#                q_request.put('SET_ACCELERATION', resacc, secret, id)
#                #time.sleep(2/50??) #-> dann kann man halt in der Zeit nichts anderes machen -> threading, asyncio
#                q_request.put('SET_ACCELERATION', 0, secret, id)
#                danger_list.remove[i] #den Puck für den ausgewichen wurde streichen          
  
#auch: reflexion an rand checken
#geschwindigkeit nach Ausweichen checken und ggf. anderes Ausweichen       