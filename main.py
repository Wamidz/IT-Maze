import pygame, sys
from player import Player
from world import generate_maze_with_room_types
from room import SCREEN_SIZE

pygame.init()
screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
pygame.display.set_caption("Inside the Network")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 32)

# Game states
STATE_TITLE = "title"
STATE_DIFFICULTY = "difficulty"
STATE_OVERWORLD = "overworld"
STATE_QUESTION = "question"
STATE_PAUSE = "pause"

state = STATE_TITLE
difficulty = 1
player = Player()
world = None
room_x = 0
room_y = 0
current_enemy = None
selected = 0

# Minimap config
MINIMAP_TILE = 12
MINIMAP_PADDING = 8
minimap_discovered = set()  # (x,y) coords

def draw_text(text, x, y, selected=False):
    color = (255, 255, 0) if selected else (200, 200, 200)
    t = font.render(text, True, color)
    screen.blit(t, (x, y))

def draw_question(enemy):
    screen.fill((0,0,0))
    q = font.render(enemy.data["q"], True, (255,255,255))
    screen.blit(q, (40,40))
    for i, opt in enumerate(enemy.data["options"]):
        draw_text(opt, 60, 100 + i*40, selected == i)

def handle_keys():
    keys = pygame.key.get_pressed()
    return {"up": keys[pygame.K_UP],
            "down": keys[pygame.K_DOWN],
            "left": keys[pygame.K_LEFT],
            "right": keys[pygame.K_RIGHT]}

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # TITLE
        if state == STATE_TITLE and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = 0
            elif event.key == pygame.K_DOWN:
                selected = 1
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    state = STATE_DIFFICULTY
                    selected = 0
                else:
                    pygame.quit()
                    sys.exit()

        # DIFFICULTY
        elif state == STATE_DIFFICULTY and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 3
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 3
            elif event.key == pygame.K_RETURN:
                difficulty = selected + 1
                world = generate_maze_with_room_types(width=3, height=3, difficulty=difficulty)
                player = Player()
                room_x, room_y = 0, 0
                state = STATE_OVERWORLD
            elif event.key == pygame.K_ESCAPE:
                state = STATE_TITLE
                selected = 0

        # QUESTION
        elif state == STATE_QUESTION and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % len(current_enemy.data["options"])
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % len(current_enemy.data["options"])
            elif event.key == pygame.K_RETURN:
                if selected == current_enemy.data["correct"]:
                    current_enemy.alive = False
                    # Reveal this room when an enemy in it is defeated
                    minimap_discovered.add((room_x, room_y))
                state = STATE_OVERWORLD

        # OVERWORLD
        elif state == STATE_OVERWORLD and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state = STATE_PAUSE

        # PAUSE
        elif state == STATE_PAUSE and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                selected = 1 - selected
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    state = STATE_TITLE
                    selected = 0
                else:
                    pygame.quit()
                    sys.exit()
            elif event.key == pygame.K_ESCAPE:
                state = STATE_OVERWORLD

    keys = handle_keys()
    screen.fill((0,0,0))

    # DRAW
    if state == STATE_TITLE:
        draw_text("Inside the Network", 60, 50)
        draw_text("New Game", 100, 150, selected==0)
        draw_text("Exit", 100, 200, selected==1)

    elif state == STATE_DIFFICULTY:
        draw_text("Select Difficulty", 60, 50)
        draw_text("Easy", 100, 150, selected==0)
        draw_text("Medium", 100, 200, selected==1)
        draw_text("Hard", 100, 250, selected==2)

    elif state == STATE_OVERWORLD:
        room = world[(room_x, room_y)]
        # Reveal this room when entered
        minimap_discovered.add((room_x, room_y))

        player.update(keys, room)
        for e in room.enemies:
            e.update(player, room)

        # Enemy collision
        for e in room.enemies:
            if e.alive and e.x == player.x and e.y == player.y:
                current_enemy = e
                selected = 0
                state = STATE_QUESTION

        room.draw(screen)
        player.draw(screen)

        # ROOM TRANSITIONS (door must exist)
        if player.x < 0 and "L" in room.doors:
            if (room_x-1, room_y) in world:
                room_x -= 1
                player.x = 8
            else:
                player.x = 0
        elif player.x > 8 and "R" in room.doors:
            if (room_x+1, room_y) in world:
                room_x += 1
                player.x = 0
            else:
                player.x = 8
        elif player.y < 0 and "U" in room.doors:
            if (room_x, room_y-1) in world:
                room_y -= 1
                player.y = 8
            else:
                player.y = 0
        elif player.y > 8 and "D" in room.doors:
            if (room_x, room_y+1) in world:
                room_y += 1
                player.y = 0
            else:
                player.y = 8

        # Draw minimap (top-right)
        map_w = 3 * MINIMAP_TILE
        map_h = 3 * MINIMAP_TILE
        map_x = SCREEN_SIZE - map_w - MINIMAP_PADDING
        map_y = MINIMAP_PADDING
        pygame.draw.rect(screen, (10,10,10), (map_x-2, map_y-2, map_w+4, map_h+4))
        for mx in range(3):
            for my in range(3):
                cell_x = map_x + mx * MINIMAP_TILE
                cell_y = map_y + my * MINIMAP_TILE
                world_coord = (mx, my)
                if world is not None and world_coord in minimap_discovered:
                    pygame.draw.rect(screen, (80, 80, 80), (cell_x, cell_y, MINIMAP_TILE, MINIMAP_TILE))
                    # draw enemies if present in revealed room
                    r = world.get(world_coord)
                    if r:
                        for en in r.enemies:
                            if en.alive:
                                # small red dot inside the cell
                                cx = cell_x + MINIMAP_TILE//2
                                cy = cell_y + MINIMAP_TILE//2
                                pygame.draw.circle(screen, (200,40,40), (cx, cy), 2)
                    # Draw door markers for discovered rooms to show where you can go
                    if r:
                        midx = cell_x + MINIMAP_TILE // 2
                        midy = cell_y + MINIMAP_TILE // 2
                        for door in r.doors:
                            if door == "U":
                                pygame.draw.rect(screen, (180,180,60), (midx-2, cell_y, 4, 2))
                            elif door == "D":
                                pygame.draw.rect(screen, (180,180,60), (midx-2, cell_y+MINIMAP_TILE-2, 4, 2))
                            elif door == "L":
                                pygame.draw.rect(screen, (180,180,60), (cell_x, midy-2, 2, 4))
                            elif door == "R":
                                pygame.draw.rect(screen, (180,180,60), (cell_x+MINIMAP_TILE-2, midy-2, 2, 4))
                else:
                    # unrevealed = blank
                    pygame.draw.rect(screen, (0, 0, 0), (cell_x, cell_y, MINIMAP_TILE, MINIMAP_TILE))

        # draw player marker on minimap if that room is revealed
        if (room_x, room_y) in minimap_discovered:
            px = map_x + room_x * MINIMAP_TILE + MINIMAP_TILE//2
            py = map_y + room_y * MINIMAP_TILE + MINIMAP_TILE//2
            pygame.draw.circle(screen, (160, 200, 160), (px, py), 3)

    elif state == STATE_QUESTION:
        draw_question(current_enemy)

    elif state == STATE_PAUSE:
        room = world[(room_x, room_y)]
        room.draw(screen)
        player.draw(screen)
        overlay = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE))
        overlay.set_alpha(180)
        overlay.fill((0,0,0))
        screen.blit(overlay, (0,0))
        draw_text("Paused", 100, 50)
        draw_text("Title Screen", 100, 150, selected==0)
        draw_text("Exit", 100, 200, selected==1)

    pygame.display.flip()
    clock.tick(60)
