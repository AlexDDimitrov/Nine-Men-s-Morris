import random
import copy
from collections import defaultdict
import json

class MCTSBot:
    def __init__(self, name="Morris"):
        self.name = name
        self.visits = defaultdict(int)
        self.wins = defaultdict(int)

    def _get_state_key(self, game):
        return (tuple(game.board), game.player, game.phase.name)
    
    def _simulate(self, game):
        simulation_game = game.copy()

        states_visited = []
        moves_made = 0
        limit = 100

        while not simulation_game.is_over() and moves_made < limit:
            current_state = self._get_state_key(simulation_game)
            states_visited.append(current_state, simulation_game.player)

            if simulation_game.must_remove:
                removed_pin = simulation_game.get_removable()
                if removed_pin:
                    simulation_game.remove(random.choice(removed_pin))
                else:
                    simulation_game.must_remove = False
                continue

            if simulation_game.phase.name == "PLACEMENT":
                valid_place = simulation_game.ger_valid_placements()
                if not valid_place:
                    break
                simulation_game.place(random.choice(valid_place))
            
            else:
                ai_pieces = [
                    i for i in range(24) if simulation_game.board[i] == simulation_game.player
                ]

                possible_moves = []

                for pin in ai_pieces:
                    for target in simulation_game.get_valid_moves(pin):
                        possible_moves.append((pin, target))
                
                if not possible_moves: 
                    break

                chosen_move = random.choice(possible_moves)
                simulation_game.move(chosen_move[0], chosen_move[1])

            moves_made+=1
        
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

    def get_best_movement(self, game, num_simulations=1000):
        for _ in range(num_simulations):
            self._simulate(game)
        
        possible_moves = []
        if game.must_remove:
            for r in game.get_removable():
                possible_moves.append(("remove", r))
        elif game.phase.name == "PLACEMENT":
            for p in game.ger_valid_placements():
                possible_moves.append(("place", p))
        else:
            ai_pieces = [
                i for i in range(24) if game.board[i] == game.player
            ]

            for pin in ai_pieces:
                for target in game.get_valid_moves(pin):
                    possible_moves.append(("move", pin, target))
            
        if not possible_moves:
            return None
        
        best_move = None
        best_win_rate = -1.0

        for move in possible_moves:
            test_game = game.copy()
            if move[0] == "remove":
                test_game.remove(move[1])
            elif move[0] == "place":
                test_game.place(move[1])
            else:
                test_game.move(move[1], move[2])

            next_state_key = self._get_state_key(test_game)
            visits = self.visits[next_state_key]
            wins = self.wins[next_state_key]
        
            if visits > 0:
                win_rate = wins / visits
            else:
                win_rate = 0.0
            
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_move = move

        return best_move
