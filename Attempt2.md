# Nine Men's Morris — Codebase Documentation

## Overview

The project is split into three files:

- **`morris.py`** — the game engine, rule enforcement, and a Flask REST API
- **`morrisAI.py`** — an MCTS (Monte Carlo Tree Search) bot that plays the game
- **`morris-P-vs-AI.py`** - connects everything

---

## `morris.py`

### Phase (Enum)

Tracks which of the three game phases is active.

| Value | Meaning |
|---|---|
| `PLACEMENT` | Players take turns placing their 9 pieces on the board |
| `MOVEMENT` | Players move pieces to adjacent positions |
| `FLYING` | Triggered when a player drops to 3 pieces — they can move anywhere |

---

### Game

The core game class. Holds all state and enforces all rules.

#### Board Layout

24 positions indexed 0–23, stored in a flat list:

- `0` = empty
- `1` = White's piece
- `2` = Black's piece

#### Key Attributes

| Attribute | Type | Description |
|---|---|---|
| `board` | `list[int]` | 24-element list representing the board |
| `phase` | `Phase` | Current game phase |
| `player` | `int` | Current player (1 = White, 2 = Black) |
| `white_placed` | `int` | Total pieces White has placed |
| `black_placed` | `int` | Total pieces Black has placed |
| `white_board` | `int` | White's pieces currently on the board |
| `black_board` | `int` | Black's pieces currently on the board |
| `must_remove` | `bool` | `True` when the current player just formed a mill and must remove an opponent piece |
| `winner` | `str or None` | `"WHITE"`, `"BLACK"`, or `None` if ongoing |
| `history` | `list` | Log of all moves made |

#### Adjacency (`ADJACENT`)

A dict mapping each position to its list of adjacent positions. Used to validate moves in `MOVEMENT` phase.

#### Mills (`MILLS`)

All 16 possible three-in-a-row combinations. Used to detect mill formation and identify mill-protected pieces.

---

#### Methods

**`place(pos)`** — Places a piece. Fails if not in `PLACEMENT` or position is occupied. Sets `must_remove` if a mill is formed. Switches phase to `MOVEMENT` once both players have placed all 9 pieces.

**`move(from_pos, to_pos)`** — Moves a piece. In `MOVEMENT`, target must be adjacent. In `FLYING`, target can be anywhere. Sets `must_remove` if a mill is formed. Transitions to `FLYING` if the moving player drops to 3 pieces.

**`remove(pos)`** — Removes an opponent piece after a mill. Mill-protected pieces are blocked unless all opponent pieces are in mills.

**`get_valid_placements()`** — Returns all empty positions.

**`get_valid_moves(pos)`** — Returns valid destinations for a piece: adjacent empties in `MOVEMENT`, all empties in `FLYING`.

**`get_removable()`** — Returns legally removable opponent pieces.

**`is_over()`** — Returns `True` if `winner` is set.

---

#### Win Conditions

A player wins if:
1. The opponent drops below 3 pieces on the board (after placement ends), or
2. The opponent has no valid moves in `MOVEMENT` or `FLYING` phase

---

