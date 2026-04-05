from enum import Enum
from threading import Thread
from flask import Flask, request, jsonify
from flask_cors import CORS
class Phase(Enum):
    PLACEMENT = 1
    MOVEMENT = 2
    FLYING = 3
class Game:
    ADJACENT = {
        0: [1, 9],   1: [0, 2, 4],  2: [1, 5],
        3: [4, 10],  4: [1, 3, 5, 7], 5: [2, 4, 8],
        6: [7, 11],  7: [4, 6, 8],  8: [5, 7, 12],
        9: [0, 10, 17], 10: [3, 9, 11, 20], 11: [6, 10, 12],
        12: [8, 11, 13], 13: [12, 14, 22], 14: [13, 15, 18],
        15: [14, 16], 16: [15, 17, 19], 17: [9, 16, 18],
        18: [14, 17, 23], 19: [16, 20], 20: [10, 19, 21],
        21: [20, 22], 22: [13, 21, 23], 23: [18, 22],
    }

    MILLS = [
        (0, 1, 2), (9, 10, 11), (12, 13, 14), (15, 16, 17),
        (0, 9, 17), (2, 14, 15), (1, 10, 18), (8, 12, 5),
        (3, 4, 5), (10, 11, 12), (13, 14, 15), (19, 20, 21),
        (3, 10, 19), (5, 12, 18), (4, 11, 20), (8, 13, 21),
        (6, 7, 8), (11, 12, 13), (16, 17, 18), (21, 22, 23),
        (6, 11, 16), (8, 13, 23), (7, 12, 22), (7, 11, 20),
    ]

    def __init__(self):
        self.board = [0] * 24
        self.phase = Phase.PLACEMENT
        self.player = 1
        self.white_placed = 0
        self.black_placed = 0
        self.white_board = 0
        self.black_board = 0
        self.history = []
        self.must_remove = False
        self.winner = None

    def _has_mill(self, pos, player):
        for mill in self.MILLS:
            if pos in mill and all(self.board[p] == player for p in mill):
                return True
        return False

    def _get_removable(self, player):
        opponent = 2 if player == 1 else 1
        non_mill = [
            i for i in range(24)
            if self.board[i] == opponent
            and not any(i in mill and all(self.board[p] == opponent for p in mill)
                        for mill in self.MILLS)
        ]
        if non_mill:
            return non_mill
        return [i for i in range(24) if self.board[i] == opponent]

    def _check_winner(self):
        if self.phase != Phase.PLACEMENT:
            if self.white_board < 3:
                self.winner = "BLACK"
                return True
            if self.black_board < 3:
                self.winner = "WHITE"
                return True
        return False

    def _switch_player(self):
        self.player = 2 if self.player == 1 else 1

    def place(self, pos):
        if self.phase != Phase.PLACEMENT:
            return False, "Not in placement phase."
        if self.board[pos] != 0:
            return False, "That position is already occupied."

        player = self.player
        self.board[pos] = player
        if player == 1:
            self.white_placed += 1
            self.white_board += 1
        else:
            self.black_placed += 1
            self.black_board += 1
        self.history.append(("place", player, pos))

        if self._has_mill(pos, player):
            self.must_remove = True
            return True, "MILL! Remove an opponent's piece."

        self._switch_player()
        if self.white_placed == 9 and self.black_placed == 9:
            self.phase = Phase.MOVEMENT
        return True, "OK"

    def remove(self, pos):
        if not self.must_remove:
            return False, "No mill to trigger a removal."
        player = self.player
        opponent = 2 if player == 1 else 1
        if self.board[pos] != opponent:
            return False, "That is not an opponent's piece."
        if pos not in self._get_removable(player):
            return False, "You cannot remove that piece (it is protected in a mill)."

        self.board[pos] = 0
        if player == 1:
            self.black_board -= 1
        else:
            self.white_board -= 1
        self.history.append(("remove", player, pos))
        self.must_remove = False

        if self._check_winner():
            return True, f"{self.winner} WINS"

        self._switch_player()
        return True, "OK"

    def move(self, from_pos, to_pos):
        if self.phase not in (Phase.MOVEMENT, Phase.FLYING):
            return False, "Not in movement phase."
        if self.board[from_pos] != self.player:
            return False, "No piece of yours at that position."
        if self.board[to_pos] != 0:
            return False, "Target position is occupied."
        if self.phase == Phase.MOVEMENT and to_pos not in self.ADJACENT[from_pos]:
            return False, "That position is not adjacent."

        player = self.player
        self.board[from_pos] = 0
        self.board[to_pos] = player
        self.history.append(("move", player, from_pos, to_pos))

        if self._has_mill(to_pos, player):
            self.must_remove = True
            return True, "MILL! Remove an opponent's piece."

        if sum(1 for x in self.board if x == player) == 3:
            self.phase = Phase.FLYING

        self._switch_player()
        return True, "OK"

    def get_valid_placements(self):
        return [i for i in range(24) if self.board[i] == 0]

    def get_valid_moves(self, pos):
        if self.board[pos] != self.player:
            return []
        if self.phase == Phase.FLYING:
            return [i for i in range(24) if self.board[i] == 0]
        return [i for i in self.ADJACENT[pos] if self.board[i] == 0]

    def get_removable(self):
        if not self.must_remove:
            return []
        return self._get_removable(self.player)

    def is_over(self):
        return self.winner is not None

    def to_dict(self, p1_name="White", p2_name="Black"):
        return {
            "board": self.board,
            "phase": self.phase.name,
            "player": self.player,
            "player_name": p1_name if self.player == 1 else p2_name,
            "white_name": p1_name,
            "black_name": p2_name,
            "white_board": self.white_board,
            "black_board": self.black_board,
            "white_placed": self.white_placed,
            "black_placed": self.black_placed,
            "must_remove": self.must_remove,
            "winner": self.winner,
            "history": self.history,
        }

