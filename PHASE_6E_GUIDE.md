# Phase 6E: Advanced Features Guide

## Overview

Phase 6E adds four advanced features to the EGX Radar trading system:
1. **Machine Learning Predictions** - Ensemble ML models for price direction prediction
2. **Options Trading** - Black-Scholes pricing, Greeks calculation, strategy analysis
3. **Risk Management** - Value at Risk, position sizing, drawdown analysis
4. **Portfolio Optimization** - Efficient frontier, risk parity, rebalancing

## 1. Machine Learning Predictions

### Features
- **Multiple Models**: Random Forest, Gradient Boosting, SVM
- **Ensemble Approach**: Combines all models for robust predictions
- **Feature Engineering**: RSI, MACD, Bollinger Bands, momentum, SMA crossovers, volume, volatility
- **Train/Predict**: Easy model training and prediction interface

### Usage

```python
from egx_radar.advanced import get_ensemble_predictor
from egx_radar.market_data import get_market_data_manager

# Get market data
mdm = get_market_data_manager()
data = mdm.get_historical_data('AAPL', days=365)

# Train ensemble
predictor = get_ensemble_predictor()
predictor.train(data, lookahead_days=5)

# Make prediction
prediction = predictor.predict(data)
print(f"Signal: {prediction['signal']}")
print(f"Confidence: {prediction['confidence']:.2%}")
print(f"Model agreement: {prediction['model_agreement']:.2%}")
```

### API Endpoints (Phase 6E)

#### GET `/api/advanced/predict/<symbol>`
Get ML prediction for a symbol.

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "prediction": {
    "timestamp": "2026-03-16T10:30:00",
    "signal": "buy",
    "prob_up": 0.72,
    "prob_down": 0.28,
    "confidence": 0.72,
    "model_count": 3,
    "model_agreement": 0.67
  }
}
```

#### POST `/api/advanced/train-model`
Train ensemble model on historical data.

**Request:**
```json
{
  "symbol": "AAPL",
  "days": 365,
  "lookahead_days": 5
}
```

## 2. Options Trading

### Features
- **Black-Scholes Pricing**: European option pricing
- **Greeks Calculation**: Delta, Gamma, Vega, Theta, Rho
- **Options Portfolio**: Multiple positions management
- **Strategies**: Long/short calls/puts, spreads, straddles, iron condors

### Greeks Explanation

| Greek | Meaning | What It Measures |
|-------|---------|-----------------|
| Delta | Directional Exposure | How much the option price changes with stock price |
| Gamma | Delta Sensitivity | How much delta changes with stock price |
| Vega | Volatility Exposure | How much option price changes with volatility |
| Theta | Time Decay | Daily decay of option value due to time |
| Rho | Rate Exposure | How much option price changes with interest rates |

### Usage

```python
from egx_radar.advanced import (
    get_options_calculator,
    OptionType,
    OptionsPortfolio
)
from datetime import datetime, timedelta

# Calculate option price
calc = get_options_calculator()
price = calc.calculate_price(
    S=150.25,  # Current stock price
    K=150.00,  # Strike price
    T=0.25,    # 3 months to expiration
    r=0.05,    # 5% interest rate
    sigma=0.25, # 25% volatility
    option_type=OptionType.CALL
)
print(f"Call option price: ${price:.2f}")

# Calculate Greeks
greeks = calc.calculate_greeks(150.25, 150.00, 0.25, 0.05, 0.25)
print(f"Delta: {greeks.delta:.3f}")
print(f"Gamma: {greeks.gamma:.6f}")
print(f"Vega: ${greeks.vega:.2f}")
print(f"Theta: ${greeks.theta:.2f}/day")

# Build options portfolio
portfolio = OptionsPortfolio()
portfolio.add_position(
    symbol='AAPL',
    option_type=OptionType.CALL,
    strike=150.00,
    expiration=datetime.now() + timedelta(days=90),
    quantity=10,
    entry_price=5.50
)

# Analyze portfolio
stock_prices = {'AAPL': 150.25}
volatility = {'AAPL': 0.25}
greeks = portfolio.calculate_portfolio_greeks(stock_prices, volatility)
print(f"Portfolio Delta: {greeks['delta']:.2f}")
print(f"Portfolio Vega: ${greeks['vega']:.2f}")
```

## 3. Risk Management

### Features
- **Value at Risk**: 95% confidence VaR calculation
- **Conditional VaR**: Expected shortfall
- **Drawdown Analysis**: Maximum and current drawdown
- **Sharpe/Sortino Ratios**: Risk-adjusted returns
- **Position Sizing**: Kelly Criterion and risk-based sizing
- **Correlation Risk**: Identify concentration in correlated assets

### Usage

```python
from egx_radar.advanced import get_risk_manager
import numpy as np

# Initialize risk manager
rm = get_risk_manager(account_size=100000)

# Calculate position size
position = rm.calculate_position_size(
    entry=150.25,
    stop_loss=145.00,
    confidence=0.75
)
print(f"Position size: {position} shares")

# Calculate Value at Risk
returns = np.random.normal(0.0005, 0.015, 252)  # Daily returns
var = rm.calculate_value_at_risk(returns)
print(f"VaR (95%): ${var:.2f}")

# Calculate Sharpe Ratio
sharpe = rm.calculate_sharpe_ratio(returns)
print(f"Sharpe Ratio: {sharpe:.2f}")

