"""
Connect 4 core game logic + Alpha-Beta Pruning AI.
No GUI dependencies here -- kept separate so it can be tested headlessly
and reused by any front-end (Pygame, console, web, etc).
"""
import math
import random

ROWS = 6
COLS = 7
EMPTY = 0
HUMAN = 1
AI = 2

WINDOW_LENGTH = 4


class Connect4:
    def __init__(self):
        # board[row][col], row 0 = bottom row
        self.board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.last_move = None  # (row, col) of last placed piece

    def copy(self):
        new = Connect4()
        new.board = [row[:] for row in self.board]
        new.last_move = self.last_move
        return new

    def is_valid_column(self, col):
        return 0 <= col < COLS and self.board[ROWS - 1][col] == EMPTY

    def valid_columns(self):
        return [c for c in range(COLS) if self.is_valid_column(c)]

    def get_open_row(self, col):
        for r in range(ROWS):
            if self.board[r][col] == EMPTY:
                return r
        return None

    def drop_piece(self, col, piece):
        row = self.get_open_row(col)
        if row is None:
            raise ValueError(f"Column {col} is full")
        self.board[row][col] = piece
        self.last_move = (row, col)
        return row

    def undo(self, col):
        row = None
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][col] != EMPTY:
                row = r
                break
        if row is not None:
            self.board[row][col] = EMPTY

    def is_board_full(self):
        return len(self.valid_columns()) == 0

    def winning_move(self, piece):
        b = self.board
        # Horizontal
        for r in range(ROWS):
            for c in range(COLS - 3):
                if all(b[r][c + i] == piece for i in range(4)):
                    return True
        # Vertical
        for c in range(COLS):
            for r in range(ROWS - 3):
                if all(b[r + i][c] == piece for i in range(4)):
                    return True
        # Positive diagonal
        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                if all(b[r + i][c + i] == piece for i in range(4)):
                    return True
        # Negative diagonal
        for r in range(3, ROWS):
            for c in range(COLS - 3):
                if all(b[r - i][c + i] == piece for i in range(4)):
                    return True
        return False

    def get_winning_cells(self, piece):
        b = self.board
        for r in range(ROWS):
            for c in range(COLS - 3):
                cells = [(r, c + i) for i in range(4)]
                if all(b[rr][cc] == piece for rr, cc in cells):
                    return cells
        for c in range(COLS):
            for r in range(ROWS - 3):
                cells = [(r + i, c) for i in range(4)]
                if all(b[rr][cc] == piece for rr, cc in cells):
                    return cells
        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                cells = [(r + i, c + i) for i in range(4)]
                if all(b[rr][cc] == piece for rr, cc in cells):
                    return cells
        for r in range(3, ROWS):
            for c in range(COLS - 3):
                cells = [(r - i, c + i) for i in range(4)]
                if all(b[rr][cc] == piece for rr, cc in cells):
                    return cells
        return None

    def game_over(self):
        return self.winning_move(HUMAN) or self.winning_move(AI) or self.is_board_full()


def other(piece):
    return AI if piece == HUMAN else HUMAN


def evaluate_window(window, piece):
    """Score a length-4 window from the perspective of `piece`."""
    opp = other(piece)
    score = 0
    piece_count = window.count(piece)
    empty_count = window.count(EMPTY)
    opp_count = window.count(opp)

    if piece_count == 4:
        score += 100000
    elif piece_count == 3 and empty_count == 1:
        score += 50
    elif piece_count == 2 and empty_count == 2:
        score += 10

    if opp_count == 3 and empty_count == 1:
        score -= 80  # block opponent's near-wins aggressively

    return score


def score_position(game: Connect4, piece):
    b = game.board
    score = 0

    # Center column control is valuable (more winning lines pass through it)
    center_col = [b[r][COLS // 2] for r in range(ROWS)]
    score += center_col.count(piece) * 6

    # Horizontal
    for r in range(ROWS):
        row_array = b[r]
        for c in range(COLS - 3):
            window = row_array[c:c + 4]
            score += evaluate_window(window, piece)

    # Vertical
    for c in range(COLS):
        col_array = [b[r][c] for r in range(ROWS)]
        for r in range(ROWS - 3):
            window = col_array[r:r + 4]
            score += evaluate_window(window, piece)

    # Positive diagonal
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            window = [b[r + i][c + i] for i in range(4)]
            score += evaluate_window(window, piece)

    # Negative diagonal
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            window = [b[r - i][c + i] for i in range(4)]
            score += evaluate_window(window, piece)

    return score


class AlphaBetaAgent:
    """Adversarial search agent using minimax + alpha-beta pruning."""

    def __init__(self, depth=5):
        self.depth = depth
        self.nodes_explored = 0
        self.nodes_pruned = 0

    def order_columns(self, cols):
        # Searching center-out first improves pruning efficiency
        center = COLS // 2
        return sorted(cols, key=lambda c: abs(c - center))

    def get_best_move(self, game: Connect4, piece):
        self.nodes_explored = 0
        self.nodes_pruned = 0
        _, col = self._alphabeta(
            game, self.depth, -math.inf, math.inf, True, piece
        )
        if col is None:
            col = random.choice(game.valid_columns())
        return col

    def _alphabeta(self, game: Connect4, depth, alpha, beta, maximizing, ai_piece):
        self.nodes_explored += 1
        valid_cols = self.order_columns(game.valid_columns())
        human_piece = other(ai_piece)

        is_terminal = (
            game.winning_move(ai_piece)
            or game.winning_move(human_piece)
            or len(valid_cols) == 0
        )

        if depth == 0 or is_terminal:
            if is_terminal:
                if game.winning_move(ai_piece):
                    return (10_000_000 + depth, None)
                elif game.winning_move(human_piece):
                    return (-10_000_000 - depth, None)
                else:
                    return (0, None)  # draw
            else:
                return (score_position(game, ai_piece), None)

        best_col = valid_cols[0]

        if maximizing:
            value = -math.inf
            for col in valid_cols:
                row = game.drop_piece(col, ai_piece)
                new_score, _ = self._alphabeta(
                    game, depth - 1, alpha, beta, False, ai_piece
                )
                game.undo(col)
                if new_score > value:
                    value = new_score
                    best_col = col
                alpha = max(alpha, value)
                if alpha >= beta:
                    self.nodes_pruned += 1
                    break  # beta cutoff
            return value, best_col
        else:
            value = math.inf
            for col in valid_cols:
                row = game.drop_piece(col, human_piece)
                new_score, _ = self._alphabeta(
                    game, depth - 1, alpha, beta, True, ai_piece
                )
                game.undo(col)
                if new_score < value:
                    value = new_score
                    best_col = col
                beta = min(beta, value)
                if alpha >= beta:
                    self.nodes_pruned += 1
                    break  # alpha cutoff
            return value, best_col