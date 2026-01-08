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

ROOM_CARVE_OPTIONS = [
    (1), # exit
    (2), # room connector
    (3) # dead end
]

CARDINAL_DIRECTIONS = [
    (1, 0),    # east
    (-1, 0),   # west
    (0, 1),    # south
    (0, -1)    # north
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
jobs = [(44,44,1)]

# ------------------
# Main loop 
# ------------------


#test grid white pixel placer:

xt = 4
yt = 4
grid[xt,yt] = 1
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
#         if yt <= SIZE:
#             grid[xt,yt] = 1
        
        
    
    





# Idea
#
# mark room (3x3 pixel)
# S, N, E, W pixels are all = 1
# corner pixels = 2
# choose random direction to go


def crossing_place_path(x,y):
    if grid[x+2,y] == 2:
        grid[x+1,y] = 1
    if grid[x-2,y] == 2:
        grid[x-1,y] = 1
    if grid[x,y+2] == 2:
        grid[x,y+1] = 1
    if grid[x,y-2] == 2:
        grid[x,y-1] = 1


def connect_rooms(x,y):
    for dx, dy in CARDINAL_DIRECTIONS:
        nx2, ny2 = x + (dx * 2), y + (dy * 2)
        if in_bounds(nx2, ny2):
            val = grid[nx2,ny2]
            if val == 1 and val != 3:
                grid[x + dx, y+dy] = 1
DIRECTIONS = []
# creates and modifes a list for valid options so it doesnt choose a direction its already gone in
def build_directions(x,y):
    OPTIONS_D = []
    if grid[x+5,y] == 0:
        OPTIONS_D.append((1, 0))
    if grid[x-5,y] == 0:
        OPTIONS_D.append((-1, 0))
    if grid[x,y+5] == 0:
        OPTIONS_D.append((0, 1))
    if grid[x,y-5] == 0:
        OPTIONS_D.append((0, -1))
    return OPTIONS_D

def in_bounds(nx, ny):
    return 0 <= nx <= SIZE and 0 <= SIZE

def ROOM_JOB(x, y):
    print()
    #place
    if in_bounds(x+5,y) and in_bounds(x-5,y) and in_bounds(x,y+5) and in_bounds(x,y-5):
        for ix in range (-1, 2):
            for iy in range (-1, 2):
                grid[x + ix, y + iy] = 2
                grid[x,y] = 1

    # build available directions:


    #check for each direciton
    #North
    DIRECTIONS = build_directions(x,y)
    print(str(DIRECTIONS))
    for dx, dy in DIRECTIONS:
        nx, ny = x + dx, y + dy
        
        option = random.choice(ROOM_CARVE_OPTIONS)
        
        # 1 == exit
        # 2 == room conector
        # 3 == dead end
        print(str(option))
        if option == 1:
            if in_bounds(nx,ny):
                grid[nx,ny] = 2
                for i in range(1,5):
                    grid[x+dx*i,y+dy*i] = 1
                jobs.append((x+dx*5,y+dy*5,0))
        if option == 2:
            if in_bounds(x+dx*5,y+dy*5):
                grid[nx,ny] = 1
                jobs.append((x+dx*5,y+dy*5,1))

                #ready connection:
                for i in range(1,5):
                    grid[x+dx*i,y+dy*i] = 1
                    

                print("room job added")
        if option == 3:
            if in_bounds(nx,ny):
                grid[nx,ny] = 3
        #connect_rooms(x,y)


def CORRIDOR_JOB(x,y):
    DIRECTIONS = build_directions(x,y)
    for dx, dy in DIRECTIONS:
        nx, ny = x + dx, y + dy
        bool = random.choice([0,1])

        if bool == 1:
            for i in range(1,5):
                grid[x+dx*i,y+dy*i] = 1
                bool_2 = random.choice([0,1])
                if bool_2 == 1:
                    jobs.append((x+dx*5,y+dy*5,1))
                if bool_2 == 0:
                    jobs.append((x+dx*5,y+dy*5,0))




while len(jobs) > 0:
    current_job = jobs.pop(0)


    print("Job" + str(current_job))
    x = current_job[0]
    y = current_job[1]
    job_type = current_job[2]
    if job_type == 0:
        CORRIDOR_JOB(x,y)
    if job_type == 1:
        
        ROOM_JOB(x, y)








    color_img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

    color_img[grid == 0] = [0, 0, 0]          # 0 = Black (Background)
    color_img[grid == 1] = [255, 255, 255]    # 1 = White (Corridors)
    color_img[grid == 2] = [0, 100, 255]      # 2 = Blue (Rooms)   


    img = Image.fromarray(color_img, mode="RGB")
    img.save("grid_" + str(JOB_NUMBER) + ".png")
        
        
        






    # #fix colors
    # crossing_place_path(x,y)
    # DIRECTIONS.clear()
    # build_directions(x,y)
    # if DIRECTIONS == []:
    #     break
    # print(DIRECTIONS)

    # # decide what to place

    # placement_decision = random.choice(OPTIONS)

    # # Corridor
    # if placement_decision == 1:
    #     step_x, step_y = random.choice(DIRECTIONS)
    #     x = x + step_x
    #     y = y + step_y
    #     corridors[x, y] = 1
        
    # # Room
    # if placement_decision == 2:
    #     # place room
    #     corridors[x+1, y+1] = 2
    #     corridors[x-1, y+1] = 2
    #     corridors[x+1, y-1] = 2
    #     corridors[x-1, y-1] = 2

    #     corridors[x, y+1] = 2
    #     corridors[x, y-1] = 2
    #     corridors[x+1, y] = 2
    #     corridors[x-1, y] = 2

    #     corridors[x-last_x, y-last_y] = 1

    #     step_x, step_y = random.choice(DIRECTIONS)
    #     x = x + step_x
    #     y = y + step_y
    #     corridors[x, y] = 1

    #     x = x + step_x
    #     y = y + step_y
    #     corridors[x, y] = 1
    #     x = x + step_x
    #     y = y + step_y
    #     corridors[x, y] = 1




    # current_x, current_y = x, y
    # blocked = False
    # color_img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

    # color_img[corridors == 0] = [0, 0, 0]          # 0 = Black (Background)
    # color_img[corridors == 1] = [255, 255, 255]    # 1 = White (Corridors)
    # color_img[corridors == 2] = [0, 100, 255]      # 2 = Blue (Rooms)


    # img = Image.fromarray(color_img, mode="RGB")
    # img.save("corridors_" +  str(_) + ".png")


        

    # for _ in range(STEPS_PER_SEGMENT):

    #     next_x = current_x + step_x
    #     next_y = current_y + step_y
    #     # corridors[next_x, next_y] = 1
    #     # next_x = current_x + step_x
    #     # next_y = current_y + step_y
    #     # corridors[next_x, next_y] = 1

    #     if not in_bounds(next_x, next_y):
    #         blocked = True
    #         break

    #     if corridors[next_x, next_y] == 1 or corridors[next_x, next_y] == 2:
    #         corridors[next_x, next_y] = 1
    #         if 1 == _/2:
    #             current_x, current_y = next_x, next_y
    #             next_x = current_x + step_x
    #             next_y = current_y + step_y
    #             corridors[next_x, next_y] = 1
    #             current_x, current_y = next_x, next_y
    #             break
    #         else:
    #             current_x, current_y = next_x, next_y
    #             break
        

    #     corridors[next_x, next_y] = 1
        
    #     last_x = step_x
    #     last_y = step_y

    # if not blocked:
    #     frontier.append((current_x, current_y))

# ------------------
# Export texture
# ------------------

color_img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

color_img[grid == 0] = [0, 0, 0]          # 0 = Black (Background)
color_img[grid == 1] = [255, 255, 255]    # 1 = White (Corridors)
color_img[grid == 2] = [0, 100, 255]      # 2 = Blue (Rooms)   


img = Image.fromarray(color_img, mode="RGB")
img.save("grid.png")