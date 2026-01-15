import pygame
import room

class Enemy:
    def __init__(self, x, y, question=None):
        self.x = x
        self.y = y
        self.offset_x = 0
        self.offset_y = 0
        # alive and data
        self.alive = True
        self.data = question
        # Basic combat stats
        self.max_hp = 50
        self.hp = self.max_hp

    def apply_damage(self, amount: int):
        self.hp = max(0, self.hp - int(amount))
        if self.hp == 0:
            self.alive = False

    def _enemy_rect(self, off_x=None, off_y=None):
        size = room.TILE_SIZE
        ox = self.offset_x if off_x is None else off_x
        oy = self.offset_y if off_y is None else off_y
        px = self.x * size + size // 2 + ox
        py = self.y * size + size // 2 + oy
        r = pygame.Rect(0, 0, size//2, size//2)
        r.center = (px, py)
        return r

    def update(self, player, room_obj, others=None):
        if not self.alive:
            return

        # compute speed relative to current tile size so scaling affects movement
        speed = max(1, room.TILE_SIZE // 24)

        dx = player.x - self.x
        dy = player.y - self.y

        move_x = 1 if dx > 0 else -1 if dx < 0 else 0
        move_y = 1 if dy > 0 else -1 if dy < 0 else 0

        size = room.TILE_SIZE

        # Attempt X movement separately
        if move_x != 0:
            next_offset_x = self.offset_x + move_x * speed
            rect_x = self._enemy_rect(off_x=next_offset_x, off_y=self.offset_y)

            blocked_x = False
            for w in room_obj.get_wall_rects():
                if rect_x.colliderect(w):
                    blocked_x = True
                    break
            if not blocked_x and others:
                for other in others:
                    if other is self or not getattr(other, 'alive', False):
                        continue
                    if rect_x.colliderect(other._enemy_rect()):
                        blocked_x = True
                        break

            if not blocked_x:
                self.offset_x = next_offset_x
                # finalize X crossing
                if abs(self.offset_x) >= size:
                    dx_tile = 1 if self.offset_x > 0 else -1
                    self.x += dx_tile
                    self.offset_x = 0

        # Attempt Y movement separately
        if move_y != 0:
            next_offset_y = self.offset_y + move_y * speed
            rect_y = self._enemy_rect(off_x=self.offset_x, off_y=next_offset_y)

            blocked_y = False
            for w in room_obj.get_wall_rects():
                if rect_y.colliderect(w):
                    blocked_y = True
                    break
            if not blocked_y and others:
                for other in others:
                    if other is self or not getattr(other, 'alive', False):
                        continue
                    if rect_y.colliderect(other._enemy_rect()):
                        blocked_y = True
                        break

            if not blocked_y:
                self.offset_y = next_offset_y
                # finalize Y crossing
                if abs(self.offset_y) >= size:
                    dy_tile = 1 if self.offset_y > 0 else -1
                    self.y += dy_tile
                    self.offset_y = 0

    def draw(self, screen):
        size = room.TILE_SIZE
        px = self.x * size + size // 2 + self.offset_x
        py = self.y * size + size // 2 + self.offset_y
        pygame.draw.circle(screen, (160, 0, 160), (px, py), size // 3)
