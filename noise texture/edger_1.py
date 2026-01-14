
import numpy as np
from PIL import Image
import random
import time
import math
from collections import deque
import matplotlib.pyplot as plt
import imageio.v3 as iio


# ------------------
# Config
# ------------------
SIZE = 99
KERNEL_SIZE = 3

# ------------------
# Setup
# ------------------


OPTIONS = [
    (1),
    (2)  
]

CARDINAL_DIRECTIONS = [
     (1, 0),    # east
     (1, 1),    # north east
     (-1, 0),   # west
     (-1, 1),    # North west
     (0, 1),    # south
     (1, 1),    # south East
     (1, -1),    # South West
     (0, -1)    # north
 ]
def in_bounds(x, y):
    return 0 <= x < SIZE and 0 <= y < SIZE

# ------------------
# Start point
# ------------------



# ------------------
# Main loop 
# ------------------






image = iio.imread("input.png")

x_size = image.shape[0]
y_size = image.shape[1]

grid = np.zeros((x_size, y_size), dtype=np.uint8)



new_x_size = int(x_size/3)
new_y_size = int(y_size/3)

for x in range(x_size):
    for y in range(y_size):

        # Check each neighbouring pixel (8 directional)
        for dx,dy in CARDINAL_DIRECTIONS:
            nx, ny = x + dx, y + dy

            if 0 <= nx < x_size and 0 <= ny < y_size:
                origin = image[x,y].astype(int)
                neighbour = image[x+dx,y+dy].astype(int)
                d_r = origin[0]-neighbour[0]
                d_b = origin[1]-neighbour[1]
                d_g = origin[2]-neighbour[2]
                #calc distance
                distance = math.sqrt(d_r**2 + d_b**2 + d_g**2)
                if distance > 75:
                    grid[x,y] = 1









        # grid[x*3,y*3] = 1
        #idea: 
        # look at a 3x3 area
        # check change threshold
        # check direction of change
        # place that kind of pixel



        









    
    




# ------------------
# Export texture
# ------------------

h, w = grid.shape
color_img = np.zeros((h,w,3), dtype=np.uint8)

color_img[grid == 0] = [0, 0, 0]          # 0 = Black (Background)
color_img[grid == 1] = [255, 255, 255]    # 1 = White (Corridors)
color_img[grid == 2] = [0, 100, 255]




# Display result
plt.imshow(image) # Show original
plt.title("Original Image")
plt.show()

plt.imshow(color_img, cmap='gray', vmin=0, vmax=255) # Show our processed grid
plt.title("Grid Visualization")
plt.show()