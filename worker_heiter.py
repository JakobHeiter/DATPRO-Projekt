def worker_heiter(idd, secret, q_request, q_reply):
    import time
    import numpy as np
    import puck_server

###########Benötigte Module aus modules_jh###########    
    vmax = 42.
    vmin = 10.
    amax = 100
    SCALE = 10 


    def r_of_t(r_now, v_now, a_now, t):
        r_t = r_now + v_now*t + 0.5*a_now*(t**2)
        return r_t
  
    def Tca(r_self, r_enemy, v_self, v_enemy):
    
        tca = -1*((np.dot((r_enemy - r_self),(v_enemy - v_self)))/(np.dot((v_enemy- v_self),(v_enemy - v_self))))
        return tca

    def Dtca_abs( r_self, r_enemy, v_self, v_enemy):
        dtca = np.linalg.norm((r_enemy- r_self)- ((v_enemy- v_self)*(np.dot(\
        (r_enemy-r_self),(v_enemy-v_self)))/(np.dot((v_enemy-v_self),\
        (v_enemy-v_self)))))
        return dtca

    def Dtca_vec( r_self, r_enemy, v_self, v_enemy):
        dtca = ((r_enemy- r_self)- ((v_enemy- v_self)*np.dot(\
                (r_enemy-r_self),(v_enemy-v_self))/(np.dot((v_enemy-v_self),\
                (v_enemy-v_self)))))
        return dtca
    

    def Res_acc(tca,  r_self, r_enemy, v_self, v_enemy):
        R_puck = 1.
        r_tca_self = r_of_t(r_self, v_self,np.array([0,0]), tca)
        r_tca_enemy = r_of_t(r_enemy, v_enemy, np.array([0,0]), tca)
        r_tca = r_tca_enemy - r_tca_self
        res_acc = 2*(2*R_puck - r_tca)*(tca**(-2))
        if np.linalg.norm(v_self + 10 * res_acc) <= vmin:
            acc = 15 * (v_self/np.linalg.norm(v_self))
            return acc
        if np.linalg.norm(v_self + 10 * res_acc) >= vmax:
            acc = -10 * (v_self/np.linalg.norm(v_self))
            return acc
        if np.linalg.norm(res_acc) > amax:
            return (res_acc/np.linalg.norm(res_acc))*(amax-5)
        return res_acc

    def update_me(q_request, q_reply, me, idd):
            q_request.put(('GET_PUCK', me.get_id(), idd))
            ich = q_reply.get()[1]
            if not isinstance(me, puck_server.Puck_Server):
                print(f'der falsche typ ist: {type(me)}')
                q_reply.get()
                return
            return ich

    def speed_check(q_reply, q_request, idd, me, secret):
        if np.linalg.norm(me.get_velocity()) <= 20:
            acc = 40 * (me.get_velocity()/np.linalg.norm(me.get_velocity()))
            q_request.put(('SET_ACCELERATION', acc, secret, idd))
            acc_check = q_reply.get()[1]
            if not np.array_equal(acc, acc_check):
                raise ValueError(f'acceleration mismatch! The reply was {acc_check}')
            time.sleep(2/50)
            q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
            acc_check = q_reply.get()[1]
            if not np.array_equal(np.array([0,0]), acc_check):
                raise ValueError(f'acceleration mismatch! The replz was {acc_check}')
        if np.linalg.norm(me.get_velocity()) >= 35:
            acc = -30 * (me.get_velocity()/np.linalg.norm(me.get_velocity()))
            q_request.put(('SET_ACCELERATION', acc, secret, idd))
            acc_check = q_reply.get()[1]
            if not np.array_equal(acc, acc_check):
                raise ValueError(f'acceleration mismatch! The replz was {acc_check}')
            time.sleep(2/50)
            q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
            acc_check = q_reply.get()[1]
            if not np.array_equal(np.array([0,0]), acc_check):
                raise ValueError(f'acceleration mismatch! The replz was {acc_check}')   
 

    
    def prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd):
        for i  in reversed(range(len(danger_list))):
            q_request.put(('GET_PUCK', danger_list[i][0], idd))
            puck = q_reply.get()[1]
            if type(puck) != puck_server.Puck_Server:
                continue
            if puck.is_alive() == False:
                continue
            tca = Tca(me.get_position(),puck.get_position(),me.get_velocity(),puck.get_velocity())
            if tca < 0:
                danger_list.pop(i)
                continue
            if tca >= 1.1:
                danger_list.pop(i)
 
                continue
            else:
                if Dtca_abs(me.get_position(), puck.get_position(), me.get_velocity(),  
                            puck.get_velocity()) < 1.3 * D:
                    resacc = 3 * Res_acc(tca,me.get_position(), pucks[i+1][1],\
                                     me.get_velocity(),pucks[i+1][2])           
                    q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                    acc_check = q_reply.get()[1]
                    if not np.array_equal(resacc, acc_check):
                        raise ValueError('acceleration mismatch!')
                    time.sleep(2/50)
                    q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
                    acc_check = q_reply.get()[1]
                    if not np.array_equal(np.array([0,0]), acc_check):
                        raise ValueError('acceleration mismatch!')
                    danger_list.pop(i) #den Puck für den ausgewichen wurde streichen

                
    def rest_check(pucks, me, danger_list, D, q_request, secret, idd, q_reply):
        for i in pucks:
            tca = Tca(me.get_position(),pucks[i][1],me.get_velocity(),pucks[i][2])
            if tca < 0:
                continue
            if tca < 1.3:
                if pucks[i] not in danger_list:
                    danger_list.append(pucks[i])
                if Dtca_abs(me.get_position(), pucks[i][1], me.get_velocity(),\
                            pucks[i][2]) < 1.3 * D:
                    resacc = 3 * Res_acc(tca,me.get_position(), pucks[i][1],\
                                     me.get_velocity(),pucks[i][2])
                    q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                    acc_check = q_reply.get()[1]
                    if not np.array_equal(resacc, acc_check):
                        raise ValueError('acceleration mismatch!')
                    time.sleep(2/50) #-> dann kann man halt in der Zeit nichts anderes machen
                    q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
                    acc_check = q_reply.get()[1]
                    if not np.array_equal(np.array([0,0]), acc_check):
                        raise ValueError('acceleration mismatch!')
                    danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen
                
