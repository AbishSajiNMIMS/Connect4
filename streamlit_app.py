"""
Streamlit dashboard for Connect 4 vs. the algorithm-switching AI.

Run with:
    streamlit run streamlit_app.py

Visual style comes from .streamlit/config.toml (dark theme, fonts, radius)
plus the one injected <style> block below.

Layout notes: the board is rendered as a *single* HTML grid rather than one
st.columns() call per row. Six separate column rows re-flowed independently on
every rerun (the jitter) and stretched to whatever width the page handed them
(the giant board). One grid, capped at a fixed pixel width, is stable and
predictable. The drop-button row is pinned to the same width, padding and gap
so the arrows stay centred over their columns.
"""
import streamlit as st

from game import Connect4, AutoSwitchAgent, HUMAN, AI, ROWS, COLS, EMPTY

st.set_page_config(page_title="Connect 4 — Algorithm Arena", page_icon="🔴", layout="wide")

BOARD_WIDTH = 440   # px -- the board never grows past this, on any screen
BOARD_GAP = 8       # px between slots; the button row copies this exactly
BOARD_PAD = 10      # px frame padding; the button row copies this too

STYLE = f"""
<style>
.block-container {{ padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1400px; }}

/* ---- board ------------------------------------------------------------ */
.c4-frame {{
    width: 100%;
    max-width: {BOARD_WIDTH}px;
    margin: 0 auto;
    padding: {BOARD_PAD}px;
    border-radius: 16px;
    background: linear-gradient(160deg, #1e40af 0%, #1e3a8a 55%, #172554 100%);
    box-shadow: 0 10px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.14);
}}
.c4-grid {{
    display: grid;
    grid-template-columns: repeat({COLS}, 1fr);
    gap: {BOARD_GAP}px;
}}
.c4-slot {{
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    background: #0b0f19;
    box-shadow: inset 0 3px 7px rgba(0,0,0,.75), inset 0 -2px 3px rgba(255,255,255,.06);
}}
.c4-slot.human {{
    background: radial-gradient(circle at 32% 28%, #fca5a5 0%, #ef4444 45%, #b91c1c 100%);
    box-shadow: inset 0 -3px 6px rgba(0,0,0,.45), 0 1px 3px rgba(0,0,0,.5);
}}
.c4-slot.ai {{
    background: radial-gradient(circle at 32% 28%, #fde68a 0%, #eab308 45%, #a16207 100%);
    box-shadow: inset 0 -3px 6px rgba(0,0,0,.45), 0 1px 3px rgba(0,0,0,.5);
}}
.c4-slot.last {{
    box-shadow: 0 0 0 3px #f8fafc inset, inset 0 -3px 6px rgba(0,0,0,.45);
    animation: c4drop .28s ease-out;
}}
@keyframes c4drop {{
    from {{ transform: translateY(-38%); opacity: .35; }}
    to   {{ transform: translateY(0);    opacity: 1; }}
}}

/* ---- drop-button row: same width, padding and gap as the board -------- */
.st-key-c4_controls {{
    width: 100%;
    max-width: {BOARD_WIDTH}px;
    margin: 0 auto;
    padding: 0 {BOARD_PAD}px;
}}
.st-key-c4_controls [data-testid="stHorizontalBlock"] {{
    gap: {BOARD_GAP}px !important;
    flex-wrap: nowrap !important;
}}
.st-key-c4_controls [data-testid="stColumn"] {{
    min-width: 0 !important;
    flex: 1 1 0 !important;
}}
.st-key-c4_controls .stButton > button {{
    padding: 0.15rem 0 !important;
    min-height: 2rem;
    font-size: 0.95rem;
    line-height: 1.2;
}}

/* ---- side panel: reserve height so appearing metrics don't shift things  */
.st-key-c4_brain {{ min-height: 230px; }}
.st-key-c4_newgame {{ max-width: {BOARD_WIDTH}px; margin: 0.75rem auto 0; }}
</style>
"""

CELL_CLASS = {EMPTY: "", HUMAN: " human", AI: " ai"}


def classify_algorithm(name):
    """Map a raw agent.last_algorithm string to a short label + badge color
    + icon, so the four phases stay visually distinct regardless of the
    depth/iteration numbers baked into the full name."""
    if not name:
        return "Unknown", "gray", "🤖"
    lname = name.lower()
    if "tactical" in lname:
        return "Tactical Solver", "orange", "⚡"
    if "endgame" in lname:
        return "Endgame Solver", "green", "🏁"
    if "monte carlo" in lname:
        return "Monte Carlo Tree Search", "violet", "🎲"
    if "alpha-beta" in lname or "minimax" in lname:
        return "Alpha-Beta Minimax", "blue", "🌲"
    return name, "gray", "🤖"


def reset_game():
    st.session_state.game = Connect4()
    st.session_state.agent = AutoSwitchAgent()
    st.session_state.log = []
    st.session_state.winner = None
    st.session_state.move_number = 0


def init_state():
    if "game" not in st.session_state:
        reset_game()


def render_board(game: Connect4):
    """Draw the whole board as one HTML grid -- see the module docstring for
    why this isn't built out of st.columns()."""
    slots = []
    for r in range(ROWS - 1, -1, -1):
        for c in range(COLS):
            classes = CELL_CLASS[game.board[r][c]]
            if game.last_move == (r, c):
                classes += " last"
            slots.append(f"<div class='c4-slot{classes}'></div>")
    st.html("<div class='c4-frame'><div class='c4-grid'>" + "".join(slots) + "</div></div>")


