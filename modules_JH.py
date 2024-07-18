import numpy as np
  
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
    

def Res_acc (tca,  r_self, r_enemy, v_self, v_enemy):
    R_puck = 1.
    r_tca_self = r_of_t(r_self, v_self,np.array([0,0]), tca)
    r_tca_enemy = r_of_t(r_enemy, v_enemy, np.array([0,0]), tca)
    r_tca = r_tca_enemy - r_tca_self
    res_acc = 2*(2*R_puck - r_tca)*(tca**(-2))
    return res_acc
    
#nur zum testen:
a = np.array([12,24])
b = np.array([1,12])
c = np.array([-12,5])
d = np.array([23-2])