from scipy import linalg as la
import matplotlib.pyplot as pl
import numpy as np
import math
import sys
import random

from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
import uwb_agent_1p as range_agent

sys.path.append("pycopter/")
import quadrotor as quad
import formation_distance as form
import quadlog
import animation as ani

PI = 3.14159265359

def get_dist_clean(p1, p2):
    return (np.linalg.norm(p1 - p2))

def get_dist(p1, p2):
    mu, sigma = 0, 0.05
    std_err = np.random.normal(mu, sigma, 1)[0]
    return (np.linalg.norm(p1 - p2)) + std_err

# Quadrotor
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

xyz0_0 = np.array([0.0, 0.0, 0.0])
xyz1_0 = np.array([3.0, 0.0, 0.0])
xyz2_0 = np.array([1.5, 2.59808, 0.0])
xyz3_0 = np.array([1.5, -2.59808, 0.0])
xyz_uav_0 = np.array([1.0, 1.5, 0.0])


state = 0
wp = np.array([ [ 4,  3, -2.5 ], [ 4, -1, -2.5 ], [ 0, -1, -2.5 ], [0,  3, -2.5 ] ])


v_ned_0 = np.array([0.0, 0.0, 0.0])
w_0 = np.array([0.0, 0.0, 0.0, 0.0])

# Setting quads
uwb0 = quad.quadrotor(0, m, l, J, CDl, CDr, kt, km, kw, \
        att_0, pqr_0, xyz0_0, v_ned_0, w_0)

uwb1 = quad.quadrotor(1, m, l, J, CDl, CDr, kt, km, kw, \
        att_0, pqr_0, xyz1_0, v_ned_0, w_0)

uwb2 = quad.quadrotor(2, m, l, J, CDl, CDr, kt, km, kw, \
        att_0, pqr_0, xyz2_0, v_ned_0, w_0)

uwb3 = quad.quadrotor(3, m, l, J, CDl, CDr, kt, km, kw, \
        att_0, pqr_0, xyz3_0, v_ned_0, w_0)

UAV = quad.quadrotor(10, m, l, J, CDl, CDr, kt, km, kw, \
        att_0, pqr_0, xyz_uav_0, v_ned_0, w_0)

# Simulation parameters
tf = 750
dt = 5e-2
time = np.linspace(0, tf, tf/dt)
it = 0
frames = 50

# Data log
kf_log = quadlog.quadlog(time)
mse_log = quadlog.quadlog(time)
tri_log = quadlog.quadlog(time)
UAV_log = quadlog.quadlog(time)
Ed_log = np.zeros((time.size, 3))
eig_log = np.zeros((time.size, 3))

# Plots
quadcolor = ['r', 'g', 'b']
pl.close("all")
pl.ion()
fig = pl.figure(0)
axis3d = fig.add_subplot(111, projection='3d')

init_area = 10
s = 2

'''
Position Rules:
ID = 0: Origin of the local coordinate system (a)
ID = 1: Always 0 in y- and z-components (b)
ID = 2: Always posetive in both x- and y-components

ID = 10: Always the UAV
'''

RA0 = range_agent.uwb_agent( ID=0 )
RA1 = range_agent.uwb_agent( ID=1 )
RA2 = range_agent.uwb_agent( ID=2 )
RA3 = range_agent.uwb_agent( ID=3 )

UAV_agent = range_agent.uwb_agent( ID=10 )
kalmanStarted = False
kalmanStarted_int = 0


