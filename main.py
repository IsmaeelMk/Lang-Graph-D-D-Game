import os
import random
from typing import TypedDict, Optional

from loredata import get_item, get_character,ITEMS, CHARACTERS
from vectorstore import buildvectorstore, querylore

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

model = ChatGoogleGenerativeAI( model="gemini-flash-latest",
                                google_api_key=GOOGLE_API_KEY, )

vectorstore = buildvectorstore()

def get_text(response):
    if isinstance(response.content, str):
        return response.content
    if isinstance(response.content, list):
        for block in response.content:
            if isinstance(block, dict) and "text" in block:
                return block["text"]
    return str(response.content)
 
 
class GameState(TypedDict):
    player_action: str
    narrative_log: list[str]
    hp: int
    inventory: list[str]
    equipped_weapon: Optional[str]
    character_id: Optional[str]
    action_type: Optional[str]
    game_over: bool
    outcome: Optional[str]
 
 
# nodes
 
def get_player_input(state: GameState) -> dict:
    action = interrupt("What do you do?")
    return {"player_action": action}
 
 
def classify_action(state: GameState) -> dict:
    prompt = f"""Classify this player action into exactly one of the following:
    "combat", "explore", "item", "other"

    "item" means the player is picking up, grabbing, taking, using, or interacting 
    directly with an item or object.
    "combat" means the player is attacking, fighting, or engaging an enemy.
    "explore" means the player is moving, looking around, or investigating a new area.
    "other" is only for actions that clearly don't fit any of the above.

    Respond with only a single word category.

    Action: {state['player_action']}"""

    response = model.invoke(prompt)
    action = get_text(response).strip().lower()

    if action not in ("combat", "explore", "item", "other"):
        action = "other"

    print(f'[classify_action] action = {action}')

    return {"action_type": action}


 
def combat_agent(state: GameState) -> dict:
    weapon = get_item(state["equipped_weapon"]) if state["equipped_weapon"] else None
    damage_bonus = weapon["stats"]["damage_bonus"] if weapon else 0

    needs_lore = False
    if weapon:
        weapon_name_lower = weapon["name"].lower()
        action_lower = state["player_action"].lower()
        if weapon_name_lower in action_lower:
            needs_lore = True

    lore_snippet = None
    if needs_lore:
        lore_snippet = querylore(vectorstore, weapon["name"])
 
    diceroll = random.randint(1, 20) + damage_bonus

    if diceroll >= 15:
            damagetoplayer = 0
            resultsummary = "critical hit by the player, he took 0 damage"
    elif diceroll >= 8:
            damagetoplayer = 5
            resultsummary = "moderate exchange between the players, the player took 5 damage"
    else:
            damagetoplayer = 8
            resultsummary = "bad exchange, the player took 8 damage"

    weapon_line = f"Weapon used: {weapon['name']}" if weapon else "Fighting bare-handed"
    lore_line = f"Weapon lore: {lore_snippet}" if lore_snippet else ""

    prompt = f"""narrate a short exciting combat scene between a player and an enemy.
    the players action: {state['player_action']}
    {weapon_line}
    {lore_line}
    summary of what happened: {resultsummary}"""

    response = model.invoke(prompt)
    narration = get_text(response).strip()

    newhp = max(0, state['hp'] - damagetoplayer)

    print(f'[combat_agent] dice roll = {diceroll}, damage_bonus = {damage_bonus}, damage = {damagetoplayer}, new HP = {newhp}, retrieved_lore = {needs_lore}')

    return {
            "hp": newhp,
            "narrative_log": state["narrative_log"] + [narration]
        }


def explore_agent(state: GameState) -> dict:
    action_lower = state["player_action"].lower()

    needs_lore = False
    matched_name = None

    for item in ITEMS:
        if item["name"].lower() in action_lower:
            needs_lore = True
            matched_name = item["name"]
            break

    if not needs_lore:
        for char in CHARACTERS:
            if char["name"].lower() in action_lower:
                needs_lore = True
                matched_name = char["name"]
                break

    lore_snippet = None
    if needs_lore:
        lore_snippet = querylore(vectorstore, matched_name)

    lore_line = f"Relevant lore: {lore_snippet}" if lore_snippet else ""

    prompt = f"""narrate a short exploration scene based on {state['player_action']}
describe what the player discovers (a room, a clue, an item, a threat, etc)
{lore_line}"""

    response = model.invoke(prompt)
    narration = get_text(response).strip()

    print(f'[explore_agent] retrieved_lore = {needs_lore}, matched = {matched_name}')

    return {
        "narrative_log": state["narrative_log"] + [narration]
    }
 
 
