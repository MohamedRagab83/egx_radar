# Phase 6D: Market Data & Live Signals Guide

## Overview

Phase 6D implements real-time market data feeds, live trading signal generation, and a comprehensive notification system integrated with the dashboard.

## Architecture

### Market Data Manager
- **Real-time data fetching** via yfinance
- **Price caching** with configurable cache size
- **Multi-symbol support** with efficient batch operations
- **Sentiment analysis** and volatility calculations
- **Subscriber pattern** for automatic notifications

### Live Signal Generator
- **Real-time indicator calculations**:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - Moving Averages (SMA 20/50)
  - Momentum calculations
  - Market sentiment
  
- **Signal generation** with:
  - Signal types: BUY, SELL, STRONG_BUY, STRONG_SELL, HOLD
  - Strength levels: WEAK, MODERATE, STRONG, VERY_STRONG
  - Confidence scoring (0.0 - 1.0)
  - Entry/exit targets and stop losses
  
- **Batch signal generation** for multiple symbols
- **Signal history tracking** with configurable limit

### Notification System
- **Alert types**: SIGNAL, TRADE, RISK, SYSTEM, PRICE_ALERT
- **Alert levels**: INFO, WARNING, CRITICAL
- **Subscriber pattern** for type, level, and symbol-specific alerts
- **Alert history** with metadata tracking
- **Unread count management**

### WebSocket Integration
- Real-time price updates
- Live signal notifications
- Alert broadcasting
- Market data streaming
- Symbol and type-specific rooms

## API Endpoints (Phase 6D)

### Market Data Endpoints

#### GET `/api/market/price/<symbol>`
Get current price and statistics for a symbol.

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "current_price": 150.25,
  "stats": {
    "min": 145.5,
    "max": 155.3,
    "avg": 150.1,
    "latest": 150.25,
    "count": 128,
    "last_update": "2026-03-16T10:30:00"
  }
}
```

#### GET `/api/market/volatility/<symbol>`
Get intraday volatility and sentiment for a symbol.

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "volatility_percent": 2.35,
  "sentiment": {
    "momentum": 1.25,
    "trend": "bullish",
    "rsi": 65.4,
    "strength": 1.25
  }
}
```

#### POST `/api/market/prices`
Get current prices for multiple symbols (batch operation).

**Request:**
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"]
}
```

**Response:**
```json
{
  "success": true,
  "prices": {
    "AAPL": 150.25,
    "MSFT": 380.50,
    "GOOGL": 140.75
  }
}
```

### Signal Endpoints

#### GET `/api/signals/generate/<symbol>`
Generate a trading signal for a specific symbol.

**Response:**
```json
{
  "success": true,
  "signal": {
    "symbol": "AAPL",
    "signal_type": "strong_buy",
    "strength": "very_strong",
    "confidence": 0.92,
    "entry_price": 150.25,
    "target_price": 155.50,
    "stop_loss": 145.75,
    "timestamp": "2026-03-16T10:30:00",
    "rsi": 28.5,
    "macd": 0.45,
    "momentum": 2.15,
    "trend": "bullish",
    "reason": "RSI oversold (28.5) + MACD positive crossover + SMA 20 > SMA 50",
    "indicators_used": ["RSI", "MACD", "Bollinger Bands", "Moving Averages", "Momentum"]
  }
}
```

#### POST `/api/signals/batch`
Generate signals for multiple symbols.

**Request:**
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"]
}
```

**Response:**
```json
{
  "success": true,
  "signals": {
    "AAPL": { /* signal object */ },
    "MSFT": { /* signal object */ },
    "GOOGL": { /* signal object */ }
  }
}
```

#### GET `/api/signals/history/<symbol>`
Get signal history for a symbol.

**Query Parameters:**
- `limit` (default: 100): Maximum signals to return

**Response:**
```json
{
  "success": true,
  "symbol": "AAPL",
  "count": 5,
  "signals": [ /* array of signal objects */ ]
}
```

### Alert Endpoints

