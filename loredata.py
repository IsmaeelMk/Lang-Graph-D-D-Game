CHARACTERS = [
    {
        "id": "sera",
        "name": "Sera Voss",
        "backstory": "Once captain of the royal guard, Sera was exiled after "
                      "refusing to execute an innocent prisoner. She wanders now, "
                      "seeking a way to reclaim her name.",
        "starter_item_id": "oathbreakers_edge",
    },
    {
        "id": "bram",
        "name": "Bram Thistlewood",
        "backstory": "A self-taught herbalist who fled his village after a "
                      "'cure' he brewed went catastrophically wrong. He tests "
                      "his remedies on himself first, these days.",
        "starter_item_id": "uncertain_draughts",
    },
    {
        "id": "yuki",
        "name": "Yuki Amaranth",
        "backstory": "A silent cartographer who maps places that shouldn't "
                      "exist — forgotten ruins, folded valleys, doors that only "
                      "open at certain hours. She doesn't speak; her map speaks "
                      "for her.",
        "starter_item_id": "unfinished_map",
    },
]

ITEMS = [
    {
        "id": "oathbreakers_edge",
        "name": "Oathbreaker's Edge",
        "lore": "Forged in the royal armory and stripped of its house sigil "
                "the day Sera was exiled. The blade still remembers who it "
                "was made to protect.",
        "stats": {"type": "weapon", "damage_bonus": 3, "crit_chance": 0.05},
    },
    {
        "id": "uncertain_draughts",
        "name": "Satchel of Uncertain Draughts",
        "lore": "Three vials, unlabeled. Bram insists he remembers which is "
                "which. The satchel smells faintly of burnt sugar and regret.",
        "stats": {"type": "consumable", "heal_amount": 8},
    },
    {
        "id": "unfinished_map",
        "name": "The Unfinished Map",
        "lore": "Ink moves on its own when Yuki nears something worth "
                "finding. Parts of it are still blank — on purpose, or not, "
                "no one knows.",
        "stats": {"type": "utility", "reveal_bonus": True},
    },
]

def get_item(item_id):
    for item in ITEMS:
        if item["id"] == item_id:
            return item
    return None


def get_character(char_id):
    for char in CHARACTERS:
        if char["id"] == char_id:
            return char
    return None