for t in time:
    if it % 5 == 0 or it == 0:
        UAV_agent.handle_range_msg(Id=RA0.id, range=get_dist(UAV.xyz, uwb0.xyz))
        UAV_agent.handle_range_msg(Id=RA1.id, range=get_dist(UAV.xyz, uwb1.xyz))
        UAV_agent.handle_range_msg(Id=RA2.id, range=get_dist(UAV.xyz, uwb2.xyz))
        UAV_agent.handle_range_msg(Id=RA3.id, range=get_dist(UAV.xyz, uwb3.xyz))

    mse_pos = UAV_agent.calc_pos_MSE()
    #tri_pos = UAV_agent.calc_pos_TRI()


    if UAV.xyz[2] < -2 and not kalmanStarted:
        UAV_agent.startKF(UAV.xyz, UAV.v_ned)
        kalmanStarted = True
        kalmanStarted_int = 1
    
    if kalmanStarted:
        UAV_agent.handle_acc_msg(acc_in=UAV.acc)
        kf_pos = UAV_agent.get_kf_state()[0:3]
        eig = UAV_agent.get_plot_data()
    else:
        kf_pos = UAV.xyz

    mse_pos[2] = -mse_pos[2]
    if it < 25:
        mse_pos = UAV.xyz
        #tri_pos = UAV.xyz
    '''
    print("True Pos: ", UAV.xyz)
    print("Estimated Pos[m0]: ", p1)
    print("Estimated Pos[m1]: ", p2)
    print("Estimated Pos[m2]: ", p3)
    print("MSE Pos: ", est_pos)
    '''

    x_err = abs(wp[state][0] - UAV.xyz[0])
    y_err = abs(wp[state][1] - UAV.xyz[1])
    
    
    #wp = np.array([ [ 2,  2, -5 ], [ 2, -2, -5], [ -2, -2, -5 ], [-2,  2, -5] ])
    if state == 0:
        UAV.set_v_2D_alt_lya(np.array([x_err*0.04, y_err*0.04]), random.uniform(-3.5, -1.0))
        if get_dist_clean(UAV.xyz, wp[state]) < 0.4:
            state = 2
    elif state == 1:
        UAV.set_v_2D_alt_lya(np.array([x_err*0.04, -y_err*0.04]), random.uniform(-3.5, -1.0))
        if get_dist_clean(UAV.xyz, wp[state]) < 0.4:
            state = 0
    elif state == 2:
        UAV.set_v_2D_alt_lya(np.array([-x_err*0.04, -y_err*0.04]), random.uniform(-3.5, -1.0))
        if get_dist_clean(UAV.xyz, wp[state]) < 0.4:
            state = 3
    elif state == 3:
        UAV.set_v_2D_alt_lya(np.array([-x_err*0.04, y_err*0.04]), random.uniform(-3.5, -1.0))
        if get_dist_clean(UAV.xyz, wp[state]) < 0.4:
            state = 1

    UAV.step(dt)
    '''
    # Animation
    if it%frames == 0:
        pl.figure(0)
        axis3d.cla()
        ani.draw3d(axis3d, uwb0.xyz, uwb0.Rot_bn(), quadcolor[0])
        ani.draw3d(axis3d, uwb1.xyz, uwb1.Rot_bn(), quadcolor[0])
        ani.draw3d(axis3d, uwb2.xyz, uwb2.Rot_bn(), quadcolor[0])
        ani.draw3d(axis3d, uwb3.xyz, uwb3.Rot_bn(), quadcolor[0])
        ani.draw3d(axis3d, UAV.xyz, UAV.Rot_bn(), quadcolor[1])
        axis3d.set_xlim(-5, 5)
        axis3d.set_ylim(-5, 5)
        axis3d.set_zlim(0, 10)
        axis3d.set_xlabel('South [m]')
        axis3d.set_ylabel('East [m]')
        axis3d.set_zlabel('Up [m]')
        axis3d.set_title("Time %.3f s" %t)
        pl.pause(0.001)
        pl.draw()
        #namepic = '%i'%it
        #digits = len(str(it))
        #for j in range(0, 5-digits):
        #    namepic = '0' + namepic
        #pl.savefig("./images/%s.png"%namepic)
    '''

    # Log
    kf_log.xyz_h[it, :] = kf_pos
    mse_log.xyz_h[it, :] = mse_pos
    #tri_log.xyz_h[it, :] = tri_pos


    UAV_log.xyz_h[it, :] = UAV.xyz
    UAV_log.att_h[it, :] = UAV.att
    UAV_log.w_h[it, :] = UAV.w
    UAV_log.v_ned_h[it, :] = UAV.v_ned

    Ed_log[it, :] = np.array([  get_dist_clean(kf_pos, UAV.xyz),
                                (np.linalg.norm(kf_pos[0:3]) - np.linalg.norm(UAV.xyz)), 
                                get_dist_clean(mse_pos, UAV.xyz) ])

    if kalmanStarted:
        eig_log[it, :] = np.array([ eig[0],
                                    eig[1],
                                    eig[2] ])
    else:
        eig_log[it, :] = np.array([ 0,
                                    0,
                                    0 ])


    it+=1

    # Stop if crash
    if (UAV.crashed == 1):
        break


pl.figure(1)
pl.title("2D Position [m]")
pl.plot(mse_log.xyz_h[:, 0], mse_log.xyz_h[:, 1], label="mse", color=quadcolor[2])
pl.plot(kf_log.xyz_h[:, 0], kf_log.xyz_h[:, 1], label="kf", color=quadcolor[1])
pl.plot(UAV_log.xyz_h[:, 0], UAV_log.xyz_h[:, 1], label="Ground Truth", color=quadcolor[0])
pl.xlabel("East")
pl.ylabel("South")
pl.legend()

pl.figure(2)
pl.title("Error Distance [m]")
pl.plot(time, Ed_log[:, 2], label="mse", color=quadcolor[2])
pl.plot(time, Ed_log[:, 0], label="KF", color=quadcolor[1])
pl.plot(time, Ed_log[:, 1], label="dist error dif", color=quadcolor[0])
#pl.plot(time, Ed_log[:, 3], label="$e_4$")
#pl.plot(time, Ed_log[:, 4], label="$e_5$")
pl.xlabel("Time [s]")
pl.ylabel("Formation distance error [m]")
pl.grid()
pl.legend()

pl.figure(3)
pl.title("Altitude Over Time")
pl.plot(time, mse_log.xyz_h[:, 2], label="mse", color=quadcolor[2])
pl.plot(time, kf_log.xyz_h[:, 2], label="kf", color=quadcolor[1])
pl.plot(time, UAV_log.xyz_h[:, 2], label="Ground Truth", color=quadcolor[0])
pl.xlabel("Time [s]")
pl.ylabel("Altitude [m]")
pl.grid()
pl.legend(loc=2)

pl.figure(4)
pl.title("Eigen Covariance")
pl.plot(time, eig_log[:, 0], label="cov(x,x)", color=quadcolor[2])
pl.plot(time, eig_log[:, 1], label="cov(y,y)", color=quadcolor[1])
pl.plot(time, eig_log[:, 2], label="cov(z,z)", color=quadcolor[0])
#pl.plot(time, Ed_log[:, 3], label="$e_4$")
#pl.plot(time, Ed_log[:, 4], label="$e_5$")
pl.xlabel("Time [s]")
pl.ylabel("[m]")
pl.grid()
pl.legend()



pl.pause(0)
