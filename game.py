"""
Connect 4 core game logic + Alpha-Beta Pruning AI.
No GUI dependencies here -- kept separate so it can be tested headlessly
and reused by any front-end (Pygame, console, web, etc).
"""
import math
import random
import time

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

    def check_win_at(self, row, col, piece):
        """Check only the 4 lines passing through (row, col) for a win.
        Valid only when `piece` was just placed at (row, col) -- much
        cheaper than scanning the whole board, which matters because this
        is called on every simulated move during search/rollouts."""
        b = self.board
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            count = 1
            r, c = row + dr, col + dc
            while 0 <= r < ROWS and 0 <= c < COLS and b[r][c] == piece:
                count += 1
                r += dr
                c += dc
            r, c = row - dr, col - dc
            while 0 <= r < ROWS and 0 <= c < COLS and b[r][c] == piece:
                count += 1
                r -= dr
                c -= dc
            if count >= 4:
                return True
        return False

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

    def __init__(self, depth=5, time_limit=None):
        self.depth = depth
        self.time_limit = time_limit  # if set, use iterative deepening up to `depth`
        self.nodes_explored = 0
        self.nodes_pruned = 0

    def order_columns(self, cols):
        # Searching center-out first improves pruning efficiency
        center = COLS // 2
        return sorted(cols, key=lambda c: abs(c - center))

    def get_best_move(self, game: Connect4, piece):
        if self.time_limit is None:
            self.nodes_explored = 0
            self.nodes_pruned = 0
            _, col = self._alphabeta(
                game, self.depth, -math.inf, math.inf, True, piece, None
            )
            if col is None:
                col = random.choice(game.valid_columns())
            return col

        # Iterative deepening within a time budget: always have a legal
        # move ready, and only search deeper while time allows. Protects
        # against a fixed full-depth search stalling on a sparse board
        # where the branching factor is still large.
        start = time.time()
        best_col = random.choice(game.valid_columns())
        depth = 1
        while depth <= self.depth and (time.time() - start) < self.time_limit:
            self.nodes_explored = 0
            self.nodes_pruned = 0
            _, col = self._alphabeta(
                game, depth, -math.inf, math.inf, True, piece, None
            )
            if col is not None:
                best_col = col
            depth += 1
        return best_col

    def _alphabeta(self, game: Connect4, depth, alpha, beta, maximizing, ai_piece, just_moved):
        self.nodes_explored += 1
        valid_cols = self.order_columns(game.valid_columns())
        human_piece = other(ai_piece)

        # `just_moved` is the piece that produced the current board (None
        # only for the very first call, where the board is the real,
        # presumably non-terminal, live position) -- only that piece could
        # have just won, so we can check its 4 lines instead of the whole
        # board twice.
        if just_moved is not None:
            row, col = game.last_move
            just_won = game.check_win_at(row, col, just_moved)
        else:
            just_won = game.winning_move(ai_piece) or game.winning_move(human_piece)
            just_moved = ai_piece if game.winning_move(ai_piece) else human_piece

        is_terminal = just_won or len(valid_cols) == 0

        if depth == 0 or is_terminal:
            if is_terminal:
                if just_won:
                    if just_moved == ai_piece:
                        return (10_000_000 + depth, None)
                    else:
                        return (-10_000_000 - depth, None)
                else:
                    return (0, None)  # draw
            else:
                return (score_position(game, ai_piece), None)

        best_col = valid_cols[0]

        if maximizing:
            value = -math.inf
            for col in valid_cols:
                game.drop_piece(col, ai_piece)
                new_score, _ = self._alphabeta(
                    game, depth - 1, alpha, beta, False, ai_piece, ai_piece
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
                game.drop_piece(col, human_piece)
                new_score, _ = self._alphabeta(
                    game, depth - 1, alpha, beta, True, ai_piece, human_piece
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


class _MCTSNode:
    """One node of the MCTS search tree, built lazily via make/unmake moves
    on a shared Connect4 board (no per-node board copies)."""

    __slots__ = ("parent", "move", "piece", "children", "visits", "wins", "untried_moves")

    def __init__(self, parent, move, piece, valid_moves):
        self.parent = parent
        self.move = move          # column played to reach this node
        self.piece = piece        # piece that made that move (None for root)
        self.children = []
        self.visits = 0
        self.wins = 0.0
        self.untried_moves = list(valid_moves)

    def uct_value(self, exploration):
        if self.visits == 0:
            return math.inf
        exploit = self.wins / self.visits
        explore = exploration * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore

    def best_child(self, exploration):
        return max(self.children, key=lambda n: n.uct_value(exploration))

    def most_visited_child(self):
        return max(self.children, key=lambda n: n.visits)


class MCTSAgent:
    """Monte Carlo Tree Search agent (selection/expansion/rollout/backprop
    with the UCT formula). Needs no hand-crafted evaluation function --
    only the game's rules -- and its rollout policy takes immediate
    wins/blocks so it doesn't waste simulations on obviously bad lines."""

    name = "Monte Carlo Tree Search"

    def __init__(self, iterations=1200, exploration=1.41, time_limit=None):
        self.iterations = iterations
        self.exploration = exploration
        self.time_limit = time_limit
        self.last_iterations_run = 0

    def get_best_move(self, game: Connect4, piece):
        valid = game.valid_columns()
        if not valid:
            return None
        if len(valid) == 1:
            self.last_iterations_run = 0
            return valid[0]

        root = _MCTSNode(None, None, other(piece), valid)
        start = time.time()
        i = 0
        while i < self.iterations:
            if self.time_limit is not None and (time.time() - start) > self.time_limit:
                break
            self._run_iteration(game, root, piece)
            i += 1
        self.last_iterations_run = i

        return root.most_visited_child().move

    def _run_iteration(self, game: Connect4, root: _MCTSNode, ai_piece):
        node = root
        piece_to_move = ai_piece
        moves_played = []

        # 1. Selection -- descend while fully expanded and non-terminal
        while not node.untried_moves and node.children:
            node = node.best_child(self.exploration)
            game.drop_piece(node.move, piece_to_move)
            moves_played.append(node.move)
            piece_to_move = other(piece_to_move)

        winner = None
        is_terminal = False
        if node is not root and game.check_win_at(*game.last_move, node.piece):
            winner = node.piece
            is_terminal = True
        elif game.is_board_full():
            is_terminal = True  # winner stays None -> draw

        # 2. Expansion
        if not is_terminal and node.untried_moves:
            idx = random.randrange(len(node.untried_moves))
            move = node.untried_moves.pop(idx)
            row = game.drop_piece(move, piece_to_move)
            moves_played.append(move)
            child = _MCTSNode(node, move, piece_to_move, game.valid_columns())
            node.children.append(child)
            node = child
            if game.check_win_at(row, move, piece_to_move):
                winner = piece_to_move
                is_terminal = True
            elif game.is_board_full():
                is_terminal = True
            piece_to_move = other(piece_to_move)

        # 3. Simulation (rollout) -- only if not already terminal
        if not is_terminal:
            winner, rollout_moves = self._rollout(game, piece_to_move)
            moves_played.extend(rollout_moves)

        # 4. Backpropagation
        n = node
        while n is not None:
            n.visits += 1
            if winner is None:
                n.wins += 0.5
            elif winner == n.piece:
                n.wins += 1.0
            n = n.parent

        for col in reversed(moves_played):
            game.undo(col)

    def _rollout(self, game: Connect4, piece_to_move):
        played = []
        current = piece_to_move
        winner = None
        while True:
            valid = game.valid_columns()
            if not valid:
                winner = None
                break
            move = self._rollout_policy(game, valid, current)
            row = game.drop_piece(move, current)
            played.append(move)
            if game.check_win_at(row, move, current):
                winner = current
                break
            if game.is_board_full():
                winner = None
                break
            current = other(current)
        return winner, played

    @staticmethod
    def _rollout_policy(game: Connect4, valid, piece):
        """Lightweight rollout policy: take an immediate win, else block the
        opponent's immediate win, else move randomly. Keeps rollouts from
        wasting simulations on lines any competent player would never take."""
        opp = other(piece)
        for candidate_piece in (piece, opp):
            for col in valid:
                row = game.get_open_row(col)
                game.board[row][col] = candidate_piece
                found = game.check_win_at(row, col, candidate_piece)
                game.board[row][col] = EMPTY
                if found:
                    return col
        return random.choice(valid)


class AutoSwitchAgent:
    """Meta-agent that picks a different underlying algorithm for each move
    depending on the game phase / tactical situation, and records which one
    it used (and why) so the UI can display it.

    Phases, in priority order:
      1. Tactical shortcut -- take an immediate win or block one, regardless
         of phase (no algorithm should ever miss a one-move win/loss).
      2. Endgame -- few empty cells left, so alpha-beta can search to the
         literal end of the game (an exact/near-exact solver at that point).
      3. Opening -- few pieces on the board, use MCTS to explore broadly
         before the hand-tuned heuristic has much signal to work with.
      4. Midgame -- the bulk of the game, tactical alpha-beta + heuristic.
    """

    ENDGAME_EMPTY_CELLS = 10   # search to the end once this few cells remain
    OPENING_PIECE_COUNT = 6    # use MCTS for the first few plies

    def __init__(self, midgame_depth=5, mcts_iterations=1200, mcts_time_limit=2.0, endgame_time_limit=3.0):
        self.midgame_agent = AlphaBetaAgent(depth=midgame_depth)
        self.mcts_agent = MCTSAgent(
            iterations=mcts_iterations, exploration=1.41, time_limit=mcts_time_limit
        )
        self.endgame_time_limit = endgame_time_limit

        self.last_algorithm = None
        self.last_reason = None
        self.last_move = None
        self.last_stats = {}

    @staticmethod
    def _find_immediate_win(game: Connect4, piece):
        for col in game.valid_columns():
            row = game.get_open_row(col)
            game.board[row][col] = piece
            found = game.check_win_at(row, col, piece)
            game.board[row][col] = EMPTY
            if found:
                return col
        return None

    def get_best_move(self, game: Connect4, piece):
        opponent = other(piece)

        win_col = self._find_immediate_win(game, piece)
        if win_col is not None:
            return self._record(
                "Tactical Solver",
                "Playing an immediate winning move.",
                win_col,
            )

        block_col = self._find_immediate_win(game, opponent)
        if block_col is not None:
            return self._record(
                "Tactical Solver",
                "Blocking the opponent's immediate winning move.",
                block_col,
            )

        empty_cells = sum(row.count(EMPTY) for row in game.board)
        total_pieces = ROWS * COLS - empty_cells

        if empty_cells <= self.ENDGAME_EMPTY_CELLS:
            solver = AlphaBetaAgent(depth=empty_cells, time_limit=self.endgame_time_limit)
            col = solver.get_best_move(game, piece)
            return self._record(
                f"Alpha-Beta (iterative-deepening endgame solver, up to depth={empty_cells})",
                f"Only {empty_cells} empty cells left -- searching toward the end of the game "
                f"within a {self.endgame_time_limit}s budget.",
                col,
                nodes_explored=solver.nodes_explored,
                nodes_pruned=solver.nodes_pruned,
            )

        if total_pieces < self.OPENING_PIECE_COUNT:
            col = self.mcts_agent.get_best_move(game, piece)
            return self._record(
                "Monte Carlo Tree Search",
                f"Opening phase (ply {total_pieces + 1}) -- exploring broadly via simulation.",
                col,
                iterations=self.mcts_agent.last_iterations_run,
            )

        col = self.midgame_agent.get_best_move(game, piece)
        return self._record(
            f"Alpha-Beta Pruning (Minimax, depth={self.midgame_agent.depth})",
            "Midgame -- tactical search guided by the position heuristic.",
            col,
            nodes_explored=self.midgame_agent.nodes_explored,
            nodes_pruned=self.midgame_agent.nodes_pruned,
        )

    def _record(self, algorithm, reason, move, **stats):
        self.last_algorithm = algorithm
        self.last_reason = reason
        self.last_move = move
        self.last_stats = stats
        return move