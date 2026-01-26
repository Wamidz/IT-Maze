class InventoryGrid:
    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)
        # store None or a reference to an item dict with keys including w,h
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        # items list stores dicts: {'item': item_dict, 'x':ox, 'y':oy}
        self.items = []

    def can_place(self, item, ox, oy):
        w = int(item.get('w', 1)) if isinstance(item, dict) else getattr(item, 'w', 1)
        h = int(item.get('h', 1)) if isinstance(item, dict) else getattr(item, 'h', 1)
        if ox < 0 or oy < 0 or ox + w > self.width or oy + h > self.height:
            return False
        for y in range(oy, oy + h):
            for x in range(ox, ox + w):
                if self.grid[y][x] is not None:
                    return False
        return True

    def place_item(self, item, ox=None, oy=None):
        # If no coords provided, find first-fit
        w = int(item.get('w', 1)) if isinstance(item, dict) else getattr(item, 'w', 1)
        h = int(item.get('h', 1)) if isinstance(item, dict) else getattr(item, 'h', 1)
        if ox is None or oy is None:
            for yy in range(self.height - h + 1):
                for xx in range(self.width - w + 1):
                    if self.can_place(item, xx, yy):
                        ox, oy = xx, yy
                        break
                if ox is not None and oy is not None:
                    break
            if ox is None or oy is None:
                return False
        else:
            if not self.can_place(item, ox, oy):
                return False
        entry = {'item': item, 'x': ox, 'y': oy, 'w': w, 'h': h}
        # mark grid
        for y in range(oy, oy + h):
            for x in range(ox, ox + w):
                self.grid[y][x] = entry
        self.items.append(entry)
        return True

    def remove_at(self, ox, oy):
        if oy < 0 or ox < 0 or oy >= self.height or ox >= self.width:
            return None
        entry = self.grid[oy][ox]
        if entry is None:
            return None
        # clear grid
        for y in range(entry['y'], entry['y'] + entry['h']):
            for x in range(entry['x'], entry['x'] + entry['w']):
                self.grid[y][x] = None
        try:
            self.items.remove(entry)
        except ValueError:
            pass
        return entry['item']

    def get_at(self, ox, oy):
        if oy < 0 or ox < 0 or oy >= self.height or ox >= self.width:
            return None
        entry = self.grid[oy][ox]
        if entry is None:
            return None
        return entry

    def iter_items(self):
        # yield (item_dict, x, y, w, h)
        for e in list(self.items):
            yield e['item'], e['x'], e['y'], e['w'], e['h']

    def clear(self):
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.items = []

    def to_list(self):
        # convenience: return shallow list of item dicts
        return [e['item'] for e in self.items]