#########################################################################################

    #Initialisieren des Pucks und erfassen der Parameter
    q_request.put(('SET_NAME', 'Jakob Heiter', secret, idd))
    q_request.put(('GET_SIZE', idd))
    
    nameok = q_reply.get()
    if nameok[1] == None:
        raise ValueError("Setting name failed")
    n_pucks = q_reply.get()[1]
    
    pucks = dict()#Zentrales Verzeichnis der Pucks
    danger_list = []#verzeichnis der Intruder
    D = 2 #Durchmesser der Pucks
    
        
    for i in range(n_pucks):#initiale Abfrage aller Pucks zu beginn der Sim.
        q_request.put(('GET_PUCK', i,idd))
        puck = q_reply.get()[1]
        if puck.is_alive() == False:
            continue
        if puck.get_name()== 'Jakob Heiter':
            me = puck   #speichert mich gesondert als 'me' ab
            continue
        p_list = [puck.get_id(), puck.get_position(), puck.get_velocity(), \
                  puck.get_acceleration(), puck.get_time(), puck.is_alive()]
        pucks[i] = p_list 
     
    for i in pucks:#Prüft welche Pucks gefährlich werden könnten und setzt diese auf die danger_list
        tca = Tca(me.get_position(),pucks[i][1],me.get_velocity(),pucks[i][2])
        if tca < 1.5:
            danger_list.append(pucks[i])
            if Dtca_abs(me.get_position(), pucks[i][1], me.get_velocity(),\
                        pucks[i][2]) < 1.3* D:
                resacc = 3*Res_acc(tca,me.get_position(), pucks[i][1],\
                                 me.get_velocity(),pucks[i][2])
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                acc_check = q_reply.get()[1]
                if not np.array_equal(resacc, acc_check):
                    raise ValueError('acceleration mismatch!')
                print(f"!!AUSWEICHEN!!1 mit {resacc}")
                time.sleep(2/50)
                q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
                acc_check = q_reply.get()[1]
                if not np.array_equal(np.array([0,0]), acc_check):
                    raise ValueError('acceleration mismatch!')
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen

    while True:#dauerhafte checks
        me = update_me(q_request, q_reply, me, idd)     #Aktualisiert mich selbst um korrekte Berechnungen durchführen zu können
        speed_check(q_reply, q_request, idd, me, secret)#erkennt das Risiko von overspeed und stall und beschleunigt/bremst ggf.
        prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd)#Kollisionscheck bei allen Pucks der danger_list
        time.sleep(1/50)
        me = update_me(q_request, q_reply, me, idd)
        speed_check(q_reply, q_request, idd, me, secret)
        prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd)
        time.sleep(1/50)
        me = update_me(q_request, q_reply, me, idd)
        speed_check(q_reply, q_request, idd, me, secret)
        rest_check(pucks, me, danger_list, D, q_request, secret, idd, q_reply)#Kollisionscheck für alle pucks, aktualisieren der danger_list
        time.sleep(1/50)