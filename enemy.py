import pygame
from room import TILE_SIZE

class Enemy:
    def __init__(self, x, y, question=None):
        self.x = x
        self.y = y
        self.offset_x = 0
        self.offset_y = 0
        # Lower speed so enemies move noticeably slower than the player
        self.speed = 2
        self.alive = True
        self.data = question

    def update(self, player, room):
        if not self.alive:
            return

        dx = player.x - self.x
        dy = player.y - self.y

        move_x = 1 if dx > 0 else -1 if dx < 0 else 0
        move_y = 1 if dy > 0 else -1 if dy < 0 else 0

        # Future offsets
        next_offset_x = self.offset_x + move_x * self.speed
        next_offset_y = self.offset_y + move_y * self.speed

        # Check X movement
        future_tile_x = self.x + (1 if next_offset_x > 0 else -1 if next_offset_x < 0 else 0)
        if (future_tile_x, self.y) not in room.walls:
            self.offset_x = next_offset_x
            if abs(self.offset_x) >= TILE_SIZE:
                self.x += 1 if self.offset_x > 0 else -1
                self.offset_x = 0

        # Check Y movement
        future_tile_y = self.y + (1 if next_offset_y > 0 else -1 if next_offset_y < 0 else 0)
        if (self.x, future_tile_y) not in room.walls:
            self.offset_y = next_offset_y
            if abs(self.offset_y) >= TILE_SIZE:
                self.y += 1 if self.offset_y > 0 else -1
                self.offset_y = 0

    def draw(self, screen):
        px = self.x * TILE_SIZE + TILE_SIZE // 2 + self.offset_x
        py = self.y * TILE_SIZE + TILE_SIZE // 2 + self.offset_y
        pygame.draw.circle(screen, (160, 0, 160), (px, py), TILE_SIZE // 3)
