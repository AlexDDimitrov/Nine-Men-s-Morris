from enum import Enum
from threading import Thread
from flask import Flask, request, jsonify
from flask_cors import CORS


# ---------------------------------------------------------------------------
# Game Logic
# ---------------------------------------------------------------------------

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
        self.winner = None  # None | "WHITE" | "BLACK"

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


# ---------------------------------------------------------------------------
# Flask API — background thread, shares the same Game object as the CLI
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)

_session: dict = {}   # {"game": Game, "p1": str, "p2": str}


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


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

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

    # Each column is 1 char wide; connectors are exactly 3 chars.
    # Board columns (0-based char positions):
    #   col 0 → nodes 0, 9, 17          (left outer)
    #   col 1 → "═══" or "───"
    #   col 2 → nodes 1, 10, 16         (middle outer / middle)
    #   col 3 → "═══" or "───"
    #   col 4 → nodes 2, 11, 15         (right outer)
    #   gap of 5 chars between col4 and col6
    #   col 6 → nodes 12 / etc          (left inner-right half)
    # BUT the real layout is symmetric and the middle column (node 1,4,7 etc)
    # sits dead-centre.  We build each row as a plain string so every character
    # lands in exactly the right place.
    #
    # Fixed grid (each cell = 1 char, connectors = 3 chars):
    # positions per row:
    #   Row 0:  [0]═══[1]═══[2]
    #   Row 1:  ║  [3]═[4]═[5]  ║
    #   Row 2:  ║  ║  [6]=[7]=[8]  ║  ║      <- 8 connects right to 12
    #   Row 3:  [9]─[10]─[11]   [12]─[13]─[14]
    #   Row 4:  ║  ║  [21]=[22]=[23]  ║  ║
    #   Row 5:  ║  [19]═[20]═[18]  ║
    #   Row 6:  [17]═══[16]═══[15]
    #
    # We use a 13-char wide grid (indices 0-12):
    #  0   1   2   3   4   5   6   7   8   9  10  11  12
    # n0  ──  n1  ──  n2  sp  sp  sp  n5  ──  n6  ──  n7  ...
    # That doesn't work cleanly either.  Simplest: just hardcode
    # each row with f-strings that use exactly the right padding.

    # The outer square spans columns: 0, 4, 8  (nodes 0,1,2 / 9,10+11,12+13+14 / 17,16,15)
    # Wait — row 3 has 6 nodes.  Let's use this fixed layout:
    #
    #  0 ═══════ 1 ═══════ 2          <- outer top,  width = 0+3+1+3+1 = 8 chars from node0
    #  ║   3 ═══ 4 ═══ 5   ║
    #  ║   ║ 6 ═ 7 ═ 8 ║   ║
    #  9─10─11       12─13─14
    #  ║   ║21 ═22 ═23 ║   ║
    #  ║   19 ═ 20 ═ 18    ║
    #  17═══════16═══════15
    #
    # Node columns (0-indexed chars, each node = 1 char wide):
    #   col  0 : 0, 9, 17
    #   col  1 : connector (3 chars: cols 1-3)
    #   col  4 : 1, 10, 16        <- MIDDLE
    #   col  5 : connector (3 chars: cols 5-7)
    #   col  8 : 2, 11, 15
    #   col  9 : "   "  gap (3 spaces)
    #   col 12 : 12 (mirrors col 0 on right half)  … wait this is 6-node row
    #
    # The 6-node middle row forces: left-half ends at col 8, right half starts at col 12.
    # Gap = cols 9-11 = "   " (3 spaces).
    # So total width = 8+3+5 = ... let's just count exactly:
    #
    # "█═══█═══█   █═══█═══█"   21 chars
    #  0123456789012345678901
    # col of each node: 0, 4, 8, 12, 16, 20
    # Inner nodes (3,4,5) and (21,22,23) sit at cols 2, 4, 6  and 14, 16, 18
    # Innermost (6,7,8) and (21... no: 6,7,8 are cols 3,4,5? no.
    #
    # Let's fix col positions:
    #  outer nodes:  col 0, 4, 8      /  col 12, 16, 20
    #  middle nodes: col 2, 4, 6      /  col 14, 16, 18   <- share col 4 and 16 with outer mid
    #  inner nodes:  col 3, 4, 5      /  col 15, 16, 17   <- too close
    #
    # Easier: adopt the exact same spacing as the reference image.
    # Reference image shows 7 columns of nodes:
    #   c0   c1   c2   c3   c4   c5   c6
    #   0         1              2
    #        3    4    5
    #             6    7    8
    #   9   10   11        12   13   14
    #            21   22   23
    #       19   20   18
    #  17        16             15
    #
    # So the 7 logical columns are:
    #  c0=outer-left, c1=mid-left, c2=inner-left, c3=centre,
    #  c4=inner-right, c5=mid-right, c6=outer-right
    # but nodes 1,4,7 sit at c3 (centre), and the board is symmetric.
    # Column char positions (each node = 1 char, connectors fill between):
    #   c0=0, c1=4, c2=8, c3=12, c4=16, c5=20, c6=24   (step=4, connector="═══ ")
    # But we need connectors only between adjacent cols, and each connector = 3 chars
    # between 1-char nodes means step = 4.  Total width = 25 chars.
    #
    # Now map nodes to (row, col):
    #  0→(0,c0)  1→(0,c3)  2→(0,c6)
    #  3→(1,c1)  4→(1,c3)  5→(1,c5)
    #  6→(2,c2)  7→(2,c3)  8→(2,c4)
    #  9→(3,c0) 10→(3,c1) 11→(3,c2)   12→(3,c4) 13→(3,c5) 14→(3,c6)
    # 21→(4,c2) 22→(4,c3) 23→(4,c4)
    # 19→(5,c1) 20→(5,c3) 18→(5,c5)
    # 17→(6,c0) 16→(6,c3) 15→(6,c6)
    #
    # With step=4 and connector="───" (3 chars):
    #   c0= 0, c1= 4, c2= 8, c3=12, c4=16, c5=20, c6=24
    #
    # Vertical pipes sit at the column of their node, spanning rows.

    S = " "   # space char
    C = "─"   # connector char (empty)
    CE = "═"  # connector char (both empty)

    def hc(a, z):
        """3-char horizontal connector."""
        return "═══" if b[a] == 0 and b[z] == 0 else "───"

    def sp(n):
        return " " * n

    # Build each row as a 25-char string
    # Vertical edge chars between rows (at fixed columns)
    def vrow(c0=S, c1=S, c2=S, c3=S, c4=S, c5=S, c6=S):
        # cols: 0,4,8,12,16,20,24
        row = [S] * 25
        for col, ch in [(0,c0),(4,c1),(8,c2),(12,c3),(16,c4),(20,c5),(24,c6)]:
            row[col] = ch
        return "  " + "".join(row)

    def fill(base, start, end, ch):
        for i in range(start, end):
            base[i] = ch

    def build_row(nodes, connectors, prefix="  "):
        """
        nodes: dict of col_index -> char
        connectors: list of (start_col, end_col, char)
        """
        row = [" "] * 25
        for col, ch in nodes.items():
            row[col] = ch
        for start, end, ch in connectors:
            for i in range(start, end):
                row[i] = ch
        return prefix + "".join(row)

    # Row 0: nodes 0(c0=0), 1(c3=12), 2(c6=24)  connected 0-12, 12-24
    r0 = build_row(
        {0: p(0), 12: p(1), 24: p(2)},
        [(1, 12, "═" if b[0]==0 and b[1]==0 else "─"),
         (13, 24, "═" if b[1]==0 and b[2]==0 else "─")]
    )

    # Row 1: nodes 3(c1=4), 4(c3=12), 5(c5=20), vertical at 0 and 24
    r1 = build_row(
        {0: "║", 4: p(3), 12: p(4), 20: p(5), 24: "║"},
        [(5, 12, "═" if b[3]==0 and b[4]==0 else "─"),
         (13, 20, "═" if b[4]==0 and b[5]==0 else "─")]
    )

    # Row 2: nodes 6(c2=8), 7(c3=12), 8(c4=16), verticals at 0,4 and 20,24
    r2 = build_row(
        {0: "║", 4: "║", 8: p(6), 12: p(7), 16: p(8), 20: "║", 24: "║"},
        [(9, 12, "═" if b[6]==0 and b[7]==0 else "─"),
         (13, 16, "═" if b[7]==0 and b[8]==0 else "─")]
    )

    # Row 3: nodes 9(0),10(4),11(8)  and  12(16),13(20),14(24)  gap at 9-15
    r3 = build_row(
        {0: p(9), 4: p(10), 8: p(11), 16: p(12), 20: p(13), 24: p(14)},
        [(1,  4,  "═" if b[9]==0  and b[10]==0 else "─"),
         (5,  8,  "═" if b[10]==0 and b[11]==0 else "─"),
         (17, 20, "═" if b[12]==0 and b[13]==0 else "─"),
         (21, 24, "═" if b[13]==0 and b[14]==0 else "─")]
    )

    # Row 4: nodes 21(c2=8), 22(c3=12), 23(c4=16), verticals at 0,4 and 20,24
    r4 = build_row(
        {0: "║", 4: "║", 8: p(21), 12: p(22), 16: p(23), 20: "║", 24: "║"},
        [(9, 12, "═" if b[21]==0 and b[22]==0 else "─"),
         (13, 16, "═" if b[22]==0 and b[23]==0 else "─")]
    )

    # Row 5: nodes 19(c1=4), 20(c3=12), 18(c5=20), verticals at 0 and 24
    r5 = build_row(
        {0: "║", 4: p(19), 12: p(20), 20: p(18), 24: "║"},
        [(5, 12, "═" if b[19]==0 and b[20]==0 else "─"),
         (13, 20, "═" if b[20]==0 and b[18]==0 else "─")]
    )

    # Row 6: nodes 17(c0=0), 16(c3=12), 15(c6=24)
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
    display(game, p1_name, p2_name)
    print(f"  >> {player_name}'s turn ({'W' if player_num == 1 else 'B'})\n")

    if game.phase == Phase.PLACEMENT:
        valid = game.get_valid_placements()
        print(f"  Valid placements: {valid}")
        pos = ask_int(f"  {player_name}, choose a position to place: ", valid)
        ok, msg = game.place(pos)
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

    else:
        my_pieces = [i for i in range(24) if game.board[i] == player_num]
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