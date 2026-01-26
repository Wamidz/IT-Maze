import pygame
import random
import math

# Combat Sub-states
TURN_PLAYER_MENU = 0
TURN_PLAYER_ATTACK = 1
TURN_PLAYER_HACK = 2
TURN_ENEMY_INTRO = 3
TURN_ENEMY_DODGE = 4
TURN_RESULT = 5

class CombatEncounter:
    def __init__(self, player, enemy, canvas_size):
        self.player = player
        self.enemy = enemy
        self.cw, self.ch = canvas_size
        self.font = pygame.font.SysFont(None, 32)
        self.small_font = pygame.font.SysFont(None, 24)
        
        self.state = TURN_PLAYER_MENU
        self.menu_options = ["Attack", "Hack (IT Skill)"]
        self.menu_index = 0
        
        self.message = f"Encountered {enemy.__class__.__name__}!"
        self.message_timer = 60
        
        # Attack Minigame vars
        self.attack_bar_x = 0
        self.attack_bar_dir = 1
        self.attack_bar_width = 200
        self.attack_target_width = 20
        self.attack_speed = 4
        
        # Hack vars
        self.hack_options = []
        self.hack_index = 0
        
        # Dodge Minigame vars
        self.dodge_box = pygame.Rect(self.cw//2 - 100, self.ch//2 + 20, 200, 150)
        self.player_rect = pygame.Rect(0, 0, 16, 16)
        self.player_rect.center = self.dodge_box.center
        self.projectiles = []
        self.dodge_timer = 0
        self.dodge_duration = 300 # 5 seconds at 60fps
        self.spawn_timer = 0
        
        self.finished = False
        self.player_won = False
        
        # Initialize Hack options from enemy data
        if self.enemy.data:
            self.hack_options = self.enemy.data.get("options", [])
            self.hack_correct = self.enemy.data.get("correct", 0)
        else:
            # Fallback
            self.hack_options = ["Option A", "Option B"]
            self.hack_correct = 0

    def update(self, keys, events):
        if self.message_timer > 0:
            self.message_timer -= 1
            return

        if self.state == TURN_PLAYER_MENU:
            # Navigate menu
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_UP:
                        self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                    elif e.key == pygame.K_DOWN:
                        self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif e.key == pygame.K_RETURN or e.key == pygame.K_SPACE:
                        if self.menu_index == 0:
                            self.state = TURN_PLAYER_ATTACK
                            self.attack_bar_x = 0
                            self.message = "Press SPACE in the center!"
                        elif self.menu_index == 1:
                            self.state = TURN_PLAYER_HACK
                            self.message = self.enemy.data.get("q", "Hack the enemy!")
                            self.hack_index = 0

        elif self.state == TURN_PLAYER_ATTACK:
            # Move bar
            self.attack_bar_x += self.attack_speed * self.attack_bar_dir
            if self.attack_bar_x < 0 or self.attack_bar_x > self.attack_bar_width:
                self.attack_bar_dir *= -1
            
            for e in events:
                if e.type == pygame.KEYDOWN and (e.key == pygame.K_SPACE or e.key == pygame.K_RETURN):
                    # Calculate damage based on distance to center
                    center = self.attack_bar_width // 2
                    dist = abs(self.attack_bar_x - center)
                    # Max damage 20, min 5
                    accuracy = max(0, 1.0 - (dist / (self.attack_bar_width/2)))
                    damage = int(5 + 25 * accuracy)
                    
                    self.enemy.apply_damage(damage)
                    self.message = f"Hit for {damage} damage!"
                    self.message_timer = 60
                    
                    if not self.enemy.alive:
                        self.finished = True
                        self.player_won = True
                    else:
                        self.state = TURN_ENEMY_INTRO
                        self.message_timer = 60

        elif self.state == TURN_PLAYER_HACK:
            for e in events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_UP:
                        self.hack_index = (self.hack_index - 1) % len(self.hack_options)
                    elif e.key == pygame.K_DOWN:
                        self.hack_index = (self.hack_index + 1) % len(self.hack_options)
                    elif e.key == pygame.K_RETURN or e.key == pygame.K_SPACE:
                        if self.hack_index == self.hack_correct:
                            # Correct answer: Massive damage or instant kill
                            damage = 50
                            self.enemy.apply_damage(damage)
                            self.message = "Hack Successful! Critical Hit!"
                        else:
                            self.message = "Hack Failed..."
                        
                        self.message_timer = 60
                        if not self.enemy.alive:
                            self.finished = True
                            self.player_won = True
                        else:
                            self.state = TURN_ENEMY_INTRO

        elif self.state == TURN_ENEMY_INTRO:
            self.message = "Enemy is attacking! Dodge!"
            if self.message_timer == 0: # Wait for previous message to clear if any
                 # Setup dodge
                self.state = TURN_ENEMY_DODGE
                self.dodge_timer = self.dodge_duration
                self.projectiles = []
                self.player_rect.center = self.dodge_box.center

        elif self.state == TURN_ENEMY_DODGE:
            self.dodge_timer -= 1
            if self.dodge_timer <= 0:
                self.state = TURN_PLAYER_MENU
                self.message = "Your turn!"
                self.message_timer = 30
                return

            # Player movement in box
            speed = 3
            if keys["up"]: self.player_rect.y -= speed
            if keys["down"]: self.player_rect.y += speed
            if keys["left"]: self.player_rect.x -= speed
            if keys["right"]: self.player_rect.x += speed
            
            # Clamp to box
            self.player_rect.clamp_ip(self.dodge_box)
            
            # Spawn projectiles
            self.spawn_timer += 1
            if self.spawn_timer > 15: # Spawn every 15 frames
                self.spawn_timer = 0
                side = random.choice(['top', 'bottom', 'left', 'right'])
                size = 10
                if side == 'top':
                    x = random.randint(self.dodge_box.left, self.dodge_box.right)
                    y = self.dodge_box.top - size
                    vx, vy = 0, 3
                elif side == 'bottom':
                    x = random.randint(self.dodge_box.left, self.dodge_box.right)
                    y = self.dodge_box.bottom + size
                    vx, vy = 0, -3
                elif side == 'left':
                    x = self.dodge_box.left - size
                    y = random.randint(self.dodge_box.top, self.dodge_box.bottom)
                    vx, vy = 3, 0
                else:
                    x = self.dodge_box.right + size
                    y = random.randint(self.dodge_box.top, self.dodge_box.bottom)
                    vx, vy = -3, 0
                
                self.projectiles.append({'rect': pygame.Rect(x, y, size, size), 'vx': vx, 'vy': vy})
            
            # Update projectiles
            for p in self.projectiles[:]:
                p['rect'].x += p['vx']
                p['rect'].y += p['vy']
                
                # Remove if far out
                if not p['rect'].colliderect(self.dodge_box.inflate(100, 100)):
                    self.projectiles.remove(p)
                    continue
                
                # Collision with player
                if p['rect'].colliderect(self.player_rect):
                    self.player.apply_damage(5) # 5 dmg per hit
                    self.projectiles.remove(p)
                    # Optional: Flash player or sound
                    if self.player.hp <= 0:
                        self.finished = True
                        self.player_won = False

    def draw(self, surface):
        # Draw background (dimmed game or black)
        surface.fill((20, 20, 30))
        
        # Draw Enemy
        ex, ey = self.cw // 2, self.ch // 4
        pygame.draw.circle(surface, (200, 50, 50), (ex, ey), 40)
        # Enemy HP
        hp_pct = self.enemy.hp / self.enemy.max_hp
        pygame.draw.rect(surface, (100, 0, 0), (ex - 50, ey + 50, 100, 10))
        pygame.draw.rect(surface, (0, 200, 0), (ex - 50, ey + 50, 100 * hp_pct, 10))
        
        # Draw Player Stats
        hp_text = self.font.render(f"Player HP: {self.player.hp}/{self.player.max_hp}", True, (255, 255, 255))
        surface.blit(hp_text, (20, self.ch - 40))
        
        # Draw Message
        msg_surf = self.font.render(self.message, True, (255, 255, 0))
        surface.blit(msg_surf, (self.cw // 2 - msg_surf.get_width() // 2, 20))

        # State specific drawing
        if self.state == TURN_PLAYER_MENU:
            mx, my = 50, self.ch // 2
            for i, opt in enumerate(self.menu_options):
                color = (255, 255, 0) if i == self.menu_index else (200, 200, 200)
                txt = self.font.render(f"> {opt}" if i == self.menu_index else f"  {opt}", True, color)
                surface.blit(txt, (mx, my + i * 40))
                
        elif self.state == TURN_PLAYER_ATTACK:
            # Draw bar container
            bx, by = self.cw // 2 - 100, self.ch // 2
            pygame.draw.rect(surface, (100, 100, 100), (bx, by, 200, 30), 2)
            # Draw center target
            pygame.draw.rect(surface, (0, 255, 0), (bx + 100 - 10, by, 20, 30))
            # Draw moving cursor
            cx = bx + self.attack_bar_x
            pygame.draw.rect(surface, (255, 255, 255), (cx - 2, by - 5, 4, 40))
            
        elif self.state == TURN_PLAYER_HACK:
            # Draw Question
            q_text = self.enemy.data.get("q", "Question?")
            # Wrap text if needed (simple wrap)
            words = q_text.split(' ')
            lines = []
            curr_line = ""
            for w in words:
                if len(curr_line) + len(w) > 40:
                    lines.append(curr_line)
                    curr_line = w + " "
                else:
                    curr_line += w + " "
            lines.append(curr_line)
            
            qy = self.ch // 2 - 50
            for line in lines:
                t = self.font.render(line, True, (255, 255, 255))
                surface.blit(t, (50, qy))
                qy += 30
            
            # Draw Options
            oy = qy + 20
            for i, opt in enumerate(self.hack_options):
                color = (255, 255, 0) if i == self.hack_index else (200, 200, 200)
                t = self.small_font.render(f"{opt}", True, color)
                surface.blit(t, (70, oy + i * 30))

        elif self.state == TURN_ENEMY_DODGE:
            # Draw Box
            pygame.draw.rect(surface, (255, 255, 255), self.dodge_box, 2)
            # Draw Player
            pygame.draw.rect(surface, (0, 100, 255), self.player_rect)
            # Draw Projectiles
            for p in self.projectiles:
                pygame.draw.rect(surface, (255, 0, 0), p['rect'])
            
            # Draw Timer
            timer_text = self.small_font.render(f"Survive: {self.dodge_timer//60 + 1}", True, (200, 200, 200))
            surface.blit(timer_text, (self.dodge_box.centerx - 30, self.dodge_box.bottom + 10))
