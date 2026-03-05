import pygame
import math

# --------------------------------------------------
# Vector utilities
# --------------------------------------------------

def length(v):
    return math.hypot(v[0], v[1])

def normalize(v):
    l = length(v)
    if l == 0:
        return (0, 0)
    return (v[0]/l, v[1]/l)

def subtract(a, b):
    return (a[0]-b[0], a[1]-b[1])

def add(a, b):
    return (a[0]+b[0], a[1]+b[1])

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def cross2d(a, b):
    return a[0]*b[1] - a[1]*b[0]

def rotate_point(p, origin, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    px, py = subtract(p, origin)
    xnew = px * c - py * s
    ynew = px * s + py * c
    return add((xnew, ynew), origin)

def clamp(value, minv, maxv):
    return max(minv, min(maxv, value))

# --------------------------------------------------
# Joint class
# --------------------------------------------------

class Joint:
    def __init__(self, position):
        self.position = position
        self.min_angle = -math.pi      # relative to parent
        self.max_angle = math.pi

# --------------------------------------------------
# Angle constraint enforcement
# --------------------------------------------------

def enforce_angle_limits(joints, index):
    if index == 0:
        return

    parent = joints[index - 1]
    joint = joints[index]

    vec = subtract(joint.position, parent.position)
    angle = math.atan2(vec[1], vec[0])

    base_vec = subtract(parent.position,
                        joints[index - 2].position) if index > 1 else (1, 0)

    base_angle = math.atan2(base_vec[1], base_vec[0])

    relative = angle - base_angle
    relative = (relative + math.pi) % (2 * math.pi) - math.pi

    clamped = clamp(relative, joint.min_angle, joint.max_angle)
    delta = clamped - relative

    if abs(delta) > 1e-5:
        for j in range(index, len(joints)):
            joints[j].position = rotate_point(
                joints[j].position,
                parent.position,
                delta
            )

# --------------------------------------------------
# CCD Solver
# --------------------------------------------------

def solve_ccd(joints, target,
              iterations=10,
              tolerance=2,
              damping=0.7,
              max_step=0.2,
              fixed_root=True):

    for _ in range(iterations):

        end = joints[-1].position
        if length(subtract(end, target)) < tolerance:
            break

        for i in reversed(range(len(joints) - 1)):

            if fixed_root and i == 0:
                continue

            joint = joints[i].position
            end = joints[-1].position

            to_end = normalize(subtract(end, joint))
            to_target = normalize(subtract(target, joint))

            d = clamp(dot(to_end, to_target), -1.0, 1.0)
            angle = math.acos(d)

            if cross2d(to_end, to_target) < 0:
                angle = -angle

            # Rotate all downstream joints
            for j in range(i+1, len(joints)):
                joints[j].position = rotate_point(
                    joints[j].position,
                    joint,
                    angle
                )

            # Enforce constraints
            enforce_angle_limits(joints, i+1)

# --------------------------------------------------
# Setup
# --------------------------------------------------

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Create chain
num_joints = 5
segment_length = 80
joints = []
start_x, start_y = WIDTH // 2, HEIGHT // 2

for i in range(num_joints):
    joints.append(Joint((start_x + i * segment_length, start_y)))

for i in range(1, len(joints)):
    joints[i].min_angle = -math.pi / 1
    joints[i].max_angle = math.pi / 1

target = (WIDTH // 2 + 200, HEIGHT // 2 - 100)

dragging_target = False
dragging_joint = None

# --------------------------------------------------
# Main Loop
# --------------------------------------------------

running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse = pygame.mouse.get_pos()

            if event.button == 1:
                if length(subtract(mouse, target)) < 15:
                    dragging_target = True

            elif event.button == 3:
                for i, joint in enumerate(joints):
                    if length(subtract(mouse, joint.position)) < 10:
                        dragging_joint = i
                        break

        elif event.type == pygame.MOUSEBUTTONUP:
            dragging_target = False
            dragging_joint = None

        elif event.type == pygame.MOUSEMOTION:
            mouse = pygame.mouse.get_pos()
            if dragging_target:
                target = mouse
            if dragging_joint is not None:
                joints[dragging_joint].position = mouse

    if not dragging_joint:
        solve_ccd(
            joints,
            target,
            iterations=12,
            damping=0.6,
            max_step=0.25,
            fixed_root=True
        )

    # --------------------------------------------------
    # Draw
    # --------------------------------------------------

    screen.fill((25, 25, 25))

    # Draw bones
    for i in range(len(joints) - 1):
        pygame.draw.line(screen, (200, 200, 200), joints[i], joints[i+1], 4)

    # Draw joints
    for joint in joints:
        pygame.draw.circle(screen, (80, 150, 255), (int(joint[0]), int(joint[1])), 8)

    # Draw target
    pygame.draw.circle(screen, (255, 80, 80), (int(target[0]), int(target[1])), 10)

    pygame.display.flip()

pygame.quit()
