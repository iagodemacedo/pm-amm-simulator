# CLAUDE.MD - pm-AMM Simulator

## Project Overview

This is an interactive simulator for prediction markets using **pm-AMM** (Prediction Market Automated Market Maker), a uniform AMM optimized for prediction markets developed by Paradigm.

**Repository**: iagodemacedo/pm-amm-simulator
**Language**: Python
**Framework**: Streamlit
**Author**: Iago Macedo

## Core Concept

The pm-AMM uses a normal distribution-based invariant to provide constant-function automated market making for binary prediction markets (YES/NO outcomes). The simulator implements both static and dynamic variants.

### Mathematical Foundation

**Price Formula**:
```
P = Φ((y - x) / L_eff)
```

**Invariant**:
```
(y - x) × Φ((y-x)/L_eff) + L_eff × φ((y-x)/L_eff) - y = 0
```

Where:
- `x`, `y`: reserves of YES and NO tokens
- `L`: base liquidity parameter
- `L_eff`: effective liquidity (varies by AMM type)
- `φ`: standard normal PDF
- `Φ`: standard normal CDF
- `T-t`: time remaining until market expiration

## AMM Variants

### Static pm-AMM
- **Constant liquidity**: `L_eff = L`
- **No time dependency**: trades don't require timestamps
- **Best for**: long-term markets where volatility doesn't increase near expiration
- **LVR behavior**: increases near expiration

### Dynamic pm-AMM
- **Time-decaying liquidity**: `L_eff = L × √(T-t)`
- **Time-dependent**: each trade requires day and time
- **Best for**: markets with defined expiration dates
- **LVR behavior**: constant over time, protecting LPs near expiration

## Project Structure

```
pm-amm-simulator/
├── streamlit_app.py       # Main application (single-file architecture)
├── requirements.txt       # Python dependencies
├── README.md             # User documentation (Portuguese)
├── CLAUDE.MD             # This file - AI assistant guide
├── LICENSE               # MIT License
└── .devcontainer/        # Development container config
```

## Key File: streamlit_app.py

This is the complete application in a single file (~1000 lines). Structure:

### Mathematical Functions (lines 1-150)
- `phi(z)`: Standard normal PDF
- `Phi(z)`: Standard normal CDF
- `Phi_inv(p)`: Inverse CDF (quantile function)
- `get_effective_L()`: Calculate L_eff based on AMM type
- `calc_price_pmamm()`: Calculate YES token price
- `calc_portfolio_value()`: Calculate portfolio value V(P)
- `invariant_pmamm()`: The invariant equation
- `solve_for_y()`, `solve_for_x()`: Numerical solvers using Brentq
- `calc_trade_cost()`: Calculate cost for buying/selling shares

### Trade Simulation Logic (lines 150-400)
- `simulate_trades()`: Main simulation engine
- Trade sequencing with proper state management
- Fee calculations
- Time-dependent liquidity updates (Dynamic mode)

### UI Components (lines 400-1000)
- Streamlit interface with sidebar parameters
- Trade input forms (different for Static/Dynamic)
- JSON import/export functionality
- Data tables with formatted output
- Visualization charts (Price Evolution, L_eff Evolution, Invariant Curve)

## Time Calculation (Dynamic Mode)

```python
elapsed_days = (day - 1) + (hour + minute/60) / 24
T_minus_t = market_duration_days - elapsed_days
```

**Example** (14-day market):
- Day 1, 00:00 → T-t = 14.0 days
- Day 1, 12:00 → T-t = 13.5 days
- Day 7, 18:00 → T-t = 7.25 days
- Day 14, 23:59 → T-t ≈ 0.001 days

## Dependencies

```
streamlit
numpy
pandas
matplotlib
scipy
```

All listed in `requirements.txt`.

## Running the Application

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app runs on `http://localhost:8501` by default.

## Trade Data Format

### JSON Import Format
```json
{
  "trades": [
    {"direction": "YES", "shares": 10, "day": 1, "time": "09:30"},
    {"direction": "NO", "shares": 5, "day": 3, "time": "14:15"}
  ]
}
```

