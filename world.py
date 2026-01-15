from room import Room
from enemy import Enemy
from questions import QUESTIONS
import random
try:
    from items import Item
    from items import small_heal, med_heal, battery_boost
except Exception:
    Item = None

def are_opposite(dirs):
    return ("U" in dirs and "D" in dirs) or ("L" in dirs and "R" in dirs)

def generate_maze_with_room_types(width=3, height=3, difficulty=1):
    rooms = {}
    for x in range(width):
        for y in range(height):
            rooms[(x, y)] = Room(doors=[], enemies=[])

    visited = set()
    stack = [(0,0)]  # start at spawn

    while stack:
        current = stack[-1]
        visited.add(current)
        x, y = current

        # Determine available neighbors
        neighbors = []
        directions = []
        for dx, dy, dir_from, dir_to in [(0,-1,"U","D"), (0,1,"D","U"), (-1,0,"L","R"), (1,0,"R","L")]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                neighbors.append((nx, ny, dir_from, dir_to))
                directions.append(dir_from)

        if neighbors:
            # Choose a neighbor to connect
            nx, ny, dir_from, dir_to = random.choice(neighbors)

            # Determine room type based on available directions
            # Avoid 4-door rooms unless necessary
            current_doors = rooms[(x,y)].doors
            potential_doors = current_doors + [dir_from]

            if len(potential_doors) > 3:
                # pick 2-3 doors randomly to avoid fully enclosed 4-door
                potential_doors = random.sample(potential_doors, 2 if len(neighbors)==1 else 3)

            rooms[(x,y)].doors = potential_doors
            # Neighbor must connect back
            neighbor_doors = rooms[(nx, ny)].doors
            neighbor_doors.append(dir_to)
            rooms[(nx, ny)].doors = neighbor_doors

            stack.append((nx, ny))
        else:
            stack.pop()

    # Optional: add extra connections (loops) respecting room types
    for (x, y), room in rooms.items():
        for dx, dy, dir_from, dir_to in [(0,-1,"U","D"), (0,1,"D","U"), (-1,0,"L","R"), (1,0,"R","L")]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < width and 0 <= ny < height:
                if dir_from not in room.doors and random.random() < 0.15:
                    room.doors.append(dir_from)
                    rooms[(nx, ny)].doors.append(dir_to)

    # Place enemies, skip spawn
    for (x, y), room in rooms.items():
        if (x, y) == (0,0):
            continue
        num_enemies = random.randint(0, difficulty)
        for _ in range(num_enemies):
            # Choose a spawn position that is not a wall and not occupied by another enemy
            max_attempts = 50
            attempt = 0
            while True:
                ex, ey = random.randint(1,7), random.randint(1,7)
                attempt += 1
                occupied = any(e.x == ex and e.y == ey for e in room.enemies)
                if (ex, ey) not in room.walls and not occupied:
                    break
                if attempt >= max_attempts:
                    # Give up and skip this enemy if no free tile found
                    ex = None
                    break

            if ex is None:
                continue

            q = random.choice(QUESTIONS)
            room.enemies.append(Enemy(ex, ey, question=q))
        # occasional chest spawn with its own inventory
        if random.random() < 0.18:
            # pick chest location
            for _a in range(20):
                cx, cy = random.randint(1,7), random.randint(1,7)
                if (cx, cy) not in room.walls and all(not (e.x == cx and e.y == cy) for e in room.enemies):
                    chest_grid = room.add_chest(cx, cy, grid_width=4, grid_height=3)
                    # populate chest with a few items
                    # use factory helpers if available
                    try:
                        chest_grid.place_item(small_heal().to_dict())
                        chest_grid.place_item(battery_boost().to_dict())
                        chest_grid.place_item(med_heal().to_dict())
                    except Exception:
                        chest_grid.place_item({'id':'small_heal','name':'Small Heal','type':'heal','value':25,'w':1,'h':1})
                    break

    return rooms
