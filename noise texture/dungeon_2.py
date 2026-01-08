import numpy as np
from PIL import Image
import random

# ------------------
# Config
# ------------------
SIZE = 256
STEPS_PER_SEGMENT = 20
MAX_ITERATIONS = 100
STOP_THRESHOLD = 0.85
SEED = None

# ------------------
# Setup
# ------------------
if SEED is not None:
    random.seed(SEED)
    np.random.seed(SEED)

noise = np.random.rand(SIZE, SIZE)
corridors = np.zeros((SIZE, SIZE), dtype=np.uint8)

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
for _ in range(1000):
    x = current_x + random.randint(-10, 10)
    y = current_y + random.randint(-10, 10)
    if in_bounds(x, y) and noise[x, y] > 0.9:
        break

corridors[x, y] = 1
frontier = [(x, y)]

# ------------------
# Main loop 
# ------------------



# Idea
#
# mark room (3x3 pixel)
# S, N, E, W pixels are all = 1
# corner pixels = 2
# choose random direction to go


def crossing_place_path(x,y):
    if corridors[x+2,y] == 2:
        corridors[x+1,y] = 1
    if corridors[x-2,y] == 2:
        corridors[x-1,y] = 1
    if corridors[x,y+2] == 2:
        corridors[x,y+1] = 1
    if corridors[x,y-2] == 2:
        corridors[x,y-1] = 1

DIRECTIONS = []
# creates and modifes a list for valid options so it doesnt choose a direction its already gone in
def build_directions(x,y):
    if corridors[x+2,y] == 0 and corridors[x+1,y] == 0:
        DIRECTIONS.append((1, 0))
    if corridors[x-2,y] == 0 and corridors[x-1,y] == 0:
        DIRECTIONS.append((-1, 0))
    if corridors[x,y+2] == 0 and corridors[x,y+1] == 0:
        DIRECTIONS.append((0, 1))
    if corridors[x,y-2] == 0 and corridors[x,y-2] == 0:
        DIRECTIONS.append((0, -1))
# DIRECTIONS = [
#     (1, 0),    # east
#     (-1, 0),   # west
#     (0, 1),    # south
#     (0, -1)    # north
# ]


for _ in range(MAX_ITERATIONS):

    if not frontier:
        break

    x, y = frontier.pop(random.randrange(len(frontier)))

    #fix colors
    crossing_place_path(x,y)
    DIRECTIONS.clear()
    build_directions(x,y)
    if DIRECTIONS == []:
        break
    print(DIRECTIONS)

    # decide what to place

    placement_decision = random.choice(OPTIONS)

    # Corridor
    if placement_decision == 1:
        step_x, step_y = random.choice(DIRECTIONS)
        x = x + step_x
        y = y + step_y
        corridors[x, y] = 1
        
    # Room
    if placement_decision == 2:
        # place room
        corridors[x+1, y+1] = 2
        corridors[x-1, y+1] = 2
        corridors[x+1, y-1] = 2
        corridors[x-1, y-1] = 2

        corridors[x, y+1] = 2
        corridors[x, y-1] = 2
        corridors[x+1, y] = 2
        corridors[x-1, y] = 2

        corridors[x-last_x, y-last_y] = 1

        step_x, step_y = random.choice(DIRECTIONS)
        x = x + step_x
        y = y + step_y
        corridors[x, y] = 1

        x = x + step_x
        y = y + step_y
        corridors[x, y] = 1
        x = x + step_x
        y = y + step_y
        corridors[x, y] = 1




    current_x, current_y = x, y
    blocked = False
    color_img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

    color_img[corridors == 0] = [0, 0, 0]          # 0 = Black (Background)
    color_img[corridors == 1] = [255, 255, 255]    # 1 = White (Corridors)
    color_img[corridors == 2] = [0, 100, 255]      # 2 = Blue (Rooms)


    img = Image.fromarray(color_img, mode="RGB")
    img.save("corridors_" +  str(_) + ".png")


        

    for _ in range(STEPS_PER_SEGMENT):

        next_x = current_x + step_x
        next_y = current_y + step_y
        # corridors[next_x, next_y] = 1
        # next_x = current_x + step_x
        # next_y = current_y + step_y
        # corridors[next_x, next_y] = 1

        if not in_bounds(next_x, next_y):
            blocked = True
            break

        if corridors[next_x, next_y] == 1 or corridors[next_x, next_y] == 2:
            corridors[next_x, next_y] = 1
            if 1 == _/2:
                current_x, current_y = next_x, next_y
                next_x = current_x + step_x
                next_y = current_y + step_y
                corridors[next_x, next_y] = 1
                current_x, current_y = next_x, next_y
                break
            else:
                current_x, current_y = next_x, next_y
                break
        

        corridors[next_x, next_y] = 1
        
        last_x = step_x
        last_y = step_y

    if not blocked:
        frontier.append((current_x, current_y))

# ------------------
# Export texture
# ------------------

color_img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

color_img[corridors == 0] = [0, 0, 0]          # 0 = Black (Background)
color_img[corridors == 1] = [255, 255, 255]    # 1 = White (Corridors)
color_img[corridors == 2] = [0, 100, 255]      # 2 = Blue (Rooms)


img = Image.fromarray(color_img, mode="RGB")
img.save("corridors.png")