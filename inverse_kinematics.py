import pygame
import math

# -----------------------------
# Basic Vector Utilities
# -----------------------------

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

# -----------------------------
# CCD Solver
# -----------------------------

def solve_ccd(joints, target, iterations=10, tolerance=2):
    for _ in range(iterations):
        end = joints[-1]
        if length(subtract(end, target)) < tolerance:
            break

        for i in reversed(range(len(joints) - 1)):
            joint = joints[i]
            end = joints[-1]

            to_end = normalize(subtract(end, joint))
            to_target = normalize(subtract(target, joint))

            d = max(-1.0, min(1.0, dot(to_end, to_target)))
            angle = math.acos(d)

            if cross2d(to_end, to_target) < 0:
                angle = -angle

            for j in range(i+1, len(joints)):
                joints[j] = rotate_point(joints[j], joint, angle)

# -----------------------------
# Setup
# -----------------------------

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

num_joints = 5
segment_length = 80
joints = []

start_x, start_y = WIDTH // 2, HEIGHT // 2
for i in range(num_joints):
    joints.append((start_x + i * segment_length, start_y))

target = (WIDTH // 2 + 200, HEIGHT // 2 - 100)

dragging_target = False
dragging_joint = None

# -----------------------------
# Main Loop
# -----------------------------

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
                    if length(subtract(mouse, joint)) < 10:
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
                joints[dragging_joint] = mouse

    if not dragging_joint:
        solve_ccd(joints, target, iterations=8)

    # -----------------------------
    # Drawing
    # -----------------------------
    screen.fill((30, 30, 30))

    # Bones
    for i in range(len(joints) - 1):
        pygame.draw.line(screen, (200, 200, 200), joints[i], joints[i+1], 4)

    # Joints
    for joint in joints:
        pygame.draw.circle(screen, (80, 150, 255), (int(joint[0]), int(joint[1])), 8)

    # Target
    pygame.draw.circle(screen, (255, 80, 80), (int(target[0]), int(target[1])), 10)

    pygame.display.flip()

pygame.quit()
