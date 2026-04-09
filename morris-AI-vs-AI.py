from morrisAI import MCTSBot
from morris import Game, print_big_board

def main():
    print("Welcome to Morris! You will be playing against an AI bot. You will be playing as the first player (X).")
    myGame = Game()
    bot = MCTSBot(name = "MCTS Bot")

    while not myGame.is_over():
        print_big_board(myGame)
        print(f"Its {myGame.player}'s turn, phase: {myGame.phase.name}")

        if myGame.player == "WHITE":
            print("Your turn!")
            if myGame.must_remove:
                print("You must remove an opponent's piece.")
                try:
                    target = int(input("Enter the position of the piece you want to remove (0-23): "))
                    if target in myGame.get_removable():
                        myGame.remove_piece(target)
                    else:
                        print("Invalid move. Try again.")
                except ValueError:
                    print("Invalid input. Please enter a number between 0 and 23.")
                continue
            elif myGame.phase == "Placement":
                print(f"Free positions: {myGame.get_valid_placements()}")
                try:
                    target = int(input("Enter the position where you want to place your piece (0-23): "))
                    if target in myGame.get_valid_placements():
                        myGame.place(target)
                    else:
                        print("Invalid move. Try again.")
                except ValueError:
                    print("Invalid input. Please enter a number between 0 and 23.")
            else:
                try:
                    start_pos = int(input("Enter the position of the piece you want to move (0-23): "))
                    valid_targets = myGame.get_valid_moves(start_pos)
                    if not valid_targets:
                        print("No valid moves for that piece. Try again.")
                        continue

                    print(f"Target positions: {valid_targets}")
                    end_pos = int(input("Enter the position where you want to move your piece (0-23): "))
                    if end_pos in valid_targets:
                        myGame.move(start_pos, end_pos)
                    else:
                        print("Invalid move. Try again.")
                except ValueError:
                    print("Invalid input. Please enter a number between 0 and 23.")
        else:
            print("AI is thinking...")
            best_action = bot.get_best_action(myGame, num_simulations=1000)
            if best_action is None:
                print("AI has no valid moves.")
                break
            action_type = best_action[0]

            if action_type == "remove":
                target_pos = best_action[1]
                myGame.remove(target_pos)
                print(f"AI removed your piece at position {target_pos}.")
            elif action_type == "place":
                target_pos = best_action[1]
                myGame.place(target_pos)
                print(f"AI placed a piece at position {target_pos}.")
            elif action_type == "move":
                start_pos = best_action[1]
                end_pos = best_action[2]
                myGame.move(start_pos, end_pos)
                print(f"AI moved a piece from position {start_pos} to position {end_pos}.")
    print("\n"+ '='*30)
    print("Game Over!")

    if myGame.winner == "WHITE":
        print("Congratulations! You win!")
    elif myGame.winner == "BLACK":
        print("AI wins! Better luck next time.")
    else:
        print("It's a draw!")
    
if __name__ == "__main__":
    main()
