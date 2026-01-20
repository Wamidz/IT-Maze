class Item:
    def __init__(self, id, name, type, value, w=1, h=1, description=""):
        self.id = id
        self.name = name
        self.type = type  # 'heal', 'buff_attack', 'buff_defense', 'stun'
        self.value = value
        self.w = int(w)
        self.h = int(h)
        self.description = description

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "type": self.type, 
            "value": self.value, "w": self.w, "h": self.h,
            "description": self.description
        }

# convenience factory helpers
def small_heal():
    return Item('small_heal', 'Small Heal', 'heal', 25, w=1, h=1, description="Restores 25 HP")

def med_heal():
    return Item('med_heal', 'Med Heal', 'heal', 50, w=1, h=2, description="Restores 50 HP")

def battery_boost():
    return Item('battery', 'Overclock', 'buff_attack', 2.0, w=2, h=1, description="2x Damage next attack")

def firewall_chip():
    return Item('firewall', 'Firewall', 'buff_defense', 0.5, w=1, h=1, description="50% less dmg next turn")

def emp_grenade():
    return Item('emp', 'EMP', 'stun', 1, w=1, h=1, description="Stuns enemy 1 turn")
