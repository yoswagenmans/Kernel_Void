
import datetime
import sqlite3
import sys
#sys.path.append('/var/jail/home/team68/phys') #need this for importing in sandbox
from physics import request_handler as req
from physics import score

db = 'test.db'
#db = '/var/jail/home/team68/test.db'
PTS2WIN = 11


def request_handler(request):
    """
    Handles complete game FSM for Kernel Void.

    Request types:
        1. GET gamestate
            - need to query by game_id
            @returns string containing state, ids of both players, and a list of throw_ids(0 specifying not thrown yet)
        2. POST start
            - type='start', must specify playerOne and playerTwo fields
            @returns the game_id of the new game
        3. POST throw
            - type='throw', must specify user throwing, vx, vy, vz
    """

    
    conn = sqlite3.connect(db)  # connect to that database (will create if it doesn't already exist)
    c = conn.cursor()  # move cursor into database (allows us to execute commands
    c.execute('''CREATE TABLE IF NOT EXISTS games (time_ timestamp, game_id int, state int, score_one int, score_two int);''') #persistently store gamestates
    c.execute('''CREATE TABLE IF NOT EXISTS players (game_id int, player_one text, player_two text);''') #know which players are playing in what game
    c.execute('''CREATE TABLE IF NOT EXISTS game_bags (time_ timestamp, game_id int, 
        throw_a1 int, throw_a2 int, throw_a3 int, throw_a4 int, 
        throw_b1 int, throw_b2 int, throw_b3 int, throw_b4 int);''') #what throws are 'active'
    c.execute('''CREATE TABLE IF NOT EXISTS throws (throw_id int);''')
    conn.commit()
    now = datetime.datetime.now()
    c.execute('''INSERT into games VALUES (?, ?, ?, ?, ?);''', (now, 0, 0, 0, 0))
    c.execute('''INSERT into throws VALUES (?);''', (0, ))
    conn.commit()


    if request['method'] == 'GET':
        game_id = request['values']['game_id']
        state = c.execute('''SELECT state, score_one, score_two FROM games WHERE game_id = ? ORDER by time_ DESC;''', (game_id,)).fetchone()
        players = c.execute('''SELECT player_one, player_two FROM players WHERE game_id = ?;''', (game_id,)).fetchone()
        bags = c.execute('''SELECT * FROM game_bags WHERE game_id = ? ORDER by time_ DESC;''', (game_id,)).fetchone()[2:]
        return f'state={state[0]},p_one={players[0]},p_two={players[1]},bags={str(bags)},score={state[1]}:{state[2]}'

    elif request['method'] == 'POST':
        #need to deal with setup separately
        if request['form']['type'] == 'start':
            highest_id = c.execute('''SELECT game_id FROM games ORDER by game_id DESC;''').fetchone()
            new_id = highest_id[0] + 1
            c.execute('''INSERT INTO players VALUES (?, ?, ?);''', (new_id, request['values']['playerOne'], request['values']['playerTwo'],))
            c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, new_id, 1,0,0))
            c.execute('''INSERT INTO game_bags VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', (now, new_id, 0,0,0,0,0,0,0,0,))
            conn.commit()
            conn.close()
            return 'game_id='+str(new_id)

        game_id = request['values']['game_id']
        player_id = request['values']['user']
        px = request['values']['px']
        vy = request['values']['vy'] #shouldn't need
        vz = request['values']['vz']
        game = c.execute('''SELECT state, score_one, score_two FROM games WHERE game_id = ? ORDER by time_ DESC;''', (game_id,)).fetchone()
        players = c.execute('''SELECT player_one, player_two FROM players;''').fetchone()
        bags = c.execute('''SELECT * FROM game_bags WHERE game_id = ? ORDER by time_ DESC;''', (game_id,)).fetchone()[2:]
        print("bags:"+str(bags))
        throws = count_bags(bags)
        state = game[0]
        p1_score = game[1]
        p2_score = game[2]
        player_one = players[0]
        player_two = players[1]

        #calibration/setup state, not implemented yet
        if state == 1:
            c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, game_id, 2,0,0))
        #fresh board
        elif state == 2:
            c.execute('''INSERT INTO game_bags VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', (now, game_id, 0,0,0,0,0,0,0,0,))
            c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, game_id, 3,p1_score,p2_score))
        #player 1 turn
        elif state == 3:
            if player_id == player_one:
                highest_id = c.execute('''SELECT throw_id FROM throws ORDER by throw_id DESC;''').fetchone()
                new_id = highest_id[0] + 1
                c.execute('''INSERT INTO throws VALUES (?);''', (new_id,))
                insertable = tuple([now, game_id] + add_bag(throws, bags, new_id, True))
                req({'method': 'POST', 'values':{'x_pc':px, 'vy':vy, 'vz':vz, 'id':new_id}})
                c.execute('''INSERT INTO game_bags VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', insertable)
                c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, game_id, 4,p1_score,p2_score))
            else:
                return "player id:"+player_id+" doesn't match player one:"+player_one
        #player 2 turn
        elif state == 4:
            if player_id == player_two:
                #run chloes code
                highest_id = c.execute('''SELECT throw_id FROM throws ORDER by throw_id DESC;''').fetchone()
                new_id = highest_id[0] + 1
                c.execute('''INSERT INTO throws VALUES (?);''', (new_id,))
                insertable = tuple([now, game_id] + add_bag(throws, bags, new_id, False))
                req({'method': 'POST', 'values':{'x_pc':px, 'vy':vy, 'vz':vz, 'id':new_id}})
                c.execute('''INSERT INTO game_bags VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', insertable)
                #round is over
                if throws[0] == 4:
                    final_bags = bags[:7] + (new_id,)
                    score_one, score_two = tally_points(p1_score, p2_score, final_bags)
                    #checks if the game is over or fresh round
                    if (score_one >= PTS2WIN or score_two >= PTS2WIN):
                        c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, game_id, 5, score_one, score_two,))
                    else:
                        c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, game_id, 2, score_one, score_two,))
                else: #back to player 1
                    c.execute('''INSERT INTO games VALUES (?, ?, ?, ?, ?);''', (now, game_id, 3, p1_score, p2_score,))
            else:
                return "player id:"+player_id+" doesn't match player one:"+player_one
                
        #gameover!
        elif state == 5:
            return f'Gameover! {player_one if p1_score > p2_score else player_two} won!'
        conn.commit()
        final_state = c.execute('''SELECT state FROM games WHERE game_id = ? ORDER by time_ DESC;''', (game_id,)).fetchone()
        conn.close()
        return str(final_state[0])
    else:
        return "Not accepted type of request"

def count_bags(bags: list):
    #assumes the empty throw_id is 0
    player_one = 0
    player_two = 0
    for bag in bags[:4]:
        if bag != 0: 
            player_one += 1
    for bag in bags[4:]:
        if bag != 0: 
            player_two += 1
    return (player_one, player_two)

def add_bag(bag_count: tuple, bags: list, new_bag_id: int, player_one: bool):
    bag_ind = 0
    if player_one:
        bag_ind = bag_count[0]
    else:
        bag_ind = bag_count[1] + 4
    new_bags = list(bags)
    new_bags[bag_ind] = new_bag_id
    return new_bags

def tally_points(score_one, score_two, bags):
    p1_pts = score(bags[0:4])
    p2_pts = score(bags[4:])
    if (p1_pts > p2_pts):
        score_one += p1_pts - p2_pts
    elif (p2_pts > p1_pts):
        score_two += p2_pts - p1_pts
    return score_one, score_two




