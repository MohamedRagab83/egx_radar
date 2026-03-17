"""WebSocket support for real-time dashboard updates."""

from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from typing import Dict, Any, Optional

socketio = SocketIO(cors_allowed_origins="*")


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f'Client connected')
    emit('response', {
        'status': 'connected',
        'server_time': datetime.utcnow().isoformat(),
        'message': 'Connected to EGX Radar Dashboard'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f'Client disconnected')


@socketio.on('subscribe_backtest')
def handle_subscribe_backtest(data):
    """Subscribe to real-time backtest updates."""
    backtest_id = data.get('backtest_id')
    room = f'backtest_{backtest_id}'
    
    join_room(room)
    emit('subscribed', {
        'backtest_id': backtest_id,
        'room': room,
        'message': f'Subscribed to backtest {backtest_id}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_backtest')
def handle_unsubscribe_backtest(data):
    """Unsubscribe from backtest updates."""
    backtest_id = data.get('backtest_id')
    room = f'backtest_{backtest_id}'
    
    leave_room(room)
    emit('unsubscribed', {
        'backtest_id': backtest_id,
        'message': f'Unsubscribed from backtest {backtest_id}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('subscribe_symbol')
def handle_subscribe_symbol(data):
    """Subscribe to symbol updates."""
    symbol = data.get('symbol')
    room = f'symbol_{symbol}'
    
    join_room(room)
    emit('subscribed', {
        'symbol': symbol,
        'room': room,
        'message': f'Subscribed to {symbol} updates',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_symbol')
def handle_unsubscribe_symbol(data):
    """Unsubscribe from symbol updates."""
    symbol = data.get('symbol')
    room = f'symbol_{symbol}'
    
    leave_room(room)
    emit('unsubscribed', {
        'symbol': symbol,
        'message': f'Unsubscribed from {symbol} updates',
        'timestamp': datetime.utcnow().isoformat()
    })


def emit_backtest_update(backtest_id: int, update: Dict[str, Any]):
    """
    Emit backtest update to all subscribers.
    
    Args:
        backtest_id: Backtest ID
        update: Update data
    """
    room = f'backtest_{backtest_id}'
    socketio.emit('backtest_update', {
        'backtest_id': backtest_id,
        'update': update,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


def emit_trade_update(backtest_id: int, trade_data: Dict[str, Any]):
    """
    Emit new trade to subscribers.
    
    Args:
        backtest_id: Backtest ID
        trade_data: Trade information
    """
    room = f'backtest_{backtest_id}'
    socketio.emit('trade_executed', {
        'backtest_id': backtest_id,
        'trade': trade_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)
    
    # Also emit to symbol-specific room
    symbol = trade_data.get('symbol')
    if symbol:
        room = f'symbol_{symbol}'
        socketio.emit('trade_executed', {
            'symbol': symbol,
            'trade': trade_data,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)


def emit_signal_alert(symbol: str, signal_data: Dict[str, Any]):
    """
    Emit trading signal alert.
    
    Args:
        symbol: Symbol that generated signal
        signal_data: Signal information
    """
    room = f'symbol_{symbol}'
    socketio.emit('signal_alert', {
        'symbol': symbol,
        'signal': signal_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


def emit_system_update(message: str, level: str = 'info'):
    """
    Emit system-wide update to all connected clients.
    
    Args:
        message: Update message
        level: Log level (info, warning, error)
    """
    socketio.emit('system_update', {
        'message': message,
        'level': level,
        'timestamp': datetime.utcnow().isoformat()
    }, broadcast=True)


# ==================== MARKET DATA & SIGNALS ====================

@socketio.on('subscribe_market_symbol')
def handle_subscribe_market(data):
    """Subscribe to real-time market data for a symbol."""
    symbol = data.get('symbol')
    room = f'market_{symbol}'
    
    join_room(room)
    emit('market_subscribed', {
        'symbol': symbol,
        'room': room,
        'message': f'Subscribed to market data for {symbol}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_market_symbol')
def handle_unsubscribe_market(data):
    """Unsubscribe from market data."""
    symbol = data.get('symbol')
    room = f'market_{symbol}'
    
    leave_room(room)
    emit('market_unsubscribed', {
        'symbol': symbol,
        'message': f'Unsubscribed from market data for {symbol}',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('subscribe_signals')
def handle_subscribe_signals(data):
    """Subscribe to real-time trading signals."""
    signal_type = data.get('type', 'all')  # 'all', 'buy', 'sell', etc.
    room = f'signals_{signal_type}'
    
    join_room(room)
    emit('signals_subscribed', {
        'type': signal_type,
        'room': room,
        'message': f'Subscribed to {signal_type} signals',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_signals')
def handle_unsubscribe_signals(data):
    """Unsubscribe from signals."""
    signal_type = data.get('type', 'all')
    room = f'signals_{signal_type}'
    
    leave_room(room)
    emit('signals_unsubscribed', {
        'type': signal_type,
        'message': f'Unsubscribed from {signal_type} signals',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('subscribe_alerts')
def handle_subscribe_alerts(data):
    """Subscribe to real-time alerts and notifications."""
    alert_level = data.get('level', 'all')  # 'all', 'warning', 'critical', etc.
    room = 'alerts'
    
    join_room(room)
    emit('alerts_subscribed', {
        'level': alert_level,
        'message': f'Subscribed to alerts (level: {alert_level})',
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('unsubscribe_alerts')
def handle_unsubscribe_alerts(data):
    """Unsubscribe from alerts."""
    room = 'alerts'
    leave_room(room)
    emit('alerts_unsubscribed', {
        'message': 'Unsubscribed from alerts',
        'timestamp': datetime.utcnow().isoformat()
    })


def emit_price_update(symbol: str, price: float, timestamp: Optional[datetime] = None):
    """
    Emit real-time price update.
    
    Args:
        symbol: Stock symbol
        price: Current price
        timestamp: Update timestamp
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    room = f'market_{symbol}'
    socketio.emit('price_update', {
        'symbol': symbol,
        'price': price,
        'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
    }, room=room)


def emit_signal_generated(signal_data: Dict[str, Any]):
    """
    Emit newly generated trading signal.
    
    Args:
        signal_data: Signal information (dict)
    """
    # Emit to all signals subscribers
    socketio.emit('signal_generated', {
        'signal': signal_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room='signals_all')


def emit_scan_complete(results: list) -> None:
    """
    Emit scan_complete event to all connected dashboard clients.
    Called by scan/runner.py after every scan completes.
    
    Args:
        results: List of result dicts from run_scan() — same format as
                 scan_snapshot.json. Each result contains signal analysis
                 with SmartRank scores.
    """
    try:
        payload = {
            "event":     "scan_complete",
            "count":     len(results),
            "timestamp": datetime.utcnow().isoformat(),
            "signals": [{
                "sym":        r.get("sym"),
                "sector":     r.get("sector"),
                "signal":     r.get("signal"),
                "tag":        r.get("tag"),
                "smart_rank": r.get("smart_rank", 0.0),
                "direction":  r.get("signal_dir", r.get("direction", "")),
                "action":     r.get("plan", {}).get("action", "WAIT")
                               if isinstance(r.get("plan"), dict) else "WAIT",
                "entry":      r.get("plan", {}).get("entry", 0.0)
                               if isinstance(r.get("plan"), dict) else 0.0,
                "stop":       r.get("plan", {}).get("stop", 0.0)
                               if isinstance(r.get("plan"), dict) else 0.0,
                "target":     r.get("plan", {}).get("target", 0.0)
                               if isinstance(r.get("plan"), dict) else 0.0,
            } for r in results[:50]],  # cap at 50 to keep payload small
        }
        socketio.emit("scan_complete", payload, namespace="/", broadcast=True)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("emit_scan_complete failed: %s", exc)


def emit_alert(alert_data: Dict[str, Any]):
    """
    Emit alert/notification to subscribers.
    
    Args:
        alert_data: Alert information (dict)
    """
    socketio.emit('alert', {
        'alert': alert_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room='alerts')


def emit_market_update(symbol: str, update_data: Dict[str, Any]):
    """
    Emit comprehensive market update for a symbol.
    
    Args:
        symbol: Stock symbol
        update_data: Market data (price, volatility, sentiment, etc.)
    """
    room = f'market_{symbol}'
    socketio.emit('market_update', {
        'symbol': symbol,
        'data': update_data,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)
