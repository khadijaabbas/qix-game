import pygame
import random
from .Enemy import Enemy

class Qix(Enemy):
    def __init__(self, x, y, world):
        super().__init__(x, y, (255, 0, 0), size=8)
        self.world = world
        self.speed = 1.5
        self.target = None
        self.target_timer = 0
        self.min_target_time = 45
        self.max_target_time = 120
    
    def update(self, world=None):
        if not self.world:
            return
        
        self.target_timer -= 1
        if self.target is None or self.target_timer <= 0 or self._at_target():
            self._choose_new_target()
        
        if not self.target:
            return
        
        dir_x = self.target[0] - self.x
        dir_y = self.target[1] - self.y
        distance = (dir_x ** 2 + dir_y ** 2) ** 0.5
        if distance < 0.1:
            self._choose_new_target()
            return
        
        dir_x /= max(distance, 1e-6)
        dir_y /= max(distance, 1e-6)
        
        new_x = self.x + dir_x * self.speed
        new_y = self.y + dir_y * self.speed
        
        if self.world.is_point_in_unclaimed_area(new_x, new_y):
            self.x = new_x
            self.y = new_y
        else:
            self._choose_new_target()
    
    def draw(self, screen):
        points = []
        for i in range(6):
            angle = i * 60 * 3.14159 / 180
            px = self.x + self.size * 1.5 * pygame.math.Vector2(1, 0).rotate_rad(angle).x
            py = self.y + self.size * 1.5 * pygame.math.Vector2(1, 0).rotate_rad(angle).y
            points.append((px, py))
        
        if len(points) > 2:
            pygame.draw.polygon(screen, self.color, points)
        else:
            super().draw(screen)
    
    def reset_motion(self):
        self.target = None
        self.target_timer = random.randint(self.min_target_time, self.max_target_time)
    
    def _choose_new_target(self):
        attempts = 0
        max_attempts = 50
        target = None
        while attempts < max_attempts:
            tx = random.uniform(self.world.x + 10, self.world.x + self.world.width - 10)
            ty = random.uniform(self.world.y + 10, self.world.y + self.world.height - 10)
            if self.world.is_point_in_unclaimed_area(tx, ty):
                target = (tx, ty)
                break
            attempts += 1
        self.target = target
        self.target_timer = random.randint(self.min_target_time, self.max_target_time)
    
    def _at_target(self):
        if not self.target:
            return True
        return abs(self.x - self.target[0]) < 5 and abs(self.y - self.target[1]) < 5
