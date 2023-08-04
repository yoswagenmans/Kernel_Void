import sys
import datetime
import sqlite3
import time


db = "/var/jail/home/team68/physics.db"

width = 200
height = 400
distance = 4000
throw_start = (100,4000)

#in meters
actual_long_distance = 10
actual_width_distance = 1

def queryData():
    # conn = sqlite3.connect(db)  # connect to that database (will create if it doesn't already exist)
    # c = conn.cursor()  # move cursor into database (allows us to execute commands)
    # c.execute('''CREATE TABLE IF NOT EXISTS end_location (throw_id int, x float, y float);''')
    # c.execute('''CREATE TABLE IF NOT EXISTS throws (throw_id int, ax float, ay float, az float, vx float, vy float, vz float, time timestamp);''')
    
    # end_locations = c.execute('''SELECT * FROM end_location''').fetchall()
    # throw = c.execute('''SELECT * FROM throws ORDER BY time_ ASC''').fetchone()
    

    # conn.commit()

    end_locations = []
    throw = ('3',)

    return (end_locations, throw)

def renderThrow(data):
    end_locations = data[0]
    throw = data[1]

    if throw == None or len(end_locations) == 0:
        return ''''''

    throwId  = throw[0]
    end_x = -1
    end_y = -1

    for bag in end_locations:
        if bag[0] == throwId:
            end_x = bag[1]
            end_y = bag[2]
            break

    if end_x == -1:
        return ''''''
        
    scaled_x = int(end_x * width / actual_width_distance) + width/2
    scaled_y = distance - int(end_y * distance / actual_long_distance)

    varName = 'Throw' + throwId

    # throw_start is global variable.
    renderCode = '''
ctx.beginPath();   
ctx.setLineDash([10,10]);  
ctx.moveTo(%d,%d);
ctx.lineTo(%d,%d); 
ctx.stroke(); 
'''%(throw_start[0],throw_start[1],scaled_x,scaled_y)

    return renderCode


def renderBag(x, y, id):
    scaled_x = int(x * width / actual_width_distance) + width/2
    scaled_y = distance - int(y * distance / actual_long_distance)

    print(scaled_x, scaled_y)
    print("")

    varName = 'bag' + id

    renderCode = '''
    var %s = new Path2D(); 
    %s.arc(%d, %d, 20, 0, 2 * Math.PI);
    ctx.fill(%s);
    '''%(varName, varName, scaled_x, scaled_y, varName)

    return renderCode

def renderAll(data):
    end_locations = data[0]
    throw = data[1]

    strToInsert = renderThrow(data)
    
    for entry in end_locations:
        strToInsert += renderBag(entry[1], entry[2], entry[0])

    return strToInsert

main = '''
<!DOCTYPE html>
<title>

</title>

<body>
    <h1>Kernel Void</h1>
    <canvas id="myCanvas" width="200" height="400" margin=auto>
    </canvas>   
    <script>
        var width = 200;
        var height = 400;
        var startPoint = {width: width/2, height: 4000};

        var c = document.getElementById("myCanvas");
        var ctx = c.getContext("2d");

        // rectangular board
        var board = new Path2D();
        board.rect(0,0,width,height);
        ctx.stroke(board);
        
        // circular hole
        var hole = new Path2D();
        hole.arc(width/2, 75, 32.5, 0, 2 * Math.PI);
        ctx.stroke(hole);

        ''' + renderAll(queryData()) + '''
    </script>

    <script>
       setTimeout(function(){
           location.reload();
       }, 1000);
    </script>
</body>
'''           

def request_handler(request):
    return main

print(request_handler("testing"))





