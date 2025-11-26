import streamlit as st
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.optimize import brentq
from datetime import datetime, time

# =============================================================================
# pm-AMM Mathematical Functions
# Based on: https://www.paradigm.xyz/2024/11/pm-amm
# =============================================================================

@st.cache_data
def phi(z):
    """Standard normal probability density function (PDF)."""
    return norm.pdf(z)

@st.cache_data
def Phi(z):
    """Standard normal cumulative distribution function (CDF)."""
    return norm.cdf(z)

@st.cache_data
def Phi_inv(p):
    """Inverse of standard normal CDF (quantile function)."""
    # Clamp p to avoid infinity
    p = np.clip(p, 1e-10, 1 - 1e-10)
    return norm.ppf(p)

@st.cache_data
def get_effective_L(L, T_minus_t, is_dynamic):
    """Get effective liquidity parameter based on AMM type."""
    if is_dynamic:
        return L * np.sqrt(max(T_minus_t, 1e-10))
    return L

@st.cache_data
def calc_price_pmamm(x, y, L, T_minus_t=1.0, is_dynamic=False):
    """
    Calculate the price of YES token in pm-AMM.
    P = Φ((y - x) / L_eff)
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)
    if L_eff <= 0:
        return 0.5
    z = (y - x) / L_eff
    return Phi(z)

@st.cache_data
def calc_portfolio_value(P, L, T_minus_t=1.0, is_dynamic=False):
    """
    Calculate the portfolio value V(P) = L_eff * φ(Φ⁻¹(P))
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)
    z = Phi_inv(P)
    return L_eff * phi(z)

@st.cache_data
def invariant_pmamm(x, y, L, T_minus_t=1.0, is_dynamic=False):
    """
    pm-AMM invariant equation (should equal 0 on the curve):
    (y - x) * Φ((y-x)/L_eff) + L_eff * φ((y-x)/L_eff) - y = 0
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)
    if L_eff <= 0:
        return float('inf')
    z = (y - x) / L_eff
    return (y - x) * Phi(z) + L_eff * phi(z) - y

def solve_for_y(x, L, T_minus_t=1.0, is_dynamic=False, y_guess=None):
    """
    Given x and L, solve for y that satisfies the pm-AMM invariant.
    Uses numerical root finding.
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)
    
    def equation(y):
        return invariant_pmamm(x, y, L, T_minus_t, is_dynamic)
    
    # Search for y in a reasonable range
    # y should be positive and bounded
    try:
        y_min = max(0.001, x - 10 * L_eff)
        y_max = x + 10 * L_eff
        y_solution = brentq(equation, y_min, y_max)
        return y_solution
    except:
        # Fallback: use initial guess or x
        return y_guess if y_guess is not None else x

def solve_for_x(y, L, T_minus_t=1.0, is_dynamic=False, x_guess=None):
    """
    Given y and L, solve for x that satisfies the pm-AMM invariant.
    Uses numerical root finding.
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)
    
    def equation(x):
        return invariant_pmamm(x, y, L, T_minus_t, is_dynamic)
    
    try:
        x_min = y - 10 * L_eff
        x_max = y + 10 * L_eff
        x_solution = brentq(equation, x_min, x_max)
        return x_solution
    except:
        return x_guess if x_guess is not None else y

@st.cache_data
def get_reserves_from_price(P, L, T_minus_t=1.0, is_dynamic=False):
    """
    Given a price P, calculate the reserves (x, y) on the pm-AMM curve.

    From P = Φ((y-x)/L_eff), we get: y - x = L_eff * Φ⁻¹(P)
    Then we need another equation - we use the invariant.
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)

    # From price equation: y - x = L_eff * Φ⁻¹(P)
    z = Phi_inv(P)
    diff = L_eff * z

    # From invariant: (y-x)*Φ(z) + L_eff*φ(z) - y = 0
    # Substituting diff = y - x:
    # diff * P + L_eff * φ(z) = y
    y = diff * P + L_eff * phi(z)
    x = y - diff

    return x, y