**Fields**:
- `direction`: "YES" or "NO" (required)
- `shares`: positive number (required)
- `day`: 1 to market_duration (optional, default: 1)
- `time`: "HH:MM" format (optional, default: "12:00")

Note: In Static mode, `day` and `time` are ignored.

## Key Features

1. **Dual AMM Support**: Switch between Static and Dynamic variants
2. **Interactive Trade Entry**: Manual form-based trade addition
3. **Batch Import**: JSON-based bulk trade import
4. **Real-time Calculations**: Instant price and cost updates
5. **Rich Visualizations**:
   - Price evolution over time
   - L_eff evolution (Dynamic mode)
   - Invariant curve plotting
6. **Detailed Metrics**: Trade-by-trade breakdown with fees, prices, L_eff

## Development Guidelines

### When Making Changes

1. **Mathematical Functions**: Be careful with numerical stability
   - Always clamp probabilities to avoid infinities
   - Use `max(T_minus_t, 1e-10)` to prevent division by zero
   - Brentq solver requires proper bounds

2. **UI Updates**: Streamlit re-runs entire script on interaction
   - Use `st.session_state` for persistent data
   - Trades are stored in `st.session_state['trades']`
   - Parameters in `st.session_state['params']`

3. **Testing Changes**:
   - Test both Static and Dynamic modes
   - Verify edge cases (T-t → 0, extreme prices)
   - Check JSON import/export round-trip

### Common Tasks

**Add a new parameter**:
1. Add to sidebar UI
2. Store in `st.session_state['params']`
3. Pass to calculation functions
4. Update simulation logic if needed

**Modify trade calculations**:
1. Update `calc_trade_cost()` or related functions
2. Update `simulate_trades()` logic
3. Test with sample trades
4. Verify results table displays correctly

**Add visualizations**:
1. Create matplotlib figure after simulation results
2. Use existing data structures (DataFrames)
3. Add to appropriate tab in results section

## Important Notes

### Numerical Stability
- Probability values are clamped to [1e-10, 1-1e-10]
- T-t is bounded to minimum 1e-10
- Solver bounds are ±10 × L_eff from current position

### Session State Management
Streamlit re-executes the entire script on each interaction. Key state:
- `st.session_state['trades']`: List of trade dictionaries
- `st.session_state['params']`: AMM parameters
- `st.session_state['show_json_import']`: UI state flags

### Language
- README.md is in Portuguese (target audience)
- Code comments and UI strings are in English/Portuguese mix
- Documentation should maintain this bilingual approach

## Reference Material

**Primary Source**: [pm-AMM: A Uniform AMM for Prediction Markets](https://www.paradigm.xyz/2024/11/pm-amm) - Paradigm Research

**Key Concepts**:
- Uniform AMMs for prediction markets
- Loss-versus-Rebalancing (LVR)
- Time-decaying liquidity mechanisms
- Normal distribution-based pricing

## Testing Scenarios

### Basic Functionality
1. Static mode: Add several YES/NO trades, verify prices move correctly
2. Dynamic mode: Add trades at different times, verify L_eff decreases
3. JSON import: Import sample trades, verify they appear in table
4. Parameter changes: Modify L and fee rate, verify recalculation

### Edge Cases
1. Near expiration (Dynamic): Trade at day=duration, time=23:59
2. Extreme prices: Drive price to ~0.01 or ~0.99
3. Large trades: Test with shares >> L
4. Empty state: App should handle zero trades gracefully

## Git Workflow

**Current Branch**: `claude/update-claude-md-017yeSqpSYAjNUH5MdGc92H2`

When making changes:
```bash
git add .
git commit -m "descriptive message"
git push -u origin claude/update-claude-md-017yeSqpSYAjNUH5MdGc92H2
```

## Future Enhancement Ideas

- Multi-outcome markets (beyond binary)
- Historical trade replay with animation
- LP position tracking and PnL
- Comparison mode (Static vs Dynamic side-by-side)
- Export results to CSV/JSON
- Interactive parameter sensitivity analysis
- Real-time market data integration

---

*This document is designed to help AI assistants quickly understand and work with the pm-AMM simulator codebase.*
