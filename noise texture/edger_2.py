
import numpy as np
from PIL import Image
import random
import time
import math
from collections import deque
import matplotlib.pyplot as plt
import imageio.v3 as iio
import colorsys


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
     (0, 1),    # North
     (1, -1),    # South East
     (0, -1),    # South
     (-1, -1)    # South west
 ]
def in_bounds(x, y):
    return 0 <= x < SIZE and 0 <= y < SIZE


image = iio.imread("input.png")

x_size = image.shape[0]
y_size = image.shape[1]

grid = np.zeros((x_size, y_size), dtype=np.uint8)
grid_color = np.zeros((x_size, y_size, 3), dtype=np.uint8)
vector_length = np.zeros((x_size, y_size), dtype=np.uint8)
vector_angle = np.zeros((x_size, y_size), dtype=np.uint8)


new_x_size = int(x_size/3)
new_y_size = int(y_size/3)

#pass 1
for x in range(x_size):
    for y in range(y_size):


        d_all = [0]*8

        # Check each neighbouring pixel (8 directional)
        i = 0
        color_vector_x = 0
        color_vector_y = 0
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

                dir_len = math.sqrt(dx*dx + dy*dy)
                ndx = dx / dir_len
                ndy = dy / dir_len
                color_vector_x += ndx * distance
                color_vector_y += ndy * distance
                

                if distance > 75:
                    grid[x,y] = 1
            i += 1
        #CALCULATE HSV

        length = math.sqrt(color_vector_x**2 + color_vector_y**2)
        color_vector_angle = math.atan2(color_vector_y,color_vector_x)
        vector_length[x,y] = length
        vector_angle[x,y] = color_vector_angle
        #HUE
    
        hue = (color_vector_angle + math.pi) / (2*math.pi)
        #Saturation
        saturation = min(length/500, 1.0)

        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, saturation)
        r = int(r*255)
        g = int(g*255)
        b = int(b*255)
        grid_color[x,y] = (r,g,b)


#pass 2
# for x in range(x_size):
#     for y in range(y_size):
#         for dx,dy in CARDINAL_DIRECTIONS:
#             nx, ny = x + dx, y + dy
#             if 0 <= nx < x_size and 0 <= ny < y_size:
#                 origin = image[x,y].astype(int)
#                 neighbour = image[x+dx,y+dy].astype(int)

                
#         # kill pixel if neighbour is bigger
        
#         vector_dx = round(math.cos(vector_angle[x,y]))
#         vector_dy = round(math.sin(vector_angle[x,y]))

#         if 0 <= x+vector_dx < x_size and 0 <= y+vector_dy < y_size:
#             if vector_length[x,y] < vector_length[x+vector_dx,y+vector_dy]:
#                 grid_color[x,y] = (0,0,0)
#         if 0 <= x+vector_dx*-1 < x_size and 0 <= y+vector_dy*-1 < y_size:
#             if vector_length[x,y] < vector_length[x+vector_dx*-1,y+vector_dy*-1]:
#                 grid_color[x,y] = (0,0,0)






        









    
    




# ------------------
# Export texture
# ------------------

h, w = grid.shape
black_img = np.zeros((h,w,3), dtype=np.uint8)

black_img[grid == 0] = [0, 0, 0]          # 0 = Black (Background)
black_img[grid == 1] = [255, 255, 255]    # 1 = White (Corridors)
black_img[grid == 2] = [0, 100, 255]

color_img = grid_color



# Display result
plt.imshow(image) # Show original
plt.title("Original Image")
plt.show()

plt.imshow(black_img, cmap='gray', vmin=0, vmax=255) # Show our processed grid
plt.title("Grid Visualization")
plt.show()

plt.imshow(color_img, cmap='gray', vmin=0, vmax=255) # Show our processed grid
plt.title("Grid Visualization")
plt.show()