import pygame
import room

class Player:
    def __init__(self):
        self.x = 4
        self.y = 4
        self.offset_x = 0
        self.offset_y = 0
        self.moving = False
        self.dir = (0, 0)

    def _player_rect(self):
        size = room.TILE_SIZE
        px = self.x * size + size // 2 + self.offset_x
        py = self.y * size + size // 2 + self.offset_y
        r = pygame.Rect(0, 0, size//2, size//2)
        r.center = (px, py)
        return r

    def update(self, keys, room_obj):
        # compute speed from current tile size so scaling applies immediately
        speed = max(4, room.TILE_SIZE // 8)

        if not self.moving:
            if keys["up"]:
                self.dir = (0, -1)
            elif keys["down"]:
                self.dir = (0, 1)
            elif keys["left"]:
                self.dir = (-1, 0)
            elif keys["right"]:
                self.dir = (1, 0)
            else:
                return

            # attempt to start movement: check target tile isn't blocked (tile coords)
            nx = self.x + self.dir[0]
            ny = self.y + self.dir[1]
            if (nx, ny) not in room_obj.walls:
                self.moving = True
        else:
            # simulate pixel movement and detect collisions against wall rects
            next_offset_x = self.offset_x + self.dir[0] * speed
            next_offset_y = self.offset_y + self.dir[1] * speed

            # build tentative rect
            size = room.TILE_SIZE
            px = self.x * size + size // 2 + next_offset_x
            py = self.y * size + size // 2 + next_offset_y
            rect = pygame.Rect(0, 0, size//2, size//2)
            rect.center = (px, py)

            blocked = False
            for w in room_obj.get_wall_rects():
                if rect.colliderect(w):
                    blocked = True
                    break

            if not blocked:
                self.offset_x = next_offset_x
                self.offset_y = next_offset_y

            # finalize tile crossing
            if abs(self.offset_x) >= size or abs(self.offset_y) >= size:
                self.x += self.dir[0]
                self.y += self.dir[1]
                # adjust offsets (in case of overshoot)
                self.offset_x = 0
                self.offset_y = 0
                self.moving = False

    def draw(self, screen):
        size = room.TILE_SIZE
        px = self.x * size + size // 2 + self.offset_x
        py = self.y * size + size // 2 + self.offset_y
        pygame.draw.circle(screen, (200, 160, 160), (px, py), size // 3)
