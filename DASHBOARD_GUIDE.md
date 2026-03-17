# Dashboard & Web UI Guide

## Overview

EGX Radar includes a comprehensive web-based dashboard for real-time monitoring, analytics, and trade management. Built with Flask for the backend and vanilla JavaScript (with Socket.IO) for the frontend, it provides:

- **Real-time monitoring** of backtests and trades
- **Interactive charts** showing performance metrics
- **Trade browser** with detailed trade analysis
- **Signal watchlist** for tracking trading signals
- **System monitoring** and health status
- **Responsive design** for desktop and mobile

## Features

### Dashboard
- Summary metrics (total backtests, trades, win rate, P&L)
- Recent backtests table
- Real-time updates via WebSocket
- Quick navigation to other sections

### Backtests
- Browse historical backtest results
- Filter by symbol and date range
- View detailed backtest information
- Performance metrics visualization
- Execution statistics

### Trades
- Detailed trade history browser
- Filter by backtest, symbol, and result (winning/losing)
- Trade P&L and duration analysis
- Entry/exit price tracking
- Trade outcome classification

### Signals
- Trading signal history
- Signal strength and confidence levels
- Indicator information
- Trade outcome tracking
- Performance statistics by signal type

### Settings
- System configuration view
- Database settings
- Worker configuration
- Performance tuning options
- Strategy parameters

## Architecture

### Backend (Flask)

```
egx_radar/dashboard/
├── app.py           # Flask application factory
├── routes.py        # API routes and blueprints
├── websocket.py     # WebSocket server (Socket.IO)
├── run.py          # Entry point
└── templates/       # HTML templates
    ├── dashboard.html
    ├── backtests.html
    ├── trades.html
    ├── signals.html
    └── settings.html
```

### API Routes

**Dashboard & Pages:**
- `GET /` - Main dashboard
- `GET /backtests` - Backtests history
- `GET /trades` - Trades browser
- `GET /signals` - Signals page
- `GET /settings` - Settings page

**API Endpoints:**

**Backtests:**
- `GET /api/backtests` - List backtests (pagination, filtering)
- `GET /api/backtests/<id>` - Get backtest details

**Trades:**
- `GET /api/trades?backtest_id=<id>` - Get trades for backtest
  - Query params: `symbol`, `result` (win/loss)

**Signals:**
- `GET /api/signals?backtest_id=<id>` - Get signals
  - Query params: `symbol`, `type` (buy/sell/strong_buy/strong_sell)

**Statistics:**
- `GET /api/statistics/summary?days=<N>` - Summary stats
- `GET /api/statistics/symbol/<symbol>?days=<N>` - Symbol performance

**Configuration:**
- `GET /api/config` - Current system configuration

**Health:**
- `GET /api/health` - API health check
- `GET /health` - Server health check

### WebSocket Events

**Client → Server:**
- `subscribe_backtest` - Subscribe to backtest updates
- `unsubscribe_backtest` - Unsubscribe from backtest
- `subscribe_symbol` - Subscribe to symbol updates
- `unsubscribe_symbol` - Unsubscribe from symbol

**Server → Client:**
- `backtest_update` - Backtest metric updates
- `trade_executed` - New trade executed
- `signal_alert` - New trading signal
- `system_update` - System-wide notifications

## Running the Dashboard

### Development Mode

```bash
# Start dashboard server
python -m egx_radar.dashboard.run --debug --port 5000

# Or directly
python egx_radar/dashboard/run.py --debug

# Access at: http://localhost:5000
```

### Production Mode

```bash
# Start with production settings
python -m egx_radar.dashboard.run --host 0.0.0.0 --port 5000

# Using Gunicorn (recommended)
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 'egx_radar.dashboard.app:create_app()'

# Using Werkzeug (development)
python egx_radar/dashboard/run.py
```

### Docker Deployment

```dockerfile
# In existing Dockerfile, add dashboard support:
# Already configured in provided docker-compose.yml
```

```bash
# Start with Docker Compose
docker-compose up

# Dashboard will be available at http://localhost:5000
```

