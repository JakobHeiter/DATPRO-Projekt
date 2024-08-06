import numpy as np
import asyncio

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
    vel = v_self
    r_tca_self = r_of_t(r_self, v_self,np.array([0,0]), tca)
    r_tca_enemy = r_of_t(r_enemy, v_enemy, np.array([0,0]), tca)
    r_tca = r_tca_enemy - r_tca_self
    res_acc = 2*(2*R_puck - r_tca)*(tca**(-2))
    if vel+res_acc >= vmax:
        max_acc = vmax-vel
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

    
def prio_check():
    for i  in range(len(danger_list)):#check der gefährder, timing fehlt
        q_request.put('GET_PUCK', danger_list[i[0]], id)
        puck = q_reply.get()[1]
        if puck.is_alive() == False:
            continue
        tca = Tca(me.get_position(),puck.get_position(),me.get_velocity(),puck.get_velocity())
        if tca >= (11/50):
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
                
def rest_check():
    for i in pucks:
        tca = Tca(me.get_position(),pucks(i[1]),me.get_velocity(),pucks(i[2]))
        if tca < (11/50):#random Zahl -> testen
            danger_list.append(pucks(i))
            if Dtca_abs(tca,me.get_position(), pucks(i[1]), me.get_velocity(),\
                        pucks(i[2])) < 1.1 * D:
                resacc = Res_acc(tca,me.get_position(), pucks(i[1]),\
                                 me.get_velocity(),pucks(i[2]))
                q_request.put('SET_ACCELERATION', resacc, secret, id)
                #time.sleep(2/50) #-> dann kann man halt in der Zeit nichts anderes machen -> threading, asyncio
                q_request.put('SET_ACCELERATION', 0, secret, id)
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen        

    
        
    
    
    
#nur zum testen:
a = np.array([12,24])
b = np.array([1,12])
c = np.array([-12,5])
d = np.array([23-2])
 