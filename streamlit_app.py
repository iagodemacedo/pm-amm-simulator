import streamlit as st
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt

# LMSR functions
def calc_cost(q_yes, q_no, b):
    return b * np.log(np.exp(q_yes / b) + np.exp(q_no / b))

def calc_price(q_yes, q_no, b):
    """Calculate the price of YES shares. NO price is always 1 - YES price."""
    exp_yes = np.exp(q_yes / b)
    exp_no = np.exp(q_no / b)
    price_yes = exp_yes / (exp_yes + exp_no)
    return price_yes

def dynamic_fee(q_yes, q_no, base_fee=0.02):
    return base_fee

def dynamic_b(q_yes, q_no, base_b=100, min_b=30):
    total = q_yes + q_no
    if total == 0:
        return base_b
    imbalance_ratio = abs(q_yes - q_no) / total
    # return max(min_b, base_b * (1 - 0.6 * imbalance_ratio))
    return base_b

# Streamlit UI
st.title("LMSR Simulator")

# Initialize session state
if 'base_b' not in st.session_state:
    st.session_state.base_b = 100
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

# Parameters section
st.subheader("Parameters")
base_b = st.number_input("Base b Parameter", value=st.session_state.base_b, step=1, key="base_b_input")
st.session_state.base_b = base_b

base_fee_input = st.number_input("Base Fee Rate (%)", value=st.session_state.base_fee, step=0.1, key="base_fee_input")
st.session_state.base_fee = base_fee_input
base_fee = st.session_state.base_fee / 100

# Initial Probabilities
st.markdown("**Initial Probabilities:**")

# Handle reset button click - check BEFORE rendering slider
col_slider, col_reset = st.columns([4, 1])
with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)  # Align button with slider
    if st.button("Reset", key="reset_prob_button", use_container_width=True, help="Reset to 50/50"):
        st.session_state.initial_prob_yes = 50.0
        # Increment counter to force slider recreation
        st.session_state.slider_key_counter += 1
        st.rerun()

with col_slider:
    initial_prob_yes = st.slider(
        "Initial Probability",
        min_value=0.0,
        max_value=100.0,
        value=st.session_state.initial_prob_yes,
        step=0.1,
        key=f"initial_prob_slider_{st.session_state.slider_key_counter}",
        help="Probability distribution: Left (YES) | Right (NO)"
    )

# Update session state with slider value
st.session_state.initial_prob_yes = initial_prob_yes
initial_prob_no = 100.0 - initial_prob_yes

# Display probability values
col_prob_yes, col_prob_no = st.columns(2)
with col_prob_yes:
    st.metric("YES", f"{initial_prob_yes:.1f}%")
with col_prob_no:
    st.metric("NO", f"{initial_prob_no:.1f}%")

# Visual separator
st.divider()

# Trades section
st.subheader("Trades")

# Import JSON buttons
col_import, col_model = st.columns(2)

with col_import:
    if st.button("Import JSON", use_container_width=True):
        st.session_state.show_import_json = not st.session_state.show_import_json
        st.session_state.show_json_model = False

with col_model:
    if st.button("JSON Template", use_container_width=True):
        st.session_state.show_json_model = not st.session_state.show_json_model
        st.session_state.show_import_json = False

# Show JSON model
if st.session_state.show_json_model:
    json_model = {
        "trades": [
            {"direction": "YES", "shares": 10},
            {"direction": "NO", "shares": 5},
            {"direction": "YES", "shares": 20}
        ]
    }
    st.json(json_model)
    st.code(json.dumps(json_model, indent=2), language="json")
    st.info("Copy the JSON above and use it in the import field.")

