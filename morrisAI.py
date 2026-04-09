import random
import copy
from collections import defaultdict

class MCTSBot:
    def __init__(self, name="Morris"):
        self.name = name
        self.visits = defaultdict(int)
        self.wins = defaultdict(int)

    def _get_state_key(self, game):
        return (tuple(game.board), game.player, game.phase.name)

    def _simulate(self, game):
        simulation_game = copy.deepcopy(game)

        states_visited = []
        moves_made = 0
        limit = 100

        while not simulation_game.is_over() and moves_made < limit:
            current_state = self._get_state_key(simulation_game)
            states_visited.append((current_state, simulation_game.player))

            if simulation_game.must_remove:
                removable = simulation_game.get_removable()
                if removable:
                    simulation_game.remove(random.choice(removable))
                else:
                    simulation_game.must_remove = False
                continue

            if simulation_game.phase.name == "PLACEMENT":
                valid_place = simulation_game.get_valid_placements()
                if not valid_place:
                    break
                simulation_game.place(random.choice(valid_place))

            else:
                ai_pieces = [
                    i for i in range(24)
                    if simulation_game.board[i] == simulation_game.player
                ]
                possible_moves = []
                for pin in ai_pieces:
                    for target in simulation_game.get_valid_moves(pin):
                        possible_moves.append((pin, target))

                if not possible_moves:
                    break

                chosen_move = random.choice(possible_moves)
                simulation_game.move(chosen_move[0], chosen_move[1])

            moves_made += 1

        winner = None
        if simulation_game.winner == "WHITE":
            winner = 1
        elif simulation_game.winner == "BLACK":
            winner = 2
        else:
            if simulation_game.white_board > simulation_game.black_board:
                winner = 1
            elif simulation_game.white_board < simulation_game.black_board:
                winner = 2

        for state_key, player_at_turn in states_visited:
            self.visits[state_key] += 1
            if player_at_turn == winner:
                self.wins[state_key] += 1

    def _get_candidate_moves(self, game):
        if game.must_remove:
            return [("remove", r) for r in game.get_removable()]

        if game.phase.name == "PLACEMENT":
            return [("place", p) for p in game.get_valid_placements()]

        ai_pieces = [i for i in range(24) if game.board[i] == game.player]
        moves = []
        for pin in ai_pieces:
            for target in game.get_valid_moves(pin):
                moves.append(("move", pin, target))
        return moves

    def _apply_move(self, game, move):
        g = copy.deepcopy(game)
        if move[0] == "remove":
            g.remove(move[1])
        elif move[0] == "place":
            g.place(move[1])
        else:
            g.move(move[1], move[2])
        return g

    def get_best_action(self, game, num_simulations=5000):
        candidate_moves = self._get_candidate_moves(game)
        if not candidate_moves:
            return None

        for _ in range(num_simulations):
            move = random.choice(candidate_moves)
            next_game = self._apply_move(game, move)
            self._simulate(next_game)

        best_move = None
        best_win_rate = -1.0

        for move in candidate_moves:
            next_game = self._apply_move(game, move)
            state_key = self._get_state_key(next_game)
            visits = self.visits[state_key]
            wins = self.wins[state_key]
            win_rate = wins / visits if visits > 0 else 0.0

            if next_game.must_remove:
                win_rate+= 1000
                

            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_move = move

        return best_move