from turtle import st
import server_fsm as fsm


player_one = 'nick'
player_two = 'yos'
start = {'method': "POST", 'values': {'type': 'start',
                                    'playerOne': player_one,
                                    'playerTwo': player_two},
                            'form': {'type':'start'}}
start_resp = fsm.request_handler(start)
print("START response"+start_resp)
game_id = int(start_resp[start_resp.index('=')+1:])
basic_get = {'method': "GET", 
                'values':{'game_id': game_id}}
print("First GET" + fsm.request_handler(basic_get))
basic_throw_one = {'method': "POST",
                'values':{'type': 'throw',
                        'game_id': game_id,
                        'user': player_one,
                        'px': 2,
                        'vy': 2,
                        'vz': 1},
                    'form': {'type':'throw'}}
basic_throw_two = {'method': "POST",
                'values':{'type': 'throw',
                        'game_id': game_id,
                        'user': player_two,
                        'px': 1.5,
                        'vy': 2,
                        'vz': 1},
                    'form': {'type':'throw'}}
print("Expect state 2"+fsm.request_handler(basic_throw_one))
print("Expect state 3"+fsm.request_handler(basic_throw_one))
#testing refusing repeat throws
print("Expect state 4"+fsm.request_handler(basic_throw_one))
print("Expect state 3"+fsm.request_handler(basic_throw_two))
print("GET after two throws" + fsm.request_handler(basic_get))

print("Expect state 4"+fsm.request_handler(basic_throw_one))
print("Expect state 3"+fsm.request_handler(basic_throw_two))
print("Expect state 4"+fsm.request_handler(basic_throw_one))
print("Expect state 3"+fsm.request_handler(basic_throw_two))
print("Expect state 4"+fsm.request_handler(basic_throw_one))
print("Expect state 2"+fsm.request_handler(basic_throw_two))
#fresh board
print("Expect state 3"+fsm.request_handler(basic_throw_two))
print("Expect state 4"+fsm.request_handler(basic_throw_one))
print("GET after two throws on a fresh board" + fsm.request_handler(basic_get))

