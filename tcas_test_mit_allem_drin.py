# This file is part of the TCAS Server. Do not redistribute.

import random
import time
import pygame
import numpy as np
import multiprocessing as mp
import queue # for Empty

import params
import secret
import box_server
import puck_server
#import worker

SCALE = 10






vmax = 42.
vmin = 10.
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
    

def Res_acc (tca,  r_self, r_enemy, v_self, v_enemy):#Idee: als return ein Tupel geben, dann kann in den besonderen Situationen z.B. die Laufzeit angepasst werden
    R_puck = 1.
    r_tca_self = r_of_t(r_self, v_self,np.array([0,0]), tca)
    r_tca_enemy = r_of_t(r_enemy, v_enemy, np.array([0,0]), tca)
    r_tca = r_tca_enemy - r_tca_self
    res_acc = 2*(2*R_puck - r_tca)*(tca**(-2))
    if np.linalg.norm(v_self+res_acc) >= vmax:
        max_acc = vmax-v_self
        return max_acc #dann für länger laufen lassen! Check im Programm dazu einbauen!
    if np.linalg.norm(v_self+res_acc) <= vmin:
        min_acc = vmin + v_self
        return min_acc
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


def update_me(q_request, q_reply, me, idd):
        q_request.put(('GET_PUCK', me.get_id(), idd))
        ich = q_reply.get()[1]
        if not isinstance(me, puck_server.Puck_Server):
            print(f'der falsche typ ist: {type(me)}')
            q_reply.get()
            return
        return ich

def speed_check(q_reply, q_request, idd, me, secret):# passt noch gar nicht, siehe z.B. negative vektorkomponenten!!!
    if np.linalg.norm(me.get_velocity()) <= 20:
        acc = 5 * (me.get_velocity()/np.linalg.norm(me.get_velocity()))
        q_request.put(('SET_ACCELERATION', acc, secret, idd))
        print('STALL')
        acc_check = q_reply.get()[1]
        if not np.array_equal(acc, acc_check):
            raise ValueError(f'acceleration mismatch! The replz was {acc_check}')
        time.sleep(10/50)
        q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
        acc_check = q_reply.get()[1]
        if not np.array_equal(np.array([0,0]), acc_check):
            raise ValueError(f'acceleration mismatch! The replz was {acc_check}')
    if np.linalg.norm(me.get_velocity()) >= 35:
        acc = -4 * (me.get_velocity()/np.linalg.norm(me.get_velocity()))
        q_request.put(('SET_ACCELERATION', acc, secret, idd))
        print('OVERSPEED')
        acc_check = q_reply.get()[1]
        if not np.array_equal(acc, acc_check):
            raise ValueError(f'acceleration mismatch! The replz was {acc_check}')
        time.sleep(10/50)
        q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
        acc_check = q_reply.get()[1]
        if not np.array_equal(np.array([0,0]), acc_check):
            raise ValueError(f'acceleration mismatch! The replz was {acc_check}')   

    
def prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd):
    for i  in reversed(range(len(danger_list))):#check der gefährder, reversed um poppen zu können
        q_request.put(('GET_PUCK', danger_list[i][0], idd))#i-1??
        #try:
        #    puck = q_reply.get(timeout=2)[1]  #vermeidet deadlock
        #except q_reply.Empty:
        #    print("Keine Antwort in der Queue erhalten.")
        puck = q_reply.get()[1]
        if type(puck) != puck_server.Puck_Server:#sollte jetzt nicht mehr vorkommen
            continue
        if puck.is_alive() == False:
            continue
        tca = Tca(me.get_position(),puck.get_position(),me.get_velocity(),puck.get_velocity())
        if tca < 0:
            continue
        if tca >= 1.5:
            danger_list.pop(i)#ganz gefährlich: indexverschiebung!
            continue
        else:
            if Dtca_abs(tca,me.get_position(), puck.get_position(), me.get_velocity(),  
                        puck.get_velocity()) < 1.3 * D:
                resacc = Res_acc(tca,me.get_position(), pucks[i+1][1],\
                                 me.get_velocity(),pucks[i+1][2])              #ist da beides mal das +1 legit?
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                print(f"!!AUSWEICHEN!!prio mit {resacc}")
                acc_check = q_reply.get()[1]
                if not np.array_equal(resacc, acc_check):
                    raise ValueError('acceleration mismatch!')
                time.sleep(10/50)
                q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
                acc_check = q_reply.get()[1]
                if not np.array_equal(np.array([0,0]), acc_check):
                    raise ValueError('acceleration mismatch!')
                danger_list.pop(i) #den Puck für den ausgewichen wurde streichen, siehe oben!

                
