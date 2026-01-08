import numpy as np
from PIL import Image
import random

# ------------------
# Config
# ------------------
SIZE = 256
STEPS_PER_SEGMENT = 20
MAX_ITERATIONS = 1300
STOP_THRESHOLD = 0.55
SEED = None

# ------------------
# Setup
# ------------------
if SEED is not None:
    random.seed(SEED)
    np.random.seed(SEED)

noise = np.random.rand(SIZE, SIZE)
corridors = np.zeros((SIZE, SIZE), dtype=np.uint8)

# Cardinal directions
DIRS = [
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
for _ in range(MAX_ITERATIONS):
    if not frontier:
        break

    x, y = frontier.pop(random.randrange(len(frontier)))

    step_x, step_y = random.choice(DIRS)
    current_x, current_y = x, y
    blocked = False

    for _ in range(STEPS_PER_SEGMENT):
        next_x = current_x + step_x
        next_y = current_y + step_y


        if not in_bounds(next_x, next_y):
            blocked = True
            break

        if corridors[next_x, next_y] == 1 or noise[next_x, next_y] >= STOP_THRESHOLD:
            corridors[next_x, next_y] = 1
            current_x, current_y = next_x, next_y
            break
        


        corridors[next_x, next_y] = 1
        current_x, current_y = next_x, next_y

    # continue even if no collision
    if not blocked:
        frontier.append((current_x, current_y))

# ------------------
# Export texture
# ------------------
img = Image.fromarray(corridors * 255, mode="L")
img.save("corridors.png")
