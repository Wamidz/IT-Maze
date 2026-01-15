"""Non-graphical smoke test for the Pythongame project.
This script imports the game modules and runs a few update ticks to catch import/runtime errors.
It avoids initializing any pygame display or drawing functions.
"""
import random
from player import Player
from world import generate_maze_with_room_types
from questions import QUESTIONS

random.seed(0)

print("Starting smoke test")
world = generate_maze_with_room_types(width=3, height=3, difficulty=1)
print(f"World size: {len(world)} rooms")

# Basic consistency checks
for coord, room in world.items():
    assert hasattr(room, 'doors') and hasattr(room, 'enemies') and hasattr(room, 'walls')

# Create player and run a few update cycles
player = Player()
print(f"Initial player position: ({player.x}, {player.y})")

# Count enemies
total_enemies = sum(len(r.enemies) for r in world.values())
print(f"Total enemies placed: {total_enemies}")

# Run a few simulated ticks without drawing
for tick in range(5):
    for coord, room in world.items():
        # simulate enemy AI updates
        for e in list(room.enemies):
            # sanity: enemy has question data
            if e.data is None:
                raise AssertionError(f"Enemy at {coord} missing question data")
            e.update(player, room)

print("Update ticks completed successfully")

# Sanity-check questions
for q in QUESTIONS:
    assert 'q' in q and 'options' in q and 'correct' in q

print("Questions format OK")
print("Smoke test passed")