def rest_check(pucks, me, danger_list, D, q_request, secret, idd, q_reply):#grade konmmen gefuelt alle ausweichungen von hier
    for i in pucks:
        tca = Tca(me.get_position(),pucks[i][1],me.get_velocity(),pucks[i][2])
        if tca < 0:#wenn tca<0: liegt in der Vergangenheit, egal!
            continue
        if tca < 1.5:#random Zahl -> testen
            if pucks[i] not in danger_list:
                danger_list.append(pucks[i])
            if Dtca_abs(tca,me.get_position(), pucks[i][1], me.get_velocity(),\
                        pucks[i][2]) < 1.2 * D:
                resacc = Res_acc(tca,me.get_position(), pucks[i][1],\
                                 me.get_velocity(),pucks[i][2])
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                print(f"!!AUSWEICHEN!!rest mit {resacc}")
                acc_check = q_reply.get()[1]
                if not np.array_equal(resacc, acc_check):
                    raise ValueError('acceleration mismatch!')
                time.sleep(10/50) #-> dann kann man halt in der Zeit nichts anderes machen
                q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
                acc_check = q_reply.get()[1]
                if not np.array_equal(np.array([0,0]), acc_check):
                    raise ValueError('acceleration mismatch!')
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen

 
##########################################################################################    
 
def worker_heiter(idd, secret, q_request, q_reply):
    #import modules_JH
    #1. Initialisieren des Pucks und erfassen der Parameter
    q_request.put(('SET_NAME', 'Jakob Heiter', secret, idd))
    q_request.put(('GET_SIZE', idd))
    q_request.put(('GET_BOX', idd))
    
    print("initial requests sent")
    
    nameok = q_reply.get()
    if nameok[1] == None:
        raise ValueError("Setting name failed")
    n_pucks = q_reply.get()[1]
    simbox = q_reply.get()[1]#für Reflexionscheck
    box_xmin = simbox.xmin
    box_xmax = simbox.xmax
    box_ymin = simbox.ymin
    box_ymax = simbox.ymax
    
    print("box received")
    
    pucks = dict()#Zentrales Verzeichnis der Pucks
    danger_list = []#verzeichnis der Intruder
    D = 2 #Durchmesser der Pucks
    
    print("danger_list and dicitionary set up")
        
    for i in range(n_pucks):#initiale Abfrage aller Pucks zu beginn der Sim.
        q_request.put(('GET_PUCK', i,idd))
        puck = q_reply.get()[1]
        if puck.is_alive() == False:
            continue
        if puck.get_name()== 'Jakob Heiter':
            me = puck
            print(f"Ich bin abgespeichert: {puck.get_name()}")    #speichert mich gesondert als 'me' ab
            continue
        p_list = [puck.get_id(), puck.get_position(), puck.get_velocity(), \
                  puck.get_acceleration(), puck.get_time(), puck.is_alive()]
        pucks[i] = p_list

    print("initial puck request sent, dict:" ,pucks)

