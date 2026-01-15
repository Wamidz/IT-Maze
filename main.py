import pygame, sys
from player import Player
from world import generate_maze_with_room_types
import room

pygame.init()
SCREEN_SIZE = room.get_screen_size()
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
STATE_OPTIONS = "options"
STATE_GRAPHICS = "graphics"
STATE_CONTROLS = "controls"
STATE_AUDIO = "audio"

state = STATE_TITLE
difficulty = 1
player = Player()
world = None
room_x = 0
room_y = 0
current_enemy = None
selected = 0

# Minimap config (scaled up a bit)
MINIMAP_TILE = 20
MINIMAP_PADDING = 12
minimap_discovered = set()  # (x,y) coords

# Options storage
options = {
    "graphics": {
        "tile_size": room.TILE_SIZE,  # will store selected tile size
        "display_mode": "windowed",  # windowed | fullscreen | borderless
        "fit_to_screen": False,
    },
    "controls": {
        # placeholder for future keybindings
    },
    "audio": {
        "volume": 1.0,
    }
}


def apply_graphics_options():
    # Apply tile size change at runtime; if fit_to_screen is enabled, compute tile size
    info = pygame.display.Info()
    if options["graphics"].get("fit_to_screen", False):
        # compute tile size to fit ROOM_TILES across the display
        fs_w = max(16, info.current_w // room.ROOM_TILES)
        fs_h = max(16, info.current_h // room.ROOM_TILES)
        new_size = min(fs_w, fs_h)
        options["graphics"]["tile_size"] = new_size
    else:
        desired = int(options["graphics"]["tile_size"])
        max_tile_w = max(16, info.current_w // room.ROOM_TILES)
        max_tile_h = max(16, info.current_h // room.ROOM_TILES)
        max_tile = min(max_tile_w, max_tile_h)
        new_size = min(desired, max_tile)
        if new_size != desired:
            # update stored value to the clamped value
            options["graphics"]["tile_size"] = new_size

    room.set_tile_size(new_size)

    global SCREEN_SIZE, screen
    SCREEN_SIZE = room.get_screen_size()

    # Choose flags based on display mode
    mode = options["graphics"].get("display_mode", "windowed")
    flags = 0
    screen_size = (SCREEN_SIZE, SCREEN_SIZE)
    if mode == "fullscreen":
        flags = pygame.FULLSCREEN
        # fullscreen uses desktop size; request desktop resolution
        screen_size = (info.current_w, info.current_h)
    elif mode == "borderless":
        # borderless/windowed-fullscreen: set NOFRAME and match desktop size
        flags = pygame.NOFRAME
        screen_size = (info.current_w, info.current_h)

    screen = pygame.display.set_mode(screen_size, flags)

    # reset offsets so entities align to the new tile grid
    try:
        player.offset_x = 0
        player.offset_y = 0
    except Exception:
        pass

    if world is not None:
        for r in world.values():
            for e in r.enemies:
                e.offset_x = 0
                e.offset_y = 0


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

# Helper to redraw background when in menus

def draw_title_menu():
    draw_text("Inside the Network", 60, 50)
    draw_text("New Game", 100, 150, selected==0)
    draw_text("Options", 100, 200, selected==1)
    draw_text("Exit", 100, 250, selected==2)

# Start main loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # TITLE
        if state == STATE_TITLE and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 3
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 3
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    state = STATE_DIFFICULTY
                    selected = 0
                elif selected == 1:
                    state = STATE_OPTIONS
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
                # Reset minimap discoveries
                minimap_discovered = set()
                state = STATE_OVERWORLD
            elif event.key == pygame.K_ESCAPE:
                state = STATE_TITLE
                selected = 0

        # OPTIONS menu
        elif state == STATE_OPTIONS and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 3
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 3
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    state = STATE_GRAPHICS
                    selected = 0
                elif selected == 1:
                    state = STATE_CONTROLS
                    selected = 0
                else:
                    state = STATE_AUDIO
                    selected = 0
            elif event.key == pygame.K_ESCAPE:
                state = STATE_TITLE
                selected = 0

        # GRAPHICS submenu
        elif state == STATE_GRAPHICS and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 3
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 3
            elif event.key == pygame.K_LEFT:
                # cycle display mode left
                modes = ["windowed", "fullscreen", "borderless"]
                cur = options["graphics"].get("display_mode", "windowed")
                idx = modes.index(cur)
                options["graphics"]["display_mode"] = modes[(idx - 1) % len(modes)]
                # apply immediately when user changes display mode
                apply_graphics_options()
            elif event.key == pygame.K_RIGHT:
                # cycle display mode right
                modes = ["windowed", "fullscreen", "borderless"]
                cur = options["graphics"].get("display_mode", "windowed")
                idx = modes.index(cur)
                options["graphics"]["display_mode"] = modes[(idx + 1) % len(modes)]
                apply_graphics_options()
            elif event.key == pygame.K_f:
                # toggle fit-to-screen mode
                options["graphics"]["fit_to_screen"] = not options["graphics"].get("fit_to_screen", False)
                apply_graphics_options()
            elif event.key == pygame.K_RETURN:
                # Map selected to tile sizes small/medium/large
                tile_options = [48, 64, 96]
                options["graphics"]["tile_size"] = tile_options[selected]
                apply_graphics_options()
            elif event.key == pygame.K_ESCAPE:
                state = STATE_OPTIONS
                selected = 0

        # CONTROLS submenu
        elif state == STATE_CONTROLS and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state = STATE_OPTIONS
                selected = 1

        # AUDIO submenu
        elif state == STATE_AUDIO and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state = STATE_OPTIONS
                selected = 2

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
        draw_title_menu()

    elif state == STATE_DIFFICULTY:
        draw_text("Select Difficulty", 60, 50)
        draw_text("Easy", 100, 150, selected==0)
        draw_text("Medium", 100, 200, selected==1)
        draw_text("Hard", 100, 250, selected==2)

    elif state == STATE_OPTIONS:
        draw_text("Options", 60, 50)
        draw_text("Graphics", 100, 150, selected==0)
        draw_text("Controls", 100, 200, selected==1)
        draw_text("Audio", 100, 250, selected==2)

    elif state == STATE_GRAPHICS:
        draw_text("Graphics Options", 60, 50)
        # Show current selection for tile sizes
        ts = options["graphics"]["tile_size"]
        dm = options["graphics"].get("display_mode", "windowed")
        ft = options["graphics"].get("fit_to_screen", False)
        draw_text("Small (48)", 100, 150, selected==0)
        draw_text("Medium (64)", 100, 200, selected==1)
        draw_text("Large (96)", 100, 250, selected==2)
        draw_text(f"Current tilesize: {ts}", 300, 150)
        draw_text(f"Display mode: {dm}", 300, 200)
        draw_text(f"Fit to screen: {'ON' if ft else 'OFF'} (press F)", 300, 240)

    elif state == STATE_CONTROLS:
        draw_text("Controls", 60, 50)
        draw_text("Arrow keys to move", 100, 150)
        draw_text("Esc to pause/open menus", 100, 200)

    elif state == STATE_AUDIO:
        draw_text("Audio", 60, 50)
        draw_text(f"Volume: {options['audio']['volume']}", 100, 150)

    elif state == STATE_OVERWORLD:
        room_obj = world[(room_x, room_y)]
        # Reveal this room when entered
        minimap_discovered.add((room_x, room_y))

        player.update(keys, room_obj)
        # Update enemies, passing others so they don't overlap
        for i, e in enumerate(room_obj.enemies):
            others = room_obj.enemies[:i] + room_obj.enemies[i+1:]
            e.update(player, room_obj, others=others)

        # Enemy collision
        for e in room_obj.enemies:
            if e.alive and e.x == player.x and e.y == player.y:
                current_enemy = e
                selected = 0
                state = STATE_QUESTION

        room_obj.draw(screen)
        player.draw(screen)

        # ROOM TRANSITIONS (door must exist)
        size = room.ROOM_TILES
        if player.x < 0 and "L" in room_obj.doors:
            if (room_x-1, room_y) in world:
                room_x -= 1
                player.x = size-1
            else:
                player.x = 0
        elif player.x > size-1 and "R" in room_obj.doors:
            if (room_x+1, room_y) in world:
                room_x += 1
                player.x = 0
            else:
                player.x = size-1
        elif player.y < 0 and "U" in room_obj.doors:
            if (room_x, room_y-1) in world:
                room_y -= 1
                player.y = size-1
            else:
                player.y = 0
        elif player.y > size-1 and "D" in room_obj.doors:
            if (room_x, room_y+1) in world:
                room_y += 1
                player.y = 0
            else:
                player.y = size-1

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
                                pygame.draw.circle(screen, (200,40,40), (cx, cy), 3)
                    # Draw door markers for discovered rooms to show where you can go
                    if r:
                        midx = cell_x + MINIMAP_TILE // 2
                        midy = cell_y + MINIMAP_TILE // 2
                        for door in r.doors:
                            if door == "U":
                                pygame.draw.rect(screen, (180,180,60), (midx-3, cell_y, 6, 3))
                            elif door == "D":
                                pygame.draw.rect(screen, (180,180,60), (midx-3, cell_y+MINIMAP_TILE-3, 6, 3))
                            elif door == "L":
                                pygame.draw.rect(screen, (180,180,60), (cell_x, midy-3, 3, 6))
                            elif door == "R":
                                pygame.draw.rect(screen, (180,180,60), (cell_x+MINIMAP_TILE-3, midy-3, 3, 6))
                else:
                    # unrevealed = blank
                    pygame.draw.rect(screen, (0, 0, 0), (cell_x, cell_y, MINIMAP_TILE, MINIMAP_TILE))

        # draw player marker on minimap if that room is revealed
        if (room_x, room_y) in minimap_discovered:
            px = map_x + room_x * MINIMAP_TILE + MINIMAP_TILE//2
            py = map_y + room_y * MINIMAP_TILE + MINIMAP_TILE//2
            pygame.draw.circle(screen, (160, 200, 160), (px, py), 5)

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
