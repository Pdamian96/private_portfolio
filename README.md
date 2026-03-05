## README

This is a collection of random prototype projects I made. Note that some were made during a time where I still mostly used AI (this excludes the mean shift project and the dungeon generator). 
I might rewrite these from the ground up but i can't be bothered, I as I mostly used them as a learning tool for coding, as well as messing around with ideas.

## Mean Shift
Mean shift is a Project I made inspired by a youtube video I saw by GneissName. He explored finding the average color of low resolution art (Pixel art, or specifically in his case, minecraft assets)
Taking the average of all colors of a block is not a good solution, as pixel art uses highlights that falsify this. So the idea was to use a different color space (OKLab instead of RGB of HSV), and then put all the colors in a cooridnate grid.
Then it finds groups of colors which are closest together, takes the average of the group, and then you have multiple main colors of the image. 
This Project also has a .exe with a proper GUI to mess around with. The folder also includes some examples that I made. 
The main point of this was for me for picking colors when making pixel art. Usually, I make assets for modded minecraft, so my goal is to have colors which are similar to minecrafts.
I've used this tool with existing assets to make my pixel art feel similar to Minecrafts Art Style.


## "Noise Texture"
That folder is dedicated to my attempt at making an interesting dungeon generator. It was called noise, is because I used a Noise algorithm at first, but then moved to other means. There are a bunch of versions as it was my first time messing about with making my algorithm. This also means that its really not that great, but its a proof concept that I really want to revisit, as it was incredibly fun.

## Inverse Kinematics
This was a small Project for figuring out the algorithm behind it. Not really special as I made it with mostly AI, because I actually only needed the final Product as a test to see if that algorithm was performant enough.