def finish_move_checks(piece):
    game = st.session_state.game
    if game.winning_move(piece):
        st.session_state.winner = piece
    elif game.is_board_full():
        st.session_state.winner = "draw"


def do_ai_move():
    game = st.session_state.game
    agent = st.session_state.agent
    col = agent.get_best_move(game, AI)
    game.drop_piece(col, AI)
    st.session_state.move_number += 1
    st.session_state.log.append(
        {
            "Move #": st.session_state.move_number,
            "Player": "AI 🟡",
            "Column": col,
            "Algorithm": agent.last_algorithm,
            "Reason": agent.last_reason,
        }
    )
    finish_move_checks(AI)


def do_human_move(col):
    if st.session_state.winner is not None:
        return
    game = st.session_state.game
    if not game.is_valid_column(col):
        return
    game.drop_piece(col, HUMAN)
    st.session_state.move_number += 1
    st.session_state.log.append(
        {
            "Move #": st.session_state.move_number,
            "Player": "You 🔴",
            "Column": col,
            "Algorithm": "—",
            "Reason": "—",
        }
    )
    finish_move_checks(HUMAN)
    if st.session_state.winner is None:
        do_ai_move()


init_state()
st.html(STYLE)

st.title("🔴 Connect 4 — Algorithm Arena 🟡")
st.caption(
    "Play against an AI that switches strategies mid-game — a tactical "
    "shortcut, Monte Carlo simulation, minimax search, and a full-depth "
    "endgame solver — and watch which one it reaches for as the board fills up."
)

game = st.session_state.game
agent = st.session_state.agent
over = st.session_state.winner is not None

board_col, panel_col = st.columns([1, 1], gap="large")

with board_col:
    if st.session_state.winner == HUMAN:
        st.success("🎉 You won this round!")
    elif st.session_state.winner == AI:
        st.error("🤖 The AI won this round.")
    elif st.session_state.winner == "draw":
        st.info("🤝 It's a draw.")
    else:
        st.info("🔴 Your move — drop a piece into any column.")

    # The button row is always rendered (disabled once the game ends) so the
    # board never jumps up the page when someone wins.
    with st.container(key="c4_controls"):
        drop_cols = st.columns(COLS, gap="small")
        for c in range(COLS):
            with drop_cols[c]:
                st.button(
                    "▼",
                    key=f"drop_{c}",
                    disabled=over or not game.is_valid_column(c),
                    width="stretch",
                    on_click=do_human_move,
                    args=(c,),
                )
    render_board(game)

    with st.container(key="c4_newgame"):
        st.button("🔄 New Game", on_click=reset_game, width="stretch", type="primary")

with panel_col:
    with st.container(border=True, key="c4_brain"):
        st.subheader("🧠 AI algorithm — this turn")
        if agent.last_algorithm:
            label, color, icon = classify_algorithm(agent.last_algorithm)
            st.badge(agent.last_algorithm, icon=icon, color=color)
            st.write(agent.last_reason)
            if agent.last_stats:
                stat_cols = st.columns(len(agent.last_stats))
                for (k, v), sc in zip(agent.last_stats.items(), stat_cols):
                    with sc:
                        st.metric(k.replace("_", " ").title(), v, border=True)
        else:
            st.caption("The AI hasn't moved yet — make the first move.")

    ai_moves = [row for row in st.session_state.log if row["Player"].startswith("AI")]
    if ai_moves:
        with st.container(border=True):
            st.subheader("📊 Algorithm usage this game")
            counts = {}
            for row in ai_moves:
                label, color, icon = classify_algorithm(row["Algorithm"])
                counts.setdefault(label, {"icon": icon, "count": 0})
                counts[label]["count"] += 1
            usage_cols = st.columns(len(counts))
            for (label, info), uc in zip(counts.items(), usage_cols):
                with uc:
                    st.metric(f"{info['icon']} {label}", info["count"], border=True)

    with st.expander("📖 How the AI decides"):
        st.badge("Tactical Solver", icon="⚡", color="orange")
        st.caption("Always takes a one-move win, or blocks the opponent's.")
        st.badge("Monte Carlo Tree Search", icon="🎲", color="violet")
        st.caption("Opening moves — explores broadly via simulation, no heuristic needed.")
        st.badge("Alpha-Beta Minimax", icon="🌲", color="blue")
        st.caption("Midgame — tactical search guided by a hand-tuned position heuristic.")
        st.badge("Endgame Solver", icon="🏁", color="green")
        st.caption("Late game — searches toward the literal end of the game within a time budget.")

# Full page width -- the log is the thing you actually read, so it gets the
# room rather than being squeezed into the narrow side column.
st.divider()
st.subheader("📜 Move log")
if st.session_state.log:
    st.dataframe(
        list(reversed(st.session_state.log)),
        width="stretch",
        hide_index=True,
        height=420,
        column_config={
            "Move #": st.column_config.NumberColumn("Move", width=70),
            "Player": st.column_config.TextColumn(width=110),
            "Column": st.column_config.NumberColumn("Col", width=70),
            "Algorithm": st.column_config.TextColumn(width=260),
            "Reason": st.column_config.TextColumn(width="large"),
        },
    )
else:
    st.caption("No moves yet — the AI explains every move it makes here.")
