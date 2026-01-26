# IT-Maze 🎮

A Python dungeon crawler game where you navigate through procedurally generated mazes, battle enemies with IT-themed questions, and test your knowledge while exploring!

## 🎯 About

IT-Maze is an educational dungeon crawler that combines classic maze exploration with IT trivia questions. Navigate through rooms, collect items, battle enemies using a unique combat system that includes trivia questions, dodge minigames, and strategic item usage.

## ✨ Features

- **Procedurally Generated Mazes**: Each playthrough offers a unique maze layout
- **Combat System**: Engage enemies with multiple combat mechanics:
  - **Attack Minigame**: Timing-based attack system
  - **Dodge Minigame**: Dodge enemy projectiles in bullet-hell style gameplay
  - **Hack/Question System**: Answer IT-related questions for critical damage
- **Inventory System**: Grid-based inventory with various item types:
  - Health potions (small and medium)
  - Attack and defense buffs
  - Special items like EMP grenades and firewall chips
- **Chest & Loot System**: Find treasure chests scattered throughout rooms
- **Difficulty Levels**: Multiple question difficulties (VG1, VG2, Hard)
- **Minimap**: Track your exploration progress
- **Cheat Menu**: Debug options for testing (toggle noclip, godmode, reveal map)

## 🎮 Controls

### Exploration
- **Arrow Keys**: Move player
- **M**: Toggle big map view
- **F3**: Toggle debug information

### Combat
- **Arrow Keys**: Navigate menu options / Move during dodge phase
- **Enter/Z**: Select option / Attack
- **Space**: Alternate selection key

### Inventory
- **Mouse Click**: Use items from inventory during combat

## 🔧 Requirements

### Python Version
- **Python 3.11 (Recommended)** - Best compatibility with pygame
- Python versions **below 3.12** - pygame may have issues with Python 3.12+

### Dependencies
- **pygame** (for graphics and game engine)

## 📦 Installation

1. **Clone the repository**
```bash
git clone https://github.com/Wamidz/IT-Maze.git
cd IT-Maze
```

2. **Install Python 3.11** (if not already installed)
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to select Python 3.11.x

3. **Install dependencies**

   **Option 1: Using the included script**
   ```bash
   python install_deps.py
   ```

   **Option 2: Manual installation**
   ```bash
   pip install pygame
   ```

4. **Run the game**
```bash
python main.py
```

## 🎲 Game Mechanics

### Room Types
- **Normal Rooms**: Standard exploration areas
- **Enemy Rooms**: Contain enemies that must be defeated
- **Loot Rooms**: Contain items and treasure chests
- **Exit Room**: Complete the maze!

### Combat Phases
1. **Player Turn**: Choose between Attack, Item, or Hack/Question
2. **Attack Minigame**: Time your attack for maximum damage
3. **Enemy Turn**: Dodge incoming projectiles
4. **Question Phase**: Answer IT questions correctly for bonus damage

### Items
- **Small Heal**: Restore 20 HP
- **Medium Heal**: Restore 40 HP
- **Battery Boost**: Increase attack power
- **Firewall Chip**: Increase defense
- **EMP Grenade**: Stun enemy for one turn

## 🧪 Testing

Run the smoke test to verify the game modules:
```bash
python smoke_test.py
```

## 🎓 Educational Content

The game includes IT trivia questions across multiple categories:
- Programming fundamentals
- Web technologies (HTML, CSS, JavaScript)
- Networking concepts
- Database basics (SQL)
- Computer science concepts (Algorithms, Data Types)

## 🐛 Known Issues

- pygame compatibility issues with Python 3.12 and above
- Best experience on Python 3.11.x

## 🎨 Graphics Settings

The game includes adjustable graphics settings:
- Scaling options for different screen sizes
- Resolution adjustments
- Letterboxing for proper aspect ratio

## 🚀 Future Enhancements

Potential features for future development:
- More enemy types and behaviors
- Additional item types
- Boss battles
- Multiple maze themes
- Sound effects and music

## 📝 File Structure

```
IT-Maze/
├── main.py           # Main game loop and rendering
├── player.py         # Player class and movement
├── enemy.py          # Enemy class and AI
├── room.py           # Room generation and management
├── world.py          # Maze generation
├── combat.py         # Combat encounter system
├── inventory.py      # Inventory grid system
├── items.py          # Item definitions
├── questions.py      # IT trivia questions
├── install_deps.py   # Dependency installer
└── smoke_test.py     # Non-graphical test suite
```

## 👤 Author

**Wamidz**
- GitHub: [@Wamidz](https://github.com/Wamidz)

## 📄 License

This project is available for educational and personal use.

---

**Note**: This game requires pygame, which works best with Python versions below 3.12. Python 3.11 is recommended for optimal compatibility.
```