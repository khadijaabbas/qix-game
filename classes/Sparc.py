import pygame
from .Enemy import Enemy

class Sparc(Enemy):
    def __init__(self, x, y, world, direction=1):
        super().__init__(x, y, (255, 165, 0), size=5)
        self.world = world
        self.speed = 1.5
        self.boundary_version = world.boundary_version
        self.path_distance = 0.0
        self.perimeter_total = 1.0
        self.edge_lengths = []
        self.cumulative_lengths = []
        self.edges_cache_version = None
        
        self.current_edge_index = 0
        self.base_direction = 1 if direction >= 0 else -1
        self.direction = self.base_direction
        self.t = 0.0
        self._attach_to_edge(self.x, self.y)

    def _attach_to_edge(self, target_x, target_y):
        """Keep Sparc aligned with the world perimeter."""
        edges = self.world.get_boundary_edges()
        if not edges:
            self.x = target_x
            self.y = target_y
            self.current_edge_index = 0
            self.t = 0.0
            return
        
        best_index = 0
        best_t = 0.0
        best_dist = float("inf")
        best_pos = (target_x, target_y)
        
        for idx, (x1, y1, x2, y2) in enumerate(edges):
            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx * dx + dy * dy
            if length_sq == 0:
                continue
            
            t = 0.0
            if length_sq > 0:
                t = ((target_x - x1) * dx + (target_y - y1) * dy) / length_sq
            t = max(0.0, min(0.999, t))
            
            proj_x = x1 + dx * t
            proj_y = y1 + dy * t
            dist_sq = (proj_x - target_x) ** 2 + (proj_y - target_y) ** 2
            
            if dist_sq < best_dist:
                best_dist = dist_sq
                best_index = idx
                best_t = t
                best_pos = (proj_x, proj_y)
        
        self._ensure_edge_cache(edges)
        self.current_edge_index = best_index
        self.t = max(0.0, min(0.999, best_t))
        self.x, self.y = best_pos
        edge_length = self.edge_lengths[best_index] if self.edge_lengths else 0.0
        self.path_distance = self.cumulative_lengths[best_index] + self.t * edge_length
        self.direction = self.base_direction
        self.boundary_version = self.world.boundary_version
    
    def update(self, world=None):
        edges = self.world.get_boundary_edges()
        if not edges:
            return
        
        if self.boundary_version != self.world.boundary_version:
            self._attach_to_edge(self.x, self.y)
            edges = self.world.get_boundary_edges()
            if not edges:
                return
        
        self._ensure_edge_cache(edges)
        if not self.edge_lengths:
            return
        
        self.direction = self.base_direction
        self.path_distance = (self.path_distance + self.speed * self.direction) % self.perimeter_total
        
        self._update_position_from_distance(edges)
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(screen, (255, 200, 100), (int(self.x), int(self.y)), self.size - 2)

    def _ensure_edge_cache(self, edges):
        if self.edges_cache_version == self.world.boundary_version and self.edge_lengths:
            return
        
        self.edge_lengths = []
        self.cumulative_lengths = [0.0]
        total = 0.0
        for x1, y1, x2, y2 in edges:
            length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            self.edge_lengths.append(length)
            total += length
            self.cumulative_lengths.append(total)
        
        self.perimeter_total = max(total, 1.0)
        self.edges_cache_version = self.world.boundary_version
    
    def _update_position_from_distance(self, edges):
        distance = self.path_distance % self.perimeter_total
        edge_index = 0
        for i in range(len(self.edge_lengths)):
            start = self.cumulative_lengths[i]
            end = self.cumulative_lengths[i + 1]
            if start <= distance < end or (i == len(self.edge_lengths) - 1 and distance == end):
                edge_index = i
                break
        
        edge_length = self.edge_lengths[edge_index] or 1.0
        offset = distance - self.cumulative_lengths[edge_index]
        t = max(0.0, min(1.0, offset / edge_length))
        
        x1, y1, x2, y2 = edges[edge_index]
        self.current_edge_index = edge_index
        self.t = t
        self.x = x1 + (x2 - x1) * t
        self.y = y1 + (y2 - y1) * t
