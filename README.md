LangGraph D&D Game — Agentic RAG Dungeon Crawler

A text-based dungeon adventure built with LangGraph, Google Gemini, and Chroma as a hands-on exploration of agentic architecture and retrieval-augmented generation (RAG).

Instead of retrieving lore on every turn (naive RAG), each agent node decides at runtime whether the player's action warrants pulling lore from the vector store — combat, exploration, and item interactions each make their own conditional retrieval judgment before generating narration.

Features
Character selection — choose between three characters, each with a unique backstory and starter item
LangGraph state machine — turn-based game loop with conditional routing (combat / explore / item / other)
Human-in-the-loop — uses LangGraph's interrupt/Command(resume=...) pattern to pause execution and wait for real player input
Persistent checkpointing — game state is checkpointed via MemorySaver
Agentic RAG — combat, explore, and item nodes each check whether the player's action references known lore (an item or character by name) and conditionally query a Chroma vector store, rather than retrieving unconditionally every turn
Combat mechanics — equipped weapons affect damage rolls via stats stored separately from lore text
Architecture
select_character → init_character_state → get_input
                                               │
                                           classify
                                               │
                          ┌────────────────────┼────────────────────┐
                       combat                explore                item
                          │                     │                    │
                          └─────────────────────┼────────────────────┘
                                          check_status
                                               │
                                    ┌──────────┴──────────┐
                                 ending                 continue
                                    │                      │
                                   END              (back to get_input)

Each of combat, explore, and item follows the same internal pattern:

Check whether the player's action references a known item/character by name
If so, query the Chroma vector store for that entity's lore
Feed the retrieved lore (if any) into the LLM prompt
Generate narration and update game state
Project structure
main.py          # GameState, all nodes, graph wiring, game loop
lore_data.py     # Character and item data (stats + lore text), plain lookups
vectorstore.py   # Chroma setup, persistence, and retrieval (query_lore)
Setup
1. Install dependencies
bash
pip install langgraph langchain-google-genai langchain-chroma chromadb
2. Set your Google API key

This project reads your API key from an environment variable — it is never hardcoded in source.

Git Bash / macOS / Linux:

bash
export GOOGLE_API_KEY="your-key-here"

Windows (permanent, via System Environment Variables): Settings → System → About → Advanced system settings → Environment Variables → New (User variable) → GOOGLE_API_KEY

Get a key from Google AI Studio.

3. Run the game
bash
python main.py
How it plays
Choose a character from the selection menu
Type actions in plain English ("I attack the goblin", "I search the room", "I grab the sword")
The game classifies your action, routes it to the right agent, and narrates the outcome
Game ends when HP reaches 0 (death) or inventory reaches 3 items (win)
What this project demonstrates

Built as a practical exercise in agentic RAG — the goal was to move beyond "always retrieve" RAG patterns and build nodes that make a genuine runtime decision about whether retrieval is worth the cost, based on the actual content of user input. Combat, exploration, and item interactions each implement this decision independently, using simple keyword matching against a Chroma vector store built from character backstories and item lore.

Notes / known limitations
Item name matching uses case-insensitive substring matching, which can miss variations (e.g. possessives, plurals) — a semantic or LLM-based matching approach would be more robust
"Using" vs "acquiring" an item is not currently distinguished — both are handled by a single item agent
The vector store (dungeon_lore_db/) is generated locally on first run and is not committed to this repo — it will rebuild automatically
