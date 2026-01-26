import pygame
from inventory import InventoryGrid

# Default tile size (pixels) — can be changed at runtime with set_tile_size()
TILE_SIZE = 64
ROOM_TILES = 9

def set_tile_size(new_size: int):
    """Set the module-wide TILE_SIZE. Other modules should access room.TILE_SIZE
    (or call room.get_screen_size()) so changes are visible at runtime.
    """
    global TILE_SIZE
    TILE_SIZE = int(new_size)

def get_screen_size():
    return TILE_SIZE * ROOM_TILES

class Room:
    def __init__(self, doors=None, enemies=None):
        self.doors = doors if doors else []  # list of "U","D","L","R"
        self.enemies = enemies if enemies else []
        # loot boxes: list of (tx, ty, item_dict)
        self.loot_boxes = []
        # chests: list of dicts: {'x':tx, 'y':ty, 'grid': InventoryGrid}
        self.chests = []
        self.is_exit = False
        self.exit_coords = (4, 4) # Center by default
        self._wall_cache = None  # Cache for computed walls
        self._wall_rects_cache = None  # Cache for wall rects

    def _generate_walls(self):
        walls = set()
        size = ROOM_TILES
        mid = size // 2

        # Outer walls
        for i in range(size):
            walls.add((0, i))
            walls.add((size - 1, i))
            walls.add((i, 0))
            walls.add((i, size - 1))

        # Remove walls for doors
        if "U" in self.doors:
            walls.discard((mid, 0))
        if "D" in self.doors:
            walls.discard((mid, size - 1))
        if "L" in self.doors:
            walls.discard((0, mid))
        if "R" in self.doors:
            walls.discard((size - 1, mid))

        return walls

    @property
    def walls(self):
        # Return cached walls or compute if not cached
        if self._wall_cache is None:
            self._wall_cache = self._generate_walls()
        return self._wall_cache

    def get_wall_rects(self):
        """Return a list of pygame.Rect in pixel coordinates representing wall tiles.
        This lets collision be tested in pixel space so walls scale physically with TILE_SIZE.
        Results are cached for performance.
        """
        if self._wall_rects_cache is None:
            rects = []
            for x, y in self.walls:
                rects.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            self._wall_rects_cache = rects
        return self._wall_rects_cache

    def draw(self, screen):
        screen.fill((30, 30, 30))
        size = ROOM_TILES
        mid = size // 2

        # Draw walls
        for x, y in self.walls:
            pygame.draw.rect(
                screen,
                (60, 60, 60),
                (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            )

        # Highlight door positions visually
        for door in self.doors:
            if door == "U":
                pygame.draw.rect(screen, (100, 200, 100),
                                 (mid * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
            elif door == "D":
                pygame.draw.rect(screen, (100, 200, 100),
                                 (mid * TILE_SIZE, (size - 1) * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif door == "L":
                pygame.draw.rect(screen, (100, 200, 100),
                                 (0, mid * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif door == "R":
                pygame.draw.rect(screen, (100, 200, 100),
                                 ((size - 1) * TILE_SIZE, mid * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Draw exit if present
        if self.is_exit:
            ex, ey = self.exit_coords
            # Draw a blue portal/ladder
            pygame.draw.rect(screen, (0, 100, 255), (ex * TILE_SIZE + 10, ey * TILE_SIZE + 10, TILE_SIZE - 20, TILE_SIZE - 20))
            pygame.draw.rect(screen, (100, 200, 255), (ex * TILE_SIZE + 20, ey * TILE_SIZE + 20, TILE_SIZE - 40, TILE_SIZE - 40))
            # Draw "EXIT" text above it
            font = pygame.font.SysFont(None, 24)
            text = font.render("EXIT", True, (255, 255, 255))
            text_rect = text.get_rect(center=(ex * TILE_SIZE + TILE_SIZE // 2, ey * TILE_SIZE - 10))
            screen.blit(text, text_rect)

        # Draw enemies
        for e in self.enemies:
            if e.alive:
                e.draw(screen)

        # Draw chests (wooden brown with darker border)
        for c in self.chests:
            bx, by = c['x'], c['y']
            chest_w = TILE_SIZE * 2 // 3
            chest_x = bx * TILE_SIZE + (TILE_SIZE - chest_w) // 2
            chest_y = by * TILE_SIZE + (TILE_SIZE - chest_w) // 2
            pygame.draw.rect(screen, (139, 69, 19), (chest_x, chest_y, chest_w, chest_w))  # saddle brown
            pygame.draw.rect(screen, (100, 50, 20), (chest_x, chest_y, chest_w, chest_w), 2)

    def pickup_loot_at(self, tx, ty):
        """Remove and return item at tile coords tx,ty or None."""
        for i, (bx, by, item) in enumerate(self.loot_boxes):
            if bx == tx and by == ty:
                return self.loot_boxes.pop(i)[2]
        return None

    def add_chest(self, tx, ty, grid_width=4, grid_height=3):
        g = InventoryGrid(grid_width, grid_height)
        self.chests.append({'x': tx, 'y': ty, 'grid': g})
        return g

    def get_chest_at(self, tx, ty):
        for c in self.chests:
            if c['x'] == tx and c['y'] == ty:
                return c['grid']
        return None

    def invalidate_cache(self):
        """Invalidate wall cache when room configuration changes."""
        self._wall_cache = None
        self._wall_rects_cache = None

