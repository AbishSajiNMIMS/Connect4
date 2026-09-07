"""Streamlit Connect 4 friend-agent dashboard."""

import hashlib
import math
import sqlite3
from pathlib import Path

import streamlit as st

from game import AI, COLS, HUMAN, ROWS, AlphaBetaAgent, Connect4, score_position


APP_DIR = Path(__file__).parent
AUTH_DB = APP_DIR / "connect4_users.db"
ALGORITHM_ORDER = [
    "Uniform Cost Search",
    "Greedy Best First Search",
    "A* Search",
    "Minimax",
    "Alpha-Beta Pruning",
]
EXTRA_ALGORITHMS = [
    ("Monte Carlo Tree Search", "Samples many random continuations and chooses the move with the strongest average result."),
    ("Expectimax", "Models uncertain opponent choices by averaging chance outcomes instead of always taking the worst case."),
    ("Beam Search", "Keeps only the best few frontier states at each depth to control the branching factor."),
    ("Negamax", "A compact minimax formulation that flips the score when the player changes."),
]


def init_auth():
    with sqlite3.connect(AUTH_DB) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL)"
        )
        connection.commit()


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(username, password):
    try:
        with sqlite3.connect(AUTH_DB) as connection:
            connection.execute(
                "INSERT INTO users(username, password) VALUES (?, ?)",
                (username.strip(), password_hash(password)),
            )
            connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate(username, password):
    with sqlite3.connect(AUTH_DB) as connection:
        row = connection.execute(
            "SELECT password FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    return row is not None and row[0] == password_hash(password)


def reset_game():
    st.session_state.game = Connect4()
    st.session_state.game_over = False
    st.session_state.status = "Your turn. Choose a column."
    st.session_state.analysis = {}
    st.session_state.history = []


def board_html(game):
    colors = {0: "#f8fafc", HUMAN: "#ef4444", AI: "#facc15"}
    cells = []
    for row in range(ROWS - 1, -1, -1):
        for col in range(COLS):
            cells.append(
                f'<div class="cell" style="background:{colors[game.board[row][col]]};'
                f'border-color:{"#f97316" if game.last_move == (row, col) else "#1e293b"}"></div>'
            )
    return f'<div class="board">{"".join(cells)}</div>'


def board_text(game):
    symbols = {0: ".", HUMAN: "R", AI: "Y"}
    return "\n".join(
        " ".join(symbols[game.board[row][col]] for col in range(COLS))
        for row in range(ROWS - 1, -1, -1)
    )


def heuristic(game, piece=HUMAN):
    if game.winning_move(piece):
        return 1000000
    if game.winning_move(AI if piece == HUMAN else HUMAN):
        return -1000000
    return score_position(game, piece)


def response_value(state, algorithm):
    """Return a comparable score for a candidate human state."""
    if state.winning_move(HUMAN):
        return 1000000
    if state.winning_move(AI):
        return -1000000
    human_score = heuristic(state, HUMAN)
    opponent_score = heuristic(state, AI)
    if algorithm == "Uniform Cost Search":
        return human_score - 0.35 * len(state.valid_columns())
    if algorithm == "Greedy Best First Search":
        return human_score
    if algorithm == "A* Search":
        return human_score + 0.5 * (human_score - opponent_score)
    if algorithm == "Minimax":
        values = []
        for col in state.valid_columns():
            reply = state.copy()
            reply.drop_piece(col, AI)
            values.append(heuristic(reply, HUMAN))
        return min(values) if values else human_score
    if algorithm == "Alpha-Beta Pruning":
        agent = AlphaBetaAgent(depth=3)
        reply_col = agent.get_best_move(state.copy(), AI)
        reply = state.copy()
        if reply_col in reply.valid_columns():
            reply.drop_piece(reply_col, AI)
        return heuristic(reply, HUMAN)
    return human_score


def analyse_algorithm(game, algorithm):
    candidates = []
    for col in game.valid_columns():
        state = game.copy()
        state.drop_piece(col, HUMAN)
        candidates.append({"column": col, "board": state, "score": response_value(state, algorithm)})
    if not candidates:
        return []
    minimum = min(item["score"] for item in candidates)
    maximum = max(item["score"] for item in candidates)
    spread = max(maximum - minimum, 1)
    for item in candidates:
        scaled = (item["score"] - minimum) / spread
        item["probability"] = round(15 + 80 * scaled, 1)
        if item["score"] >= 1000000:
            item["probability"] = 99.9
    return sorted(candidates, key=lambda item: item["probability"], reverse=True)


def analyse_all(game):
    return {algorithm: analyse_algorithm(game, algorithm) for algorithm in ALGORITHM_ORDER}


def play_turn(column):
    game = st.session_state.game
    if st.session_state.game_over or not game.is_valid_column(column):
        return
    game.drop_piece(column, HUMAN)
    st.session_state.history.append(f"You played column {column + 1}")
    if game.winning_move(HUMAN):
        st.session_state.status = "You won! Great connection."
        st.session_state.game_over = True
        st.session_state.analysis = {}
        return
    if game.is_board_full():
        st.session_state.status = "Draw — the board is full."
        st.session_state.game_over = True
        st.session_state.analysis = {}
        return
    agent = AlphaBetaAgent(depth=4)
    ai_column = agent.get_best_move(game, AI)
    game.drop_piece(ai_column, AI)
    st.session_state.history.append(f"Friend agent played column {ai_column + 1}")
    if game.winning_move(AI):
        st.session_state.status = "The friend agent connected four. Try another line."
        st.session_state.game_over = True
    elif game.is_board_full():
        st.session_state.status = "Draw — the board is full."
        st.session_state.game_over = True
    else:
        st.session_state.status = f"Friend agent played column {ai_column + 1}. Your recommended states are ready."
        st.session_state.analysis = analyse_all(game)


def render_login():
    st.markdown('<div class="hero"><div class="hero-kicker">SEARCH LAB</div><h1>CONNECT<span>4</span></h1><p>Play against an adversarial friend agent and see the state space behind every suggestion.</p></div>', unsafe_allow_html=True)
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Enter the arena", type="primary", use_container_width=True):
            if authenticate(username, password):
                st.session_state.user = username.strip()
                reset_game()
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with signup_tab:
        username = st.text_input("Choose a username", key="signup_user")
        password = st.text_input("Choose a password", type="password", key="signup_password")
        if st.button("Create account", use_container_width=True):
            if len(username.strip()) < 3 or len(password) < 4:
                st.warning("Use at least 3 characters for a username and 4 for a password.")
            elif create_user(username, password):
                st.success("Account created. You can now log in.")
            else:
                st.error("That username is already taken.")


def render_algorithm_card(name, description, process, diagram):
    with st.expander(name, expanded=name == "Alpha-Beta Pruning"):
        st.markdown(f"**Concept:** {description}")
        st.markdown(f"**Process:** {process}")
        st.code(diagram, language="text")


def render_algorithms():
    st.header("How the friend agent searches")
    st.caption("Every board below is a state. An edge is one legal dropped piece; terminal states are wins, losses, or draws.")
    cards = [
        ("Uniform Cost Search", "Expands the lowest path-cost state first.", "Start at the current board, add every legal column to a priority queue, then expand the cheapest path until the best frontier state is found.", "Current board\n  ├─ c1 (cost 1)\n  ├─ c2 (cost 1)\n  └─ c3 (cost 1)\n       └─ lowest-cost state"),
        ("Greedy Best First Search", "Always expands the state with the most promising heuristic.", "Generate legal child boards, score immediate threats and center control, then follow the highest heuristic until a recommendation is reached.", "Board S → [S+c1, S+c2, S+c3]\n             ↑ best heuristic"),
        ("A* Search", "Balances path cost g(n) with estimated future value h(n).", "For each board compute f(n)=g(n)+h(n), retain the frontier ordered by f, and choose the state with the strongest combined present and future value.", "S --g+h--> S+c2 --g+h--> S+c2+c4"),
        ("Minimax", "Assumes the opponent always chooses the move worst for you.", "Build alternating MAX/MIN layers, score leaves with the Connect 4 heuristic, propagate the minimum opponent reply back to the best human move.", "MAX: your move\n ├─ MIN: AI reply ── leaf score\n └─ MIN: AI reply ── leaf score"),
        ("Alpha-Beta Pruning", "Minimax with bounds that skips branches that cannot change the decision.", "Search center-first, maintain alpha and beta bounds, and cut a subtree when alpha >= beta. This keeps the minimax answer while exploring fewer boards.", "MAX α=3\n ├─ MIN β=2  ✂ prune remaining replies\n └─ MIN β=5"),
    ]
    for card in cards:
        render_algorithm_card(*card)
    st.subheader("Useful supporting algorithms")
    for name, description in EXTRA_ALGORITHMS:
        st.markdown(f"**{name}:** {description}")


def render_state_space():
    analysis = st.session_state.analysis
    if not analysis:
        st.info("After the friend agent moves, its recommended human state spaces will appear here.")
        return
    st.header("Your possible moves as state spaces")
    st.caption("Probabilities are heuristic win estimates for the current position, not guarantees. Higher values mean stronger defensive and offensive features.")
    for algorithm in ALGORITHM_ORDER:
        candidates = analysis[algorithm]
        st.subheader(algorithm)
        cols = st.columns(min(3, len(candidates)))
        for index, item in enumerate(candidates[:3]):
            with cols[index % len(cols)]:
                st.markdown(f"**Play column {item['column'] + 1}** — `{item['probability']}%` estimated win chance")
                st.markdown(board_html(item["board"]), unsafe_allow_html=True)
                st.caption(f"State score: {item['score']:.1f}  |  Board state: `{item['column'] + 1}`")


def render_game():
    game = st.session_state.game
    st.header("Play the friend agent")
    st.write(st.session_state.status)
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown(board_html(game), unsafe_allow_html=True)
        st.markdown("**Choose your column**")
        buttons = st.columns(COLS)
        for col, button in enumerate(buttons):
            with button:
                if st.button(str(col + 1), key=f"move_{col}", disabled=st.session_state.game_over or not game.is_valid_column(col), use_container_width=True):
                    play_turn(col)
                    st.rerun()
        if st.button("New game", use_container_width=True):
            reset_game()
            st.rerun()
    with right:
        st.subheader("Turn history")
        st.code("\n".join(st.session_state.history[-8:]) or "No moves yet", language="text")
        st.markdown("**State encoding**")
        st.code(board_text(game), language="text")
        st.caption("R = you, Y = friend agent, . = empty. Rows are shown from top to bottom.")
    render_state_space()


def main():
    st.set_page_config(page_title="Connect4 Search Lab", page_icon="🔴", layout="wide")
    st.markdown(
        """<style>
        .stApp { background: #0b1120; color: #e2e8f0; }
        .block-container { max-width: 1180px; padding-top: 2rem; }
        .hero { padding: 2.5rem 2.8rem; border: 1px solid #334155; border-radius: 24px; background: linear-gradient(135deg,#172554,#0f172a); margin-bottom: 1.5rem; }
        .hero h1 { font-size: 4.6rem; line-height: 1; margin: .2rem 0; letter-spacing: .12em; color: #f8fafc; }
        .hero h1 span { color: #facc15; }
        .hero p { color: #cbd5e1; font-size: 1.1rem; max-width: 650px; }
        .hero-kicker { color: #fb923c; font-weight: 700; letter-spacing: .2em; }
        .board { display: grid; grid-template-columns: repeat(7, 1fr); gap: 7px; background: #1d4ed8; border: 8px solid #1d4ed8; border-radius: 18px; padding: 8px; max-width: 520px; margin: 1rem 0; }
        .cell { aspect-ratio: 1; border: 3px solid #1e293b; border-radius: 50%; box-shadow: inset 0 3px 5px #0004; }
        [data-testid="stExpander"] { border-color: #334155; }
        </style>""",
        unsafe_allow_html=True,
    )
    init_auth()
    if "user" not in st.session_state:
        render_login()
        return
    if "game" not in st.session_state:
        reset_game()
    st.sidebar.success(f"Signed in as **{st.session_state.user}**")
    if st.sidebar.button("Log out"):
        del st.session_state["user"]
        st.rerun()
    st.title("Connect4 Search Lab")
    st.caption("A visual friend agent for adversarial search")
    pages = st.tabs(["Algorithm Lab", "Play & State Spaces"])
    with pages[0]:
        render_algorithms()
    with pages[1]:
        render_game()


if __name__ == "__main__":
    main()