# Import JSON modal
if st.session_state.show_import_json:
    st.markdown("**Import Trades via JSON:**")
    json_input = st.text_area(
        "Paste JSON here:",
        height=200,
        key="json_input",
        help="Expected format: {\"trades\": [{\"direction\": \"YES\", \"shares\": 10}, ...]}"
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
                                shares = int(trade["shares"])
                                if shares > 0:
                                    imported_trades.append((direction, shares))
                    
                    if imported_trades:
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

# Display existing trades in a table
if st.session_state.trades:
    # Clear all trades button
    col_clear, _ = st.columns([1, 4])
    with col_clear:
        if st.button("Clear All Trades", use_container_width=True, type="secondary"):
            st.session_state.trades = []
            st.session_state.trades_page = 1
            st.rerun()
    
    # Display trades with remove buttons
    st.markdown("**Trades:**")
    
    # Pagination settings
    trades_per_page = 10
    total_trades = len(st.session_state.trades)
    total_pages = max(1, (total_trades + trades_per_page - 1) // trades_per_page)
    
    # Ensure current page is valid
    if st.session_state.trades_page > total_pages:
        st.session_state.trades_page = total_pages
    if st.session_state.trades_page < 1:
        st.session_state.trades_page = 1
    
    # Calculate start and end indices for current page
    start_idx = (st.session_state.trades_page - 1) * trades_per_page
    end_idx = min(start_idx + trades_per_page, total_trades)
    
    # Get trades for current page
    page_trades = st.session_state.trades[start_idx:end_idx]
    
    # Display trades as a list
    for idx, (direction, shares) in enumerate(page_trades):
        global_idx = start_idx + idx
        col_num, col_dir, col_shares, col_remove = st.columns([1, 2, 2, 1])
        with col_num:
            st.write(f"**#{global_idx + 1}**")
        with col_dir:
            st.write(direction)
        with col_shares:
            st.write(f"{shares} shares")
        with col_remove:
            if st.button("🗑️", key=f"remove_trade_{global_idx}", use_container_width=True, help=f"Remove trade #{global_idx + 1}"):
                st.session_state.trades.pop(global_idx)
                # Adjust page if needed
                if st.session_state.trades_page > 1 and len(st.session_state.trades) <= (st.session_state.trades_page - 1) * trades_per_page:
                    st.session_state.trades_page -= 1
                st.rerun()
    
    # Pagination controls
    st.markdown("---")
    col_info, col_first, col_prev, col_next, col_last = st.columns([3, 1, 1, 1, 1])
    
    with col_info:
        st.markdown(f"**Page {st.session_state.trades_page} of {total_pages}** (Showing trades {start_idx + 1}-{end_idx} of {total_trades})")
    
    with col_first:
        if st.button("⏮ First", use_container_width=True, disabled=(st.session_state.trades_page == 1)):
            st.session_state.trades_page = 1
            st.rerun()
    
    with col_prev:
        if st.button("◀ Previous", use_container_width=True, disabled=(st.session_state.trades_page == 1)):
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
col_dir, col_shares = st.columns(2)

with col_dir:
    new_direction = st.selectbox("Trade Direction", ["YES", "NO"], key="new_trade_direction")

with col_shares:
    new_shares = st.number_input("Shares", min_value=1, value=10, step=1, key="new_trade_shares")

if st.button("Add Trade", use_container_width=True, type="primary"):
    st.session_state.trades.append((new_direction, new_shares))
    st.rerun()

trades = st.session_state.trades

# Final Outcome buttons
st.markdown("**Final Outcome of Market:**")

yes_selected = st.session_state.final_outcome == "YES"
no_selected = st.session_state.final_outcome == "NO"

# CSS to style buttons based on selection state
st.markdown(f"""
<style>
    /* Style for YES button - both primary and secondary */
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
    /* Style for NO button - both primary and secondary */
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
    # Use type="primary" when selected to make it more visible
    button_type = "primary" if yes_selected else "secondary"
    if st.button("YES", key="btn_yes", use_container_width=True, type=button_type):
        st.session_state.final_outcome = "YES"
        st.rerun()

with col_no:
    # Use type="primary" when selected to make it more visible
    button_type = "primary" if no_selected else "secondary"
    if st.button("NO", key="btn_no", use_container_width=True, type=button_type):
        st.session_state.final_outcome = "NO"
        st.rerun()

final_outcome = st.session_state.final_outcome

# Simulation logic
# Calculate initial q_yes and q_no based on initial probabilities
# P(YES) = e^(q_yes/b) / (e^(q_yes/b) + e^(q_no/b))
# If we set q_no = 0 as reference: q_yes = b * ln(p_yes / p_no)
p_yes = initial_prob_yes / 100.0
p_no = initial_prob_no / 100.0

if p_yes > 0 and p_no > 0:
    q_yes = base_b * np.log(p_yes / p_no)
    q_no = 0.0
elif p_yes == 0:
    # Extreme case: 0% YES probability
    q_yes = -base_b * 10  # Very negative
    q_no = 0.0
elif p_no == 0:
    # Extreme case: 100% YES probability
    q_yes = base_b * 10  # Very positive
    q_no = 0.0
else:
    # Default: 50/50
    q_yes = 0.0
    q_no = 0.0

total_cost = 0
total_fee = 0
rows = []

# Track user's purchased shares separately (for payout calculation)
user_q_yes = 0
user_q_no = 0

# Track price evolution for chart
price_history = []

# Calculate initial prices before any trades
b_initial = dynamic_b(q_yes, q_no, base_b)
initial_price_yes = calc_price(q_yes, q_no, b_initial)
price_history.append({
    "Trade": 0,
    "YES Price": initial_price_yes,
    "NO Price": 1.0 - initial_price_yes
})

for idx, (direction, shares) in enumerate(trades, start=1):
    b_now = dynamic_b(q_yes, q_no, base_b)
    cost_before = calc_cost(q_yes, q_no, b_now)

    if direction == "YES":
        q_yes_new = q_yes + shares
        q_no_new = q_no
        user_q_yes += shares  # Track user's shares
    else:
        q_yes_new = q_yes
        q_no_new = q_no + shares
        user_q_no += shares  # Track user's shares

    cost_after = calc_cost(q_yes_new, q_no_new, b_now)
    cost = cost_after - cost_before
    fee_rate = dynamic_fee(q_yes, q_no, base_fee)
    fee = cost * fee_rate

    total_cost += cost
    total_fee += fee
    q_yes, q_no = q_yes_new, q_no_new

    # Calculate prices after this trade
    price_yes = calc_price(q_yes, q_no, b_now)
    price_no = 1.0 - price_yes
    price_history.append({
        "Trade": idx,
        "YES Price": price_yes,
        "NO Price": price_no
    })

    avg_price = cost / shares if shares > 0 else 0
    
    rows.append({
        "Direction": direction,
        "Shares": shares,
        "b Used": round(b_now, 2),
        "Fee Rate": round(fee_rate, 4),
        "Cost Paid": round(cost, 4),
        "Avg. Price": round(avg_price, 4),
        "Fee Earned": round(fee, 4)
    })

# Payout is based only on user's purchased shares, not market state
payout = user_q_yes if final_outcome == "YES" else user_q_no
net_worth = total_fee + total_cost - payout

# Calculate final prices after all trades
b_final = dynamic_b(q_yes, q_no, base_b)
final_price_yes = calc_price(q_yes, q_no, b_final)
final_price_no = 1.0 - final_price_yes

# Results
st.subheader("Simulation Results")

if not trades:
    st.warning("No trades to simulate. Please add trades above.")
else:
    # Summary before table
    st.markdown(f"**Total Cost Paid:** {total_cost:.2f} BRL")
    st.markdown(f"**Total Fees Earned:** {total_fee:.2f} BRL")
    st.markdown(f"**Final Payout:** {payout:.2f} BRL")
    st.markdown(f"**Final YES Price:** {final_price_yes:.4f}")
    st.markdown(f"**Final NO Price:** {final_price_no:.4f}")

    # Net Worth with conditional color
    net_worth_color = "red" if net_worth < 0 else "green"
    st.markdown(f"**Net Worth:** <span style='color:{net_worth_color}'>{net_worth:.2f} BRL</span>", unsafe_allow_html=True)

    # Price evolution chart
    if price_history:
        st.markdown("**Price Evolution:**")
        price_df = pd.DataFrame(price_history)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(price_df["Trade"], price_df["YES Price"], label="YES Price", color="#28a745", linewidth=2, marker="o")
        ax.plot(price_df["Trade"], price_df["NO Price"], label="NO Price", color="#dc3545", linewidth=2, marker="s")
        ax.set_xlabel("Trade Number")
        ax.set_ylabel("Price")
        ax.set_title("Share Price Evolution")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 1])
        plt.tight_layout()
        st.pyplot(fig)

    # Table with scroll (showing approximately 10 rows)
    df = pd.DataFrame(rows)
    st.dataframe(df, height=400)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #6c757d; font-size: 0.8em;">By Iago Macedo</p>',
    unsafe_allow_html=True
)