## Usage Examples

### Accessing the Dashboard

1. **Open browser:** Navigate to `http://localhost:5000`
2. **View dashboard:** Summary metrics and recent backtests
3. **Browse backtests:** Click "Backtests" nav link
4. **View trades:** Click "Trades" to see detailed trade history
5. **Check configuration:** Click "Settings" for system info

### Using the API

```bash
# Get summary statistics
curl http://localhost:5000/api/statistics/summary?days=30

# Get backtests
curl http://localhost:5000/api/backtests?limit=10&days=30

# Get trades for a backtest
curl "http://localhost:5000/api/trades?backtest_id=1&result=win"

# Get symbol performance
curl http://localhost:5000/api/statistics/symbol/CAIB?days=90

# Check health
curl http://localhost:5000/api/health
```

### WebSocket Integration

```javascript
// Connect to dashboard
const socket = io('http://localhost:5000');

socket.on('connect', () => {
    console.log('Connected to dashboard');
    
    // Subscribe to backtest updates
    socket.emit('subscribe_backtest', { backtest_id: 1 });
    
    // Subscribe to symbol updates
    socket.emit('subscribe_symbol', { symbol: 'CAIB' });
});

// Listen for updates
socket.on('trade_executed', (data) => {
    console.log('New trade:', data.trade);
});

socket.on('signal_alert', (data) => {
    console.log('New signal:', data.signal);
});

socket.on('backtest_update', (data) => {
    console.log('Backtest update:', data.update);
});
```

## Customization

### Adding Charts

The dashboard uses Chart.js for visualizations. Add to templates:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<canvas id="equity-chart"></canvas>
<script>
    const ctx = document.getElementById('equity-chart').getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar'],
            datasets: [{
                label: 'Equity',
                data: [100000, 105000, 102000],
                borderColor: '#00d9ff',
                fill: false
            }]
        }
    });
</script>
```

### Styling

The dashboard uses CSS Grid and Flexbox with CSS Variables:

```css
:root {
    --primary-color: #00d9ff;
    --bg-dark: #0f172a;
    --bg-darker: #1e293b;
    --border-color: #334155;
    --text-light: #e2e8f0;
}
```

Modify these variables to customize the theme globally.

### Adding New Pages

1. Create HTML template in `egx_radar/dashboard/templates/`
2. Add route in `egx_radar/dashboard/routes.py`
3. Add API endpoints as needed
4. Update navigation in templates

## Performance Optimization

### Database Queries
- Uses pagination (limit/offset) for large result sets
- Indexes on frequently queried columns
- Connection pooling for better performance

### Frontend
- Lazy loading of data
- Efficient DOM updates
- Minimal JavaScript
- Responsive design reduces bandwidth

### Caching
- WebSocket reduces polling overhead
- Server-side caching for static resources
- Browser caching for assets

## Security

### CORS
- Configured to allow cross-origin requests (can be restricted)
- API key authentication (optional enhancement):

```python
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.environ.get('API_KEY'):
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

### HTTPS
- Use reverse proxy (Nginx) with SSL in production
- Configure secure cookies
- Set security headers

## Monitoring & Logging

### Access Logs
```bash
# Using Gunicorn
gunicorn --access-logfile - --error-logfile - 'egx_radar.dashboard.app:create_app()'
```

### Error Handling
- Comprehensive error responses
- Health check endpoint
- System update notifications via WebSocket

## Troubleshooting

### Dashboard won't connect
```bash
# Check if server is running
curl http://localhost:5000/health

# Check firewall
netstat -an | grep 5000

# Review logs for errors
```

### WebSocket connection issues
```javascript
// Debug socket connection
const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
});
```

### Slow performance
- Check database size: `SELECT COUNT(*) FROM backtests;`
- Run cleanup: `db.cleanup_old_data(days=180)`
- Increase worker count for Gunicorn
- Add database indexes

## API Reference

See [API_DOCUMENTATION.md](../API_DOCUMENTATION.md) for complete endpoint documentation.
