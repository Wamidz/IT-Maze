import pygame
from room import TILE_SIZE

class Player:
    def __init__(self):
        self.x = 4
        self.y = 4
        self.offset_x = 0
        self.offset_y = 0
        self.speed = 8
        self.moving = False
        self.dir = (0, 0)

    def update(self, keys, room):
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

            nx = self.x + self.dir[0]
            ny = self.y + self.dir[1]
            if (nx, ny) not in room.walls:
                self.moving = True
        else:
            self.offset_x += self.dir[0] * self.speed
            self.offset_y += self.dir[1] * self.speed
            if abs(self.offset_x) >= TILE_SIZE or abs(self.offset_y) >= TILE_SIZE:
                self.x += self.dir[0]
                self.y += self.dir[1]
                self.offset_x = 0
                self.offset_y = 0
                self.moving = False

    def draw(self, screen):
        px = self.x * TILE_SIZE + TILE_SIZE // 2 + self.offset_x
        py = self.y * TILE_SIZE + TILE_SIZE // 2 + self.offset_y
        pygame.draw.circle(screen, (200, 160, 160), (px, py), TILE_SIZE // 3)
