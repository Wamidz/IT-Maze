# python
import copy
import random
import sys

import pygame

import room
from player import Player
from world import generate_maze_with_room_types

# Text rendering cache to avoid expensive font.render() calls
_text_cache = {}
def get_cached_text(text, color=(200, 200, 200)):
    """Cache text renders to avoid re-rendering the same text every frame."""
    key = (text, color)
    if key not in _text_cache:
        _text_cache[key] = font.render(text, True, color)
    return _text_cache[key]

def clear_text_cache():
    """Clear the text cache (call when font changes or memory is needed)."""
    global _text_cache
    _text_cache.clear()

pygame.init()
pygame.display.init()
# Try to get desktop info reliably. On some platforms pygame.display.Info() returns zeros
# until a window is created, so create a hidden window briefly if needed.
info = pygame.display.Info()
if info.current_w <= 0 or info.current_h <= 0:
    # create a temporary hidden window to populate display info
    tmp = pygame.display.set_mode((1, 1), pygame.HIDDEN)
    info = pygame.display.Info()
    # we can keep this tiny window until we call apply_graphics_options(), which will replace it

pygame.display.set_caption("IM Maze")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 32)

# Fallback screen size (internal) until options are applied
SCREEN_SIZE = room.get_screen_size()

# Note: do not create a full window yet; apply_graphics_options() will set up the actual display and canvas.

def build_resolutions(info):
    # Wider set of common presets, plus desktop resolution
    common = [
        (640, 480), (800, 600), (1024, 768), (1152, 864),
        (1280, 720), (1280, 800), (1360, 768), (1366, 768),
        (1440, 900), (1536, 864), (1600, 900), (1680, 1050),
        (1920, 1080), (1920, 1200), (2048, 1152), (2560, 1440), (3840, 2160)
    ]
    desktop = (info.current_w, info.current_h)
    vals = []
    # First, try platform-provided fullscreen modes list if available
    try:
        modes = pygame.display.list_modes()
    except Exception:
        modes = None

    if modes and isinstance(modes, list) and len(modes) > 0:
        # list_modes typically returns resolutions ordered from largest to smallest
        for w, h in modes:
            if w <= desktop[0] and h <= desktop[1]:
                vals.append((w, h))
    # fallback: include common presets that fit desktop
    for w, h in common:
        if w <= desktop[0] and h <= desktop[1]:
            vals.append((w, h))
    # ensure desktop resolution (use exact desktop size) is included and unique
    if desktop not in vals:
        vals.append(desktop)
    # unique and sort by width then height
    vals = sorted(list(dict.fromkeys(vals)), key=lambda x: (x[0], x[1]))
    return vals

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
STATE_GAMEOVER = "gameover"
STATE_COMBAT = "combat"
STATE_CHEAT = "cheat"
STATE_WIN = "win"

state = STATE_TITLE
difficulty = 1
player = Player()
world = None
room_x = 0
room_y = 0
current_enemy = None
selected = 0

# Minimap optimization - cache discovered rooms to avoid recalculating every frame
minimap_discovery_cache = None
minimap_cache_valid = False

# Debug performance tracking (press F3 to toggle display)
DEBUG_MODE = False
frame_times = []  # Rolling window of frame times for FPS calculation
debug_text_cache_size = 0  # Monitor cache size

# Combat state variables
combat_turn = "player" # "player" or "enemy"
combat_action = "menu" # "menu", "attack_minigame", "defend_minigame", "question"
combat_timer = 0
combat_player_pos = [0, 0] # For minigames
combat_projectiles = [] # List of projectiles in minigame
combat_score = 0
combat_question_answered = False
combat_question_feedback = None  # "correct" or "incorrect"
combat_question_feedback_timer = 0

# World & minimap configuration
WORLD_W = 21
WORLD_H = 21

# Minimap config (each room cell will show a ROOM_TILES x ROOM_TILES mini-grid)
MINIMAP_TILE = 64
MINIMAP_PADDING = 12
minimap_discovered = set()  # (x,y) coords

# Minimap animation / state
prev_minimap_center = (None, None)
minimap_flash_timer = 0

# Big map overlay state
BIGMAP_BASE = 36  # base size (px) per room cell at zoom=1.0
big_map_zoom = 1.0
big_map_visible = False
big_map_dragging = False
big_map_pan_x = 0
big_map_pan_y = 0
big_map_last_mouse = (0, 0)
big_map_just_opened = False

# Inventory UI config
INVENTORY_SLOTS = 6
INVENTORY_SLOT_SIZE = 48
# Chest / drag state
chest_open = False
chest_grid = None
chest_owner_coords = (None, None)
dragging_item = None  # dict of item being dragged
drag_source = None  # 'player' or 'chest'
drag_origin = None  # original (grid, x, y) for restore
drag_mouse_offset = (0, 0)

# Item tooltip state
hovered_item = None  # current item being hovered
hovered_item_pos = (0, 0)  # position to draw tooltip

def clamp_big_map_pan():
    global big_map_pan_x, big_map_pan_y
    # Pan lock removed: intentionally do not clamp pan here so the user can freely drag the map.
    # This function is kept for compatibility (calls from zoom etc.) but is currently a no-op.
    return


def recenter_big_map_on_player():
    """Center the big map view on the player's exact sub-tile position."""
    global big_map_pan_x, big_map_pan_y
    try:
        if canvas is None:
            return
        room_px = int(BIGMAP_BASE * big_map_zoom)
        # normalized in-room position (tile center + offset)
        in_x = (player.x + 0.5) + (player.offset_x / max(1, room.TILE_SIZE))
        in_y = (player.y + 0.5) + (player.offset_y / max(1, room.TILE_SIZE))
        sub_px_x = int((in_x / room.ROOM_TILES) * room_px)
        sub_px_y = int((in_y / room.ROOM_TILES) * room_px)
        prx_world = (room_x * room_px) + sub_px_x
        pry_world = (room_y * room_px) + sub_px_y
        cw, ch = canvas.get_size()
        big_map_pan_x = cw // 2 - prx_world
        big_map_pan_y = ch // 2 - pry_world
    except Exception:
        pass

def start_new_world(width, height, difficulty_level):
    global world, player, room_x, room_y, minimap_discovered, prev_minimap_center, minimap_flash_timer, WORLD_W, WORLD_H
    WORLD_W, WORLD_H = width, height
    world = generate_maze_with_room_types(width=width, height=height, difficulty=difficulty_level)
    player = Player()
    # spawn player roughly in center so minimap can show movement in all directions
    room_x, room_y = width // 2, height // 2
    minimap_discovered = set()
    minimap_discovered.add((room_x, room_y))
    prev_minimap_center = (room_x, room_y)
    minimap_flash_timer = 12
    return world

# Options storage (resolutions will be populated after we query display)
options = {
    "graphics": {
        "tile_size": room.TILE_SIZE,  # will store selected tile size
        "display_mode": "windowed",  # windowed | fullscreen | borderless
        "fit_to_screen": False,
        "resolutions": [],
        "resolution_index": 0,
    },
    "controls": {},
    "audio": {"volume": 1.0}
}

# internal render canvas will be created by apply_graphics_options() once the display mode is known
canvas = None

# Populate resolutions list based on current desktop
options["graphics"]["resolutions"] = build_resolutions(info)

def choose_default_16_9(res_list, info):
    """Choose a default resolution that matches 16:9 if possible; fall back to desktop or largest."""
    # prefer common 16:9 presets in ascending preference
    preferred = [(1280,720), (1366,768), (1600,900), (1920,1080), (2560,1440), (3840,2160)]
    for p in preferred:
        if p in res_list:
            return res_list.index(p)
    # otherwise choose the desktop resolution if present
    desktop = (info.current_w, info.current_h)
    if desktop in res_list:
        return res_list.index(desktop)
    # otherwise pick the largest available (last in our sorted list)
    return len(res_list) - 1

# default index: prefer a 16:9 resolution when possible
options["graphics"]["resolution_index"] = choose_default_16_9(options["graphics"]["resolutions"], info)

# Pending UI-only graphics settings (changes here are not applied until the user clicks Apply)
pending_graphics = copy.deepcopy(options["graphics"])
graphics_dropdown_open = False
graphics_dropdown_hover = -1

def open_graphics_menu():
    """Initialize the pending graphics state when opening the graphics menu."""
    global pending_graphics, graphics_dropdown_open, graphics_dropdown_hover
    pending_graphics = copy.deepcopy(options["graphics"])
    graphics_dropdown_open = False
    graphics_dropdown_hover = -1


def get_canvas_mouse_pos():
    """Map mouse position on the actual window to internal canvas coordinates."""
    mx, my = pygame.mouse.get_pos()
    sw, sh = screen.get_size()
    cw, ch = canvas.get_size()
    if sw == 0 or sh == 0:
        return 0, 0
    return int(mx * cw / sw), int(my * ch / sh)