app = Flask(__name__)
CORS(app)

_session: dict = {}

def _state():
    if not _session:
        return None
    return _session["game"].to_dict(_session["p1"], _session["p2"])

@app.route("/state", methods=["GET"])
def api_state():
    d = _state()
    return jsonify(d) if d else (jsonify({"error": "No game in progress."}), 404)

@app.route("/place", methods=["POST"])
def api_place():
    if not _session:
        return jsonify({"error": "No game in progress."}), 404
    ok, msg = _session["game"].place(request.json.get("pos"))
    return jsonify({"ok": ok, "msg": msg, "state": _state()})

@app.route("/remove", methods=["POST"])
def api_remove():
    if not _session:
        return jsonify({"error": "No game in progress."}), 404
    ok, msg = _session["game"].remove(request.json.get("pos"))
    return jsonify({"ok": ok, "msg": msg, "state": _state()})

@app.route("/move", methods=["POST"])
def api_move():
    if not _session:
        return jsonify({"error": "No game in progress."}), 404
    d = request.json
    ok, msg = _session["game"].move(d.get("from"), d.get("to"))
    return jsonify({"ok": ok, "msg": msg, "state": _state()})

@app.route("/valid_placements", methods=["GET"])
def api_valid_placements():
    if not _session:
        return jsonify({"error": "No game in progress."}), 404
    return jsonify({"positions": _session["game"].get_valid_placements()})

@app.route("/valid_moves", methods=["POST"])
def api_valid_moves():
    if not _session:
        return jsonify({"error": "No game in progress."}), 404
    return jsonify({"moves": _session["game"].get_valid_moves(request.json.get("pos"))})

@app.route("/removable", methods=["GET"])
def api_removable():
    if not _session:
        return jsonify({"error": "No game in progress."}), 404
    return jsonify({"positions": _session["game"].get_removable()})


def start_server(port=5000):
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # silence request logs
    Thread(
        target=lambda: app.run(port=port, debug=False, use_reloader=False),
        daemon=True
    ).start()
    print(f"  [API] Flask running on http://localhost:{port}\n")

def ask_int(prompt, valid=None):
    while True:
        raw = input(prompt).strip()
        if not raw.isdigit():
            print("  Please enter a number.")
            continue
        n = int(raw)
        if valid is not None and n not in valid:
            print(f"  Invalid choice. Valid options: {valid}")
            continue
        return n