def calc_trade_cost(x, y, shares, direction, L, T_minus_t=1.0, is_dynamic=False):
    """
    Calculate the cost of buying 'shares' in 'direction' (YES or NO).
    """
    L_eff = get_effective_L(L, T_minus_t, is_dynamic)
    
    # Current price
    P_before = calc_price_pmamm(x, y, L, T_minus_t, is_dynamic)
    
    if direction == "YES":
        x_new = x + shares
        y_new = solve_for_y(x_new, L, T_minus_t, is_dynamic, y)
    else:
        y_new = y + shares
        x_new = solve_for_x(y_new, L, T_minus_t, is_dynamic, x)
    
    P_after = calc_price_pmamm(x_new, y_new, L, T_minus_t, is_dynamic)
    
    if direction == "YES":
        # Cost of YES = integral of price from x to x+shares
        n_points = 20  # Reduced from 100 for better performance
        x_range = np.linspace(x, x_new, n_points)
        prices = []
        for xi in x_range:
            yi = solve_for_y(xi, L, T_minus_t, is_dynamic, y)
            prices.append(calc_price_pmamm(xi, yi, L, T_minus_t, is_dynamic))
        cost = np.trapz(prices, x_range)
    else:
        # Cost of NO = integral of (1 - price) from y to y+shares
        n_points = 20  # Reduced from 100 for better performance
        y_range = np.linspace(y, y_new, n_points)
        prices = []
        for yi in y_range:
            xi = solve_for_x(yi, L, T_minus_t, is_dynamic, x)
            prices.append(1 - calc_price_pmamm(xi, yi, L, T_minus_t, is_dynamic))
        cost = np.trapz(prices, y_range)
    
    return cost, x_new, y_new, P_after

@st.cache_data
def calc_time_to_expiry(market_duration_days, trade_day, trade_time_str):
    """
    Calculate T-t (time to expiry) based on market duration and trade timestamp.

    Args:
        market_duration_days: Total market duration in days
        trade_day: Day of the trade (1 to market_duration_days)
        trade_time_str: Time of trade in "HH:MM" format

    Returns:
        T_minus_t in days (float)
    """
    # Parse time
    try:
        hours, minutes = map(int, trade_time_str.split(":"))
    except:
        hours, minutes = 12, 0  # Default to noon

    # Calculate elapsed time in days
    # Day 1 at 00:00 = 0 days elapsed
    # Day 1 at 12:00 = 0.5 days elapsed
    elapsed_days = (trade_day - 1) + (hours + minutes / 60) / 24

    # T-t = total duration - elapsed time
    T_minus_t = market_duration_days - elapsed_days

    return max(T_minus_t, 0.001)  # Ensure positive

def format_trade_time(day, time_str):
    """Format trade timestamp for display."""
    return f"Day {day} @ {time_str}"

