import pygame

TILE_SIZE = 64
ROOM_TILES = 9
SCREEN_SIZE = TILE_SIZE * ROOM_TILES

class Room:
    def __init__(self, doors=None, enemies=None):
        self.doors = doors if doors else []  # list of "U","D","L","R"
        self.enemies = enemies if enemies else []
        # walls are computed dynamically from current doors so that
        # modifying `self.doors` (via append or assignment) immediately
        # affects collision checks. Access via the `walls` property below.

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
        # Compute on access to reflect current door state
        return self._generate_walls()

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

        # Draw enemies
        for e in self.enemies:
            if e.alive:
                e.draw(screen)
