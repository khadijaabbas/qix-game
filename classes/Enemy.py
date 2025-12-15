import pygame
import math

class Enemy:
    def __init__(self, x, y, color, size=5):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.speed = 2
        
    def get_position(self):
        return (self.x, self.y)
    
    def distance_to(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
    
    def check_collision(self, x, y, threshold=10):
        return self.distance_to(x, y) < threshold
    
    def update(self, world):
        pass
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
