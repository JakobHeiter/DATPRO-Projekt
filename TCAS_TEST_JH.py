import unittest
import numpy as np
from tcas_test_mit_allem_drin import Res_acc, Tca, Dtca_abs, r_of_t


class TCAS_TEST(unittest.TestCase):

    def test_Tca(self):
        r_self1 = np.array([0, 0])
        r_enemy1 = np.array([10, 10])
        v_self1 = np.array([1, 1])
        v_enemy1 = np.array([-1, -1])
        tca = Tca(r_self1, r_enemy1, v_self1, v_enemy1)
        self.assertEqual(tca, 5.0)

        r_self2 = np.array([12, 18])
        r_enemy2 = np.array([1, 7])
        v_self2 = np.array([7, 1])
        v_enemy2 = np.array([5, 5])
        tca = Tca(r_self2, r_enemy2, v_self2, v_enemy2)
        self.assertEqual(tca, 1.1)


    def test_Dtca_abs(self):
        r_self = np.array([0, 0])
        r_enemy = np.array([10, 10])
        v_self = np.array([1, 1])
        v_enemy = np.array([-1, -1])
        dtca_abs = Dtca_abs(r_self, r_enemy, v_self, v_enemy)
        self.assertEqual(dtca_abs, 0.0)

    def test_Res_acc(self):
        r_self = np.array([0, 0])
        r_enemy = np.array([10, 10])
        v_self = np.array([1, 1])
        v_enemy = np.array([-1, -1])
        tca = Tca(r_self, r_enemy, v_self, v_enemy)
        res_acc = Res_acc(tca, r_self, r_enemy, v_self, v_enemy)
        self.assertTrue(np.linalg.norm(res_acc) <= 100)
        
        r_self2 = np.array([0, 0])
        r_enemy2 = np.array([3, 0])
        v_self2 = np.array([2, 0])
        v_enemy2 = np.array([-4, 0])
        tca2 = Tca(r_self2, r_enemy2, v_self2, v_enemy2)
        res_acc2 = Res_acc(tca2, r_self, r_enemy, v_self, v_enemy)
        self.assertTrue(np.linalg.norm(res_acc2) <= 100)

    def test_r_of_t(self):
        r_now = np.array([12,2])
        v_now = np.array([-4,-7])
        a_now = np.array([2,3])
        t = 20
        R_of_t = r_of_t(r_now, v_now, a_now, t)
        self.assertTrue(np.array_equal([332., 462.],R_of_t) )

if __name__ == '__main__':
    unittest.main()
