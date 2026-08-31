# Connect4 Repository Code Breakdown

This repository contains a terminal-based Connect 4 game with an AI opponent using **Minimax with Alpha-Beta Pruning**.

## Repository Structure

```
Connect4/
├── game.py
├── main.py
└── __pycache__/   (excluded from this breakdown)
```

## High-Level Architecture

- **`game.py`**: Core game model, rules, board operations, win detection, evaluation heuristics, and AI search agent.
- **`main.py`**: CLI game runner that handles user interaction, board printing, game loop, and turn management.

---

## `game.py` — Core Logic + AI Engine

### Module Constants

- `ROWS = 6`, `COLS = 7`: Standard Connect 4 board dimensions.
- `EMPTY = 0`, `HUMAN = 1`, `AI = 2`: Encoded cell states / players.
- `WINDOW_LENGTH = 4`: Winning sequence length (defined for clarity; logic directly uses `4` in checks).

### `Connect4` Class

Represents game state and board operations.

- **`__init__(self)`**
  - Creates an empty `6x7` board as a 2D list.
  - Stores `last_move` as `(row, col)` or `None`.

- **`copy(self)`**
  - Returns a deep-ish copy of game state (board rows copied, `last_move` preserved).
  - Useful for simulation-style workflows.

- **`is_valid_column(self, col)`**
  - Returns `True` if `col` is in bounds and topmost cell is empty.
  - Prevents dropping into full columns.

- **`valid_columns(self)`**
  - Returns list of all legal columns for the next move.

- **`get_open_row(self, col)`**
  - Scans from bottom row upward to find first empty row in `col`.
  - Returns row index or `None` if full.

- **`drop_piece(self, col, piece)`**
  - Places a piece in the first open row of `col`.
  - Raises `ValueError` if the column is full.
  - Updates `last_move` and returns chosen row.

- **`undo(self, col)`**
  - Removes the topmost placed piece in `col` (used by AI backtracking).

- **`is_board_full(self)`**
  - Returns `True` when no valid columns remain.

- **`winning_move(self, piece)`**
  - Checks four-in-a-row for `piece` in:
    - Horizontal direction
    - Vertical direction
    - Positive diagonal (`\`)
    - Negative diagonal (`/`)

- **`get_winning_cells(self, piece)`**
  - Similar to `winning_move`, but returns exact list of 4 winning coordinates.
  - Returns `None` if no win exists.

- **`game_over(self)`**
  - Returns `True` when either player has won or board is full.

### Helper Functions

- **`other(piece)`**
  - Returns opponent piece ID (`HUMAN ↔ AI`).

- **`evaluate_window(window, piece)`**
  - Heuristic scoring for a 4-cell slice:
    - Own 4: `+100000`
    - Own 3 + 1 empty: `+50`
    - Own 2 + 2 empty: `+10`
    - Opponent 3 + 1 empty: `-80`
  - Encourages winning opportunities and blocking threats.

- **`score_position(game, piece)`**
  - Aggregates board heuristic score for `piece`.
  - Includes:
    - Center-column preference (`* 6` weight)
    - Horizontal, vertical, and diagonal window scoring.

### `AlphaBetaAgent` Class

AI player using minimax search with alpha-beta pruning.

- **State fields**
  - `depth`: search depth limit (default `5`).
  - `nodes_explored`, `nodes_pruned`: runtime stats for search effort.

- **`order_columns(self, cols)`**
  - Sorts candidate columns center-out.
  - Improves pruning by exploring stronger moves earlier.

- **`get_best_move(self, game, piece)`**
  - Resets search stats.
  - Runs `_alphabeta(...)` to select best move.
  - Falls back to random valid move if search returns `None`.

- **`_alphabeta(self, game, depth, alpha, beta, maximizing, ai_piece)`**
  - Recursive minimax:
    - Terminal checks: AI win, human win, draw, or depth limit.
    - Maximizing turn: plays AI move and maximizes score.
    - Minimizing turn: plays human move and minimizes score.
  - Uses `drop_piece` + `undo` for in-place simulation.
  - Uses alpha/beta cutoffs and tracks prune count.
  - Terminal scoring:
    - Large positive for AI win (`10_000_000 + depth`)
    - Large negative for AI loss (`-10_000_000 - depth`)
    - `0` for draw
    - Heuristic `score_position` at depth limit

---

## `main.py` — Command-Line Game Runner

### Imports

- Pulls core game objects/constants from `game.py`:
  - `Connect4`, `AlphaBetaAgent`, `HUMAN`, `AI`, `ROWS`, `COLS`

### Functions

- **`print_board(game)`**
  - Renders board in terminal with row/column labels.
  - Uses emoji:
    - `🔴` for human
    - `🟡` for AI
    - `⚪` for empty
  - Prints top row first for user-friendly orientation.

- **`get_human_move(game)`**
  - Input loop for player's column selection.
  - Accepts integer input and validates with `is_valid_column`.
  - Handles invalid and non-numeric input gracefully with retry.

- **`main()`**
  - Initializes game state and AI agent (`depth=5`).
  - Runs turn loop:
    1. Print board
    2. Human move + win/draw checks
    3. AI move (`get_best_move`) + win/draw checks
  - Prints final outcome and exits loop.

- **Entrypoint**
  - `if __name__ == "__main__": main()`

---

## Runtime Flow Summary

1. Program starts in `main.py`.
2. Human and AI alternate turns on shared `Connect4` state.
3. AI computes moves via depth-limited minimax with alpha-beta pruning.
4. Game ends on win condition or full board draw.

---

## Notes

- `__pycache__/` contains Python bytecode cache and is intentionally excluded.
- The logic is cleanly split so `game.py` can be reused by other front-ends (GUI/web) without changing core rules or AI.
