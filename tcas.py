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
import worker

SCALE = 10

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
    workers = [ worker.worker_heiter, worker.worker_heiter,
                worker.worker_heiter, worker.worker_heiter]
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
                case ('GET_SIZE', id):
                    reply = ('GET_SIZE', n_workers)

                case ('GET_BOX', id):
                    reply = ('GET_BOX', simbox)

                case ('GET_PUCK', n_puck, id):
                    try:
                        puck = pucks[n_puck]
                    except IndexError:
                        puck = None
                    reply = ('GET_PUCK', puck)

                case ('SET_NAME', name, scrt, id):
                    if secrets.authenticate(scrt, id):
                        if type(name) == str:
                            pucks[id].set_name(name)
                            reply = ('SET_NAME', name)
                        else:
                            reply = ('SET_NAME', None)
                    else:
                        print("authenication failed")

                case ('SET_ACCELERATION', a, scrt, id):
                    if secrets.authenticate(scrt, id):
                        if np.linalg.norm(a) <= params.A_MAX:
                            pucks[id].set_acceleration(a)
                            reply = ('SET_ACCELERATION', a)
                        else:
                            reply = ('SET_ACCELERATION', None)

                case None:
                    reply = None

                case _:
                    print(f"main(): Unknown request received.")
                    continue

            if reply != None:
                queues[id].put(reply)
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
    #exit()


if __name__ == '__main__':
    main()
