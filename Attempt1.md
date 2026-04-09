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

The bot uses **Monte Carlo Tree Search (MCTS)** — a simulation-based decision algorithm. Instead of computing the best move by exhaustive analysis, it simulates thousands of random games and tracks which moves tend to win.

#### Attributes

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Bot's display name |
| `visits` | `defaultdict(int)` | How many times has the bot seen this exact board layout |
| `wins` | `defaultdict(int)` | How many of those simulations ended in a win |

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
- If `simulation_game.winner` is set
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

Calculate win_rate = wins[state] / visits[state].

- Return the candidate move that has the highest win rate.

Simulations run from the resulting state after each move, so the stats collected directly reflect the quality of that move's outcome.

---

## AI vs AI — The Bug

When running a `MCTSBot` instance against a player, the game enters a Ai vs Ai regime where they play against one another until one wins.