###queue clean bis hier###   
     
    for i in pucks:#Prüft welche Pucks gefährlich werden könnten und setzt diese auf die danger_list
        tca = Tca(me.get_position(),pucks[i][1],me.get_velocity(),pucks[i][2])
        if tca < 1.5 :#random Zahl -> testen, <2.5!, wohl auch kleiner 1.5
            danger_list.append(pucks[i])
            if Dtca_abs(tca,me.get_position(), pucks[i][1], me.get_velocity(),\
                        pucks[i][2]) < 1.2 * D:
                resacc = Res_acc(tca,me.get_position(), pucks[i][1],\
                                 me.get_velocity(),pucks[i][2])
                q_request.put(('SET_ACCELERATION', resacc, secret, idd))
                acc_check = q_reply.get()[1]
                if not np.array_equal(resacc, acc_check):
                    raise ValueError('acceleration mismatch!')
                print(f"!!AUSWEICHEN!!1 mit {resacc}")
                time.sleep(10/50)
                q_request.put(('SET_ACCELERATION', np.array([0,0]), secret, idd))
                acc_check = q_reply.get()[1]
                if not np.array_equal(np.array([0,0]), acc_check):
                    raise ValueError('acceleration mismatch!')
                danger_list.pop(-1) #den Puck für den ausgewichen wurde streichen
                
    print("initial danger check done, danger_list:", danger_list , "entering continuous checks")

    while True:#dauerhafte checks
        me = update_me(q_request, q_reply, me, idd)
        speed_check(q_reply, q_request, idd, me, secret)
        prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd)
        time.sleep(3/50)
        me = update_me(q_request, q_reply, me, idd)
        speed_check(q_reply, q_request, idd, me, secret)
        prio_check(danger_list, q_request, q_reply, me, D, pucks, secret, idd)
        time.sleep(3/50)
        me = update_me(q_request, q_reply, me, idd)
        speed_check(q_reply, q_request, idd, me, secret)
        rest_check(pucks, me, danger_list, D, q_request, secret, idd, q_reply)
        time.sleep(3/50)
        print(me.get_fuel())
        if me.is_alive() == False:
            break


################################################################################################### 

def dummy_worker(idd, secret, q_request, q_reply):
    #import modules_JH
    #1. Initialisieren des Pucks und erfassen der Parameter
    q_request.put(('SET_NAME', 'dummy', secret, idd))
    q_request.put(('GET_SIZE', idd))
    q_request.put(('GET_BOX', idd))
    
    nameok = q_reply.get()
    if nameok[1] == None:
        raise ValueError("Setting name failed")

##################################################################################

def main():
    margin = 1.5 # new pucks will be created at least this far from an edge
    fps = 50 # frames per second
    tick = 1.0/fps # duration of a tick
    t = 0.0  # time in s 
    v0 = (params.V_MIN + params.V_MAX)/2 # initial velocity

# Create box:
    simbox = box_server.Box_Server(0.0, 120.0, 0.0, 75.0)

    pygame.init()

    screen = pygame.display.set_mode( (SCALE*simbox.xmax, SCALE*simbox.ymax) )
    screen.fill(pygame.Color("black"))
#   font = pygame.font.SysFont("timesnewroman", 11)
    pygame.display.set_caption("TCAS")
    pygame.display.flip()
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        return

# Create the request and reply queues
    manager = mp.Manager()
    q_request = manager.Queue()

# Create a list of workers and their queues
# In diese Liste können Sie zum Testen mehrere Instanzen Ihres
# Workers einfügen. Jeder Worker kontrolliert einen Puck, es werden
# soviele Pucks erzeugt, wie es Worker gibt.
    workers = [ worker_heiter, dummy_worker, dummy_worker, dummy_worker, dummy_worker, dummy_worker, dummy_worker]
    n_workers = len(workers)
    queues = [ manager.Queue() for i in range(n_workers)]
    secrets = secret.Secret(n_workers)

# Create a puck for each worker
    pucks = []
    for n in range(n_workers):
        while True:
            s = np.array(
                [ random.uniform(simbox.xmin + margin, simbox.xmax - margin),
                  random.uniform(simbox.ymin + margin, simbox.ymax - margin) ] )
# Check here that there is no puck closer than margin to this one ...
            too_close = False
            for puck in pucks:
                dist = np.linalg.norm(puck.s - s)
                if dist < margin:
                    too_close = True
                    break
            if too_close:
                print("DEBUG: Puck too close.")
                continue
            else:
                break
        phi = random.uniform(0.0, 2.0*np.pi)
        v = v0*np.array( [ np.cos(phi), np.sin(phi) ])
        puck = puck_server.Puck_Server(n, 0.0, s, v)
        pucks.append(puck)