def item_agent(state: GameState) -> dict:
    action_lower = state["player_action"].lower()

    matched_item = None
    for item in ITEMS:
        if item["name"].lower() in action_lower:
            matched_item = item
            break

    lore_snippet = matched_item["lore"] if matched_item else None
    lore_line = f"Item lore: {lore_snippet}" if lore_snippet else ""

    prompt = f"""Narrate the player finding or using an item, based on: {state['player_action']}
{lore_line}
Respond in exactly this format:
NARRATION: <a short exciting description>
ITEM: <name of the item>"""

    response = model.invoke(prompt)
    text = get_text(response).strip()
    line1, line2 = text.split("\n")

    if line1[0:5] == "ITEM:":
        item_line, narration_line = line1, line2
    else:
        item_line, narration_line = line2, line1

    narration = narration_line.replace("NARRATION:", "").strip()
    item_name = item_line.replace("ITEM:", "").strip()

    print(f'[item_agent] matched = {matched_item["id"] if matched_item else None}, item_name = {item_name}')

    return {
        "narrative_log": state["narrative_log"] + [narration],
        "inventory": state["inventory"] + [item_name]
    }
 
 
def check_status(state: GameState) -> dict:
    if state["hp"] <= 0:
        outcome = "death"
        gameover = True
    elif len(state["inventory"]) >= 3:
        outcome = "win"
        gameover = True
    else:
        gameover = False
        outcome = None
 
    print(f"[check_status] HP: {state['hp']}, inventory length: {len(state['inventory'])}, game over? {gameover}")
 
    return {
        "game_over": gameover,
        "outcome": outcome
    }
 
 
def narrate_ending(state: GameState) -> dict:
    prompt = f"""write a short dramatic ending to this story where the game ends with the player: {state['outcome']}, heres a bit of what happened so far: {state['narrative_log']}"""
 
    response = model.invoke(prompt)
    narration = get_text(response).strip()
 
    return {
        "narrative_log": state["narrative_log"] + [narration]
    }

#RAG NODES: 
def select_character(state: GameState) -> dict:
    menu_text = "Choose your character:\n\n"
    for char in CHARACTERS:
        menu_text += f"{char['id']}: {char['name']} — {char['backstory']}\n\n"
    menu_text += "Type the character id to choose:"

    chosen_id = interrupt(menu_text)
    return {"character_id": chosen_id}

def init_character_state(state: GameState) -> dict:
    char = get_character(state["character_id"])
    item = get_item(char["starter_item_id"])

    is_weapon = item["stats"]["type"] == "weapon"

    intro_text = f"You are {char['name']}. {char['backstory']}"

    return {
        "hp": 30,
        "inventory": [item["id"]],
        "equipped_weapon": item["id"] if is_weapon else None,
        "narrative_log": [intro_text],
    }


# routers
 
def route_by_action_type(state: GameState) -> str:
    return state["action_type"]
 
 
def route_by_status_check(state: GameState) -> str:
    if state["game_over"]:
        return "ending"
    else:
        return "continue"
 
 
# graph
 
graph = StateGraph(GameState)

graph.add_node("select_character", select_character)
graph.add_node("init_character_state", init_character_state)
graph.add_node("get_input", get_player_input)
graph.add_node("classify", classify_action)
graph.add_node("combat", combat_agent)
graph.add_node("explore", explore_agent)
graph.add_node("item", item_agent)
graph.add_node("check_status", check_status)
graph.add_node("ending", narrate_ending)


graph.set_entry_point("select_character")


graph.add_edge("select_character", "init_character_state")
graph.add_edge("init_character_state", "get_input")


graph.add_edge("get_input", "classify")


graph.add_conditional_edges(
    "classify",
    route_by_action_type,
    {"combat": "combat", "explore": "explore", "item": "item", "other": "explore"}
)

graph.add_edge("combat", "check_status")
graph.add_edge("explore", "check_status")
graph.add_edge("item", "check_status")


graph.add_conditional_edges(
    "check_status",
    route_by_status_check,
    {"ending": "ending", "continue": "get_input"}
)


graph.add_edge("ending", END)


checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)


# game loop
 
config = {"configurable": {"thread_id": "game-1"}}
 
initial_state = {
    "player_action": "",
    "narrative_log": [],
    "hp": 0,
    "inventory": [],
    "equipped_weapon": None,
    "character_id": None,
    "action_type": None,
    "game_over": False,
    "outcome": None,
}
 
print("You wake up at the entrance of a dark dungeon. HP: 30\n")
 
result = app.invoke(initial_state, config=config)
 
while True:
    if result.get("narrative_log"):
        print("\n" + result["narrative_log"][-1])
        print(f"[HP: {result['hp']} | Inventory: {result['inventory']}]")
 
    if result.get("game_over"):
        print("\n--- GAME OVER ---")
        break
 
    if "__interrupt__" in result:
        prompt_text = result["__interrupt__"][0].value
        player_input = input(f"\n{prompt_text} ")
        result = app.invoke(Command(resume=player_input), config=config)
    else:
        break