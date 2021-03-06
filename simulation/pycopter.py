#!/usr/bin/env python3

from scipy import linalg as la
import matplotlib.pyplot as pl
import numpy as np
import math
import sys
import random
import scipy.stats
import csv

from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
import uwb_agent as range_agent

sys.path.append("pycopter/")
import quadrotor as quad
import formation_distance as form
import quadlog
import animation as ani

PI = 3.14159265359

class pycopter:
    def __init__(self, tf=500, dt=0.02):
        m = 0.65 # Kg
        l = 0.23 # m
        Jxx = 7.5e-3 # Kg/m^2
        Jyy = Jxx
        Jzz = 1.3e-2
        Jxy = 0
        Jxz = 0
        Jyz = 0
        J = np.array([[Jxx, Jxy, Jxz], \
                    [Jxy, Jyy, Jyz], \
                    [Jxz, Jyz, Jzz]])
        CDl = 9e-3
        CDr = 9e-4
        kt = 3.13e-5  # Ns^2
        km = 7.5e-7   # Ns^2
        kw = 1/0.18   # rad/s

        # Initial conditions
        att_0 = np.array([0.0, 0.0, 0.0])
        pqr_0 = np.array([0.0, 0.0, 0.0])

        d = 4.0
        dy = d * (np.sqrt(3)/2)

        xyz0_0 = np.array([0.0, 0.0, 0.1]) #4
        xyz1_0 = np.array([d,   0.0, 0.05]) #1.5
        xyz2_0 = np.array([d/2, dy, 0.0])
        xyz3_0 = np.array([d/2, -dy, 0.0])

        xyz4_0 = np.array([-(d/2), dy, 0.0])
        xyz5_0 = np.array([-d, 0.0, 0.05]) #1.5
        xyz6_0 = np.array([-(d/2), -dy, 0.0])

        xyz_uav_0 = np.array([1.0, 1.5, 0.0])


        self.state = 0
        #wp = np.array([ [ 2,  2, -5 ], [ 2, -2, -5], [ -2, -2, -5 ], [-2,  2, -5] ])
        #wp = np.array([ [ d,  dy+1, -3 ], [ d, -(dy+1), -3 ], [ -1, -(dy+1), -3 ], [-1,  dy+1, -3 ] ])
        self.wp = np.array([ [ d,  dy+1, -3 ], [ d, -dy+1, -3 ], [ -3, -dy-1, -3 ], [-4,  dy+1, -3 ] ])


        v_ned_0 = np.array([0.0, 0.0, 0.0])
        w_0 = np.array([0.0, 0.0, 0.0, 0.0])

        # Setting quads
        self.uwb0 = quad.quadrotor(0, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz0_0, v_ned_0, w_0)

        self.uwb1 = quad.quadrotor(1, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz1_0, v_ned_0, w_0)

        self.uwb2 = quad.quadrotor(2, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz2_0, v_ned_0, w_0)

        self.uwb3 = quad.quadrotor(3, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz3_0, v_ned_0, w_0)

        self.uwb4 = quad.quadrotor(4, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz4_0, v_ned_0, w_0)

        self.uwb5 = quad.quadrotor(5, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz5_0, v_ned_0, w_0)

        self.uwb6 = quad.quadrotor(6, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz6_0, v_ned_0, w_0)

        self.UAV = quad.quadrotor(10, m, l, J, CDl, CDr, kt, km, kw, \
                att_0, pqr_0, xyz_uav_0, v_ned_0, w_0)

        # Simulation parameters
        self.tf = tf
        self.dt = dt
        self.time = np.linspace(0, tf, int(tf/dt))
        self.it = 0
        self.frames = 50

        # Data log
        self.alg_log = quadlog.quadlog(self.time)
        self.UAV_log = quadlog.quadlog(self.time)

        #self.est_pos = np.zeros((self.time.size, 3))
        #self.gt_pos  = np.zeros((self.time.size, 3))

        self.Ed_log = np.zeros((self.time.size, 1))
        self.Ed2d_log = np.zeros((self.time.size, 1))
        self.Edalt_log = np.zeros((self.time.size, 1))
        self.Ed_vel_log = np.zeros((self.time.size, 1))
        self.eig_log = np.zeros((self.time.size, 3))

        self.RA0 = range_agent.uwb_agent( ID=0 )
        self.RA1 = range_agent.uwb_agent( ID=1 )
        self.RA2 = range_agent.uwb_agent( ID=2 )
        self.RA3 = range_agent.uwb_agent( ID=3 )
        self.RA4 = range_agent.uwb_agent( ID=4 )
        self.RA5 = range_agent.uwb_agent( ID=5 )
        self.RA6 = range_agent.uwb_agent( ID=6 )

        self.UAV_agent = range_agent.uwb_agent( ID=10, d=d)

        self.R = self.Q = self.n_of_particles = self.std_add = 0.0

    def get_dist_clean(self, p1, p2):
        return (np.linalg.norm(p1 - p2))

    def get_dist(self, p1, p2):
        mu, sigma = 0, 0.015
        std_err = np.random.normal(mu, sigma, 1)[0]
        '''
        with open('sim_std_err.csv', mode='a') as writeFile:
            writer = csv.writer(writeFile, delimiter=',')
            writer.writerow([std_err])
        writeFile.close()
        '''
        return (np.linalg.norm(p1 - p2)) + std_err


    def run(self, method, run_animation=False):
        if not (method == 'NF' or method == 'KF' or method == 'PF' or method == 'PKF' or \
                method == 'NF4' or method == 'KF4' or method == 'PF4' or method == 'PKF4' or method == 'PF2' or method == 'PKF2'):
            print ("Wrong Input, your in put was: ", method)
            return -1
        use = 4
        use4 = False
        if len(method) > 2:
            if method == 'PKF4' or method == 'PKF' or method == 'PKF2':
                if method == 'PKF4':
                    method = method[0:3]
                    use4 = True
                elif method == 'PKF2':
                    method = method[0:3]
                    use4 = True
                    use = 2  
            else:
                use4 = True
                method = method[0:2]

        dt = self.dt
        it = self.it
        kalmanStarted = False
        PFstarted = False
        PKFstarted = False

        quadcolor = ['r', 'g', 'b']
        pl.close("all")
        pl.ion()
        fig = pl.figure(0)
        axis3d = fig.add_subplot(111, projection='3d')
        frames = self.frames

        for t in self.time:
            acc_err = np.random.normal(0, 0.012, 1)[0]
            #HANDLE RANGE MEASUREMENTS:
            if it % 50 == 0 or it == 0: # or method == 'NF':
                #print(t)
                self.UAV_agent.handle_range_msg(self.RA0.id, self.get_dist(self.UAV.xyz, self.uwb0.xyz))
                self.UAV_agent.handle_range_msg(self.RA1.id, self.get_dist(self.UAV.xyz, self.uwb1.xyz))
                self.UAV_agent.handle_range_msg(self.RA2.id, self.get_dist(self.UAV.xyz, self.uwb2.xyz))
                self.UAV_agent.handle_range_msg(self.RA3.id, self.get_dist(self.UAV.xyz, self.uwb3.xyz))
                self.UAV_agent.handle_range_msg(self.RA4.id, self.get_dist(self.UAV.xyz, self.uwb4.xyz))
                self.UAV_agent.handle_range_msg(self.RA5.id, self.get_dist(self.UAV.xyz, self.uwb5.xyz))
                self.UAV_agent.handle_range_msg(self.RA6.id, self.get_dist(self.UAV.xyz, self.uwb6.xyz))
                if PFstarted and method == 'PF':
                    self.UAV_agent.PFupdate(use4=use4, use=use)
                if PKFstarted and method == 'PKF':
                    self.UAV_agent.updatePKF(use4=use4, use=use)
                if kalmanStarted and method == 'KF':
                    alg_pos = self.UAV_agent.calc_pos_alg(use4=use4)


            #HANDLE POS NO FILTER:
            if method == 'NF':
                alg_pos = self.UAV_agent.calc_pos_alg(use4=use4)

            
            #HANDLE KALMAN FILTER:
            if method == 'KF':
                if self.UAV.xyz[2] < -3 and not kalmanStarted:
                    self.R, self.Q = self.UAV_agent.startKF(self.UAV.xyz, v_ned=self.UAV.v_ned, dt=dt)
                    kalmanStarted = True
                
                if kalmanStarted:
                    self.UAV_agent.KFpredict( self.UAV.acc + acc_err )
                    alg_pos = self.UAV_agent.get_kf_state()
                else:
                    alg_pos = self.UAV_agent.calc_pos_alg(use4=use4)
                

            #HANDLE PARTICLE FILTER
            if method == 'PF':
                if self.UAV.xyz[2] < -3 and not PFstarted:
                    self.n_of_particles, self.std_add =  self.UAV_agent.startPF(start_vel=self.UAV.v_ned, dt=dt)
                    PFstarted = True

                if PFstarted:
                    alg_pos = self.UAV_agent.getPFpos()
                    #print (PF_pos)
                    self.UAV_agent.PFpredict(self.UAV.acc + acc_err)
                else:
                    alg_pos = self.UAV.xyz

            #HANDLE PARTICLE KALMAN FILTER
            if method == 'PKF':
                if self.UAV.xyz[2] < -3 and not PKFstarted:
                    self.R, self.Q, self.n_of_particles, self.std_add = self.UAV_agent.startPKF(self.UAV.acc + acc_err, dt=dt, xyz=self.UAV.xyz, v_ned=self.UAV.v_ned)
                    PKFstarted = True
                if PKFstarted:
                    alg_pos = self.UAV_agent.get_PKFstate()
                    self.UAV_agent.predictPKF(self.UAV.acc + acc_err)
                else:
                    alg_pos = self.UAV.xyz

            #print("Estimated pos:",alg_pos)
            #print("True pos:     ",self.UAV.xyz)

            #HANDLE UAV MOVEMENT:
            x_err = abs(self.wp[self.state][0] - self.UAV.xyz[0])
            y_err = abs(self.wp[self.state][1] - self.UAV.xyz[1])

            if self.state == 0:
                self.UAV.set_v_2D_alt_lya(np.array([x_err*0.03, y_err*0.03]), -3)
                if self.get_dist_clean(self.UAV.xyz, self.wp[self.state]) < 0.4:
                    self.state = 2
            elif self.state == 1:
                self.UAV.set_v_2D_alt_lya(np.array([x_err*0.03, -y_err*0.03]),-3)
                if self.get_dist_clean(self.UAV.xyz, self.wp[self.state]) < 0.4:
                    self.state = 0
            elif self.state == 2:
                self.UAV.set_v_2D_alt_lya(np.array([-x_err*0.03, -y_err*0.03]), -3)
                if self.get_dist_clean(self.UAV.xyz, self.wp[self.state]) < 0.4:
                    self.state = 3
            elif self.state == 3:
                self.UAV.set_v_2D_alt_lya(np.array([-x_err*0.03, y_err*0.03]), -3)
                if self.get_dist_clean(self.UAV.xyz, self.wp[self.state]) < 0.4:
                    self.state = 1

            self.UAV.step(dt)
            
            #LOGS:
            #self.est_pos[it] = alg_pos
            #self.gt_pos[it]  = self.UAV.xyz
            if kalmanStarted or PFstarted or PKFstarted or method == 'NF':
                self.Ed_log[it, :] = np.array([ self.get_dist_clean(alg_pos, self.UAV.xyz) ])
                self.Ed2d_log[it, :] = np.array([ self.get_dist_clean(alg_pos[0:2], self.UAV.xyz[0:2]) ])
                self.Edalt_log[it, :] = np.array([ self.get_dist_clean(alg_pos[2], self.UAV.xyz[2]) ])
                self.Ed_vel_log[it, :] = np.array([ self.get_dist_clean(alg_pos, self.UAV.v_ned) ])
                self.alg_log.xyz_h[it, :] = alg_pos
            self.UAV_log.xyz_h[it, :] = self.UAV.xyz
            self.UAV_log.att_h[it, :] = self.UAV.att
            self.UAV_log.w_h[it, :] = self.UAV.w
            self.UAV_log.v_ned_h[it, :] = self.UAV.v_ned
            

            it+=1

            # Stop if crash
            if (self.UAV.crashed == 1):
                break

            if run_animation:
                if it%frames == 0:
                    pl.figure(0)
                    axis3d.cla()
                    ani.draw3d(axis3d, self.uwb0.xyz, self.uwb0.Rot_bn(), quadcolor[0])

                    ani.draw3d(axis3d, self.uwb1.xyz, self.uwb1.Rot_bn(), quadcolor[2])
                    ani.draw3d(axis3d, self.uwb2.xyz, self.uwb2.Rot_bn(), quadcolor[2])
                    ani.draw3d(axis3d, self.uwb3.xyz, self.uwb3.Rot_bn(), quadcolor[2])

                    ani.draw3d(axis3d, self.uwb4.xyz, self.uwb4.Rot_bn(), quadcolor[2])
                    ani.draw3d(axis3d, self.uwb5.xyz, self.uwb5.Rot_bn(), quadcolor[2])
                    ani.draw3d(axis3d, self.uwb6.xyz, self.uwb6.Rot_bn(), quadcolor[2])

                    ani.draw3d(axis3d, self.UAV.xyz, self.UAV.Rot_bn(), quadcolor[1])

                    axis3d.set_xlim(-6, 6)
                    axis3d.set_ylim(-6, 6)
                    axis3d.set_zlim(0, 10)
                    axis3d.set_xlabel('South [m]')
                    axis3d.set_ylabel('East [m]')
                    axis3d.set_zlabel('Up [m]')
                    axis3d.set_title("Time %.3f s" %t)
                    pl.pause(0.001)
                    pl.draw()

        alg_log = np.array([self.alg_log.xyz_h[:,0], self.alg_log.xyz_h[:,1], self.alg_log.xyz_h[:,2]])
        uav_log = np.array([self.UAV_log.xyz_h[:,0], self.UAV_log.xyz_h[:,1], self.UAV_log.xyz_h[:,2]])
        #print(self.Ed_log)
        return [uav_log, alg_log, self.Ed_log, self.Ed2d_log, self.Edalt_log]