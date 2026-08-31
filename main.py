from game import Connect4, AlphaBetaAgent, HUMAN, AI, ROWS, COLS

def print_board(game):
    """Display the board in a human-readable format."""
    b = game.board
    print("\n" + "=" * 29)
    # Print column numbers
    print("   " + "  ".join(str(i) for i in range(COLS)))
    # Print board (top to bottom)
    for row in range(ROWS - 1, -1, -1):
        print(str(row) + " " + " ".join(
            "🔴" if b[row][col] == HUMAN else 
            "🟡" if b[row][col] == AI else 
            "⚪" 
            for col in range(COLS)
        ))
    print("=" * 29 + "\n")

def get_human_move(game):
    """Get valid column input from human player."""
    while True:
        try:
            col = int(input("Your move (0-6): "))
            if game.is_valid_column(col):
                return col
            else:
                print("❌ Column full or invalid! Try again.")
        except (ValueError, IndexError):
            print("❌ Invalid input! Enter 0-6.")

def main():
    game = Connect4()
    agent = AlphaBetaAgent(depth=5)  # Adjust depth for difficulty
    
    print("🎮 Welcome to Connect 4!")
    print("You are 🔴 (Red), AI is 🟡 (Yellow)")
    
    while True:
        print_board(game)
        
        # Human move
        col = get_human_move(game)
        game.drop_piece(col, HUMAN)
        
        if game.winning_move(HUMAN):
            print_board(game)
            print("🎉 You won!")
            break
        
        if game.is_board_full():
            print_board(game)
            print("🤝 It's a draw!")
            break
        
        # AI move
        print("AI is thinking...")
        col = agent.get_best_move(game, AI)
        game.drop_piece(col, AI)
        print(f"AI played column {col}")
        
        if game.winning_move(AI):
            print_board(game)
            print("🤖 AI won!")
            break
        
        if game.is_board_full():
            print_board(game)
            print("🤝 It's a draw!")
            break

if __name__ == "__main__":
    main()