### Flask REST API

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/state` | — | Full game state as JSON |
| `POST` | `/place` | `{"pos": N}` | Place a piece |
| `POST` | `/move` | `{"from": N, "to": N}` | Move a piece |
| `POST` | `/remove` | `{"pos": N}` | Remove an opponent piece |
| `GET` | `/valid_placements` | — | All empty positions |
| `POST` | `/valid_moves` | `{"pos": N}` | Valid destinations for a piece |
| `GET` | `/removable` | — | Removable opponent pieces |

---

## `morrisAI.py`

### MCTSBot — How It Works

The bot uses an **Adaptive Monte Carlo Tree Search (MCTS)**. It simulates thousands of random games to find mathematically strong moves, but it is also actively attacks, defends, and learns from the player's habits dynamically.

#### Attributes

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Bot's display name |
| `visits` | `defaultdict(int)` | How many times has the bot seen this exact board layout |
| `wins` | `defaultdict(int)` | How many of those simulations ended in a win |
| `player_heatmap` | `defaultdict(int)` | NEW: Tracks the human player's preferred placement positions |

#### State Key — `_get_state_key(game)`

Each unique game state is identified by:
```
(tuple of board contents, current player, phase name)
```
This tuple is the dictionary key for `visits` and `wins`, so every distinct board position is tracked separately.

---

### Step 1 — Get Candidate Moves — `_get_candidate_moves(game)`

Before simulating anything, the bot collects every legal action available right now:

- If `must_remove` is `True` -> list all removable opponent positions as `("remove", pos)`
- If phase is `PLACEMENT` -> list all empty positions as `("place", pos)`
- Otherwise -> loop over the bot's pieces and collect all valid destinations as `("move", from, to)`

---

### Step 2 — Apply a Move — `_apply_move(game, move)`

Takes a deep copy of the game and applies a single action to it, returning the new game state without touching the real game. This lets the bot explore hypothetical futures safely.

---

### Step 3 — Simulate — `_simulate(game)`

Runs one full random playout from a given game state, up to a 100-move limit.

**Each step of the loop:**
1. Record the current state key and whose turn it is into `states_visited`
2. If `must_remove` is set -> pick a random removable piece and call `remove()`
3. Else if phase is `PLACEMENT` -> pick a random empty position and call `place()`
4. Else -> collect all possible moves for all the current player's pieces, pick one randomly, call `move()`
5. If no moves are available -> break out of the loop

**After the loop ends**, determine the winner:
- If `simulation_game.winner` is set -> the winner is displayed directly
- If the limit was hit with no winner -> whichever player has more pieces on the board is treated as the winner for scoring purposes

**Update the stats tables:**
```
for every state visited during this simulation:
    visits[state] += 1
    if the player whose turn it was at that state ended up winning:
        wins[state] += 1
```

---

### Step 4 — Pick the Best Move — `get_best_action(game, num_simulations=1000)`

- Run _simulate(game) 1000 times starting from the current, real board state. This fills up the visits and wins dictionary.

- Get all immediate Candidate Moves available right now.

For each candidate move:

- Apply it to a temporary copy of the game to get the resulting state key.

- Look up that specific state key in the dictionary.

- Calculate win_rate = wins[state] / visits[state].

Apply Adaptive AI Heuristics:
- Instead of relying purely on random simulations, the bot modifies the win_rate score based on immediate board analysis and player behavior:

- Attack Instinct: If the move results in a mill (must_remove becomes True), add +1000 points. 

- Defense Instinct: The bot simulates the opponent's next possible responses. If any of those responses allow the opponent to form a mill, subtract -500 points. 

- Adaptive Learning (Heatmap Response): If in the PLACEMENT phase, the bot checks its player_heatmap. It adds a bonus (times_player_played_here * 100) to positions the player likes. The bot actively adapts its strategy to block the player's favorite zones.

- Return the candidate move that has the highest total score.

Simulations and heuristic adjustments run from the resulting state after each move.

## Resolved Bugs & Structural Improvements

### The "Blind AI" Misfunctionality (Resolved)
**The Issue:** The initial pure MCTS implementation resulted in an AI that felt "dumb" and lacked competitive instinct. It frequently ignored immediate opportunities to form its own mills or block the player's mills. This logical flaw occurred because pure MCTS relies strictly on random simulations that only reward the final end-game state. It failed to recognize the value of intermediate tactical goals (like forming a mill on move 10).
**The Fix:** Introduced a **Heuristic Evaluation Layer** inside `get_best_action`. By overriding the raw MCTS win-rate with immediate point bonuses (+1000 for attacking/forming a mill) and penalties (-500 for leaving a mill open to the opponent), the bot was successfully transformed from a random simulator into a highly responsive, aggressive, and defensive opponent.



