import pygame

class Player:
    def __init__(self, x, y, world):
        self.x = x
        self.y = y
        self.world = world
        self.size = 6
        self.color = (0, 255, 0)
        self.hit_color = (255, 165, 0)
        self.hit_flash_end_time = 0
        self.invulnerable_end_time = 0
        self.speed = 3
        self.lives = 3
        
        self.is_pushing = False
        self.push_start_pos = None
        self.last_edge_pos = (x, y)
        self.push_dir = None
        self.last_push_move_time = 0
        self.push_idle_timeout = 1500
        self.push_warning_delay = 0
        self.edge_axis = self._detect_edge_axis(x, y, default="horizontal")

    def move(self, dx, dy, qix_pos=None):
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed
        move_dir = self._normalize_direction(dx, dy)

        if self.is_pushing:
            if move_dir == (0, 0):
                return False
            on_edge_current = self.world.is_point_on_edge(self.x, self.y)
            on_edge_new = self.world.is_point_on_edge(new_x, new_y)

            if on_edge_current and on_edge_new:
                if self._is_departing_edge(move_dir):
                    on_edge_new = False
                else:
                    return False

            if on_edge_new and self.world.is_point_within_bounds(new_x, new_y):
                if not self._validate_push_direction(move_dir):
                    return False
                self.x, self.y = self.world.snap_to_edge(new_x, new_y)
                self.world.add_to_incursion(self.x, self.y)
                self._record_push_movement()
                self._update_edge_axis_from_position(self.x, self.y)
                self.complete_incursion(qix_pos)
                return True
            elif self._can_extend_incursion_trace(new_x, new_y):
                if self.world.check_incursion_collision(
                    new_x, new_y, threshold=self.speed + 1, skip_tail_segments=1
                ):
                    self._fail_current_incursion()
                    return False
                if not self._validate_push_direction(move_dir):
                    return False
                self.x = new_x
                self.y = new_y
                self.world.add_to_incursion(self.x, self.y)
                self._record_push_movement()
                return True
            return False
        else:
            if self.world.is_point_on_edge(new_x, new_y) and self.world.is_point_within_bounds(new_x, new_y):
                self.x, self.y = self.world.snap_to_edge(new_x, new_y)
                self.last_edge_pos = (self.x, self.y)
                self.push_dir = None
                self._update_edge_axis_from_position(self.x, self.y)
                return True
            return False
    
    def start_push(self):
        if self.is_invulnerable():
            return
        if not self.is_pushing and self.world.is_point_on_edge(self.x, self.y) and \
           self.world.is_point_within_bounds(self.x, self.y):
            self.x, self.y = self.world.snap_to_edge(self.x, self.y)
            self.is_pushing = True
            self.push_start_pos = (self.x, self.y)
            self.world.start_incursion(self.x, self.y)
            self.push_dir = None
            self.last_push_move_time = pygame.time.get_ticks()
            self.world.set_incursion_warning(False)
            self._update_edge_axis_from_position(self.x, self.y)

    def complete_incursion(self, qix_pos=None):
        if self.is_pushing:
            success = self.world.complete_incursion(qix_pos)
            self.is_pushing = False
            self.push_start_pos = None
            self.last_edge_pos = (self.x, self.y)
            self.push_dir = None
            self.world.set_incursion_warning(False)
            self._update_edge_axis_from_position(self.x, self.y)
            return success
        return False
    
    def cancel_push(self):
        if self.is_pushing:
            start_pos = self.world.cancel_incursion()
            if start_pos:
                self.x, self.y = start_pos
                self.last_edge_pos = start_pos
                self._update_edge_axis_from_position(*start_pos)
            self.is_pushing = False
            self.push_start_pos = None
            self.lose_life()
            self.push_dir = None
            self.world.set_incursion_warning(False)
    
    def lose_life(self):
        now = pygame.time.get_ticks()
        if now < self.invulnerable_end_time:
            return False
        self.lives -= 1
        self.hit_flash_end_time = now + 400
        self.invulnerable_end_time = now + 800
        return True
    
    def get_position(self):
        return (self.x, self.y)
    
    def is_alive(self):
        return self.lives > 0
    
    def is_invulnerable(self):
        return pygame.time.get_ticks() < self.invulnerable_end_time
    
    def reset_position(self):
        self.x, self.y = self.last_edge_pos
        if self.is_pushing:
            self.cancel_push()
        self.push_dir = None
        self._update_edge_axis_from_position(self.x, self.y)
    
    def draw(self, screen):
        current_time = pygame.time.get_ticks()
        draw_color = self.hit_color if current_time < self.hit_flash_end_time else self.color
        pygame.draw.circle(screen, draw_color, (int(self.x), int(self.y)), self.size)
        
        if self.is_pushing and self.push_start_pos:
            pygame.draw.circle(screen, (255, 200, 0), 
                             (int(self.push_start_pos[0]), int(self.push_start_pos[1])), 4)

    def check_push_idle(self, current_time=None):
        if not self.is_pushing:
            self.world.set_incursion_warning(False)
            return False
        now = pygame.time.get_ticks() if current_time is None else current_time
        idle_time = now - self.last_push_move_time
        if idle_time >= self.push_idle_timeout:
            self._handle_idle_failure()
            return True
        if idle_time >= self.push_warning_delay:
            self.world.set_incursion_warning(True)
        else:
            self.world.set_incursion_warning(False)
        return False
    
    def _validate_push_direction(self, move_dir):
        if move_dir == (0, 0):
            return False
        if self.push_dir is None:
            self.push_dir = move_dir
            return True
        opposite = (-self.push_dir[0], -self.push_dir[1])
        if move_dir == opposite:
            return False
        if move_dir != self.push_dir:
            self.push_dir = move_dir
        return True
    
    def _record_push_movement(self):
        self.last_push_move_time = pygame.time.get_ticks()
        self.world.set_incursion_warning(False)
    
    def _handle_idle_failure(self):
        self._fail_current_incursion()
    
    def _normalize_direction(self, dx, dy):
        if dx != 0:
            return (1 if dx > 0 else -1, 0)
        if dy != 0:
            return (0, 1 if dy > 0 else -1)
        return (0, 0)

    def _update_edge_axis_from_position(self, x, y):
        axis = self._detect_edge_axis(x, y, default=self.edge_axis)
        if axis:
            self.edge_axis = axis

    def _detect_edge_axis(self, x, y, tolerance=4, default=None):
        world = self.world
        top = abs(y - world.y) <= tolerance
        bottom = abs(y - (world.y + world.height)) <= tolerance
        left = abs(x - world.x) <= tolerance
        right = abs(x - (world.x + world.width)) <= tolerance

        horizontal = top or bottom
        vertical = left or right

        if horizontal and not vertical:
            return "horizontal"
        if vertical and not horizontal:
            return "vertical"
        if horizontal and vertical:
            return default or "horizontal"
        return default

    def _is_departing_edge(self, move_dir):
        axis = self._detect_edge_axis(self.x, self.y, default=self.edge_axis)
        if not axis:
            return False
        if axis == "horizontal":
            return move_dir[1] != 0
        if axis == "vertical":
            return move_dir[0] != 0
        return False

    def _can_extend_incursion_trace(self, x, y):
        if self.world.is_point_in_unclaimed_area(x, y):
            return True
        if not self.world.current_incursion:
            return False
        if not self.world.is_point_within_bounds(x, y):
            return False
        if self.world.is_point_claimed(x, y):
            return False
        last_x, last_y = self.world.current_incursion[-1]
        return abs(x - last_x) < 10 and abs(y - last_y) < 10

    def _fail_current_incursion(self):
        start_pos = self.world.cancel_incursion()
        if start_pos:
            self.last_edge_pos = start_pos
        self.is_pushing = False
        self.push_start_pos = None
        self.push_dir = None
        self.world.set_incursion_warning(False)
        self.x, self.y = self.last_edge_pos
        self._update_edge_axis_from_position(self.x, self.y)
        self.lose_life()
    