@st.cache_data
def plot_price_evolution(price_history_tuple, amm_type, is_dynamic):
    """Cached price evolution plot."""
    # Convert tuple back to list of dicts
    price_history = [dict(zip(['Trade', 'Time', 'YES Price', 'NO Price', 'T-t'], p))
                     for p in price_history_tuple]

    price_df = pd.DataFrame(price_history)

    fig, ax = plt.subplots(figsize=(10, 5))

    x_labels = price_df["Time"].tolist()
    x_positions = range(len(x_labels))

    ax.plot(x_positions, price_df["YES Price"], label="YES Price",
            color="#28a745", linewidth=2, marker="o")
    ax.plot(x_positions, price_df["NO Price"], label="NO Price",
            color="#dc3545", linewidth=2, marker="s")

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.set_xlabel("Trade" if not is_dynamic else "Time")
    ax.set_ylabel("Price")
    ax.set_title(f"Share Price Evolution ({amm_type} pm-AMM)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 1])
    plt.tight_layout()

    return fig

@st.cache_data
def plot_leff_evolution(price_history_tuple, L_param, x_labels):
    """Cached L_eff evolution plot for dynamic mode."""
    # Extract T-t values from tuple
    t_minus_t_values = [p[4] for p in price_history_tuple if p[4] is not None]
    l_eff_values = [L_param * np.sqrt(t) for t in t_minus_t_values]

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.bar(range(len(l_eff_values)), l_eff_values, color="#3498db", alpha=0.7)
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.set_xlabel("Time")
    ax.set_ylabel("L_eff")
    ax.set_title("Effective Liquidity Over Time")
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    return fig

@st.cache_data
def plot_invariant_curve(L_param, T_minus_t_initial, is_dynamic, amm_type,
                        market_duration_days, x_initial, y_initial,
                        x_final, y_final, has_trades):
    """Cached invariant curve plot."""
    # Generate curve points
    prices = np.linspace(0.01, 0.99, 50)
    x_curve = []
    y_curve = []

    for p in prices:
        xi, yi = get_reserves_from_price(p, L_param, T_minus_t_initial, is_dynamic)
        x_curve.append(xi)
        y_curve.append(yi)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(x_curve, y_curve, 'b-', linewidth=2, label=f'{amm_type} pm-AMM Curve')

    # Mark initial and final positions
    ax.plot(x_initial, y_initial, 'go', markersize=12, label='Initial Position', zorder=5)
    if has_trades:
        ax.plot(x_final, y_final, 'ro', markersize=12, label='Final Position', zorder=5)

    ax.set_xlabel('x (YES reserves)')
    ax.set_ylabel('y (NO reserves)')
    title_suffix = f", T={market_duration_days} days)" if is_dynamic else ")"
    ax.set_title(f'{amm_type} pm-AMM Invariant Curve (L={L_param:.1f}' + title_suffix)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()

    return fig

@st.cache_data
def simulate_trades_cached(trades_tuple, L_param, base_fee, initial_prob_yes,
                          market_duration_days, is_dynamic, final_outcome):
    """
    Cached simulation function. Takes hashable inputs and returns simulation results.

    Args:
        trades_tuple: Tuple of tuples (direction, shares, day, time) for hashability
        L_param: Liquidity parameter
        base_fee: Fee rate (decimal, not percentage)
        initial_prob_yes: Initial YES probability (0-100)
        market_duration_days: Market duration in days
        is_dynamic: Boolean for Dynamic vs Static AMM
        final_outcome: "YES" or "NO"

    Returns:
        Dictionary with simulation results
    """
    # Convert trades_tuple back to list of dicts
    trades = [
        {"direction": t[0], "shares": t[1], "day": t[2], "time": t[3]}
        for t in trades_tuple
    ]

    # Calculate initial reserves based on initial probability
    p_yes = initial_prob_yes / 100.0

    # For initial state, use full market duration (T-t = T at t=0)
    if is_dynamic:
        T_minus_t_initial = float(market_duration_days)
    else:
        T_minus_t_initial = 1.0

    # Get initial reserves from price
    x, y = get_reserves_from_price(p_yes, L_param, T_minus_t_initial, is_dynamic)

    # Track initial state
    x_initial, y_initial = x, y

    total_cost = 0
    total_fee = 0
    rows = []

    # Track user's purchased shares
    user_q_yes = 0
    user_q_no = 0

    # Track price evolution
    price_history = []

    # Initial price
    initial_price_yes = calc_price_pmamm(x, y, L_param, T_minus_t_initial, is_dynamic)
    price_history.append({
        "Trade": 0,
        "Time": "Start",
        "YES Price": initial_price_yes,
        "NO Price": 1.0 - initial_price_yes,
        "T-t": T_minus_t_initial if is_dynamic else None
    })

    # Process trades
    for idx, trade in enumerate(trades, start=1):
        direction = trade["direction"]
        shares = trade["shares"]
        trade_day = trade["day"]
        trade_time = trade["time"]

        # Calculate T-t for this trade
        if is_dynamic:
            T_minus_t = calc_time_to_expiry(market_duration_days, trade_day, trade_time)
        else:
            T_minus_t = 1.0  # Not used for static

        price_before = calc_price_pmamm(x, y, L_param, T_minus_t, is_dynamic)

        # Calculate trade cost
        cost, x_new, y_new, price_after = calc_trade_cost(
            x, y, shares, direction, L_param, T_minus_t, is_dynamic
        )

        # Apply fee
        fee = cost * base_fee

        total_cost += cost
        total_fee += fee

        # Update state
        x, y = x_new, y_new

        # Track user shares
        if direction == "YES":
            user_q_yes += shares
        else:
            user_q_no += shares

        # Record price history
        time_label = f"D{trade_day} {trade_time}" if is_dynamic else str(idx)
        price_history.append({
            "Trade": idx,
            "Time": time_label,
            "YES Price": price_after,
            "NO Price": 1.0 - price_after,
            "T-t": T_minus_t if is_dynamic else None
        })

        avg_price = cost / shares if shares > 0 else 0

        row_data = {
            "Direction": direction,
            "Shares": shares,
            "Price Before": round(price_before, 4),
            "Price After": round(price_after, 4),
            "Avg. Price": round(avg_price, 4),
            "Cost Paid": round(cost, 4),
            "Fee": round(fee, 4)
        }

        if is_dynamic:
            row_data["Day"] = trade_day
            row_data["Time"] = trade_time
            row_data["T-t (days)"] = round(T_minus_t, 2)
            L_eff = L_param * np.sqrt(T_minus_t)
            row_data["L_eff"] = round(L_eff, 2)

        rows.append(row_data)

    # Calculate payout
    payout = user_q_yes if final_outcome == "YES" else user_q_no
    net_worth = total_fee + total_cost - payout

    # Final prices (use last T-t or initial if no trades)
    if trades and is_dynamic:
        last_trade = trades[-1]
        T_minus_t_final = calc_time_to_expiry(market_duration_days, last_trade["day"], last_trade["time"])
    else:
        T_minus_t_final = T_minus_t_initial

    final_price_yes = calc_price_pmamm(x, y, L_param, T_minus_t_final, is_dynamic)
    final_price_no = 1.0 - final_price_yes

    return {
        'rows': rows,
        'price_history': price_history,
        'total_cost': total_cost,
        'total_fee': total_fee,
        'payout': payout,
        'net_worth': net_worth,
        'x': x,
        'y': y,
        'x_initial': x_initial,
        'y_initial': y_initial,
        'final_price_yes': final_price_yes,
        'final_price_no': final_price_no,
        'T_minus_t_initial': T_minus_t_initial,
        'T_minus_t_final': T_minus_t_final
    }

# =============================================================================
# Streamlit UI
# =============================================================================

st.set_page_config(page_title="pm-AMM Simulator", layout="wide")

st.title("pm-AMM Simulator")
st.markdown("""
Simulador para o **pm-AMM** (Prediction Market AMM), um AMM uniforme otimizado para mercados de previsão.
Baseado em: [Paradigm Research](https://www.paradigm.xyz/2024/11/pm-amm)
""")

# Initialize session state
if 'L_param' not in st.session_state:
    st.session_state.L_param = 100.0
if 'base_fee' not in st.session_state:
    st.session_state.base_fee = 2.0
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'final_outcome' not in st.session_state:
    st.session_state.final_outcome = "YES"
if 'show_import_json' not in st.session_state:
    st.session_state.show_import_json = False
if 'show_json_model' not in st.session_state:
    st.session_state.show_json_model = False
if 'initial_prob_yes' not in st.session_state:
    st.session_state.initial_prob_yes = 50.0
if 'slider_key_counter' not in st.session_state:
    st.session_state.slider_key_counter = 0
if 'trades_page' not in st.session_state:
    st.session_state.trades_page = 1
if 'amm_type' not in st.session_state:
    st.session_state.amm_type = "Static"
if 'market_duration_days' not in st.session_state:
    st.session_state.market_duration_days = 14

# =============================================================================
# AMM Type Selection
# =============================================================================
st.subheader("AMM Type")

amm_type = st.radio(
    "Select pm-AMM variant:",
    ["Static", "Dynamic"],
    horizontal=True,
    key="amm_type_radio",
    help="""
    **Static pm-AMM**: Liquidity constante ao longo do tempo.
    
    **Dynamic pm-AMM**: Liquidity diminui conforme se aproxima da expiração, mantendo LVR constante.
    """
)
st.session_state.amm_type = amm_type
is_dynamic = amm_type == "Dynamic"

# Show invariant formula based on selection
if is_dynamic:
    st.latex(r"(y - x) \Phi\left( \frac{y - x}{L\sqrt{T - t}} \right) + L\sqrt{T - t} \, \phi\left( \frac{y - x}{L\sqrt{T-t}} \right) - y = 0")
    st.caption("Invariante do Dynamic pm-AMM, onde T-t é o tempo até expiração.")
else:
    st.latex(r"(y - x) \Phi\left( \frac{y - x}{L} \right) + L \, \phi\left( \frac{y - x}{L} \right) - y = 0")
    st.caption("Invariante do Static pm-AMM.")

st.divider()

# =============================================================================
# Parameters section
# =============================================================================
st.subheader("Parameters")

col_params1, col_params2 = st.columns(2)

with col_params1:
    L_param = st.number_input(
        "L (Liquidity Parameter)", 
        value=st.session_state.L_param, 
        min_value=1.0,
        step=10.0, 
        key="L_param_input",
        help="Parâmetro de escala/liquidez do pm-AMM. Valores maiores = mais liquidez."
    )
    st.session_state.L_param = L_param

with col_params2:
    base_fee_input = st.number_input(
        "Base Fee Rate (%)", 
        value=st.session_state.base_fee, 
        min_value=0.0,
        step=0.1, 
        key="base_fee_input",
        help="Taxa aplicada em cada trade."
    )
st.session_state.base_fee = base_fee_input
base_fee = st.session_state.base_fee / 100

# Dynamic-specific parameters
if is_dynamic:
    st.markdown("**Market Duration (Dynamic pm-AMM):**")
    market_duration_days = st.number_input(
        "Market Duration (days)", 
        value=st.session_state.market_duration_days, 
        min_value=1,
        step=1, 
        key="market_duration_input",
        help="Duração total do mercado em dias. Cada trade deve ter dia e hora dentro deste intervalo."
    )
    st.session_state.market_duration_days = market_duration_days
    st.info(f"📅 O mercado tem duração de **{market_duration_days} dias**. Trades devem ocorrer entre o Dia 1 e o Dia {market_duration_days}.")
else:
    market_duration_days = 14  # Default, not used for static

# Initial Probabilities
st.markdown("**Initial Probabilities:**")

col_slider, col_reset = st.columns([4, 1])
with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Reset", key="reset_prob_button", use_container_width=True, help="Reset to 50/50"):
        st.session_state.initial_prob_yes = 50.0
        st.session_state.slider_key_counter += 1
        st.rerun()

with col_slider:
    initial_prob_yes = st.slider(
        "Initial Probability",
        min_value=1.0,
        max_value=99.0,
        value=st.session_state.initial_prob_yes,
        step=0.1,
        key=f"initial_prob_slider_{st.session_state.slider_key_counter}",
        help="Probabilidade inicial: Esquerda (YES) | Direita (NO)"
    )

st.session_state.initial_prob_yes = initial_prob_yes
initial_prob_no = 100.0 - initial_prob_yes

col_prob_yes, col_prob_no = st.columns(2)
with col_prob_yes:
    st.metric("YES", f"{initial_prob_yes:.1f}%")
with col_prob_no:
    st.metric("NO", f"{initial_prob_no:.1f}%")

st.divider()

# =============================================================================
# Trades section
# =============================================================================
st.subheader("Trades")

col_import, col_model = st.columns(2)

with col_import:
    if st.button("Import JSON", use_container_width=True):
        st.session_state.show_import_json = not st.session_state.show_import_json
        st.session_state.show_json_model = False

with col_model:
    if st.button("JSON Template", use_container_width=True):
        st.session_state.show_json_model = not st.session_state.show_json_model
        st.session_state.show_import_json = False

if st.session_state.show_json_model:
    json_model = {
        "trades": [
            {"direction": "YES", "shares": 10, "day": 1, "time": "09:30"},
            {"direction": "NO", "shares": 5, "day": 3, "time": "14:15"},
            {"direction": "YES", "shares": 20, "day": 7, "time": "17:49"},
            {"direction": "NO", "shares": 15, "day": 12, "time": "10:00"}
        ]
    }
    st.json(json_model)
    st.code(json.dumps(json_model, indent=2), language="json")
    st.info("""
    **Formato das trades:**
    - `direction`: "YES" ou "NO"
    - `shares`: quantidade de shares
    - `day`: dia da trade (1 a duração do mercado)
    - `time`: hora da trade no formato "HH:MM"
    
    ⚠️ No modo **Static**, os campos `day` e `time` são ignorados.
    """)

if st.session_state.show_import_json:
    st.markdown("**Import Trades via JSON:**")
    json_input = st.text_area(
        "Paste JSON here:",
        height=200,
        key="json_input",
        help='Expected format: {"trades": [{"direction": "YES", "shares": 10, "day": 1, "time": "09:30"}, ...]}'
    )
    
    col_confirm, col_cancel = st.columns(2)
    
    with col_confirm:
        if st.button("Confirm Import", use_container_width=True, type="primary"):
            try:
                data = json.loads(json_input)
                if "trades" in data and isinstance(data["trades"], list):
                    imported_trades = []
                    for trade in data["trades"]:
                        if "direction" in trade and "shares" in trade:
                            direction = trade["direction"].upper()
                            if direction in ["YES", "NO"]:
                                shares = float(trade["shares"])
                                if shares > 0:
                                    # Get day and time (with defaults)
                                    day = int(trade.get("day", 1))
                                    trade_time = trade.get("time", "12:00")
                                    
                                    # Validate day is within market duration
                                    if is_dynamic:
                                        day = max(1, min(day, market_duration_days))
                                    
                                    # Validate time format
                                    try:
                                        h, m = map(int, trade_time.split(":"))
                                        trade_time = f"{h:02d}:{m:02d}"
                                    except:
                                        trade_time = "12:00"
                                    
                                    imported_trades.append({
                                        "direction": direction,
                                        "shares": shares,
                                        "day": day,
                                        "time": trade_time
                                    })
                    
                    if imported_trades:
                        # Sort by day and time
                        imported_trades.sort(key=lambda t: (t["day"], t["time"]))
                        st.session_state.trades = imported_trades
                        st.session_state.show_import_json = False
                        st.success(f"Imported {len(imported_trades)} trades successfully!")
                        st.rerun()
                    else:
                        st.error("No valid trades found in JSON.")
                else:
                    st.error("Invalid JSON format. Use the 'JSON Template' button to see the expected format.")
            except json.JSONDecodeError:
                st.error("Invalid JSON. Check the syntax.")
            except Exception as e:
                st.error(f"Error importing: {str(e)}")
    
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_import_json = False
            st.rerun()

# Display existing trades
if st.session_state.trades:
    col_clear, _ = st.columns([1, 4])
    with col_clear:
        if st.button("Clear All Trades", use_container_width=True, type="secondary"):
            st.session_state.trades = []
            st.session_state.trades_page = 1
            st.rerun()
    
    st.markdown("**Trades:**")
    
    trades_per_page = 10
    total_trades = len(st.session_state.trades)
    total_pages = max(1, (total_trades + trades_per_page - 1) // trades_per_page)
    
    if st.session_state.trades_page > total_pages:
        st.session_state.trades_page = total_pages
    if st.session_state.trades_page < 1:
        st.session_state.trades_page = 1
    
    start_idx = (st.session_state.trades_page - 1) * trades_per_page
    end_idx = min(start_idx + trades_per_page, total_trades)
    
    page_trades = st.session_state.trades[start_idx:end_idx]
    
    for idx, trade in enumerate(page_trades):
        global_idx = start_idx + idx
        
        if is_dynamic:
            col_num, col_time, col_dir, col_shares, col_remove = st.columns([1, 2, 1.5, 1.5, 1])
        else:
            col_num, col_dir, col_shares, col_remove = st.columns([1, 2, 2, 1])
        
        with col_num:
            st.write(f"**#{global_idx + 1}**")
        
        if is_dynamic:
            with col_time:
                st.write(f"📅 Day {trade['day']} @ {trade['time']}")
        
        with col_dir:
            st.write(trade['direction'])
        with col_shares:
            st.write(f"{trade['shares']} shares")
        with col_remove:
            if st.button("🗑️", key=f"remove_trade_{global_idx}", use_container_width=True, help=f"Remove trade #{global_idx + 1}"):
                st.session_state.trades.pop(global_idx)
                if st.session_state.trades_page > 1 and len(st.session_state.trades) <= (st.session_state.trades_page - 1) * trades_per_page:
                    st.session_state.trades_page -= 1
                st.rerun()
    
    if total_pages > 1:
        st.markdown("---")
        col_info, col_first, col_prev, col_next, col_last = st.columns([3, 1, 1, 1, 1])
        
        with col_info:
            st.markdown(f"**Page {st.session_state.trades_page} of {total_pages}** (Showing trades {start_idx + 1}-{end_idx} of {total_trades})")
        
        with col_first:
            if st.button("⏮ First", use_container_width=True, disabled=(st.session_state.trades_page == 1)):
                st.session_state.trades_page = 1
                st.rerun()
        
        with col_prev:
            if st.button("◀ Prev", use_container_width=True, disabled=(st.session_state.trades_page == 1)):
                st.session_state.trades_page -= 1
                st.rerun()
        
        with col_next:
            if st.button("Next ▶", use_container_width=True, disabled=(st.session_state.trades_page == total_pages)):
                st.session_state.trades_page += 1
                st.rerun()
        
        with col_last:
            if st.button("Last ⏭", use_container_width=True, disabled=(st.session_state.trades_page == total_pages)):
                st.session_state.trades_page = total_pages
                st.rerun()
else:
    st.info("No trades added yet. Add a trade below or import via JSON.")

# Add new trade section
st.markdown("**Add New Trade:**")

if is_dynamic:
    col_day, col_time, col_dir, col_shares = st.columns([1.5, 1.5, 1.5, 1.5])
    
    with col_day:
        new_day = st.number_input(
            "Day", 
            min_value=1, 
            max_value=market_duration_days, 
            value=1, 
            step=1, 
            key="new_trade_day"
        )
    
    with col_time:
        new_time = st.time_input(
            "Time", 
            value=time(12, 0), 
            key="new_trade_time"
        )
        new_time_str = new_time.strftime("%H:%M")
    
    with col_dir:
        new_direction = st.selectbox("Direction", ["YES", "NO"], key="new_trade_direction")
    
    with col_shares:
        new_shares = st.number_input("Shares", min_value=0.1, value=10.0, step=1.0, key="new_trade_shares")
else:
    col_dir, col_shares = st.columns(2)
    
    with col_dir:
        new_direction = st.selectbox("Trade Direction", ["YES", "NO"], key="new_trade_direction")
    
    with col_shares:
        new_shares = st.number_input("Shares", min_value=0.1, value=10.0, step=1.0, key="new_trade_shares")
    
    # Default values for static (not used but needed for consistency)
    new_day = 1
    new_time_str = "12:00"

if st.button("Add Trade", use_container_width=True, type="primary"):
    new_trade = {
        "direction": new_direction,
        "shares": new_shares,
        "day": new_day,
        "time": new_time_str
    }
    st.session_state.trades.append(new_trade)
    
    # Sort trades by day and time
    st.session_state.trades.sort(key=lambda t: (t["day"], t["time"]))
    st.rerun()

trades = st.session_state.trades

# Final Outcome buttons
st.markdown("**Final Outcome of Market:**")

yes_selected = st.session_state.final_outcome == "YES"
no_selected = st.session_state.final_outcome == "NO"

st.markdown(f"""
<style>
    div[data-testid="column"]:first-of-type button {{
        background-color: {'#28a745' if yes_selected else '#f8f9fa'} !important;
        color: {'white' if yes_selected else '#6c757d'} !important;
        border: 2px solid {'#28a745' if yes_selected else '#dee2e6'} !important;
        font-weight: {'bold' if yes_selected else 'normal'} !important;
    }}
    div[data-testid="column"]:first-of-type button:hover {{
        background-color: {'#218838' if yes_selected else '#e9ecef'} !important;
        border-color: {'#1e7e34' if yes_selected else '#adb5bd'} !important;
    }}
    div[data-testid="column"]:last-of-type button {{
        background-color: {'#dc3545' if no_selected else '#f8f9fa'} !important;
        color: {'white' if no_selected else '#6c757d'} !important;
        border: 2px solid {'#dc3545' if no_selected else '#dee2e6'} !important;
        font-weight: {'bold' if no_selected else 'normal'} !important;
    }}
    div[data-testid="column"]:last-of-type button:hover {{
        background-color: {'#c82333' if no_selected else '#e9ecef'} !important;
        border-color: {'#bd2130' if no_selected else '#adb5bd'} !important;
    }}
</style>
""", unsafe_allow_html=True)

col_yes, col_no = st.columns(2)

with col_yes:
    button_type = "primary" if yes_selected else "secondary"
    if st.button("YES", key="btn_yes", use_container_width=True, type=button_type):
        st.session_state.final_outcome = "YES"
        st.rerun()

with col_no:
    button_type = "primary" if no_selected else "secondary"
    if st.button("NO", key="btn_no", use_container_width=True, type=button_type):
        st.session_state.final_outcome = "NO"
        st.rerun()

final_outcome = st.session_state.final_outcome

# =============================================================================
# Simulation logic - Using cached function for performance
# =============================================================================

# Convert trades to hashable format (tuple of tuples) for caching
trades_tuple = tuple(
    (t['direction'], t['shares'], t['day'], t['time'])
    for t in trades
)

# Call cached simulation function
sim_results = simulate_trades_cached(
    trades_tuple, L_param, base_fee, initial_prob_yes,
    market_duration_days, is_dynamic, final_outcome
)

# Unpack results
rows = sim_results['rows']
price_history = sim_results['price_history']
total_cost = sim_results['total_cost']
total_fee = sim_results['total_fee']
payout = sim_results['payout']
net_worth = sim_results['net_worth']
x = sim_results['x']
y = sim_results['y']
x_initial = sim_results['x_initial']
y_initial = sim_results['y_initial']
final_price_yes = sim_results['final_price_yes']
final_price_no = sim_results['final_price_no']
T_minus_t_initial = sim_results['T_minus_t_initial']
T_minus_t_final = sim_results['T_minus_t_final']

# =============================================================================
# Results
# =============================================================================
st.subheader("Simulation Results")

if not trades:
    st.warning("No trades to simulate. Please add trades above.")
else:
    # Summary metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.metric("Total Cost Paid", f"{total_cost:.2f}")
        st.metric("Total Fees", f"{total_fee:.2f}")
    
    with col_m2:
        st.metric("Final Payout", f"{payout:.2f}")
        net_worth_delta = -net_worth if net_worth > 0 else abs(net_worth)
        st.metric("Net Worth", f"{net_worth:.2f}", delta=f"{net_worth_delta:.2f}", delta_color="inverse")
    
    with col_m3:
        st.metric("Final YES Price", f"{final_price_yes:.4f}")
        st.metric("Final NO Price", f"{final_price_no:.4f}")

    # Price evolution chart - Using cached plot function
    if price_history:
        st.markdown("**Price Evolution:**")

        # Convert price_history to tuple for caching
        price_history_tuple = tuple(
            (p['Trade'], p['Time'], p['YES Price'], p['NO Price'], p['T-t'])
            for p in price_history
        )

        fig = plot_price_evolution(price_history_tuple, amm_type, is_dynamic)
        st.pyplot(fig)

        # Show L_eff evolution for dynamic
        if is_dynamic and len(price_history) > 1:
            st.markdown("**Effective Liquidity (L_eff) Evolution:**")

            x_labels = [p['Time'] for p in price_history]
            fig3 = plot_leff_evolution(price_history_tuple, L_param, tuple(x_labels))
            st.pyplot(fig3)

    # Trades table
    st.markdown("**Trade Details:**")
    df = pd.DataFrame(rows)
    
    # Reorder columns for dynamic
    if is_dynamic and len(rows) > 0:
        cols_order = ["Day", "Time", "Direction", "Shares", "T-t (days)", "L_eff", "Price Before", "Price After", "Avg. Price", "Cost Paid", "Fee"]
        cols_order = [c for c in cols_order if c in df.columns]
        df = df[cols_order]
    
    st.dataframe(df, height=400, use_container_width=True)

# =============================================================================
# Invariant Curve Visualization - Using cached plot function
# =============================================================================
st.subheader("pm-AMM Invariant Curve")

# Use cached plot function
fig2 = plot_invariant_curve(
    L_param, T_minus_t_initial, is_dynamic, amm_type,
    market_duration_days, x_initial, y_initial,
    x, y, len(trades) > 0
)
st.pyplot(fig2)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #6c757d; font-size: 0.8em;">pm-AMM Simulator by Iago Macedo | Based on <a href="https://www.paradigm.xyz/2024/11/pm-amm">Paradigm Research</a></p>',
    unsafe_allow_html=True
)