#### GET `/api/alerts/history`
Get alert history with optional filtering.

**Query Parameters:**
- `limit` (default: 50): Maximum alerts to return
- `type` (optional): Filter by alert type (signal, trade, risk, system, price_alert)

**Response:**
```json
{
  "success": true,
  "count": 5,
  "unread": 2,
  "alerts": [
    {
      "alert_type": "signal",
      "level": "critical",
      "title": "Strong Buy: AAPL",
      "message": "Strong Buy signal at $150.25...",
      "timestamp": "2026-03-16T10:30:00",
      "symbol": "AAPL",
      "price": 150.25,
      "metadata": { /* alert metadata */ }
    }
  ]
}
```

#### POST `/api/alerts/mark-read`
Mark alerts as read.

**Request:**
```json
{
  "count": 5
}
```

**Response:**
```json
{
  "success": true,
  "unread": 1
}
```

## WebSocket Events (Phase 6D)

### Incoming Events (Client → Server)

#### subscribe_market_symbol
Subscribe to real-time market data for a symbol.

```javascript
socket.emit('subscribe_market_symbol', { symbol: 'AAPL' });
```

Response:
```javascript
socket.on('market_subscribed', (data) => {
  console.log(`Subscribed to ${data.symbol}`);
});
```

#### subscribe_signals
Subscribe to real-time trading signals.

```javascript
socket.emit('subscribe_signals', { type: 'buy' }); // or 'all', 'sell', etc.
```

#### subscribe_alerts
Subscribe to real-time alerts.

```javascript
socket.emit('subscribe_alerts', { level: 'all' }); // or 'warning', 'critical'
```

### Outgoing Events (Server → Client)

#### price_update
Real-time price update for a symbol.

```javascript
socket.on('price_update', (data) => {
  console.log(`${data.symbol}: $${data.price}`);
});
```

#### signal_generated
New trading signal generated.

```javascript
socket.on('signal_generated', (data) => {
  console.log(`${data.signal.signal_type} signal for ${data.signal.symbol}`);
  console.log(`Confidence: ${data.signal.confidence * 100}%`);
});
```

#### alert
New alert or notification.

```javascript
socket.on('alert', (data) => {
  console.log(`[${data.alert.level}] ${data.alert.title}`);
  console.log(data.alert.message);
});
```

#### market_update
Comprehensive market update for a symbol.

```javascript
socket.on('market_update', (data) => {
  console.log(`Market update for ${data.symbol}:`, data.data);
});
```

## Code Examples

### Python: Using Market Data Manager

```python
from egx_radar.market_data import get_market_data_manager

# Get market data manager
mdm = get_market_data_manager()

# Get current price
price = mdm.get_current_price('AAPL')
print(f"Current AAPL price: ${price}")

# Get multiple prices
prices = mdm.get_multi_prices(['AAPL', 'MSFT', 'GOOGL'])
print(prices)

# Get price statistics
stats = mdm.get_price_stats('AAPL')
print(f"AAPL stats: {stats}")

# Get volatility
vol = mdm.get_intraday_volatility('AAPL')
print(f"AAPL volatility: {vol}%")

# Subscribe to price updates
def on_price_update(symbol, price, timestamp):
    print(f"{symbol} update: ${price} at {timestamp}")

mdm.subscribe('AAPL', on_price_update)
```

### Python: Using Signal Generator

```python
from egx_radar.market_data import get_signal_generator

# Get signal generator
sg = get_signal_generator()

# Generate signal for a symbol
signal = sg.generate_signal('AAPL')
if signal:
    print(f"{signal.signal_type.value}: {signal.symbol}")
    print(f"Confidence: {signal.confidence * 100:.1f}%")
    print(f"Entry: ${signal.entry_price}")
    print(f"Target: ${signal.target_price}")
    print(f"Stop Loss: ${signal.stop_loss}")

# Generate signals for multiple symbols
signals = sg.generate_signals_batch(['AAPL', 'MSFT', 'GOOGL'])
for symbol, signal in signals.items():
    if signal:
        print(f"{symbol}: {signal.signal_type.value}")

# Get signal history
history = sg.get_signal_history('AAPL', limit=10)
print(f"Recent signals for AAPL: {len(history)}")
```

