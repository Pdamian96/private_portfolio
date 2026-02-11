import pygame
import sys

# --- Config ---
GRID_SIZE = 20        # 20x20 tiles
TILE_SIZE = 32        # pixels per tile
WIDTH = GRID_SIZE * TILE_SIZE
HEIGHT = GRID_SIZE * TILE_SIZE

# Colors
WHITE = (240, 240, 240)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (50, 100, 255)     # Player
RED = (200, 60, 60)       # Factory
GREEN = (60, 180, 75)     # Storage

# Positions (grid coordinates)
factory_pos = (5, 5)
storage_pos = (14, 14)
player_pos = [10, 10]

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Transport Game Prototype")
clock = pygame.time.Clock()

def draw_grid():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, GRAY, rect, 1)

def draw_entity(pos, color):
    x, y = pos
    rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
    pygame.draw.rect(screen, color, rect)

def move_player(dx, dy):
    nx = player_pos[0] + dx
    ny = player_pos[1] + dy

    # Boundary check
    if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
        player_pos[0] = nx
        player_pos[1] = ny

# --- Main Loop ---
running = True
while running:
    clock.tick(60)
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                move_player(0, -1)
            elif event.key == pygame.K_s:
                move_player(0, 1)
            elif event.key == pygame.K_a:
                move_player(-1, 0)
            elif event.key == pygame.K_d:
                move_player(1, 0)

    # Draw everything
    draw_grid()
    draw_entity(factory_pos, RED)
    draw_entity(storage_pos, GREEN)
    draw_entity(player_pos, BLUE)

    pygame.display.flip()