def display(game, p1_name, p2_name):
    b = game.board

    def p(i):
        if b[i] == 1: return "O"
        if b[i] == 2: return "X"
        return "█"

    def h(a, z):
        return "═══" if b[a] == 0 and b[z] == 0 else "───"

    S = " "
    C = "─"
    CE = "═"

    def hc(a, z):
        """3-char horizontal connector."""
        return "═══" if b[a] == 0 and b[z] == 0 else "───"

    def sp(n):
        return " " * n

    def vrow(c0=S, c1=S, c2=S, c3=S, c4=S, c5=S, c6=S):
        row = [S] * 25
        for col, ch in [(0,c0),(4,c1),(8,c2),(12,c3),(16,c4),(20,c5),(24,c6)]:
            row[col] = ch
        return "  " + "".join(row)

    def fill(base, start, end, ch):
        for i in range(start, end):
            base[i] = ch

    def build_row(nodes, connectors, prefix="  "):
        row = [" "] * 25
        for col, ch in nodes.items():
            row[col] = ch
        for start, end, ch in connectors:
            for i in range(start, end):
                row[i] = ch
        return prefix + "".join(row)

    r0 = build_row(
        {0: p(0), 12: p(1), 24: p(2)},
        [(1, 12, "═" if b[0]==0 and b[1]==0 else "─"),
         (13, 24, "═" if b[1]==0 and b[2]==0 else "─")]
    )

    r1 = build_row(
        {0: "║", 4: p(3), 12: p(4), 20: p(5), 24: "║"},
        [(5, 12, "═" if b[3]==0 and b[4]==0 else "─"),
         (13, 20, "═" if b[4]==0 and b[5]==0 else "─")]
    )

    r2 = build_row(
        {0: "║", 4: "║", 8: p(6), 12: p(7), 16: p(8), 20: "║", 24: "║"},
        [(9, 12, "═" if b[6]==0 and b[7]==0 else "─"),
         (13, 16, "═" if b[7]==0 and b[8]==0 else "─")]
    )

    r3 = build_row(
        {0: p(9), 4: p(10), 8: p(11), 16: p(12), 20: p(13), 24: p(14)},
        [(1,  4,  "═" if b[9]==0  and b[10]==0 else "─"),
         (5,  8,  "═" if b[10]==0 and b[11]==0 else "─"),
         (17, 20, "═" if b[12]==0 and b[13]==0 else "─"),
         (21, 24, "═" if b[13]==0 and b[14]==0 else "─")]
    )

    r4 = build_row(
        {0: "║", 4: "║", 8: p(21), 12: p(22), 16: p(23), 20: "║", 24: "║"},
        [(9, 12, "═" if b[21]==0 and b[22]==0 else "─"),
         (13, 16, "═" if b[22]==0 and b[23]==0 else "─")]
    )

    r5 = build_row(
        {0: "║", 4: p(19), 12: p(20), 20: p(18), 24: "║"},
        [(5, 12, "═" if b[19]==0 and b[20]==0 else "─"),
         (13, 20, "═" if b[20]==0 and b[18]==0 else "─")]
    )

    r6 = build_row(
        {0: p(17), 12: p(16), 24: p(15)},
        [(1, 12, "═" if b[17]==0 and b[16]==0 else "─"),
         (13, 24, "═" if b[16]==0 and b[15]==0 else "─")]
    )

    print()
    print(r0)
    print(r1)
    print(r2)
    print(r3)
    print(r4)
    print(r5)
    print(r6)
    print()
    print(f"  Pos:  0──────1──────2       O = {p1_name} (White)")
    print(f"        ║  3───4───5  ║       X = {p2_name} (Black)")
    print(f"        ║  ║ 6─7─8 ║  ║       █ = empty")
    print(f"        9─10─11   12─13─14")
    print(f"        ║  ║21─22─23║  ║")
    print(f"        ║  19──20──18  ║")
    print(f"        17──────16──────15")
    print()
    print(f"  {p1_name} (O): {game.white_board} on board | {9 - game.white_placed} left to place")
    print(f"  {p2_name} (X): {game.black_board} on board | {9 - game.black_placed} left to place")
    print(f"  Phase: {game.phase.name}")
    print()
    if game.must_remove:
        print("  *** MILL! You must remove an opponent's piece! ***")
        print()
    print()
    print(f"  {p1_name} (O): {game.white_board} on board | {9 - game.white_placed} left to place")
    print(f"  {p2_name} (X): {game.black_board} on board | {9 - game.black_placed} left to place")
    print(f"  Phase: {game.phase.name}")
    print()
    if game.must_remove:
        print("  *** MILL! You must remove an opponent's piece! ***")
        print()