def menu_items_for_state(cur_state):
    """Return list of (label_text, x, y) for clickable menu items for a given state.
    Positions must match the drawn positions used by the renderer below.
    """
    items = []
    if cur_state == STATE_TITLE:
        items = [("New Game", 100, 150), ("Options", 100, 200), ("Exit", 100, 250)]
    elif cur_state == STATE_DIFFICULTY:
        items = [("Easy", 100, 150), ("Medium", 100, 200), ("Hard", 100, 250)]
    elif cur_state == STATE_OPTIONS:
        items = [("Graphics", 100, 150), ("Controls", 100, 200), ("Audio", 100, 250)]
    elif cur_state == STATE_GRAPHICS:
        # Use the pending_graphics values so UI changes don't immediately apply
        dm = pending_graphics.get("display_mode", "windowed")
        ridx = pending_graphics.get("resolution_index", 0)
        res = pending_graphics.get("resolutions", options["graphics"]["resolutions"])  # fallback
        if ridx < 0 or ridx >= len(res):
            ridx = 0
        res_text = f"{res[ridx][0]}x{res[ridx][1]}"
        items = [
            (f"Display Mode: {dm}", 100, 150),
            (f"Resolution: {res_text}" + (" (disabled in fullscreen)" if dm == "fullscreen" else ""), 100, 200),
            (f"Fit to screen: {'ON' if pending_graphics.get('fit_to_screen', False) else 'OFF'} (press F)", 100, 250),
            ("Apply", 100, 300),
            ("Cancel", 220, 300)
        ]
    elif cur_state == STATE_CONTROLS:
        items = [("Back", 100, 250)]
    elif cur_state == STATE_AUDIO:
        items = [("Back", 100, 250)]
    elif cur_state == STATE_PAUSE:
        items = [("Title Screen", 100, 150), ("Exit", 100, 200)]
    elif cur_state == STATE_GAMEOVER:
        items = [("Try Again", 100, 150), ("Title Screen", 100, 200), ("Exit", 100, 250)]
    elif cur_state == STATE_WIN:
        items = [("New Game", 100, 150), ("Title Screen", 100, 200), ("Exit", 100, 250)]
    elif cur_state == STATE_COMBAT:
        if combat_action == "menu":
            items = [("Attack", 100, 350), ("Item", 100, 390), ("Answer Question", 100, 430)]
        elif combat_action == "question":
            for i, opt in enumerate(current_enemy.data["options"]):
                items.append((opt, 60, 100 + i*40))
    elif cur_state == STATE_CHEAT:
        items = [
            (f"Noclip: {'ON' if player.noclip else 'OFF'}", 100, 150),
            (f"Godmode: {'ON' if player.godmode else 'OFF'}", 100, 200),
            ("Reveal Map", 100, 250),
            ("Show Exit", 100, 300),
            ("Back", 100, 350)
        ]
    return items


def rect_for_text_at(text, x, y):
    w, h = font.size(text)
    return pygame.Rect(x, y, w, h)


