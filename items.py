class Item:
    def __init__(self, id, name, type, value, w=1, h=1):
        self.id = id
        self.name = name
        self.type = type  # e.g., 'heal', 'buff'
        self.value = value
        self.w = int(w)
        self.h = int(h)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type, "value": self.value, "w": self.w, "h": self.h}

# convenience factory helpers
def small_heal():
    return Item('small_heal', 'Small Heal', 'heal', 25, w=1, h=1)

def med_heal():
    return Item('med_heal', 'Med Heal', 'heal', 50, w=1, h=2)

def battery_boost():
    return Item('battery', 'Battery', 'buff', 1, w=2, h=1)
