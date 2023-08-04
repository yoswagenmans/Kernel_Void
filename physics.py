#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 10:21:57 2022

@author: chloelangley
"""

G = 9.81
import sqlite3
import datetime
import math

db = "/var/jail/home/team68/physics.db"

game = "/var/jail/home/team68/test.db"

#surface area of beanbag in m^2
A = 0.00580644
#rough drag coefficent from shape, source:https://www.grc.nasa.gov/www/k-12/airplane/shaped.html
CD = 0.2
#density of air
R = 1.225
#estimated mass of beanbag in kg
M = 0.45
#estimated width of square bag on board
BAG_SIZE = 0.1524
#board distance from player (beginning of board)
B_DIST = 10
#board width and height (in meters)
B_W = 0.91
B_H = 1.22
#cornhole board corners
TL = (-B_W/2, B_DIST + B_H) # top left
TR = (B_W/2, B_DIST + B_H)
BL = (-B_W/2, B_DIST)
BR = (B_W/2, B_DIST)
BOARD_COORDS = (TL, TR, BL, BR)
ANGLE = 10/360 * 2 * 3.14159

#hole position
HOLE_X = 0
HOLE_Y = B_DIST + B_H * (325/400)
HOLE_R = B_H * (75/400)
HOLE_COORDS = (HOLE_X, HOLE_Y, HOLE_R)

MU_FRIC = 3

SCORE_POINTS = 3
ON_BOARD_POINTS = 1

def get_others(id_):
    conn = sqlite3.connect(game)  # connect to that database (will create if it doesn't already exist)
    c = conn.cursor()
    result = c.execute('''SELECT throw_a1, throw_a2, throw_a3, throw_a4, throw_b1, throw_b2, throw_b3, throw_b4 from game_abgs ORDER BY time_ DESC;''').fetchall()
    conn.close()
    for each in result:
        if id_ in each:
            final = []
            for bag in each:
                if bag != id_ and bag != 0:
                    final.append(bag)
            return final

'''
from list of throw IDs, player total
'''
def score(throws):
    return sum([point_val(bag) for bag in throws])

def point_val(throw_id):
    pos = get_pos(throw_id)

    if in_hole(pos, HOLE_COORDS):
        return SCORE_POINTS
    elif on_board(pos, BOARD_COORDS):
        return ON_BOARD_POINTS
    return 0

def on_board(point_coord,box):
    x_max = max(box,key = lambda t:t[0])[0]
    x_min = min(box,key = lambda t:t[0])[0]
    y_max = max(box,key = lambda t:t[1])[1]
    y_min = min(box,key = lambda t:t[1])[1]
    if (x_min <= point_coord[0] <= x_max) and (y_min <= point_coord[1] <= y_max):
        return True
    return False

def in_hole(point_coord, hole):
    px, py = point_coord
    hx, hy, hr = hole
    return ((px - hx)**2 + (py - hy)**2)**0.5 <= hr

def airtime_to_dist(v, t):
    #a from air resistance 
    a = -0.5 * CD * R * v**2 * A / M
    return v*t + 0.5*a*t**2

def get_slide(vy):
    #vf^2 = vi^2 + 2adeltay
    delta_y = (vy*math.cos(ANGLE))**2*M/(2*G*math.cos(ANGLE)*MU_FRIC)
    return delta_y


'''
Returns (x, y) coordinate of final position relative to throw
'''
def projection(x_pc, vy, vz):
    total_az = -1* G
    #delta_y = 0 = vyt - 0.5at^2 = vy - 0.5at
    t = -2*vz/total_az
    if x_pc == -1:
        dx = -1
    else:
        dx = (-0.5 + x_pc) * B_W
    dy = airtime_to_dist(vy, t)
    return (dx, dy)

def implement_slide(id_, slide, others):
    final = get_pos(id_)
    set_pos(id_, final[0], final[1]+slide)
    will_slide = [] #nested list of id and y coord
    for each in others:
        pos = get_pos(each)
        if abs(pos[0] - final[0]) < BAG_SIZE:
            will_slide.append([each, pos[1]])
    min_dist = 0
    next = None
    for each in will_slide:
        if each[1] < min_dist:
            min_dist = each[1]
            next = each[0]
    if next != None:
        implement_slide(next, final[1] + BAG_SIZE - each[1], will_slide)

def get_pos(throw_id):
    conn = sqlite3.connect(db)  # connect to that database (will create if it doesn't already exist)
    c = conn.cursor()
    result = c.execute('''SELECT x, y from end_location WHERE throw_id = ? ORDER BY t DESC;''', (throw_id,)).fetchone()
    conn.close()
    return result

def set_pos(id_, x, y):
    conn = sqlite3.connect(db)  # connect to that database (will create if it doesn't already exist)
    c = conn.cursor()  # move cursor into database (allows us to execute commands)
    t = datetime.datetime.now()
    c.execute('''CREATE TABLE IF NOT EXISTS end_location (throw_id int, x float, y float, t timestamp);''')
    c.execute('''CREATE TABLE IF NOT EXISTS throws (throw_id int, x_pc float, vy float, vz float, t timestamp);''')
    conn.commit() # commit commands (VERY IMPORTANT!!)
    c.execute('''INSERT into end_location VALUES (?,?,?,?);''', (id_, x, y, t))
    conn.commit()

def get_throw(throw_id):
    conn = sqlite3.connect(db)  # connect to that database (will create if it doesn't already exist)
    c = conn.cursor()
    result = c.execute('''SELECT x_pc, vy, vz, t from throws WHERE throw_id = ? ORDER BY t DESC;''', (throw_id,)).fetchone()
    conn.close()
    return result

def set_throw(id_, x_pc, vy, vz):
    conn = sqlite3.connect(db)  # connect to that database (will create if it doesn't already exist)
    c = conn.cursor()  # move cursor into database (allows us to execute commands)
    t = datetime.datetime.now()
    c.execute('''CREATE TABLE IF NOT EXISTS end_location (throw_id int, x float, y float, t timestamp);''')
    c.execute('''CREATE TABLE IF NOT EXISTS throws (throw_id int, x_pc float, vy float, vz float, t timestamp);''')
    c.execute('''INSERT into throws VALUES (?,?,?,?,?);''', (id_, x_pc, vy, vz, t))
    conn.commit() # commit commands (VERY IMPORTANT!!)

def abs_pos_to_board_pos(x, y):
    return (B_W/2-x, B_DIST + B_H - y)

def request_handler(request):
    if request["method"] == "GET":
        get_type = ""
        try:
            get_type = request["values"]["type"]
        except:
            return "Error: get type not specified"
        if get_type == "pos_info":
            return get_pos(request['values']['throw_id'])
        elif get_type == "throw_info":
            return get_throw(request['values']['throw_id'])
        elif get_type == "board_info":
            result = get_pos(request['values']['throw_id'])
            abs_loc = result[-1]
            if in_hole((abs_loc[0],abs_loc[1]), HOLE_COORDS):
                #in the hole
                return (-1, 0)
            elif on_board((abs_loc[0],abs_loc[1]), BOARD_COORDS) and abs_loc[0] != -1:
                return abs_pos_to_board_pos(abs_loc[0], abs_loc[1])
            else:
                #off the board
                return (-1, -1)
        else:
            return "Error: invalid get type"
    else: #POST
        x_pc = float(request["values"]["x_pc"])
        vy = float(request["values"]["vy"])
        vz = float(request["values"]["vz"])
        id_ = int(request["values"]["id"])
        final = projection(x_pc, vy, vz)

        set_throw(id_, x_pc, vy, vz)
        set_pos(id_, final[0], final[1])

        slide = get_slide(vy)
        implement_slide(id_, slide)
        return "Throw posted!"