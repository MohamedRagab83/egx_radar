"""Flask blueprints for API and dashboard routes."""

from flask import Blueprint, jsonify, request, render_template, current_app
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import os


# Create blueprints
api_bp = Blueprint('api', __name__)
dashboard_bp = Blueprint('dashboard', __name__)


def _load_scan_snapshot() -> list:
    """Load the latest scanner results from the snapshot file.
    
    Returns:
        List of signal dicts from the most recent scan, or empty list if no snapshot exists.
    """
    try:
        from egx_radar.config.settings import K
        
        snapshot_path = os.path.join(
            os.path.dirname(K.OUTCOME_LOG_FILE), "scan_snapshot.json"
        )
        
        if not os.path.exists(snapshot_path):
            return []
        
        with open(snapshot_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return []


# ==================== DASHBOARD ROUTES ====================

@dashboard_bp.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@dashboard_bp.route('/backtests')
def backtests_page():
    """Backtests history page."""
    return render_template('backtests.html')


@dashboard_bp.route('/trades')
def trades_page():
    """Trades browser page."""
    return render_template('trades.html')


@dashboard_bp.route('/signals')
def signals_page():
    """Trading signals page."""
    return render_template('signals.html')


@dashboard_bp.route('/settings')
def settings_page():
    """Settings page."""
    return render_template('settings.html')


# ==================== API: BACKTESTS ====================

@api_bp.route('/backtests', methods=['GET'])
def get_backtests():
    """Get list of backtests with optional filtering."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        days = request.args.get('days', 30, type=int)
        symbol = request.args.get('symbol', None, type=str)
        status = request.args.get('status', None, type=str)
        
        backtests = current_app.db_manager.get_backtests(
            limit=limit,
            offset=offset,
            symbol=symbol,
            status=status,
            days=days
        )
        
        return jsonify({
            'success': True,
            'count': len(backtests),
            'backtests': [
                {
                    'id': bt.id,
                    'backtest_id': bt.backtest_id,
                    'date': bt.backtest_date.isoformat(),
                    'symbols': bt.symbols.split(','),
                    'symbol_count': bt.symbol_count,
                    'trades': bt.total_trades,
                    'win_rate': round(bt.win_rate, 4),
                    'pnl': float(bt.total_pnl),
                    'sharpe': round(bt.sharpe_ratio, 3),
                    'max_drawdown': round(bt.max_drawdown_pct, 2),
                    'execution_time': bt.execution_time_seconds,
                    'status': bt.status,
                }
                for bt in backtests
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/backtests/<int:backtest_id>', methods=['GET'])
def get_backtest_detail(backtest_id: int):
    """Get detailed backtest information."""
    try:
        backtest = current_app.db_manager.get_backtest(backtest_id)
        if not backtest:
            return jsonify({'success': False, 'error': 'Backtest not found'}), 404
        
        trades = current_app.db_manager.get_trades(backtest_id)
        signals = current_app.db_manager.get_signals(backtest_id)
        
        return jsonify({
            'success': True,
            'backtest': {
                'id': backtest.id,
                'backtest_id': backtest.backtest_id,
                'date': backtest.backtest_date.isoformat(),
                'start_date': backtest.start_date.isoformat(),
                'end_date': backtest.end_date.isoformat(),
                'symbols': backtest.symbols.split(','),
                'metrics': {
                    'total_trades': backtest.total_trades,
                    'winning_trades': backtest.winning_trades,
                    'losing_trades': backtest.losing_trades,
                    'win_rate': round(backtest.win_rate, 4),
                    'total_pnl': float(backtest.total_pnl),
                    'gross_profit': float(backtest.gross_profit),
                    'gross_loss': float(backtest.gross_loss),
                    'profit_factor': round(backtest.profit_factor, 2),
                    'max_drawdown': round(backtest.max_drawdown, 4),
                    'max_drawdown_pct': round(backtest.max_drawdown_pct, 2),
                    'sharpe_ratio': round(backtest.sharpe_ratio, 3),
                    'sortino_ratio': round(backtest.sortino_ratio, 3),
                    'calmar_ratio': round(backtest.calmar_ratio, 3),
                    'avg_trade_return': round(backtest.avg_trade_return, 4),
                    'expectancy': round(backtest.expectancy, 2),
                    'recovery_factor': round(backtest.recovery_factor, 2),
                },
                'execution': {
                    'time_seconds': backtest.execution_time_seconds,
                    'workers_used': backtest.workers_used,
                    'status': backtest.status,
                },
                'trades_count': len(trades),
                'signals_count': len(signals),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: TRADES ====================

@api_bp.route('/trades', methods=['GET'])
def get_trades():
    """Get trades with filtering."""
    try:
        backtest_id = request.args.get('backtest_id', type=int)
        symbol = request.args.get('symbol', None, type=str)
        result = request.args.get('result', None, type=str)  # win, loss
        
        if not backtest_id:
            return jsonify({'success': False, 'error': 'backtest_id required'}), 400
        
        trades = current_app.db_manager.get_trades(
            backtest_id,
            symbol=symbol,
            result=result
        )
        
        return jsonify({
            'success': True,
            'count': len(trades),
            'trades': [
                {
                    'id': t.id,
                    'symbol': t.symbol,
                    'entry_date': t.entry_date.isoformat(),
                    'entry_price': float(t.entry_price),
                    'entry_signal': t.entry_signal,
                    'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                    'exit_price': float(t.exit_price) if t.exit_price else None,
                    'exit_reason': t.exit_reason,
                    'quantity': t.quantity,
                    'result': t.result,
                    'pnl': float(t.pnl) if t.pnl else None,
                    'pnl_pct': round(t.pnl_pct, 4) if t.pnl_pct else None,
                    'duration_minutes': t.duration_minutes,
                }
                for t in trades
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: SIGNALS ====================

@api_bp.route('/signals', methods=['GET'])
def get_signals():
    """Get signals with filtering."""
    try:
        backtest_id = request.args.get('backtest_id', type=int)
        symbol = request.args.get('symbol', None, type=str)
        signal_type = request.args.get('type', None, type=str)
        
        if not backtest_id:
            return jsonify({'success': False, 'error': 'backtest_id required'}), 400
        
        signals = current_app.db_manager.get_signals(
            backtest_id,
            symbol=symbol,
            signal_type=signal_type
        )
        
        return jsonify({
            'success': True,
            'count': len(signals),
            'signals': [
                {
                    'id': s.id,
                    'symbol': s.symbol,
                    'date': s.signal_date.isoformat(),
                    'type': s.signal_type,
                    'strength': s.strength,
                    'momentum': s.momentum,
                    'trend': s.trend,
                    'volatility': s.volatility,
                    'volume_ratio': s.volume_ratio,
                    'indicators': s.indicators,
                    'source': s.source,
                    'trade_taken': s.trade_taken,
                }
                for s in signals
            ]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: STATISTICS ====================

@api_bp.route('/statistics/summary', methods=['GET'])
def get_summary_statistics():
    """Get summary statistics for recent backtests."""
    try:
        days = request.args.get('days', 30, type=int)
        
        summary = current_app.db_manager.get_summary_stats(days=days)
        
        return jsonify({
            'success': True,
            'summary': {
                'period_days': summary.get('period_days'),
                'total_backtests': summary.get('total_backtests'),
                'total_trades': summary.get('total_trades'),
                'total_pnl': round(summary.get('total_pnl', 0), 2),
                'avg_win_rate': round(summary.get('avg_win_rate', 0) * 100, 2),
                'avg_sharpe_ratio': round(summary.get('avg_sharpe_ratio', 0), 3),
                'best_trade_day': summary.get('best_trade_day').isoformat() if summary.get('best_trade_day') else None,
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/statistics/symbol/<symbol>', methods=['GET'])
def get_symbol_statistics(symbol: str):
    """Get performance statistics for a specific symbol."""
    try:
        days = request.args.get('days', 90, type=int)
        
        performance = current_app.db_manager.get_symbol_performance(symbol, days=days)
        
        if not performance:
            return jsonify({
                'success': True,
                'symbol': symbol,
                'data': None,
                'message': 'No data available'
            }), 200
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': {
                'backtests': performance.get('backtests', 0),
                'total_trades': performance.get('total_trades', 0),
                'avg_win_rate': round(performance.get('avg_win_rate', 0) * 100, 2),
                'avg_return': round(performance.get('avg_return', 0) * 100, 2),
                'avg_sharpe': round(performance.get('avg_sharpe', 0), 3),
                'recommendation': performance.get('recommendation', 'hold'),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: CONFIGURATION ====================

@api_bp.route('/config', methods=['GET'])
def get_configuration():
    """Get current configuration from environment."""
    try:
        import os
        
        # Try to import configuration if available, otherwise use defaults
        config_obj = None
        try:
            from egx_radar.configuration import K
            config_obj = K
        except ImportError:
            pass
        
        config_info = {
            'database': {
                'type': 'postgresql' if 'postgresql' in os.environ.get('DATABASE_URL', '') else 'sqlite',
                'url': os.environ.get('DATABASE_URL', 'sqlite:///egx_radar.db')[:50] + '...',
            },
            'workers': getattr(config_obj, 'WORKERS_COUNT', 4) if config_obj else 4,
            'chunk_size': getattr(config_obj, 'CHUNK_SIZE', 2) if config_obj else 2,
            'backtest': {
                'min_smartrank': getattr(config_obj, 'BT_MIN_SMARTRANK', 50) if config_obj else 50,
                'position_size': getattr(config_obj, 'BT_POSITION_SIZE', 1000) if config_obj else 1000,
                'stop_loss': getattr(config_obj, 'BT_STOP_LOSS_PERCENT', 0.05) if config_obj else 0.05,
                'take_profit': getattr(config_obj, 'BT_TAKE_PROFIT_PERCENT', 0.10) if config_obj else 0.10,
            },
            'data': {
                'min_bars': getattr(config_obj, 'DATA_MIN_BARS', 250) if config_obj else 250,
                'date_format': getattr(config_obj, 'DATE_FORMAT', '%Y-%m-%d') if config_obj else '%Y-%m-%d',
            },
            'version': '0.8.3'
        }
        
        return jsonify({
            'success': True,
            'config': config_info
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: HEALTH ====================

@api_bp.route('/health', methods=['GET'])
def api_health():
    """API health check."""
    try:
        # Try to access database
        current_app.db_manager.get_backtests(limit=1)
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'version': '0.8.3',
            'database': 'connected',
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
        }), 503


# ==================== API: MARKET DATA & SIGNALS ====================

@api_bp.route('/market/price/<symbol>', methods=['GET'])
def get_market_price(symbol: str):
    """Get current market price for a symbol."""
    try:
        from egx_radar.market_data import get_market_data_manager
        
        market_data = get_market_data_manager()
        price = market_data.get_current_price(symbol)
        
        if price is None:
            return jsonify({'success': False, 'error': f'Unable to fetch price for {symbol}'}), 400
        
        stats = market_data.get_price_stats(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'current_price': price,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/market/prices', methods=['POST'])
def get_market_prices():
    """Get current prices for multiple symbols."""
    try:
        from egx_radar.market_data import get_market_data_manager
        
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols provided'}), 400
        
        market_data = get_market_data_manager()
        prices = market_data.get_multi_prices(symbols)
        
        return jsonify({
            'success': True,
            'prices': prices
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/scanner', methods=['GET'])
def get_scanner_signals():
    """Return latest SmartRank signals from the core scanner.
    
    This endpoint returns real signals from the EGX Radar core scanner
    (using SmartRank scoring), not from the parallel market_data engine.
    
    Query Parameters:
        tag (str, optional): Filter by signal tag (buy, ultra, early, watch, sell)
        min_rank (float, optional): Minimum SmartRank threshold (0-100)
        sector (str, optional): Filter by sector
    
    Returns:
        success (bool): Whether the request was successful
        count (int): Number of signals returned
        source (str): Always 'core_scanner_smartrank'
        signals (list): List of signal dicts
        scan_time (str): ISO timestamp of when the scan was performed
    """
    try:
        snapshot = _load_scan_snapshot()
        if not snapshot:
            return jsonify({
                'success': False,
                'error': 'No scan results available. Run a scan first.',
                'hint': 'Launch the desktop scanner and press Gravity Scan.',
            }), 404

        # Optional filters
        tag_filter = request.args.get('tag', None)
        min_rank   = request.args.get('min_rank', 0, type=float)
        sector     = request.args.get('sector', None)

        results = snapshot
        if tag_filter:
            results = [r for r in results if r.get('tag') == tag_filter]
        if min_rank > 0:
            results = [r for r in results if r.get('smart_rank', 0) >= min_rank]
        if sector:
            results = [r for r in results if r.get('sector') == sector]

        return jsonify({
            'success':    True,
            'count':      len(results),
            'source':     'core_scanner_smartrank',
            'signals':    results,
            'scan_time':  results[0].get('scan_time') if results else (snapshot[0].get('scan_time') if snapshot else None),
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/generate/<symbol>', methods=['GET'])
def generate_signal(symbol: str):
    """Generate trading signal for a symbol."""
    try:
        from egx_radar.market_data import get_signal_generator
        
        signal_gen = get_signal_generator()
        signal = signal_gen.generate_signal(symbol)
        
        if signal is None:
            return jsonify({'success': False, 'error': f'Unable to generate signal for {symbol}'}), 400
        
        return jsonify({
            'success': True,
            'signal': signal.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/batch', methods=['POST'])
def generate_signals_batch():
    """Generate signals for multiple symbols."""
    try:
        from egx_radar.market_data import get_signal_generator
        
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols provided'}), 400
        
        signal_gen = get_signal_generator()
        signals = signal_gen.generate_signals_batch(symbols)
        
        # Convert to dict, filtering out None values
        signals_dict = {
            symbol: sig.to_dict() if sig else None
            for symbol, sig in signals.items()
        }
        
        return jsonify({
            'success': True,
            'signals': signals_dict
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/history/<symbol>', methods=['GET'])
def get_signal_history(symbol: str):
    """Get signal history for a symbol."""
    try:
        from egx_radar.market_data import get_signal_generator
        
        limit = request.args.get('limit', 100, type=int)
        signal_gen = get_signal_generator()
        signals = signal_gen.get_signal_history(symbol, limit=limit)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'count': len(signals),
            'signals': [s.to_dict() for s in signals]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/history', methods=['GET'])
def get_alerts():
    """Get alert history."""
    try:
        from egx_radar.market_data import get_notification_manager
        
        limit = request.args.get('limit', 50, type=int)
        alert_type = request.args.get('type', None, type=str)
        
        notification_mgr = get_notification_manager()
        
        # Import AlertType if filtering by type
        alerts = notification_mgr.get_alert_history(limit=limit)
        
        if alert_type:
            from egx_radar.market_data import AlertType
            try:
                atype = AlertType(alert_type)
                alerts = [a for a in alerts if a.alert_type == atype]
            except ValueError:
                pass
        
        return jsonify({
            'success': True,
            'count': len(alerts),
            'unread': notification_mgr.get_unread_count(),
            'alerts': [a.to_dict() for a in alerts]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/mark-read', methods=['POST'])
def mark_alerts_read():
    """Mark alerts as read."""
    try:
        from egx_radar.market_data import get_notification_manager
        
        data = request.get_json()
        count = data.get('count', 1)
        
        notification_mgr = get_notification_manager()
        notification_mgr.mark_as_read(count)
        
        return jsonify({
            'success': True,
            'unread': notification_mgr.get_unread_count()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/market/volatility/<symbol>', methods=['GET'])
def get_volatility(symbol: str):
    """Get intraday volatility for a symbol."""
    try:
        from egx_radar.market_data import get_market_data_manager
        
        market_data = get_market_data_manager()
        volatility = market_data.get_intraday_volatility(symbol)
        
        if volatility is None:
            return jsonify({'success': False, 'error': f'Unable to calculate volatility for {symbol}'}), 400
        
        sentiment = market_data.get_sentiment_indicators(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'volatility_percent': volatility,
            'sentiment': sentiment
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Not found'}), 404


@api_bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'error': 'Server error'}), 500
