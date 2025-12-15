import pygame
from collections import deque

class World:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = int(width)
        self.height = int(height)
        
        self.claim_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.claim_surface.fill((0, 0, 0, 0))
        self.claimed_grid = [bytearray(self.width) for _ in range(self.height)]
        self.blocked_grid = [bytearray(self.width) for _ in range(self.height)]
        self.claimed_area = 0
        self.boundary_path = []
        self.boundary_edges = []
        self.boundary_version = 0
        self.incursion_warning = False
        self._initialize_boundary()
        
        self.current_incursion = []
        
    def _initialize_boundary(self):
        self.boundary_path = [
            (self.x, self.y),
            (self.x + self.width, self.y),
            (self.x + self.width, self.y + self.height),
            (self.x, self.y + self.height)
        ]
        self._update_boundary_edges()
    
    def _update_boundary_edges(self):
        self.boundary_edges = []
        for i in range(len(self.boundary_path)):
            x1, y1 = self.boundary_path[i]
            x2, y2 = self.boundary_path[(i + 1) % len(self.boundary_path)]
            self.boundary_edges.append((x1, y1, x2, y2))
        self.boundary_version += 1
        
    def get_boundary_edges(self):
        return self.boundary_edges
    
    def set_incursion_warning(self, active):
        self.incursion_warning = active
    
    def _to_local_coords(self, x, y):
        lx = int(round(x - self.x))
        ly = int(round(y - self.y))
        lx = max(0, min(self.width - 1, lx))
        ly = max(0, min(self.height - 1, ly))
        return lx, ly
    
    def is_point_on_edge(self, x, y, tolerance=3):
        for edge in self.boundary_edges:
            x1, y1, x2, y2 = edge
            
            if abs(x1 - x2) < 1:
                if abs(x - x1) < tolerance and min(y1, y2) <= y <= max(y1, y2):
                    return True
            elif abs(y1 - y2) < 1:
                if abs(y - y1) < tolerance and min(x1, x2) <= x <= max(x1, x2):
                    return True
            else:
                dist_to_line = abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1) / ((y2-y1)**2 + (x2-x1)**2)**0.5
                if dist_to_line < tolerance:
                    if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
                        return True
        return False
    
    def snap_to_edge(self, x, y):
        closest_point = (x, y)
        best_dist = float("inf")
        for x1, y1, x2, y2 in self.boundary_edges:
            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx * dx + dy * dy
            if length_sq == 0:
                continue
            t = ((x - x1) * dx + (y - y1) * dy) / length_sq
            t = max(0.0, min(1.0, t))
            proj_x = x1 + dx * t
            proj_y = y1 + dy * t
            dist_sq = (proj_x - x) ** 2 + (proj_y - y) ** 2
            if dist_sq < best_dist:
                best_dist = dist_sq
                closest_point = (proj_x, proj_y)
        return closest_point
    
    def is_point_in_unclaimed_area(self, x, y):
        if not self.is_point_within_bounds(x, y):
            return False
        
        if self.is_point_on_edge(x, y):
            return False

        local_x, local_y = self._to_local_coords(x, y)
        if self.blocked_grid[local_y][local_x]:
            return False
        return True

    def is_point_within_bounds(self, x, y):
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def is_point_claimed(self, x, y):
        if not self.is_point_within_bounds(x, y):
            return False
        local_x, local_y = self._to_local_coords(x, y)
        return bool(self.claimed_grid[local_y][local_x])
    
    def start_incursion(self, x, y):
        snapped = self.snap_to_edge(x, y)
        self.current_incursion = [snapped]
    
    def add_to_incursion(self, x, y):
        self.current_incursion.append((x, y))
    
    def cancel_incursion(self):
        start_pos = None
        if self.current_incursion:
            start_pos = self.current_incursion[0]
        self.current_incursion = []
        return start_pos
    
    def complete_incursion(self, qix_pos=None):
        if len(self.current_incursion) < 2 or not qix_pos:
            self.current_incursion = []
            return False
        
        end_x, end_y = self.current_incursion[-1]
        if not self.is_point_on_edge(end_x, end_y):
            self.current_incursion = []
            return False
        
        area_claimed = self._claim_enclosed_area(qix_pos)
        if not area_claimed:
            self.current_incursion = []
            return False

        self._mark_incursion_path_claimed()
        self._rebuild_boundary_from_incursion(qix_pos)
        
        self.current_incursion = []
        return True
    
    def get_claimed_percentage(self):
        total_area = self.width * self.height
        return (self.claimed_area / total_area) * 100 if total_area > 0 else 0
    
    def get_current_incursion(self):
        return self.current_incursion
    
    def check_incursion_collision(self, x, y, threshold=10, skip_tail_segments=0):
        if len(self.current_incursion) < 2:
            return False

        segment_limit = len(self.current_incursion) - 1 - max(0, skip_tail_segments)
        if segment_limit <= 0:
            return False

        for i in range(segment_limit):
            x1, y1 = self.current_incursion[i]
            x2, y2 = self.current_incursion[i + 1]
            
            line_length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            if line_length < 0.1:
                continue
            
            dot = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / (line_length ** 2)
            dot = max(0, min(1, dot))
            
            closest_x = x1 + dot * (x2 - x1)
            closest_y = y1 + dot * (y2 - y1)
            
            distance = ((x - closest_x) ** 2 + (y - closest_y) ** 2) ** 0.5
            if distance < threshold:
                return True
        
        return False
    
    def _claim_enclosed_area(self, qix_pos):
        blocked = [bytearray(row) for row in self.claimed_grid]
        
        for x1, y1, x2, y2 in self.boundary_edges:
            lx1, ly1 = self._to_local_coords(x1, y1)
            lx2, ly2 = self._to_local_coords(x2, y2)
            self._mark_line_on_grid(blocked, lx1, ly1, lx2, ly2)
        
        for i in range(len(self.current_incursion) - 1):
            x1, y1 = self.current_incursion[i]
            x2, y2 = self.current_incursion[i + 1]
            lx1, ly1 = self._to_local_coords(x1, y1)
            lx2, ly2 = self._to_local_coords(x2, y2)
            self._mark_line_on_grid(blocked, lx1, ly1, lx2, ly2)
        
        qx, qy = self._to_local_coords(*qix_pos)
        if blocked[qy][qx]:
            return False
        
        visited = self._flood_fill(blocked, qx, qy)
        new_cells = []
        for y in range(self.height):
            blocked_row = blocked[y]
            visited_row = visited[y]
            for x in range(self.width):
                if not blocked_row[x] and not visited_row[x]:
                    new_cells.append((x, y))
        
        if not new_cells:
            return False
        
        self._fill_claimed_cells(new_cells)
        return True
    
    def _mark_line_on_grid(self, grid, x1, y1, x2, y2):
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        x, y = x1, y1
        
        while True:
            if 0 <= x < self.width and 0 <= y < self.height:
                grid[y][x] = 1
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
    
    def _flood_fill(self, blocked, start_x, start_y):
        visited = [bytearray(self.width) for _ in range(self.height)]
        queue = deque()
        
        queue.append((start_x, start_y))
        visited[start_y][start_x] = 1
        
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if not blocked[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = 1
                        queue.append((nx, ny))
        return visited
    
    def _fill_claimed_cells(self, cells):
        rows = {}
        for x, y in cells:
            if self.claimed_grid[y][x]:
                continue
            rows.setdefault(y, []).append(x)
        
        if not rows:
            return
        
        color = (100, 100, 150)
        for y, xs in rows.items():
            xs.sort()
            self.claimed_area += len(xs)
            for x in xs:
                self.claimed_grid[y][x] = 1
            start = xs[0]
            prev = xs[0]
            for x in xs[1:]:
                if x == prev + 1:
                    prev = x
                else:
                    self._draw_claim_rect(color, start, y, prev - start + 1, 1)
                    start = x
                    prev = x
            self._draw_claim_rect(color, start, y, prev - start + 1, 1)

    def _mark_incursion_path_claimed(self):
        if len(self.current_incursion) < 2:
            return
        color = (100, 100, 150)
        for i in range(len(self.current_incursion) - 1):
            x1, y1 = self.current_incursion[i]
            x2, y2 = self.current_incursion[i + 1]
            lx1, ly1 = self._to_local_coords(x1, y1)
            lx2, ly2 = self._to_local_coords(x2, y2)
            self._draw_claim_line(color, lx1, ly1, lx2, ly2)

    def _draw_claim_rect(self, color, x, y, width, height, padding=1):
        pad_x1 = max(0, x - padding)
        pad_y1 = max(0, y - padding)
        pad_x2 = min(self.width, x + width + padding)
        pad_y2 = min(self.height, y + height + padding)
        rect_width = max(1, pad_x2 - pad_x1)
        rect_height = max(1, pad_y2 - pad_y1)
        pygame.draw.rect(self.claim_surface, color, (pad_x1, pad_y1, rect_width, rect_height))
        self._mark_block_rect(pad_x1, pad_y1, pad_x2 - 1, pad_y2 - 1)

    def _draw_claim_line(self, color, x1, y1, x2, y2, padding=1):
        pygame.draw.line(self.claim_surface, color, (x1, y1), (x2, y2), width=padding * 2 + 1)
        self._block_line(x1, y1, x2, y2, padding)

    def _block_line(self, x1, y1, x2, y2, padding=1):
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        x, y = x1, y1
        while True:
            self._mark_block_point(x, y, padding)
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def _mark_block_rect(self, x1, y1, x2, y2):
        x1 = max(0, min(self.width - 1, int(x1)))
        y1 = max(0, min(self.height - 1, int(y1)))
        x2 = max(0, min(self.width - 1, int(x2)))
        y2 = max(0, min(self.height - 1, int(y2)))
        if x2 < x1 or y2 < y1:
            return
        for y in range(y1, y2 + 1):
            row = self.blocked_grid[y]
            for x in range(x1, x2 + 1):
                row[x] = 1

    def _mark_block_point(self, x, y, padding=0):
        for py in range(y - padding, y + padding + 1):
            if 0 <= py < self.height:
                row = self.blocked_grid[py]
                for px in range(x - padding, x + padding + 1):
                    if 0 <= px < self.width:
                        row[px] = 1
    
    def _rebuild_boundary_from_incursion(self, qix_pos):
        if not self.current_incursion:
            return
        
        start_point = self.current_incursion[0]
        end_point = self.current_incursion[-1]
        
        self._ensure_boundary_point(start_point)
        self._ensure_boundary_point(end_point)
        
        start_idx = self._find_point_index(start_point)
        end_idx = self._find_point_index(end_point)
        if start_idx == -1 or end_idx == -1 or len(self.boundary_path) < 2:
            return
        
        arc1 = self._build_arc(start_idx, end_idx)
        arc2 = self._build_arc(end_idx, start_idx)
        
        if len(self.current_incursion) < 2:
            return
        
        forward_inc = self.current_incursion[1:]
        reverse_inc = list(reversed(self.current_incursion))[1:]
        
        poly1 = arc1 + reverse_inc
        poly2 = arc2 + forward_inc
        
        if not poly1 or not poly2:
            return
        
        if self._point_inside_polygon(qix_pos, poly1):
            new_path = poly1
        else:
            new_path = poly2
        
        self.boundary_path = self._simplify_path(new_path)
        self._update_boundary_edges()
    
    def _ensure_boundary_point(self, point):
        idx = self._find_point_index(point)
        if idx != -1:
            return idx
        px, py = point
        for i in range(len(self.boundary_path)):
            x1, y1 = self.boundary_path[i]
            x2, y2 = self.boundary_path[(i + 1) % len(self.boundary_path)]
            if self._is_point_on_segment(px, py, x1, y1, x2, y2):
                insert_idx = i + 1
                self.boundary_path.insert(insert_idx, point)
                return insert_idx
        return -1
    
    def _find_point_index(self, point):
        px, py = point
        for idx, (x, y) in enumerate(self.boundary_path):
            if abs(x - px) < 0.1 and abs(y - py) < 0.1:
                return idx
        return -1
    
    def _is_point_on_segment(self, px, py, x1, y1, x2, y2, tolerance=0.1):
        if min(x1, x2) - tolerance <= px <= max(x1, x2) + tolerance and \
           min(y1, y2) - tolerance <= py <= max(y1, y2) + tolerance:
            cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
            if abs(cross) > tolerance * max(1.0, abs(x2 - x1) + abs(y2 - y1)):
                return False
            dot = (px - x1) * (px - x2) + (py - y1) * (py - y2)
            return dot <= tolerance
        return False
    
    def _build_arc(self, start_idx, end_idx):
        arc = []
        idx = start_idx
        while True:
            arc.append(self.boundary_path[idx])
            if idx == end_idx:
                break
            idx = (idx + 1) % len(self.boundary_path)
        return arc
    
    def _point_inside_polygon(self, point, polygon):
        x, y = point
        inside = False
        n = len(polygon)
        if n < 3:
            return False
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            if self._is_point_on_segment(x, y, x1, y1, x2, y2, tolerance=0.5):
                return True
            if ((y1 > y) != (y2 > y)):
                xinters = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
                if x < xinters:
                    inside = not inside
        return inside
    
    def _simplify_path(self, path):
        simplified = []
        for point in path:
            if not simplified or (abs(simplified[-1][0] - point[0]) >= 0.1 or abs(simplified[-1][1] - point[1]) >= 0.1):
                simplified.append(point)
        if len(simplified) > 1 and abs(simplified[0][0] - simplified[-1][0]) < 0.1 and abs(simplified[0][1] - simplified[-1][1]) < 0.1:
            simplified.pop()
        return simplified
    
    def draw(self, screen):
        pygame.draw.rect(screen, (0, 0, 0), (self.x, self.y, self.width, self.height))
        
        screen.blit(self.claim_surface, (self.x, self.y))
        
        for edge in self.boundary_edges:
            x1, y1, x2, y2 = edge
            pygame.draw.line(screen, (0, 255, 0), (x1, y1), (x2, y2), 2)
        
        if len(self.current_incursion) > 1:
            blink = (pygame.time.get_ticks() // 150) % 2 == 0
            color = (255, 0, 0) if self.incursion_warning and blink else (255, 255, 0)
            pygame.draw.lines(screen, color, False, self.current_incursion, 2)
