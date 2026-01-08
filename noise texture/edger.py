
import numpy as np
from PIL import Image
import random
import time
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

for x in range(new_x_size):
    for y in range(new_y_size):
        pixel = image[x, y]
        total_red = 0
        total_blue = 0
        total_green = 0
        for i in range(0, 3):
            for j in range(0, 3):
                total_red += pixel[0]
                total_green += pixel[1]
                total_blue += pixel[2]

        total_red /= 9
        total_green /= 9
        total_blue /= 9
        total = (total_red,total_blue,total_red)

        for k in range(0, 3):
            for l in range(0, 3):

                difference = (pixel[0]-total_red,pixel[1]-total_blue,pixel[2]-total_green)

                if abs(pixel[0]-total_red) > 1:
                    grid[x,y] = 1
                if abs(pixel[1]-total_blue) > 1:
                    grid[x,y] = 1
                if abs(pixel[2]-total_green) > 1:
                    grid[x,y] = 1

                print("Average in neighbourhood: " + str(total) + " difference: " + str(difference))





        # grid[x*3,y*3] = 1
        #idea: 
        # look at a 3x3 area
        # check change threshold
        # check direction of change
        # place that kind of pixel



        









    
    




# ------------------
# Export texture
# ------------------



color_img = (grid * 255).astype(np.uint8)

# Display result
plt.imshow(image) # Show original
plt.title("Original Image")
plt.show()

plt.imshow(color_img, cmap='gray', vmin=0, vmax=255) # Show our processed grid
plt.title("Grid Visualization")
plt.show()