# Now create and start the processes
    processes = []
    for n in range(n_workers):
        process = mp.Process(target=workers[n], args=(n, secrets.get_secret(n), 
                             q_request, queues[n]))
        process.name = f"{str(workers[n]).split()[1]}"
        process.start()
        processes.append(process)

    n_alive = n_workers
    t_offset = time.perf_counter()
    t_base   = 0.0
    queue_time_stamp = time.perf_counter() 
    timeout = 1.0
# Now enter the loop of reading and answering the request queue
    while True:
# We process the queue until one tick has passed, then
# update the pucks, and than return to processing the queue again ...
        while True:
            try:
                request = q_request.get(block = False)
            except queue.Empty:
                request = None
            else:
                queue_time_stamp = time.perf_counter() 

# Use structural pattern maching here to decode the requests
            match request:
                case ('GET_SIZE', idd):
                    reply = ('GET_SIZE', n_workers)

                case ('GET_BOX', idd):
                    reply = ('GET_BOX', simbox)

                case ('GET_PUCK', n_puck, idd):
                    try:
                        puck = pucks[n_puck]
                    except IndexError:
                        puck = None
                    reply = ('GET_PUCK', puck)

                case ('SET_NAME', name, scrt, idd):
                    if secrets.authenticate(scrt, idd):
                        if type(name) == str:
                            pucks[idd].set_name(name)
                            reply = ('SET_NAME', name)
                        else:
                            reply = ('SET_NAME', None)
                    else:
                        print("authenication failed")

                case ('SET_ACCELERATION', a, scrt, idd):
                    if secrets.authenticate(scrt, idd):
                        if np.linalg.norm(a) <= params.A_MAX:
                            pucks[idd].set_acceleration(a)
                            reply = ('SET_ACCELERATION', a)
                        else:
                            reply = ('SET_ACCELERATION', None)

                case None:
                    reply = None

                case _:
                    print(f"main(): Unknown request received.")
                    continue

            if reply != None:
                queues[idd].put(reply)
            t = time.perf_counter() - t_offset
            if t > t_base + tick:
                t_base += tick
                break # leave queue processing loop

# update the pucks
        for puck in pucks:
# better use is_alive() here
            if not puck.alive:
                continue
            puck.update(screen, t, simbox)
        pygame.display.flip()

# check for minimum velocity and collisions
# why not "for puck in pucks" or "for (puck, idx) in enumerate(pucks)"?
        for i in range(n_workers):
# use is_alive:
            if not pucks[i].alive:
                continue
            v_s = np.linalg.norm(pucks[i].v) # scalar velocity
            if v_s < params.V_MIN:
                pucks[i].add_points(round(10*t))
                pucks[i].kill(screen, "stalled")
                n_alive -= 1
                continue
            elif v_s > params.V_MAX:
                pucks[i].add_points(round(10*t))
                pucks[i].kill(screen, "overspeed")
                n_alive -= 1
                continue
            
            for j in range(i + 1, n_workers):
# use is_alive:
                if not pucks[j].alive:
                    continue
                if np.linalg.norm(pucks[i].s - pucks[j].s) < 2.0:
                    pucks[i].add_points(round(10*t))
                    pucks[i].kill(screen, "collision")
                    pucks[j].add_points(round(10*t))
                    pucks[j].kill(screen, "collision")
                    n_alive -= 2

        if n_alive <= 2:
            for (i, process) in enumerate(processes):
                if pucks[i].is_alive():
                    pucks[i].add_points(round(10*t))
                    pucks[i].kill(screen, "survivor")
                    n_alive -= 1

        now = time.perf_counter()
        if now - queue_time_stamp > timeout:
            break

    for process in processes:
        process.join()

    for puck in pucks:
        puck.farewell()

    print(f"TCAS beendet nach {t = }")
    pygame.base.quit()
#    exit()

if __name__ == '__main__':
    main()
