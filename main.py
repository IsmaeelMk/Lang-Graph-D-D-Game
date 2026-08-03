import os
import random
from typing import TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

model = ChatGoogleGenerativeAI( model="gemini-flash-latest",
                                google_api_key=GOOGLE_API_KEY, )

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
Respond with only a single word category.
 
Action: {state['player_action']}"""
 
    response = model.invoke(prompt)
    action = get_text(response).strip().lower()
 
    if action not in ("combat", "explore", "item", "other"):
        action = "other"
 
    print(f'[classify_action] action = {action}')
 
    return {"action_type": action}
 
 
def handle_combat(state: GameState) -> dict:
    diceroll = random.randint(1, 20)
 
    if diceroll >= 15:
        damagetoplayer = 0
        resultsummary = "critical hit by the player, he took 0 damage"
    elif diceroll >= 8:
        damagetoplayer = 5
        resultsummary = "moderate exchange between the players, the player took 5 damage"
    else:
        damagetoplayer = 8
        resultsummary = "bad exchange, the player took 8 damage"
 
    prompt = f"""narrate a short exciting combat scene between a player and an enemy. the players action: {state['player_action']} and the summary of what happened: {resultsummary}"""
 
    response = model.invoke(prompt)
    narration = get_text(response).strip()
 
    newhp = max(0, state['hp'] - damagetoplayer)
 
    print(f'[handle_combat] dice roll = {diceroll}, damage = {damagetoplayer}, new HP = {newhp}')
 
    return {
        "hp": newhp,
        "narrative_log": state["narrative_log"] + [narration]
    }
 
 
def handle_explore(state: GameState) -> dict:
    prompt = f"""narrate a short exploration scene based on {state['player_action']} describe what the player discovers (a room, a clue, an item, a threat, etc)"""
 
    response = model.invoke(prompt)
    narration = get_text(response).strip()
 
    return {
        "narrative_log": state["narrative_log"] + [narration]
    }
 
 
def handle_item(state: GameState) -> dict:
    prompt = f"""Narrate the player finding or using an item, based on: {state['player_action']}
Respond in exactly this format:
NARRATION: <a short exciting description>
ITEM: <name of the item>"""
 
    response = model.invoke(prompt)
    text = get_text(response).strip()
    line1, line2 = text.split("\n")
 
    if line1[0:5] == "ITEM:":
        item_line = line1
        narration_line = line2
    else:
        item_line = line2
        narration_line = line1
 
    narration = narration_line.replace("NARRATION:", "").strip()
    item_name = item_line.replace("ITEM:", "").strip()
 
    print(f"[handle_item] item found = {item_name}")
 
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
 
graph.add_node("get_input", get_player_input)
graph.add_node("classify", classify_action)
graph.add_node("combat", handle_combat)
graph.add_node("explore", handle_explore)
graph.add_node("item", handle_item)
graph.add_node("check_status", check_status)
graph.add_node("ending", narrate_ending)
 
graph.set_entry_point("get_input")
 
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
    "hp": 30,
    "inventory": [],
    "action_type": None,
    "game_over": False,
    "outcome": None
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