### Python: Notifications

```python
from egx_radar.market_data import (
    get_notification_manager,
    get_alert_generator,
    AlertType,
    AlertLevel
)

# Get managers
nm = get_notification_manager()
ag = get_alert_generator()

# Subscribe to alerts
def on_alert(alert):
    print(f"[{alert.level.value}] {alert.title}: {alert.message}")

nm.subscribe_to_level(AlertLevel.CRITICAL, on_alert)

# Create signal alert
signal = sg.generate_signal('AAPL')
if signal:
    alert = ag.signal_alert(signal)
    print(alert.to_dict())

# Create trade alert
trade_alert = ag.trade_alert('AAPL', 'buy', 150.25, 100)
print(trade_alert.to_dict())

# Get alert history
alerts = nm.get_alert_history(limit=20)
print(f"Recent alerts: {len(alerts)}")
```

### JavaScript: WebSocket Integration

```javascript
const socket = io('http://localhost:5000');

// Subscribe to market data
socket.emit('subscribe_market_symbol', { symbol: 'AAPL' });

// Listen for price updates
socket.on('price_update', (data) => {
  console.log(`${data.symbol}: $${data.price}`);
  updateUI(data);
});

// Subscribe to signals
socket.emit('subscribe_signals', { type: 'all' });

// Listen for signals
socket.on('signal_generated', (data) => {
  const signal = data.signal;
  notifyUser({
    title: signal.signal_type.toUpperCase(),
    message: `${signal.symbol} at $${signal.entry_price}`,
    confidence: signal.confidence
  });
});

// Subscribe to alerts
socket.emit('subscribe_alerts', { level: 'critical' });

// Listen for alerts
socket.on('alert', (data) => {
  console.log(`[${data.alert.level}] ${data.alert.title}`);
  displayAlert(data.alert);
});
```

## Running Phase 6D

### Development Mode

```bash
# Start the dashboard with market data support
python egx_radar/dashboard/run.py --debug --port 5000

# In another terminal, test market data API
curl http://localhost:5000/api/market/price/AAPL
curl http://localhost:5000/api/signals/generate/AAPL
curl http://localhost:5000/api/alerts/history
```

### Batch Signal Generation (Scheduled)

Create a scheduled task to generate signals periodically:

```python
import schedule
import time
from egx_radar.market_data import get_signal_generator
from egx_radar.dashboard.websocket import emit_signal_generated

def generate_and_broadcast_signals():
    """Generate signals for all tracked symbols."""
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
    sg = get_signal_generator()
    
    for symbol in symbols:
        signal = sg.generate_signal(symbol)
        if signal:
            emit_signal_generated(signal.to_dict())

if __name__ == '__main__':
    # Generate signals every 5 minutes
    schedule.every(5).minutes.do(generate_and_broadcast_signals)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

## Performance Considerations

- **Price caching**: Configured to keep last 5000 price points (reduces API calls)
- **Batch operations**: Efficient multi-symbol queries reduce overhead
- **WebSocket rooms**: Clients only receive updates for symbols they're subscribed to
- **Alert filtering**: Reduces noise by allowing level/type/symbol filtering

## Troubleshooting

### No prices updating
- Check yfinance connectivity: `python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='1d'))"`
- Verify API rate limits (yfinance has limits)
- Check network connectivity

### Signals not generating
- Ensure sufficient historical data available (minimum 10 days)
- Check console for exceptions
- Verify symbol spelling/format (e.g., 'AAPL' not 'Apple')

### WebSocket not connecting
- Check CORS configuration (should allow all origins)
- Verify client is using correct URL format (http://hostname:port)
- Check browser console for connection errors

## Next Phase

Phase 6E will add advanced features:
- Machine learning predictions
- Options trading support
- Advanced risk management
- Portfolio optimization

