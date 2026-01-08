
import numpy as np
from PIL import Image
import random
import time
from collections import deque

# ------------------
# Config
# ------------------
SIZE = 99
STEPS_PER_SEGMENT = 20
MAX_ITERATIONS = 100
STOP_THRESHOLD = 0.85
JOB_NUMBER = 0


# ------------------
# Setup
# ------------------

grid = np.zeros((SIZE, SIZE), dtype=np.uint8)

last_x, last_y = 0, 0
# Cardinal directions


OPTIONS = [
    (1),
    (2)  
]

def in_bounds(x, y):
    return 0 <= x < SIZE and 0 <= y < SIZE

# ------------------
# Start point
# ------------------
current_x, current_y = SIZE // 2, SIZE // 2
x = SIZE/2
y = SIZE/2

x, y = 44, 44
grid[x, y] = 1

# Jobs:
# 0 = corridor
# 1 = room
jobs = [(84,84,1)]
jobs = [(44,44,1)]
grid[94,94] = 4
grid[44,44] = 4

# ------------------
# Main loop 
# ------------------


#test grid white pixel placer:

# xt = 4
# yt = 4
# grid[xt,yt] = 1
# while xt <= SIZE and yt <= SIZE:
#     xt = xt+5

#     if xt >= SIZE and yt >= SIZE:
#         break
    
#     if xt >= SIZE:
#         xt = 4
#         yt = yt+5
#         if yt >= SIZE:
#             break
#         if xt <= SIZE:
#             grid[xt,yt] = 1
#     else:
#         print(str(xt) + " " + str(yt))
#         if yt <= SIZE:
#             grid[xt,yt] = 1


def fix_room_pixels():
    xt = 1
    yt = 1
    grid[xt,yt] = 1
    while xt <= SIZE and yt <= SIZE:
        xt = xt+1

        if xt >= SIZE and yt >= SIZE:
            break
        
        if xt >= SIZE:
            xt = 1
            yt = yt+1
            if yt >= SIZE:
                break
            if xt <= SIZE:
                if grid[xt,yt] == 3:
                    grid[xt,yt] = 1
        else:
            if yt <= SIZE:
                if grid[xt,yt] == 3:
                    grid[xt,yt] = 1
        
CARDINAL_DIRECTIONS = [
     (1, 0),    # east
     (-1, 0),   # west
     (0, 1),    # south
     (0, -1)    # north
 ]
    





# Idea
#
#

def crossing_place_path(x,y):
    if grid[x+2,y] == 2:
        grid[x+1,y] = 1
    if grid[x-2,y] == 2:
        grid[x-1,y] = 1
    if grid[x,y+2] == 2:
        grid[x,y+1] = 1
    if grid[x,y-2] == 2:
        grid[x,y-1] = 1

DIRECTIONS = []
# creates and modifes a list for valid options so it doesnt choose a direction its already gone in
def build_directions(x,y):
    if grid[x+2,y] == 0 and grid[x+1,y] == 0:
        DIRECTIONS.append((1, 0))
    if grid[x-2,y] == 0 and grid[x-1,y] == 0:
        DIRECTIONS.append((-1, 0))
    if grid[x,y+2] == 0 and grid[x,y+1] == 0:
        DIRECTIONS.append((0, 1))
    if grid[x,y-2] == 0 and grid[x,y-2] == 0:
        DIRECTIONS.append((0, -1))
# DIRECTIONS = [
#     (1, 0),    # east
#     (-1, 0),   # west
#     (0, 1),    # south
#     (0, -1)    # north
# ]

#does not paint x, y
def paint_path(x,y,dx,dy,distance):
    while distance > 0:
        grid[x+dx*distance, y+dy*distance] = 1
        distance = distance - 1

def in_bounds(x, y, dx, dy):
    new_x = x + dx * 5
    new_y = y + dy * 5
    if 1 <= new_x < SIZE - 1 and 1 <= new_y < SIZE - 1:
        return True
    return False


def fix_room_paths(x,y):
    for dx,dy in CARDINAL_DIRECTIONS:
        if in_bounds(x,y,dx,dy):
            if grid[x+dx*2,y+dy*2] == 1:
                paint_path(x,y,dx,dy,5)

def ROOM_JOB(x, y):
    print("Room")
    for ix in range (-1, 2):
        for iy in range (-1, 2 ):
            grid[x + ix, y + iy] = 2
    grid[x,y] = 3
    
    # check each direction
    #test
    #paint_path(x,y,dx,1,5)

    for dx,dy in CARDINAL_DIRECTIONS:
        if in_bounds(x,y,dx,dy):
            if grid[x+dx*5, y+dy*5] == 0:
                paint_path(x,y,dx,dy,5)
                if random.randrange(0,2) == 1:
                    #room job add
                    jobs.append((x+dx*5,y+dy*5,1))
                    if dx != 0:
                        grid[x+dx*2,y+1] = 2
                        grid[x+dx*3,y+1] = 2
                        grid[x+dx*2,y-1] = 2
                        grid[x+dx*3,y-1] = 2
                    if dy != 0:
                        grid[x+1,y+dy*2] = 2
                        grid[x+1,y+dy*3] = 2
                        grid[x-1,y+dy*2] = 2
                        grid[x-1,y+dy*3] = 2

                    
                    
                else:
                    jobs.append((x+dx*5,y+dy*5,0)) 
        fix_room_paths(x,y)
            
            
def CORRIDOR_JOB(x,y):
    print("Corridor")
    for dx,dy in CARDINAL_DIRECTIONS:
        if in_bounds(x,y,dx,dy):
            if grid[x+dx*5, y+dy*5] == 0:
                paint_path(x,y,dx,dy,5)
                if random.randrange(0,2) == 1:
                    jobs.append((x+dx*5,y+dy*5,1))
                else:
                    jobs.append((x+dx*5,y+dy*5,0))
            if grid[x+dx*5, y+dy*5] == 1:
                if random.randrange(0,5 ) == 1:
                    paint_path(x,y,dx,dy,5)
    
    



while len(jobs) > 0:
    
    random_index = random.randrange(len(jobs)) 
    
    # Pop that specific random index
    current_job = jobs.pop(random_index)


    print("Job" + str(current_job))
    x = current_job[0]
    y = current_job[1]
    job_type = current_job[2]
    if job_type == 1:
        ROOM_JOB(x, y)
    if job_type == 0:
        CORRIDOR_JOB(x,y)

    
fix_room_pixels()


# ------------------
# Export texture
# ------------------

grid[84,84] = 4
grid[44,44] = 4

color_img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

color_img[grid == 0] = [0, 0, 0]          # 0 = Black (Background)
color_img[grid == 1] = [255, 255, 255]    # 1 = White (Corridors)
color_img[grid == 2] = [0, 100, 255]      # 2 = Blue (Room_wall)   
color_img[grid == 3] = [0, 100, 170]      # 3 = Blue (Room_middle)   
color_img[grid == 4] = [100, 100, 170]      # 3 = Blue (Room_middle)   



img = Image.fromarray(color_img, mode="RGB")
img.save("grid.png")