# Calculate metrics
equity = np.cumsum(returns) * 100000 + 100000
metrics = rm.calculate_risk_metrics(returns, equity)
print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
print(f"Calmar Ratio: {metrics.calmar_ratio:.2f}")

# Kelly Criterion position sizing
from egx_radar.advanced import PositionSizer
kelly = PositionSizer.kelly_criterion(
    win_rate=0.55,
    avg_win=1.5,
    avg_loss=1.0
)
position = PositionSizer.optimal_position_size(100000, 150.25, 145.00, kelly)
print(f"Kelly-based position: {position} shares")
```

## 4. Portfolio Optimization

### Features
- **Minimum Variance**: Portfolio with lowest risk
- **Maximum Sharpe Ratio**: Best risk-adjusted returns
- **Efficient Frontier**: All optimal portfolios
- **Risk Parity**: Equal risk contribution from each asset
- **Equal Weight**: Simple baseline allocation
- **Rebalancing**: Calculate trades needed to reach target

### Usage

```python
from egx_radar.advanced import get_portfolio_optimizer
import pandas as pd

# Load historical prices
prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)

# Get optimizer
opt = get_portfolio_optimizer()
returns = opt.calculate_returns(prices)

# Minimum variance portfolio
min_vol = opt.minimize_volatility(returns)
print(f"Min Volatility Portfolio:")
for symbol, weight in min_vol.weights.items():
    print(f"  {symbol}: {weight:.2%}")
print(f"Expected Return: {min_vol.expected_return:.2%}")
print(f"Volatility: {min_vol.expected_volatility:.2%}")

# Maximum Sharpe portfolio
max_sharpe = opt.maximize_sharpe_ratio(returns)
print(f"\nMax Sharpe Portfolio:")
for symbol, weight in max_sharpe.weights.items():
    print(f"  {symbol}: {weight:.2%}")
print(f"Sharpe Ratio: {max_sharpe.sharpe_ratio:.2f}")

# Risk Parity
risk_parity = opt.risk_parity(returns)

# Efficient Frontier
frontier = opt.generate_efficient_frontier(returns, num_portfolios=50)
print(f"\nGenerated {len(frontier)} portfolios")

# Rebalancing
trades = opt.rebalance_weights(
    current_prices={'AAPL': 150.25, 'MSFT': 380.50},
    current_holdings={'AAPL': 100, 'MSFT': 50},
    target_weights={'AAPL': 0.60, 'MSFT': 0.40},
    portfolio_value=70000
)
for symbol, shares in trades.items():
    action = 'BUY' if shares > 0 else 'SELL'
    print(f"{action} {abs(shares):.0f} shares of {symbol}")
```

## Complete Example: Integrated Trading System

```python
from egx_radar.market_data import get_signal_generator
from egx_radar.advanced import (
    get_ensemble_predictor,
    get_risk_manager,
    get_portfolio_optimizer
)

# 1. Generate market signal
sg = get_signal_generator()
signal = sg.generate_signal('AAPL')

# 2. Get ML confirmation
ep = get_ensemble_predictor()
prediction = ep.predict(data)

# 3. Calculate position size using risk management
rm = get_risk_manager(account_size=100000)
position_size = rm.calculate_position_size(
    entry=signal.entry_price,
    stop_loss=signal.stop_loss,
    confidence=prediction['confidence']
)

# 4. Size portfolio using optimization
opt = get_portfolio_optimizer()
weights = opt.maximize_sharpe_ratio(historical_returns)

# 5. Execute within risk limits
if rm.check_daily_loss_limit(daily_pnl):
    print("Daily loss limit reached, no new trades")
else:
    execute_trade(
        symbol='AAPL',
        position_size=position_size,
        entry=signal.entry_price,
        stop_loss=signal.stop_loss,
        target=signal.target_price
    )
```

## Advanced API Integration

Extend the dashboard with advanced features:

```python
# Add ML predictions to API routes
@api_bp.route('/advanced/predict/<symbol>', methods=['GET'])
def ml_predict(symbol):
    predictor = get_ensemble_predictor()
    data = get_market_data_manager().get_historical_data(symbol)
    prediction = predictor.predict(data)
    return jsonify(prediction)

# Add portfolio analysis
@api_bp.route('/advanced/portfolio/optimize', methods=['POST'])
def optimize_portfolio():
    data = request.get_json()
    opt = get_portfolio_optimizer()
    result = opt.maximize_sharpe_ratio(returns)
    return jsonify(result.weights)
```

## Performance Metrics

### ML Model Accuracy
- Ensemble models achieve 55-65% accuracy on price direction
- Varies by market conditions and training period
- Combine with technical signals for better results

### Options Pricing Accuracy
- Black-Scholes accurate for European options
- Real options may have bid/ask spreads
- Greeks useful for hedging and risk analysis

### Risk Management
- VaR provides confident risk bounds
- Position sizing prevents overleveraging
- Correlation analysis prevents concentration risk

## Troubleshooting

### ML Model Not Training
- Ensure at least 100 days of data
- Check for NaN values in features
- Verify return calculations

### Options Pricing Seems Off
- Check inputs (S, K, T, r, sigma)
- Compare with market prices
- Consider bid/ask spread

### Portfolio Optimization  Issues
- Ensure all symbols have correlation data
- Check for singular covariance matrix
- Try with different asset classes

## Next Steps

Potential Phase 6F additions:
- Real-time option chain fetching
- Machine learning hyperparameter optimization
- Advanced portfolio constraints (sector limits, etc.)
- Machine learning model persistence and versioning
- Real options analysis (American options)