def player_turn(game, player_num, player_name, p1_name, p2_name):
    print(f"  >> {player_name}'s turn ({'W' if player_num == 1 else 'B'})\n")

    if game.phase == Phase.PLACEMENT:
        valid = game.get_valid_placements()

        display(game, p1_name, p2_name)

        print_big_board(game)
        print(f"  Valid placements: {valid}")
        pos = ask_int(f"  {player_name}, choose a position to place: ", valid)
        ok, msg = game.place(pos)
        if not ok:
            print(f"  Error: {msg}")
            return False
        print(f"  {msg}")

        if game.must_remove:
            removable = game.get_removable()
            print_big_board(game)
            print(f"  Removable opponent pieces: {removable}")
            rpos = ask_int(f"  {player_name}, choose a piece to remove: ", removable)
            ok, msg = game.remove(rpos)
            if not ok:
                print(f"  Error: {msg}")
                return False
            print(f"  Removed piece at {rpos}. {msg}")
            if "WINS" in msg:
                return msg

    else:
        my_pieces = [i for i in range(24) if game.board[i] == player_num]
        print_big_board(game)
        print(f"  Your pieces: {my_pieces}")
        from_pos = ask_int(f"  {player_name}, choose a piece to move (from): ", my_pieces)

        valid_moves = game.get_valid_moves(from_pos)
        if not valid_moves:
            print("  That piece has no valid moves. Choose another.")
            return False

        print(f"  Valid destinations: {valid_moves}")
        to_pos = ask_int(f"  {player_name}, choose destination (to): ", valid_moves)
        ok, msg = game.move(from_pos, to_pos)
        if not ok:
            print(f"  Error: {msg}")
            return False
        print(f"  {msg}")

        if game.must_remove:
            removable = game.get_removable()
            print(f"  Removable opponent pieces: {removable}")
            rpos = ask_int(f"  {player_name}, choose a piece to remove: ", removable)
            ok, msg = game.remove(rpos)
            if not ok:
                print(f"  Error: {msg}")
                return False
            print(f"  Removed piece at {rpos}. {msg}")
            if "WINS" in msg:
                return msg

    return True

def print_big_board(game):
    b = game.board

    def p(i):
        if b[i] == 1: return "O"
        if b[i] == 2: return "X"
        return "█"

    print()
    print(f"  {p(0)}───────────{p(1)}═══════════{p(2)}")
    print(f"  ║   {p(3)}═══════{p(4)}═══════{p(5)}   ║")
    print(f"  ║   ║   {p(6)}═══{p(7)}═══{p(8)}   ║   ║")
    print(f"  {p(9)}───{p(10)}═══{p(11)}       {p(12)}═══{p(13)}═══{p(14)}")
    print(f"  ║   ║   {p(21)}═══{p(22)}═══{p(23)}   ║   ║")
    print(f"  ║   {p(19)}═══════{p(20)}═══════{p(18)}   ║")
    print(f"  {p(17)}═══════════{p(16)}═══════════{p(15)}")
    print()

def play():
    print("=" * 50)
    print("     NINE MEN'S MORRIS — Two Player")
    print("=" * 50)
    print()

    p1_name = input("  White player name (Enter for 'White'): ").strip() or "White"
    p2_name = input("  Black player name (Enter for 'Black'): ").strip() or "Black"

    game = Game()
    _session["game"] = game
    _session["p1"] = p1_name
    _session["p2"] = p2_name

    print(f"\n  {p1_name} (White) vs {p2_name} (Black)")
    print("  White goes first.\n")
    input("  Press Enter to start...")

    while True:
        player_num = game.player
        player_name = p1_name if player_num == 1 else p2_name

        result = player_turn(game, player_num, player_name, p1_name, p2_name)

        if isinstance(result, str) and "WINS" in result:
            display(game, p1_name, p2_name)
            winner = p1_name if "WHITE" in result else p2_name
            print(f"\n  *** {winner} WINS! Congratulations! ***\n")
            break

        if game.is_over():
            display(game, p1_name, p2_name)
            winner = p2_name if game.white_board < 3 else p1_name
            print(f"\n  *** {winner} WINS! Congratulations! ***\n")
            break


if __name__ == "__main__":
    start_server(port=5000)
    try:
        play()
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!")