def apply_graphics_options():
    """
    Sets pygame display mode and the internal canvas resolution. Behavior:
    - fullscreen: display mode = desktop resolution; canvas = desktop resolution
    - borderless: display mode = desktop resolution (NOFRAME); canvas = chosen internal resolution (can be lower -> pixelated)
    - windowed: display mode = chosen resolution; canvas = chosen resolution
    Tile size is computed from the canvas width and ROOM_TILES (unless fit_to_screen is True).
    """
    global SCREEN_SIZE, screen, canvas

    info = pygame.display.Info()
    mode = options["graphics"].get("display_mode", "windowed")
    res_list = options["graphics"]["resolutions"]
    idx = options["graphics"].get("resolution_index", 0)
    idx = max(0, min(idx, len(res_list)-1))
    options["graphics"]["resolution_index"] = idx
    selected_res = res_list[idx]

    flags = 0
    display_w, display_h = SCREEN_SIZE, SCREEN_SIZE

    if mode == "fullscreen":
        flags = pygame.FULLSCREEN
        display_w, display_h = info.current_w, info.current_h
        # internal canvas matches desktop resolution in fullscreen
        canvas_w, canvas_h = display_w, display_h

    elif mode == "borderless":
        # Borderless: make a window without frame that matches the desktop size
        flags = pygame.NOFRAME
        display_w, display_h = info.current_w, info.current_h
        # internal canvas can be the selected (potentially lower) resolution so it will be scaled up
        canvas_w, canvas_h = selected_res

    else:  # windowed
        display_w, display_h = selected_res
        canvas_w, canvas_h = selected_res

    # If fit_to_screen is enabled, compute tile size to fit ROOM_TILES across the canvas
    if options["graphics"].get("fit_to_screen", False):
        fs_w = max(8, canvas_w // room.ROOM_TILES)
        fs_h = max(8, canvas_h // room.ROOM_TILES)
        new_tile = min(fs_w, fs_h)
        options["graphics"]["tile_size"] = new_tile
    else:
        # compute tile size from the internal canvas width (so the canvas resolution determines scaling)
        desired = int(options["graphics"]["tile_size"])
        canvas_tile_w = max(8, canvas_w // room.ROOM_TILES)
        canvas_tile_h = max(8, canvas_h // room.ROOM_TILES)
        max_tile = min(canvas_tile_w, canvas_tile_h)
        new_tile = min(desired, max_tile)
        if new_tile != desired:
            options["graphics"]["tile_size"] = new_tile

    # apply tile size to room
    room.set_tile_size(options["graphics"]["tile_size"])

    # recreate canvas with the internal resolution (canvas_w, canvas_h)
    canvas = pygame.Surface((canvas_w, canvas_h))

    # set up the actual display window/surface
    SCREEN_SIZE = max(canvas_w, canvas_h)
    screen = pygame.display.set_mode((display_w, display_h), flags)

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
    t = get_cached_text(text, color)
    canvas.blit(t, (x, y))


def draw_item_tooltip(item, x, y):
    """Draw a tooltip showing item information at the given coordinates."""
    if item is None:
        return

    item_name = item.get('name', 'Item') if isinstance(item, dict) else getattr(item, 'name', 'Item')
    item_desc = item.get('description', '') if isinstance(item, dict) else getattr(item, 'description', '')
    item_type = item.get('type', '') if isinstance(item, dict) else getattr(item, 'type', '')

    # Build tooltip text
    tooltip_lines = [item_name]
    if item_type:
        tooltip_lines.append(f"Type: {item_type}")
    if item_desc:
        tooltip_lines.append(item_desc)

    # Calculate tooltip dimensions
    tooltip_height = len(tooltip_lines) * 20 + 10
    max_line_width = max([len(line) for line in tooltip_lines]) * 8
    tooltip_width = max_line_width + 10

    # Ensure tooltip stays on screen
    cw, ch = canvas.get_size()
    draw_x = min(x, cw - tooltip_width - 5)
    draw_y = min(y, ch - tooltip_height - 5)

    # Draw tooltip background
    pygame.draw.rect(canvas, (40, 40, 50), (draw_x, draw_y, tooltip_width, tooltip_height))
    pygame.draw.rect(canvas, (150, 150, 180), (draw_x, draw_y, tooltip_width, tooltip_height), 2)

    # Draw tooltip text
    for i, line in enumerate(tooltip_lines):
        t = font.render(line, True, (200, 200, 220))
        canvas.blit(t, (draw_x + 5, draw_y + 5 + i * 20))


def draw_question(enemy):
    canvas.fill((0,0,0))
    q = font.render(enemy.data["q"], True, (255,255,255))
    canvas.blit(q, (40,40))
    for i, opt in enumerate(enemy.data["options"]):
        draw_text(opt, 60, 100 + i*40, selected == i)

def start_combat(enemy):
    global state, current_enemy, combat_turn, combat_action, selected, combat_question_answered
    state = STATE_COMBAT
    current_enemy = enemy
    combat_turn = "player"
    combat_action = "menu"
    selected = 0
    combat_question_answered = False

def start_defend_minigame():
    global combat_action, combat_timer, combat_player_pos, combat_projectiles
    combat_action = "defend_minigame"
    combat_timer = 300 # 5 seconds at 60fps
    combat_player_pos = [canvas.get_width() // 2, canvas.get_height() // 2]
    combat_projectiles = []

def update_defend_minigame(keys):
    global combat_timer, player, state, selected
    combat_timer -= 1
    
    # Move player heart
    speed = 4
    if keys["up"]: combat_player_pos[1] -= speed
    if keys["down"]: combat_player_pos[1] += speed
    if keys["left"]: combat_player_pos[0] -= speed
    if keys["right"]: combat_player_pos[0] += speed
    
    # Clamp to box
    box_rect = pygame.Rect(canvas.get_width()//2 - 100, canvas.get_height()//2 - 100, 200, 200)
    combat_player_pos[0] = max(box_rect.left + 10, min(box_rect.right - 10, combat_player_pos[0]))
    combat_player_pos[1] = max(box_rect.top + 10, min(box_rect.bottom - 10, combat_player_pos[1]))
    
    # Spawn projectiles
    if random.random() < 0.1:
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            start = [random.randint(box_rect.left, box_rect.right), box_rect.top]
            vel = [0, 3]
        elif side == "bottom":
            start = [random.randint(box_rect.left, box_rect.right), box_rect.bottom]
            vel = [0, -3]
        elif side == "left":
            start = [box_rect.left, random.randint(box_rect.top, box_rect.bottom)]
            vel = [3, 0]
        else:
            start = [box_rect.right, random.randint(box_rect.top, box_rect.bottom)]
            vel = [-3, 0]
        combat_projectiles.append({"pos": start, "vel": vel})
        
    # Update projectiles
    player_rect = pygame.Rect(0, 0, 16, 16)
    player_rect.center = combat_player_pos
    
    for p in combat_projectiles[:]:
        p["pos"][0] += p["vel"][0]
        p["pos"][1] += p["vel"][1]
        
        # Collision
        proj_rect = pygame.Rect(0, 0, 10, 10)
        proj_rect.center = p["pos"]
        
        if player_rect.colliderect(proj_rect):
            player.apply_damage(5)
            combat_projectiles.remove(p)
            if player.hp <= 0:
                state = STATE_GAMEOVER
                selected = 0
                return
        
        # Remove if out of bounds (roughly)
        if not box_rect.inflate(20, 20).collidepoint(p["pos"]):
            if p in combat_projectiles:
                combat_projectiles.remove(p)
                
    if combat_timer <= 0:
        # End turn
        global combat_turn, combat_action
        combat_turn = "player"
        combat_action = "menu"
        selected = 0

def draw_defend_minigame():
    box_rect = pygame.Rect(canvas.get_width()//2 - 100, canvas.get_height()//2 - 100, 200, 200)
    pygame.draw.rect(canvas, (255, 255, 255), box_rect, 2)
    
    # Draw player heart
    pygame.draw.rect(canvas, (255, 0, 0), (combat_player_pos[0]-8, combat_player_pos[1]-8, 16, 16))
    
    # Draw projectiles
    for p in combat_projectiles:
        pygame.draw.circle(canvas, (255, 255, 255), (int(p["pos"][0]), int(p["pos"][1])), 5)
        
    draw_text(f"Dodge! Time: {combat_timer//60}", 100, 50)

def start_attack_minigame():
    global combat_action, combat_timer, combat_score
    combat_action = "attack_minigame"
    combat_timer = 0
    combat_score = 0 # Used for bar position

def update_attack_minigame(keys):
    global combat_score, combat_timer, current_enemy, combat_turn, combat_action, selected, minimap_discovered, state
    # Bar moves back and forth
    combat_score = (combat_score + 5) % 400 # 0 to 400 range
    
    # Press Z or Enter to hit
    # Logic handled in event loop for key press, this is just animation update
    pass

def handle_attack_hit():
    global combat_score, current_enemy, combat_turn, combat_action, selected, minimap_discovered, state, combat_question_answered
    
    # Calculate damage based on how close to center (200)
    # Regular attacks are nerfed to incentivize question usage
    dist = abs(combat_score - 200)
    damage = 0
    if dist < 20:
        damage = 12  # Crit (was 20)
    elif dist < 50:
        damage = 6   # Normal (was 10)
    else:
        damage = 3   # Weak (was 5)

    # Bonus if question was answered correctly previously
    if combat_question_answered:
        damage = int(damage * 1.5)  # 1.5x multiplier (was 2x)
        combat_question_answered = False  # Use up the bonus

    # Apply attack multiplier buff
    damage = int(damage * player.attack_multiplier)

    # Reset attack buff after use
    player.attack_multiplier = 1.0

    current_enemy.apply_damage(damage)
    
    if not current_enemy.alive:
        minimap_discovered.add((room_x, room_y))
        state = STATE_OVERWORLD
        # Reset combat buffs
        player.attack_multiplier = 1.0
        player.defense_multiplier = 1.0
    else:
        start_defend_minigame()

def draw_attack_minigame():
    bar_rect = pygame.Rect(canvas.get_width()//2 - 200, canvas.get_height()//2 + 50, 400, 30)
    pygame.draw.rect(canvas, (100, 100, 100), bar_rect)
    
    # Target area
    target_rect = pygame.Rect(canvas.get_width()//2 - 20, canvas.get_height()//2 + 50, 40, 30)
    pygame.draw.rect(canvas, (0, 255, 0), target_rect)
    
    # Moving cursor
    cursor_x = canvas.get_width()//2 - 200 + combat_score
    pygame.draw.rect(canvas, (255, 255, 255), (cursor_x, canvas.get_height()//2 + 45, 5, 40))
    
    draw_text("Press ENTER when white bar is in green!", 100, 100)


def handle_keys():
    keys = pygame.key.get_pressed()
    return {"up": keys[pygame.K_UP] or keys[pygame.K_w],
            "down": keys[pygame.K_DOWN] or keys[pygame.K_s],
            "left": keys[pygame.K_LEFT] or keys[pygame.K_a],
            "right": keys[pygame.K_RIGHT] or keys[pygame.K_d]}


def draw_title_menu():
    draw_text("IM Maze", 60, 50)
    draw_text("New Game", 100, 150, selected==0)
    draw_text("Options", 100, 200, selected==1)
    draw_text("Exit", 100, 250, selected==2)

def inventory_panel_layout(cw, gy, gx):
    """Return panel_x, panel_y, slot_size, slot_gap for player inventory area."""
    panel_x = 10
    panel_y = gy
    panel_w = max(120, gx - 20)
    # compute slot_size to fit horizontally if needed
    cols = player.inventory.width
    rows = player.inventory.height
    slot_gap = 6
    # ensure slots fit into panel_w
    avail_w = panel_w - 16
    slot_size = min(INVENTORY_SLOT_SIZE, max(16, (avail_w - (cols-1)*slot_gap)//cols))
    return panel_x, panel_y, slot_size, slot_gap

def draw_inventory_panel(cw, gy, gx):
    """Draw player inventory grid in left gutter."""
    global hovered_item, hovered_item_pos

    panel_x, panel_y, slot_size, slot_gap = inventory_panel_layout(cw, gy, gx)
    cols = player.inventory.width
    rows = player.inventory.height
    panel_w = max(120, gx - 20)
    panel_h = max(120, 24 + rows * (slot_size + slot_gap))
    # background
    pygame.draw.rect(canvas, (20,20,30), (panel_x, panel_y, panel_w, panel_h))
    pygame.draw.rect(canvas, (120,120,120), (panel_x, panel_y, panel_w, panel_h), 1)
    # title and HP
    t = font.render("Inventory", True, (200,200,200))
    canvas.blit(t, (panel_x + 8, panel_y + 6))
    hp_text = font.render(f"HP: {player.hp}/{player.max_hp}", True, (200,200,200))
    canvas.blit(hp_text, (panel_x + 8, panel_y + 30))
    # grid origin
    sx = panel_x + 8
    sy = panel_y + 56
    # draw slots
    for y in range(rows):
        for x in range(cols):
            rx = sx + x * (slot_size + slot_gap)
            ry = sy + y * (slot_size + slot_gap)
            pygame.draw.rect(canvas, (40,40,50), (rx, ry, slot_size, slot_size))
            pygame.draw.rect(canvas, (100,100,100), (rx, ry, slot_size, slot_size), 1)

    # draw items and check for hover
    mx, my = get_canvas_mouse_pos()
    hovered_item = None
    hovered_item_pos = (0, 0)

    for item, ix, iy, iw, ih in player.inventory.iter_items():
        rx = sx + ix * (slot_size + slot_gap)
        ry = sy + iy * (slot_size + slot_gap)
        w_px = iw * slot_size + (iw-1) * slot_gap
        h_px = ih * slot_size + (ih-1) * slot_gap
        pygame.draw.rect(canvas, (180,160,60), (rx+2, ry+2, w_px-4, h_px-4))
        name = item.get('name') if isinstance(item, dict) else getattr(item, 'name', str(item))
        txt = font.render(name[:10], True, (20,20,20))
        canvas.blit(txt, (rx+4, ry+4))

        # Check if mouse is hovering over this item
        item_rect = pygame.Rect(rx, ry, w_px, h_px)
        if item_rect.collidepoint(mx, my):
            hovered_item = item
            hovered_item_pos = (rx + w_px + 5, ry)

def chest_modal_layout(cw, ch, grid):
    cols = grid.width
    rows = grid.height
    slot_gap = 6
    slot_size = min(64, INVENTORY_SLOT_SIZE)
    modal_w = cols * slot_size + (cols-1)*slot_gap + 40
    modal_h = rows * slot_size + (rows-1)*slot_gap + 80
    mx = (cw - modal_w) // 2
    my = (ch - modal_h) // 2
    return mx, my, slot_size, slot_gap

def draw_chest_modal(grid):
    global hovered_item, hovered_item_pos

    cw, ch = canvas.get_size()
    mx, my, slot_size, slot_gap = chest_modal_layout(cw, ch, grid)
    # modal background
    pygame.draw.rect(canvas, (15,15,15), (mx, my, cw - mx*2, ch - my*2))
    # header
    title = font.render("Chest", True, (220,220,220))
    canvas.blit(title, (mx + 16, my + 12))
    sx = mx + 20
    sy = my + 48
    # draw slots
    for y in range(grid.height):
        for x in range(grid.width):
            rx = sx + x * (slot_size + slot_gap)
            ry = sy + y * (slot_size + slot_gap)
            pygame.draw.rect(canvas, (40,40,50), (rx, ry, slot_size, slot_size))
            pygame.draw.rect(canvas, (120,120,120), (rx, ry, slot_size, slot_size), 1)

    # draw items and check for hover
    cursor_x, cursor_y = get_canvas_mouse_pos()
    hovered_item = None
    hovered_item_pos = (0, 0)

    for item, ix, iy, iw, ih in grid.iter_items():
        rx = sx + ix * (slot_size + slot_gap)
        ry = sy + iy * (slot_size + slot_gap)
        w_px = iw * slot_size + (iw-1) * slot_gap
        h_px = ih * slot_size + (ih-1) * slot_gap
        pygame.draw.rect(canvas, (160,120,180), (rx+2, ry+2, w_px-4, h_px-4))
        name = item.get('name') if isinstance(item, dict) else getattr(item, 'name', str(item))
        txt = font.render(name[:12], True, (20,20,20))
        canvas.blit(txt, (rx+4, ry+4))

        # Check if mouse is hovering over this item
        item_rect = pygame.Rect(rx, ry, w_px, h_px)
        if item_rect.collidepoint(cursor_x, cursor_y):
            hovered_item = item
            hovered_item_pos = (rx + w_px + 5, ry)

    return (sx, sy, slot_size, slot_gap, mx, my)

def screen_to_player_grid(mx, my, gx, gy):
    panel_x, panel_y, slot_size, slot_gap = inventory_panel_layout(canvas.get_width(), gy, gx)
    sx = panel_x + 8
    sy = panel_y + 56
    cols = player.inventory.width
    rows = player.inventory.height
    rx = mx - sx
    ry = my - sy
    if rx < 0 or ry < 0:
        return None
    cx = rx // (slot_size + slot_gap)
    cy = ry // (slot_size + slot_gap)
    if cx < 0 or cy < 0 or cx >= cols or cy >= rows:
        return None
    return int(cx), int(cy)

def screen_to_chest_grid(mx, my, chest_sx, chest_sy, slot_size, slot_gap, grid):
    rx = mx - chest_sx
    ry = my - chest_sy
    if rx < 0 or ry < 0:
        return None
    cx = rx // (slot_size + slot_gap)
    cy = ry // (slot_size + slot_gap)
    if cx < 0 or cy < 0 or cx >= grid.width or cy >= grid.height:
        return None
    return int(cx), int(cy)

def handle_inventory_click(mx, my, gx, gy):
    """Handle clicks on the player inventory panel (e.g. using items)."""
    pg = screen_to_player_grid(mx, my, gx, gy)
    if pg:
        px, py = pg
        # Right click to use item? Or just click?
        # For now, let's say right click uses item, left click drags (handled in main loop)
        # But this function is called inside left click handler in main loop...
        # Let's assume this function is for 'using' items if we want that on left click,
        # but the main loop prioritizes dragging.
        # Actually, let's make it so if you click an item and it's consumable, maybe we use it?
        # Or maybe we need a separate key for using.
        # For now, let's just return False so dragging logic takes over.
        # If we want to support using items, we might need to check for double click or right click.
        pass
    return False

# ensure initial application of graphics options (setup canvas & screen)
apply_graphics_options()

def draw_debug_info():
    """Draw performance debug information on screen. Press F3 to toggle."""
    global frame_times, debug_text_cache_size

    if not DEBUG_MODE:
        return

    # Calculate FPS
    current_time = pygame.time.get_ticks()
    if len(frame_times) > 0:
        elapsed = current_time - frame_times[-1]
        if elapsed > 0:
            frame_times.append(current_time)
        else:
            return
    else:
        frame_times.append(current_time)

    # Keep only last 60 frames for rolling FPS
    if len(frame_times) > 60:
        frame_times = frame_times[-60:]

    if len(frame_times) > 1:
        avg_frame_time = (frame_times[-1] - frame_times[0]) / (len(frame_times) - 1)
        fps = 1000 / avg_frame_time if avg_frame_time > 0 else 0
    else:
        fps = 0

    # Get cache size
    cache_size = len(_text_cache)

    # Draw debug text
    debug_texts = [
        f"FPS: {fps:.1f}",
        f"Text Cache: {cache_size}",
        f"State: {state}",
        "Press F3 to hide debug"
    ]

    y_offset = 10
    for debug_text in debug_texts:
        surf = get_cached_text(debug_text, (100, 255, 100))
        canvas.blit(surf, (10, y_offset))
        y_offset += 25

# Start main loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # Big map input handling: toggle with M, drag with left mouse
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            big_map_visible = not big_map_visible
            # mark that the map was just opened so we can optionally recenter once
            big_map_just_opened = big_map_visible
            # reset pan when opening
            if big_map_visible:
                # center on player's exact position (room index + sub-tile offset) if we have a canvas
                if canvas:
                    room_px = int(BIGMAP_BASE * big_map_zoom)
                    # compute player's sub-pixel within its room
                    in_x = (player.x + 0.5) + (player.offset_x / max(1, room.TILE_SIZE))
                    in_y = (player.y + 0.5) + (player.offset_y / max(1, room.TILE_SIZE))
                    sub_px_x = int((in_x / room.ROOM_TILES) * room_px)
                    sub_px_y = int((in_y / room.ROOM_TILES) * room_px)
                    # set pan so the player's exact marker sits at canvas center
                    big_map_pan_x = canvas.get_width()//2 - (room_x * room_px + sub_px_x)
                    big_map_pan_y = canvas.get_height()//2 - (room_y * room_px + sub_px_y)
                    clamp_big_map_pan()
                else:
                    big_map_pan_x = -(room_x * BIGMAP_BASE)
                    big_map_pan_y = -(room_y * BIGMAP_BASE)

        if big_map_visible and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # begin dragging big map (use canvas-space coords so scaling doesn't break dragging)
            big_map_dragging = True
            big_map_last_mouse = get_canvas_mouse_pos()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # finish drag/drop if active
            if dragging_item is not None:
                mx, my = get_canvas_mouse_pos()
                # try drop into chest modal if open
                if chest_open and chest_grid is not None:
                    cmx, cmy, slot_size, slot_gap = chest_modal_layout(canvas.get_width(), canvas.get_height(), chest_grid)
                    chest_sx = cmx + 20
                    chest_sy = cmy + 48
                    tgt = screen_to_chest_grid(mx, my, chest_sx, chest_sy, slot_size, slot_gap, chest_grid)
                    if tgt:
                        tx, ty = tgt
                        success = chest_grid.place_item(dragging_item, tx, ty)
                        if not success:
                            # restore to origin
                            orig_grid, ox, oy = drag_origin
                            orig_grid.place_item(dragging_item, ox, oy)
                        dragging_item = None
                        drag_source = None
                        drag_origin = None
                        continue
                # else try drop into player inventory at mouse
                cw, ch = canvas.get_size()
                gx = (cw - (room.ROOM_TILES * room.TILE_SIZE)) // 2
                gy = (ch - (room.ROOM_TILES * room.TILE_SIZE)) // 2
                pcell = screen_to_player_grid(mx, my, gx, gy)
                if pcell:
                    px, py = pcell
                    placed = player.add_item_to_inventory(dragging_item, px, py)
                    if not placed:
                        # restore to origin
                        orig_grid, ox, oy = drag_origin
                        orig_grid.place_item(dragging_item, ox, oy)
                else:
                    # cannot place, restore
                    orig_grid, ox, oy = drag_origin
                    orig_grid.place_item(dragging_item, ox, oy)
                dragging_item = None
                drag_source = None
                drag_origin = None
            big_map_dragging = False

        if big_map_dragging and event.type == pygame.MOUSEMOTION:
            # use canvas-space mouse coordinates for consistent pan deltas
            mx, my = get_canvas_mouse_pos()
            lx, ly = big_map_last_mouse
            dx = mx - lx
            dy = my - ly
            big_map_pan_x += dx
            big_map_pan_y += dy
            big_map_last_mouse = (mx, my)
            clamp_big_map_pan()

        # handle mouse wheel for zooming
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:  # scroll up
            # zoom around mouse position
            mx, my = get_canvas_mouse_pos()
            old_room_px = int(BIGMAP_BASE * big_map_zoom)
            new_zoom = min(3.0, big_map_zoom + 0.1)
            new_room_px = int(BIGMAP_BASE * new_zoom)
            if new_room_px != old_room_px:
                ratio = new_room_px / max(1, old_room_px)
                big_map_pan_x = mx - (mx - big_map_pan_x) * ratio
                big_map_pan_y = my - (my - big_map_pan_y) * ratio
                big_map_zoom = new_zoom
                clamp_big_map_pan()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:  # scroll down
            mx, my = get_canvas_mouse_pos()
            old_room_px = int(BIGMAP_BASE * big_map_zoom)
            new_zoom = max(0.5, big_map_zoom - 0.1)
            new_room_px = int(BIGMAP_BASE * new_zoom)
            if new_room_px != old_room_px:
                ratio = new_room_px / max(1, old_room_px)
                big_map_pan_x = mx - (mx - big_map_pan_x) * ratio
                big_map_pan_y = my - (my - big_map_pan_y) * ratio
                big_map_zoom = new_zoom
                clamp_big_map_pan()

        # keyboard zoom in/out (plus/minus)
        if event.type == pygame.KEYDOWN and big_map_visible:
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                # zoom centered on canvas center
                mx, my = canvas.get_width()//2, canvas.get_height()//2
                old_room_px = int(BIGMAP_BASE * big_map_zoom)
                new_zoom = min(3.0, big_map_zoom + 0.1)
                new_room_px = int(BIGMAP_BASE * new_zoom)
                if new_room_px != old_room_px:
                    ratio = new_room_px / max(1, old_room_px)
                    big_map_pan_x = mx - (mx - big_map_pan_x) * ratio
                    big_map_pan_y = my - (my - big_map_pan_y) * ratio
                    big_map_zoom = new_zoom
                    clamp_big_map_pan()
            elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                mx, my = canvas.get_width()//2, canvas.get_height()//2
                old_room_px = int(BIGMAP_BASE * big_map_zoom)
                new_zoom = max(0.5, big_map_zoom - 0.1)
                new_room_px = int(BIGMAP_BASE * new_zoom)
                if new_room_px != old_room_px:
                    ratio = new_room_px / max(1, old_room_px)
                    big_map_pan_x = mx - (mx - big_map_pan_x) * ratio
                    big_map_pan_y = my - (my - big_map_pan_y) * ratio
                    big_map_zoom = new_zoom
                    clamp_big_map_pan()

        # MOUSE support: update selection on hover, activate on click
        if event.type == pygame.MOUSEMOTION:
            mx, my = get_canvas_mouse_pos()
            # If dropdown is open in graphics menu, set hover for dropdown entries
            if state == STATE_GRAPHICS and graphics_dropdown_open:
                res_list = pending_graphics.get("resolutions", options["graphics"]["resolutions"])
                rx, ry = 100, 200
                h = font.get_linesize()
                graphics_dropdown_hover = -1
                for i, rsize in enumerate(res_list):
                    rrect = pygame.Rect(rx, ry + (i + 1) * h, *font.size(f"{rsize[0]}x{rsize[1]}"))
                    if rrect.collidepoint(mx, my):
                        graphics_dropdown_hover = i
                        selected = 1
                        break
            else:
                items = menu_items_for_state(state)
                for i, (label, x, y) in enumerate(items):
                    r = rect_for_text_at(label, x, y)
                    if r.collidepoint(mx, my):
                        selected = i
                        break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # Right click handling
            mx, my = get_canvas_mouse_pos()
            if state == STATE_OVERWORLD and not big_map_visible:
                # Check for right click on inventory to use item
                tsize = room.TILE_SIZE
                game_w = room.ROOM_TILES * tsize
                game_h = room.ROOM_TILES * tsize
                cw, ch = canvas.get_size()
                gx = (cw - game_w) // 2
                gy = (ch - game_h) // 2
                
                if gx > 40:
                    pg = screen_to_player_grid(mx, my, gx, gy)
                    if pg:
                        px, py = pg
                        # Try to use item at this location
                        player.use_item(px, py)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # left click acts like pressing Enter / interacting with menus
            mx, my = get_canvas_mouse_pos()
            # If we're in the overworld and not viewing the big map, check inventory clicks first
            if state == STATE_OVERWORLD and not big_map_visible:
                # compute game surface placement to derive left gutter area
                tsize = room.TILE_SIZE
                game_w = room.ROOM_TILES * tsize
                game_h = room.ROOM_TILES * tsize
                cw, ch = canvas.get_size()
                gx = (cw - game_w) // 2
                gy = (ch - game_h) // 2
                # if the left gutter exists, let inventory handle clicks
                if gx > 40:
                    # check player inventory grid click for drag start
                    pg = screen_to_player_grid(mx, my, gx, gy)
                    if pg:
                        px, py = pg
                        entry = player.inventory.get_at(px, py)
                        if entry:
                            # remove and begin drag
                            dragging_item = player.remove_item_from_inventory_at(px, py)
                            drag_source = 'player'
                            drag_origin = (player.inventory, px, py)
                            drag_mouse_offset = (mx, my)
                            continue
                    # handle_inventory_click removed as it was unused

                # check chest interaction (E opens chests; mouse can click chest to open if present)
                room_obj = world[(room_x, room_y)]
                # compute mouse relative to in-room pixels
                # derive top-left of room draw (gx, gy) and tile size
                size = room.TILE_SIZE
                rel_x = mx - gx
                rel_y = my - gy
                if rel_x >=0 and rel_y >=0 and rel_x < game_w and rel_y < game_h:
                    tx = int(rel_x // size)
                    ty = int(rel_y // size)
                    chest = room_obj.get_chest_at(tx, ty)
                    if chest:
                        # open chest modal
                        chest_open = True
                        chest_grid = chest
                        chest_owner_coords = (tx, ty)
                        continue
                # if chest modal already open, also check clicks inside it to start dragging
                if chest_open and chest_grid is not None:
                    # compute chest modal layout (no draw)
                    cw2, ch2 = canvas.get_size()
                    cmx, cmy, cslot, cgap = chest_modal_layout(cw2, ch2, chest_grid)
                    chest_sx = cmx + 20
                    chest_sy = cmy + 48
                    cell = screen_to_chest_grid(mx, my, chest_sx, chest_sy, cslot, cgap, chest_grid)
                    if cell:
                        cx, cy = cell
                        ent = chest_grid.get_at(cx, cy)
                        if ent:
                            # remove and begin drag
                            dragging_item = chest_grid.remove_at(cx, cy)
                            drag_source = 'chest'
                            drag_origin = (chest_grid, cx, cy)
                            drag_mouse_offset = (mx, my)
                            continue

            items = menu_items_for_state(state)
            for i, (label, x, y) in enumerate(items):
                r = rect_for_text_at(label, x, y)
                if r.collidepoint(mx, my):
                    selected = i
                    # emulate pressing RETURN or performing an action
                    if state == STATE_TITLE:
                        if selected == 0:
                            state = STATE_DIFFICULTY
                            selected = 0
                        elif selected == 1:
                            state = STATE_OPTIONS
                            selected = 0
                        else:
                            pygame.quit()
                            sys.exit()
                    elif state == STATE_DIFFICULTY:
                        difficulty = selected + 1
                        start_new_world(WORLD_W, WORLD_H, difficulty)
                        state = STATE_OVERWORLD
                    elif state == STATE_OPTIONS:
                        if selected == 0:
                            state = STATE_GRAPHICS
                            selected = 0
                            open_graphics_menu()
                        elif selected == 1:
                            state = STATE_CONTROLS
                            selected = 0
                        else:
                            state = STATE_AUDIO
                            selected = 0
                    elif state == STATE_GRAPHICS:
                        # entries: 0=Display Mode, 1=Resolution, 2=Fit To Screen, 3=Apply, 4=Cancel
                        if selected == 0:
                            modes = ["windowed", "fullscreen", "borderless"]
                            cur = pending_graphics.get("display_mode", "windowed")
                            idxm = modes.index(cur)
                            pending_graphics["display_mode"] = modes[(idxm + 1) % len(modes)]
                            # if switching to fullscreen, close dropdown and ensure desktop res selected in pending
                            if pending_graphics["display_mode"] == "fullscreen":
                                graphics_dropdown_open = False
                                # ensure pending resolution index points at desktop if available
                                desktop = (info.current_w, info.current_h)
                                res_list = pending_graphics.get("resolutions", options["graphics"]["resolutions"])
                                if desktop in res_list:
                                    pending_graphics["resolution_index"] = res_list.index(desktop)
                        elif selected == 1:
                            # toggle the dropdown (only if not fullscreen)
                            if pending_graphics.get("display_mode") != "fullscreen":
                                graphics_dropdown_open = not graphics_dropdown_open
                            else:
                                graphics_dropdown_open = False
                        elif selected == 2:
                            pending_graphics["fit_to_screen"] = not pending_graphics.get("fit_to_screen", False)
                        elif selected == 3:
                            # Apply: commit pending_graphics into options and apply
                            options["graphics"] = copy.deepcopy(pending_graphics)
                            apply_graphics_options()
                            state = STATE_OPTIONS
                            selected = 0
                        elif selected == 4:
                            # Cancel: discard changes
                            state = STATE_OPTIONS
                            selected = 0
                    elif state == STATE_CONTROLS:
                        state = STATE_OPTIONS
                        selected = 1
                    elif state == STATE_AUDIO:
                        state = STATE_OPTIONS
                        selected = 2
                    elif state == STATE_QUESTION and current_enemy:
                        if selected == current_enemy.data["correct"]:
                            current_enemy.alive = False
                            minimap_discovered.add((room_x, room_y))
                        else:
                            # Wrong answer
                            player.apply_damage(25)
                            current_enemy.alive = False # Remove enemy to prevent loop
                        
                        if player.hp <= 0:
                            state = STATE_GAMEOVER
                            selected = 0
                        else:
                            state = STATE_OVERWORLD
                    elif state == STATE_PAUSE:
                        if selected == 0:
                            state = STATE_TITLE
                            selected = 0
                        else:
                            pygame.quit()
                            sys.exit()
                    elif state == STATE_GAMEOVER:
                        if selected == 0:
                            # Try Again (same difficulty)
                            start_new_world(WORLD_W, WORLD_H, difficulty)
                            state = STATE_OVERWORLD
                        elif selected == 1:
                            state = STATE_TITLE
                            selected = 0
                        else:
                            pygame.quit()
                            sys.exit()
                    elif state == STATE_COMBAT:
                        if combat_action == "menu":
                            if selected == 0: # Attack
                                start_attack_minigame()
                            elif selected == 1: # Item
                                combat_action = "item_select"
                                selected = 0
                            elif selected == 2: # Question
                                combat_action = "question"
                                selected = 0
                        elif combat_action == "question":
                            if selected == current_enemy.data["correct"]:
                                combat_question_answered = True
                                start_defend_minigame()
                            else:
                                # Wrong answer, take damage and end turn
                                player.apply_damage(10)
                                if player.hp <= 0:
                                    state = STATE_GAMEOVER
                                    selected = 0
                                else:
                                    start_defend_minigame()
                    elif state == STATE_CHEAT:
                        if selected == 0:
                            player.noclip = not player.noclip
                        elif selected == 1:
                            player.godmode = not player.godmode
                        elif selected == 2:
                            # Reveal map
                            for x in range(WORLD_W):
                                for y in range(WORLD_H):
                                    minimap_discovered.add((x, y))
                        elif selected == 3:
                            # Show exit (find exit room and add to discovered)
                            for coord, r in world.items():
                                if r.is_exit:
                                    minimap_discovered.add(coord)
                                    # Also teleport player there for convenience? No, just show it.
                        elif selected == 4:
                            state = STATE_OVERWORLD
                            selected = 0
                    elif state == STATE_WIN:
                        if selected == 0:
                            start_new_world(WORLD_W, WORLD_H, difficulty)
                            state = STATE_OVERWORLD
                        elif selected == 1:
                            state = STATE_TITLE
                            selected = 0
                        else:
                            pygame.quit()
                            sys.exit()
                    break  # handled click

        # KEYBOARD handling (existing behavior)
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
                start_new_world(WORLD_W, WORLD_H, difficulty)
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
                    open_graphics_menu()
                elif selected == 1:
                    state = STATE_CONTROLS
                    selected = 0
                else:
                    state = STATE_AUDIO
                    selected = 0
            elif event.key == pygame.K_ESCAPE:
                state = STATE_TITLE
                selected = 0

        # GRAPHICS submenu (enhanced) - now edits pending_graphics until Apply
        elif state == STATE_GRAPHICS and event.type == pygame.KEYDOWN:
            # menu entries: 0=Display Mode, 1=Resolution, 2=Fit To Screen, 3=Apply, 4=Cancel
            entry_count = 5
            if event.key == pygame.K_UP:
                selected = (selected - 1) % entry_count
                graphics_dropdown_open = False
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % entry_count
                graphics_dropdown_open = False
            elif event.key == pygame.K_LEFT:
                if selected == 0:
                    modes = ["windowed", "fullscreen", "borderless"]
                    cur = pending_graphics.get("display_mode", "windowed")
                    idxm = modes.index(cur)
                    pending_graphics["display_mode"] = modes[(idxm - 1) % len(modes)]
                    if pending_graphics["display_mode"] == "fullscreen":
                        graphics_dropdown_open = False
                elif selected == 1:
                    # cycle pending resolution left (UI only)
                    if not pending_graphics.get("display_mode") == "fullscreen":
                        ridx = pending_graphics.get("resolution_index", 0)
                        ridx = (ridx - 1) % len(pending_graphics.get("resolutions", []))
                        pending_graphics["resolution_index"] = ridx
                elif selected == 2:
                    pending_graphics["fit_to_screen"] = not pending_graphics.get("fit_to_screen", False)
            elif event.key == pygame.K_RIGHT:
                if selected == 0:
                    modes = ["windowed", "fullscreen", "borderless"]
                    cur = pending_graphics.get("display_mode", "windowed")
                    idxm = modes.index(cur)
                    pending_graphics["display_mode"] = modes[(idxm + 1) % len(modes)]
                    if pending_graphics["display_mode"] == "fullscreen":
                        graphics_dropdown_open = False
                elif selected == 1:
                    if not pending_graphics.get("display_mode") == "fullscreen":
                        ridx = pending_graphics.get("resolution_index", 0)
                        ridx = (ridx + 1) % len(pending_graphics.get("resolutions", []))
                        pending_graphics["resolution_index"] = ridx
                elif selected == 2:
                    pending_graphics["fit_to_screen"] = not pending_graphics.get("fit_to_screen", False)
            elif event.key == pygame.K_f:
                # toggle fit-to-screen
                pending_graphics["fit_to_screen"] = not pending_graphics.get("fit_to_screen", False)
            elif event.key == pygame.K_RETURN:
                if selected == 3:
                    # Apply
                    options["graphics"] = copy.deepcopy(pending_graphics)
                    apply_graphics_options()
                    state = STATE_OPTIONS
                    selected = 0
                elif selected == 4:
                    # Cancel
                    state = STATE_OPTIONS
                    selected = 0
                else:
                    # other entries: toggle or open dropdown
                    if selected == 0:
                        modes = ["windowed", "fullscreen", "borderless"]
                        cur = pending_graphics.get("display_mode", "windowed")
                        idxm = modes.index(cur)
                        pending_graphics["display_mode"] = modes[(idxm + 1) % len(modes)]
                        if pending_graphics["display_mode"] == "fullscreen":
                            graphics_dropdown_open = False
                    elif selected == 1:
                        if pending_graphics.get("display_mode") != "fullscreen":
                            graphics_dropdown_open = not graphics_dropdown_open
                    elif selected == 2:
                        pending_graphics["fit_to_screen"] = not pending_graphics.get("fit_to_screen", False)
            elif event.key == pygame.K_ESCAPE:
                # Cancel changes
                state = STATE_OPTIONS
                selected = 0
                graphics_dropdown_open = False

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
                    minimap_discovered.add((room_x, room_y))
                state = STATE_OVERWORLD

        # OVERWORLD
        elif state == STATE_OVERWORLD and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state = STATE_PAUSE
            elif event.key == pygame.K_e or event.key == pygame.K_RETURN:
                # toggle chest open/close near player
                room_obj = world[(room_x, room_y)]
                if chest_open:
                    chest_open = False
                    chest_grid = None
                    chest_owner_coords = (None, None)
                else:
                    # check current tile and adjacent tiles for chest
                    found = None
                    for dx, dy in [(0,0),(0,-1),(0,1),(-1,0),(1,0)]:
                        tx = player.x + dx
                        ty = player.y + dy
                        c = room_obj.get_chest_at(tx, ty)
                        if c:
                            found = (c, (tx, ty))
                            break
                    if found:
                        chest_grid, chest_owner_coords = found[0], found[1]
                        chest_open = True
                    
                    # Check for exit
                    if room_obj.is_exit:
                        ex, ey = room_obj.exit_coords
                        # Check if player is on or adjacent to exit
                        dist = abs(player.x - ex) + abs(player.y - ey)
                        if dist <= 1:
                            state = STATE_WIN
                            selected = 0

            elif event.key == pygame.K_F1:
                # Secret cheat menu
                state = STATE_CHEAT
                selected = 0

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

        # GAMEOVER
        elif state == STATE_GAMEOVER and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 3
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 3
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    start_new_world(WORLD_W, WORLD_H, difficulty)
                    state = STATE_OVERWORLD
                elif selected == 1:
                    state = STATE_TITLE
                    selected = 0
                else:
                    pygame.quit()
                    sys.exit()
        
        # WIN
        elif state == STATE_WIN and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 3
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 3
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    start_new_world(WORLD_W, WORLD_H, difficulty)
                    state = STATE_OVERWORLD
                elif selected == 1:
                    state = STATE_TITLE
                    selected = 0
                else:
                    pygame.quit()
                    sys.exit()
        
        # COMBAT
        elif state == STATE_COMBAT and event.type == pygame.KEYDOWN:
            if combat_action == "menu":
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % 3
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % 3
                elif event.key == pygame.K_RETURN:
                    if selected == 0: # Attack
                        start_attack_minigame()
                    elif selected == 1: # Item
                        combat_action = "item_select"
                        selected = 0
                    elif selected == 2: # Question
                        combat_action = "question"
                        selected = 0
            elif combat_action == "item_select":
                # Get consumable items
                consumable_items = []
                for item, ix, iy, iw, ih in player.inventory.iter_items():
                    if isinstance(item, dict):
                        item_type = item.get('type', '')
                        if item_type in ['heal', 'buff_attack', 'buff_defense', 'stun']:
                            consumable_items.append((item, ix, iy))

                max_options = len(consumable_items[:5]) + 1  # items + back
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % max_options
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % max_options
                elif event.key == pygame.K_RETURN:
                    if selected < len(consumable_items[:5]):
                        # Use the selected item
                        item, ix, iy = consumable_items[selected]
                        item_type = item.get('type', '')
                        item_value = item.get('value', 0)

                        # Apply item effect
                        if item_type == 'heal':
                            player.hp = min(player.max_hp, player.hp + item_value)
                        elif item_type == 'buff_attack':
                            player.attack_multiplier = item_value
                        elif item_type == 'buff_defense':
                            player.defense_multiplier = item_value
                        elif item_type == 'stun':
                            if current_enemy:
                                current_enemy.stunned = True

                        # Remove item from inventory
                        player.remove_item_from_inventory_at(ix, iy)

                        # Enemy's turn (defend minigame)
                        start_defend_minigame()
                    else:
                        # Back to menu
                        combat_action = "menu"
                        selected = 0
                elif event.key == pygame.K_ESCAPE:
                    combat_action = "menu"
                    selected = 0
            elif combat_action == "question":
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(current_enemy.data["options"])
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(current_enemy.data["options"])
                elif event.key == pygame.K_RETURN:
                    if selected == current_enemy.data["correct"]:
                        # Correct answer: HIGH REWARD - deal significant damage
                        combat_question_feedback = "correct"
                        combat_question_feedback_timer = 120  # 2 seconds at 60fps
                        damage = 35  # Increased from 25 - much better than regular attack
                        current_enemy.apply_damage(damage)
                        if not current_enemy.alive:
                            minimap_discovered.add((room_x, room_y))
                            state = STATE_OVERWORLD
                        else:
                            combat_question_answered = True
                            start_defend_minigame()
                    else:
                        # Wrong answer: HIGH RISK - player takes significant damage
                        combat_question_feedback = "incorrect"
                        combat_question_feedback_timer = 120  # 2 seconds at 60fps
                        player.apply_damage(15)  # Increased from 10 - makes wrong answers costly
                        if player.hp <= 0:
                            state = STATE_GAMEOVER
                            selected = 0
                        else:
                            start_defend_minigame()
            elif combat_action == "attack_minigame":
                if event.key == pygame.K_RETURN or event.key == pygame.K_z:
                    handle_attack_hit()
        
        # CHEAT MENU
        elif state == STATE_CHEAT and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                selected = (selected - 1) % 5
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 5
            elif event.key == pygame.K_RETURN:
                if selected == 0:
                    player.noclip = not player.noclip
                elif selected == 1:
                    player.godmode = not player.godmode
                elif selected == 2:
                    # Reveal map
                    for x in range(WORLD_W):
                        for y in range(WORLD_H):
                            minimap_discovered.add((x, y))
                elif selected == 3:
                    # Show exit (find exit room and add to discovered)
                    for coord, r in world.items():
                        if r.is_exit:
                            minimap_discovered.add(coord)
                elif selected == 4:
                    state = STATE_OVERWORLD
                    selected = 0
            elif event.key == pygame.K_ESCAPE:
                state = STATE_OVERWORLD
                selected = 0

    keys = handle_keys()
    # Update combat feedback timer
    if combat_question_feedback_timer > 0:
        combat_question_feedback_timer -= 1
    else:
        combat_question_feedback = None
    canvas.fill((0,0,0))
    # ensure an overlay surface exists each frame sized to the internal canvas
    # so code that draws on `overlay` (big map / modals) has a valid target.
    try:
        overlay = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        # start fully transparent
        overlay.fill((0,0,0,0))
    except Exception:
        # If canvas isn't ready for some reason, fallback to a tiny surface to avoid NameError
        overlay = pygame.Surface((1,1))

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
        ts = pending_graphics.get("tile_size", options["graphics"].get("tile_size"))
        dm = pending_graphics.get("display_mode", "windowed")
        ft = pending_graphics.get("fit_to_screen", False)
        ridx = pending_graphics.get("resolution_index", 0)
        res_list = pending_graphics.get("resolutions", options["graphics"]["resolutions"])
        if ridx < 0 or ridx >= len(res_list):
            ridx = 0
            pending_graphics["resolution_index"] = 0
        res_text = f"{res_list[ridx][0]}x{res_list[ridx][1]}"

        draw_text(f"Display Mode: {dm}", 100, 150, selected==0)
        if dm == "fullscreen":
            draw_text(f"Resolution: {res_text} (disabled in fullscreen)", 100, 200, selected==1)
        else:
            draw_text(f"Resolution: {res_text}", 100, 200, selected==1)
        draw_text(f"Fit to screen: {'ON' if ft else 'OFF'} (press F)", 100, 250, selected==2)
        draw_text("Apply", 100, 300, selected==3)
        draw_text("Cancel", 220, 300, selected==4)
        draw_text(f"Current tilesize: {ts}", 400, 150)

        # Draw resolution dropdown if open
        if graphics_dropdown_open and dm != "fullscreen":
            rx, ry = 100, 200
            h = font.get_linesize()
            for i, rsize in enumerate(res_list):
                label = f"{rsize[0]}x{rsize[1]}"
                is_selected = (i == pending_graphics.get("resolution_index", 0))
                is_hover = (i == graphics_dropdown_hover)
                col = (255,255,0) if is_selected or is_hover else (200,200,200)
                t = font.render(label, True, col)
                canvas.blit(t, (rx, ry + (i+1)*h))

    elif state == STATE_CONTROLS:
        draw_text("Controls", 60, 50)
        draw_text("Arrow keys to move", 100, 150)
        draw_text("Esc to pause/open menus", 100, 200)
        draw_text("Back", 100, 250, selected==0)

    elif state == STATE_AUDIO:
        draw_text("Audio", 60, 50)
        draw_text(f"Volume: {options['audio']['volume']}", 100, 150)
        draw_text("Back", 100, 250, selected==0)

    elif state == STATE_OVERWORLD:
        room_obj = world[(room_x, room_y)]
        # Reveal this room when entered
        minimap_discovered.add((room_x, room_y))

        # If the big map is open, pause world updates so gameplay doesn't move behind the map
        if not big_map_visible:
            # Only update player/enemies if chest is NOT open
            if not chest_open:
                player.update(keys, room_obj)
                # Update enemies, passing others so they don't overlap
                for i, e in enumerate(room_obj.enemies):
                    others = room_obj.enemies[:i] + room_obj.enemies[i+1:]
                    e.update(player, room_obj, others=others)

                # Enemy collision (only when not viewing big map)
                for e in room_obj.enemies:
                    if e.alive and e.x == player.x and e.y == player.y:
                        start_combat(e)

         # draw room and player onto a centered game surface then blit into the canvas
        # compute game area size from current tile size
        tsize = room.TILE_SIZE
        game_w = room.ROOM_TILES * tsize
        game_h = room.ROOM_TILES * tsize
        # ensure game fits into canvas; if not, scale down by adjusting tsize temporarily
        cw, ch = canvas.get_size()
        if game_w > cw or game_h > ch:
            # compute scale factor to fit into canvas (preserve aspect)
            sx = cw / game_w
            sy = ch / game_h
            s = min(sx, sy)
            # compute new temporary tile size
            temp_t = max(1, int(tsize * s))
            game_w = room.ROOM_TILES * temp_t
            game_h = room.ROOM_TILES * temp_t
            temp_surface = pygame.Surface((game_w, game_h))
            # draw into temp surface by temporarily setting TILE_SIZE
            old_tile = room.TILE_SIZE
            room.set_tile_size(temp_t)
            room_obj.draw(temp_surface)
            # draw player and enemies onto temp surface
            player.draw(temp_surface)
            room.set_tile_size(old_tile)
        else:
            temp_surface = pygame.Surface((game_w, game_h))
            # normal draw at current tile size
            room_obj.draw(temp_surface)
            player.draw(temp_surface)


        # center the game surface horizontally on the canvas leaving gutters left and right
        # enforce a minimum horizontal gutter percentage so there's always 'open' space at left and right
        min_gutter_ratio = 0.06  # 6% each side by default
        min_gutter = int(cw * min_gutter_ratio)
        gx = (cw - game_w) // 2
        gy = (ch - game_h) // 2
        if gx < min_gutter:
            # need to shrink the game surface to guarantee gutters
            target_game_w = max(32, cw - 2 * min_gutter)
            # scale factor
            s = target_game_w / game_w
            target_game_h = max(32, int(game_h * s))
            # create scaled version of temp_surface
            scaled_game = pygame.transform.smoothscale(temp_surface, (target_game_w, target_game_h))
            gx = (cw - target_game_w) // 2
            gy = (ch - target_game_h) // 2
            canvas.blit(scaled_game, (gx, gy))
        else:
            canvas.blit(temp_surface, (gx, gy))

        # ROOM TRANSITIONS (door must exist)
        size = room.ROOM_TILES
        if player.x < 0:
            if "L" in room_obj.doors or player.noclip:
                if (room_x-1, room_y) in world:
                    room_x -= 1
                    player.x = size-1
                else:
                    player.x = 0
            else:
                player.x = 0
        elif player.x > size-1:
            if "R" in room_obj.doors or player.noclip:
                if (room_x+1, room_y) in world:
                    room_x += 1
                    player.x = 0
                else:
                    player.x = size-1
            else:
                player.x = size-1
        elif player.y < 0:
            if "U" in room_obj.doors or player.noclip:
                if (room_x, room_y-1) in world:
                    room_y -= 1
                    player.y = size-1
                else:
                    player.y = 0
            else:
                player.y = 0
        elif player.y > size-1:
            if "D" in room_obj.doors or player.noclip:
                if (room_x, room_y+1) in world:
                    room_y += 1
                    player.y = 0
                else:
                    player.y = size-1
            else:
                player.y = size-1

        # Draw persistent left inventory panel
        draw_inventory_panel(cw, gy, gx)

        # Draw minimap: show up to 3x3 neighbor rooms but only include existing world tiles
        center_rx = room_x
        center_ry = room_y
        # Determine candidate columns and rows in range [center-1, center+1] but clamp to world bounds
        cand_wx = [x for x in range(center_rx-1, center_rx+2) if 0 <= x < WORLD_W]
        cand_wy = [y for y in range(center_ry-1, center_ry+2) if 0 <= y < WORLD_H]

        cols = len(cand_wx)
        rows = len(cand_wy)
        map_w = cols * MINIMAP_TILE
        map_h = rows * MINIMAP_TILE
        map_x = canvas.get_width() - map_w - MINIMAP_PADDING
        map_y = MINIMAP_PADDING
        # background box
        pygame.draw.rect(canvas, (10,10,10), (map_x-3, map_y-3, map_w+6, map_h+6))

        # flash when center changes
        if prev_minimap_center != (center_rx, center_ry):
            minimap_flash_timer = 12
            prev_minimap_center = (center_rx, center_ry)

        # iterate visible columns/rows
        for ix, wx in enumerate(cand_wx):
            for iy, wy in enumerate(cand_wy):
                cell_x = map_x + ix * MINIMAP_TILE
                cell_y = map_y + iy * MINIMAP_TILE
                # default background
                pygame.draw.rect(canvas, (20,20,20), (cell_x, cell_y, MINIMAP_TILE, MINIMAP_TILE))

                if world is not None and (wx, wy) in world:
                    r = world.get((wx, wy))
                    if (wx, wy) in minimap_discovered:
                        # draw mini internal tiles within cell
                        mini_tile = max(1, MINIMAP_TILE // room.ROOM_TILES)
                        for tx in range(room.ROOM_TILES):
                            for ty in range(room.ROOM_TILES):
                                px_x = cell_x + tx * mini_tile
                                px_y = cell_y + ty * mini_tile
                                if (tx, ty) in r.walls:
                                    col = (60, 60, 60)
                                else:
                                    col = (100, 100, 100)
                                pygame.draw.rect(canvas, col, (px_x, px_y, mini_tile, mini_tile))

                        # draw doors as small highlights on the edges
                        mid = room.ROOM_TILES // 2
                        door_thickness = max(1, mini_tile)
                        for door in r.doors:
                            if door == 'U':
                                dx = cell_x + mid * mini_tile
                                dy = cell_y
                                pygame.draw.rect(canvas, (180,180,60), (dx, dy, mini_tile, door_thickness))
                            elif door == 'D':
                                dx = cell_x + mid * mini_tile
                                dy = cell_y + (room.ROOM_TILES-1) * mini_tile + (mini_tile - door_thickness)
                                pygame.draw.rect(canvas, (180,180,60), (dx, dy, mini_tile, door_thickness))
                            elif door == 'L':
                                dx = cell_x
                                dy = cell_y + mid * mini_tile
                                pygame.draw.rect(canvas, (180,180,60), (dx, dy, door_thickness, mini_tile))
                            elif door == 'R':
                                dx = cell_x + (room.ROOM_TILES-1) * mini_tile + (mini_tile - door_thickness)
                                dy = cell_y + mid * mini_tile
                                pygame.draw.rect(canvas, (180,180,60), (dx, dy, door_thickness, mini_tile))

                        # enemies
                        for en in r.enemies:
                            if en.alive:
                                ex = cell_x + en.x * mini_tile + mini_tile // 2
                                ey = cell_y + en.y * mini_tile + mini_tile // 2
                                pygame.draw.circle(canvas, (200,40,40), (ex, ey), max(1, mini_tile//2))

                        # exit (if present in this room)
                        if r.is_exit:
                            ex, ey = r.exit_coords
                            exit_x = cell_x + ex * mini_tile + mini_tile // 2
                            exit_y = cell_y + ey * mini_tile + mini_tile // 2
                            # Draw exit as a bright square
                            pygame.draw.rect(canvas, (0, 200, 200), (exit_x - mini_tile//2, exit_y - mini_tile//2, mini_tile, mini_tile))
                            pygame.draw.rect(canvas, (0, 255, 255), (exit_x - mini_tile//2, exit_y - mini_tile//2, mini_tile, mini_tile), 1)
                    else:
                        # room exists but is undiscovered: dark subtle square
                        pygame.draw.rect(canvas, (10,10,10), (cell_x+1, cell_y+1, MINIMAP_TILE-2, MINIMAP_TILE-2))
                else:
                    # out-of-world: pure black (shouldn't happen as cand lists are clamped but keep safeguard)
                    pygame.draw.rect(canvas, (0,0,0), (cell_x+1, cell_y+1, MINIMAP_TILE-2, MINIMAP_TILE-2))
                # if this is the player's current room record its pixel origin
                if (wx, wy) == (room_x, room_y):
                    player_room_rx = cell_x
                    player_room_ry = cell_y

        # Draw player marker on minimap
        if world is not None and player_room_rx is not None and player_room_ry is not None:
            # Use MINIMAP_TILE size for minimap player marker
            mini_tile = max(1, MINIMAP_TILE // room.ROOM_TILES)
            in_x = (player.x + 0.5) + (player.offset_x / max(1, room.TILE_SIZE))
            in_y = (player.y + 0.5) + (player.offset_y / max(1, room.TILE_SIZE))
            sub_px_x = int((in_x / room.ROOM_TILES) * MINIMAP_TILE)
            sub_px_y = int((in_y / room.ROOM_TILES) * MINIMAP_TILE)
            prx = player_room_rx + sub_px_x
            pry = player_room_ry + sub_px_y
            pygame.draw.circle(canvas, (0, 0, 0), (prx, pry), max(3, mini_tile//2 + 1))
            pygame.draw.circle(canvas, (160, 220, 160), (prx, pry), max(2, mini_tile//2))

        # Draw BIG MAP overlay if visible
        if big_map_visible and world is not None:
            # Clear overlay and draw semi-transparent background
            overlay.fill((0, 0, 0, 200))

            # Get canvas dimensions
            cw, ch = canvas.get_size()

            # Calculate room size in pixels based on zoom
            room_px = int(BIGMAP_BASE * big_map_zoom)
            ox = big_map_pan_x
            oy = big_map_pan_y

            # Draw all discovered rooms
            for (wx, wy) in minimap_discovered:
                if (wx, wy) not in world:
                    continue

                r = world.get((wx, wy))
                # Calculate screen position
                screen_x = ox + (wx * room_px)
                screen_y = oy + (wy * room_px)

                # Only draw if on screen
                if screen_x + room_px < 0 or screen_x > cw or screen_y + room_px < 0 or screen_y > ch:
                    continue

                # Draw room background
                pygame.draw.rect(overlay, (40, 40, 40), (screen_x, screen_y, room_px, room_px))

                # Draw internal tiles
                mini_tile = max(1, room_px // room.ROOM_TILES)
                for tx in range(room.ROOM_TILES):
                    for ty in range(room.ROOM_TILES):
                        px_x = screen_x + tx * mini_tile
                        px_y = screen_y + ty * mini_tile
                        if (tx, ty) in r.walls:
                            col = (80, 80, 80)
                        else:
                            col = (120, 120, 120)
                        pygame.draw.rect(overlay, col, (px_x, px_y, mini_tile, mini_tile))

                # Draw doors
                mid = room.ROOM_TILES // 2
                door_thickness = max(1, mini_tile)
                for door in r.doors:
                    if door == 'U':
                        dx = screen_x + mid * mini_tile
                        dy = screen_y
                        pygame.draw.rect(overlay, (200, 200, 80), (dx, dy, mini_tile, door_thickness))
                    elif door == 'D':
                        dx = screen_x + mid * mini_tile
                        dy = screen_y + (room.ROOM_TILES-1) * mini_tile + (mini_tile - door_thickness)
                        pygame.draw.rect(overlay, (200, 200, 80), (dx, dy, mini_tile, door_thickness))
                    elif door == 'L':
                        dx = screen_x
                        dy = screen_y + mid * mini_tile
                        pygame.draw.rect(overlay, (200, 200, 80), (dx, dy, door_thickness, mini_tile))
                    elif door == 'R':
                        dx = screen_x + (room.ROOM_TILES-1) * mini_tile + (mini_tile - door_thickness)
                        dy = screen_y + mid * mini_tile
                        pygame.draw.rect(overlay, (200, 200, 80), (dx, dy, door_thickness, mini_tile))

                # Draw enemies
                for en in r.enemies:
                    if en.alive:
                        ex = screen_x + (en.x + 0.5) * mini_tile
                        ey = screen_y + (en.y + 0.5) * mini_tile
                        pygame.draw.circle(overlay, (220, 60, 60), (int(ex), int(ey)), max(2, mini_tile//2))

                # Draw exit (if present in this room)
                if r.is_exit:
                    ex, ey = r.exit_coords
                    exit_x = screen_x + (ex + 0.5) * mini_tile
                    exit_y = screen_y + (ey + 0.5) * mini_tile
                    # Draw exit as a bright cyan square
                    pygame.draw.rect(overlay, (0, 200, 200), (int(exit_x - mini_tile//2), int(exit_y - mini_tile//2), mini_tile, mini_tile))
                    pygame.draw.rect(overlay, (0, 255, 255), (int(exit_x - mini_tile//2), int(exit_y - mini_tile//2), mini_tile, mini_tile), 1)

            # Draw player marker on big map
            in_x = (player.x + 0.5) + (player.offset_x / max(1, room.TILE_SIZE))
            in_y = (player.y + 0.5) + (player.offset_y / max(1, room.TILE_SIZE))
            sub_px_x = int((in_x / room.ROOM_TILES) * room_px)
            sub_px_y = int((in_y / room.ROOM_TILES) * room_px)
            player_screen_x = ox + (room_x * room_px) + sub_px_x
            player_screen_y = oy + (room_y * room_px) + sub_px_y

            # Auto-recenter if just opened and player off-screen
            if big_map_just_opened:
                if player_screen_x < 0 or player_screen_x >= cw or player_screen_y < 0 or player_screen_y >= ch:
                    prx_world = (room_x * room_px) + sub_px_x
                    pry_world = (room_y * room_px) + sub_px_y
                    big_map_pan_x = cw//2 - prx_world
                    big_map_pan_y = ch//2 - pry_world
                    ox = big_map_pan_x
                    oy = big_map_pan_y
                    player_screen_x = ox + prx_world
                    player_screen_y = oy + pry_world
                big_map_just_opened = False

            # Draw player
            outline_thickness = max(1, room_px // 16)
            pygame.draw.circle(overlay, (0, 0, 0), (player_screen_x, player_screen_y), max(5, room_px//6 + outline_thickness))
            pygame.draw.circle(overlay, (160, 255, 160), (player_screen_x, player_screen_y), max(4, room_px//6))

            # Draw hint text
            hint = font.render("Big Map - Drag to pan, mouse wheel to zoom, press M to close", True, (220, 220, 220))
            overlay.blit(hint, (10, ch - 30))

            # Blit overlay onto canvas
            canvas.blit(overlay, (0, 0))

    elif state == STATE_COMBAT:
        # Draw combat screen
        canvas.fill((20, 20, 30))

        # Draw enemy
        cw, ch = canvas.get_size()
        ex, ey = cw // 2, ch // 4
        pygame.draw.circle(canvas, (200, 50, 50), (ex, ey), 40)

        # Enemy HP bar
        if current_enemy:
            hp_pct = current_enemy.hp / current_enemy.max_hp
            pygame.draw.rect(canvas, (100, 0, 0), (ex - 50, ey + 50, 100, 10))
            pygame.draw.rect(canvas, (0, 200, 0), (ex - 50, ey + 50, int(100 * hp_pct), 10))
            enemy_name = current_enemy.__class__.__name__
            draw_text(f"{enemy_name}", ex - 40, ey - 60)

        # Player HP
        draw_text(f"HP: {player.hp}/{player.max_hp}", 20, ch - 50)

        if combat_action == "menu":
            draw_text("What will you do?", cw // 2 - 80, ch // 2 - 50)
            draw_text("Attack", 100, ch // 2, selected == 0)
            draw_text("Item", 100, ch // 2 + 40, selected == 1)
            draw_text("Answer Question (HIGH RISK/REWARD)", 100, ch // 2 + 80, selected == 2)
        elif combat_action == "item_select":
            draw_text("Select Item to Use:", 100, ch // 2 - 80)
            # Draw player's consumable items
            consumable_items = []
            for item, ix, iy, iw, ih in player.inventory.iter_items():
                if isinstance(item, dict):
                    item_type = item.get('type', '')
                    if item_type in ['heal', 'buff_attack', 'buff_defense', 'stun']:
                        consumable_items.append((item, ix, iy))

            if consumable_items:
                for idx, (item, ix, iy) in enumerate(consumable_items[:5]):  # Show max 5 items
                    item_name = item.get('name', 'Item')
                    item_desc = item.get('description', '')
                    draw_text(f"{item_name} - {item_desc}", 100, ch // 2 - 30 + idx * 35, selected == idx)
                draw_text("Back", 100, ch // 2 - 30 + len(consumable_items[:5]) * 35, selected == len(consumable_items[:5]))
            else:
                draw_text("No consumable items!", 100, ch // 2 - 30)
                draw_text("Back", 100, ch // 2 + 10, selected == 0)
        elif combat_action == "attack_minigame":
            update_attack_minigame(keys)
            draw_attack_minigame()
        elif combat_action == "defend_minigame":
            update_defend_minigame(keys)
            draw_defend_minigame()
        elif combat_action == "question":
            if current_enemy and current_enemy.data:
                q_text = current_enemy.data.get("q", "Question?")
                draw_text(q_text, 50, ch // 2 - 80)
                options = current_enemy.data.get("options", [])
                for i, opt in enumerate(options):
                    draw_text(opt, 70, ch // 2 - 30 + i * 35, selected == i)

                # Draw feedback if available
                if combat_question_feedback:
                    if combat_question_feedback == "correct":
                        draw_text("CORRECT! +35 Damage! (HIGH REWARD!)", cw // 2 - 150, 50, True)
                    elif combat_question_feedback == "incorrect":
                        draw_text("WRONG! -15 Health! (HIGH RISK!)", cw // 2 - 150, 50, True)

    elif state == STATE_PAUSE:
        draw_text("PAUSED", cw // 2 - 50 if 'cw' in dir() else 100, 100)
        draw_text("Title Screen", 100, 150, selected == 0)
        draw_text("Exit", 100, 200, selected == 1)

    elif state == STATE_GAMEOVER:
        cw, ch = canvas.get_size()
        draw_text("GAME OVER", cw // 2 - 80, ch // 2 - 60)
        draw_text("Try Again", 100, ch // 2, selected == 0)
        draw_text("Title Screen", 100, ch // 2 + 40, selected == 1)
        draw_text("Exit", 100, ch // 2 + 80, selected == 2)

    elif state == STATE_WIN:
        cw, ch = canvas.get_size()
        draw_text("YOU WIN!", cw // 2 - 60, ch // 2 - 60)
        draw_text("New Game", 100, ch // 2, selected == 0)
        draw_text("Title Screen", 100, ch // 2 + 40, selected == 1)
        draw_text("Exit", 100, ch // 2 + 80, selected == 2)

    elif state == STATE_CHEAT:
        draw_text("CHEAT MENU", 100, 50)
        draw_text(f"Noclip: {'ON' if player.noclip else 'OFF'}", 100, 150, selected == 0)
        draw_text(f"Godmode: {'ON' if player.godmode else 'OFF'}", 100, 200, selected == 1)
        draw_text("Reveal Map", 100, 250, selected == 2)
        draw_text("Show Exit", 100, 300, selected == 3)
        draw_text("Back", 100, 350, selected == 4)

    # Draw chest modal if open (on top of gameplay)
    if state == STATE_OVERWORLD and chest_open and chest_grid is not None:
        # draw translucent backdrop
        overlay = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        canvas.blit(overlay, (0,0))
        sx, sy, slot_size, slot_gap, cmx, cmy = draw_chest_modal(chest_grid)

    # Draw dragged item under cursor if active
    if dragging_item is not None:
        mx, my = get_canvas_mouse_pos()
        # simple square preview
        pygame.draw.rect(canvas, (200,200,120), (mx-16, my-16, 32, 32))

    # Draw item tooltip if hovering over an item
    if hovered_item is not None and state == STATE_OVERWORLD:
        draw_item_tooltip(hovered_item, hovered_item_pos[0], hovered_item_pos[1])

    # scale/blit canvas to actual display surface
    try:
        scaled = pygame.transform.scale(canvas, screen.get_size())
        screen.blit(scaled, (0,0))
    except Exception:
        # fallback: if scaling fails, try blitting without scaling
        screen.blit(canvas, (0,0))

    draw_debug_info()  # Draw debug info last
    pygame.display.flip()
    clock.tick(60)

