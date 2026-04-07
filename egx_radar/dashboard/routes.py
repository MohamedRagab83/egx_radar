"""Flask blueprints for API and dashboard routes."""

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from flask_login import current_user, login_required, login_user, logout_user
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import os

from egx_radar.database.models import User, ScanRun, ScanSignal
from egx_radar.dashboard.telegram_service import (
    build_connect_url,
    connect_user_from_telegram_updates,
    dispatch_latest_snapshot_alerts,
    ensure_connect_token,
    get_bot_username,
    send_test_message,
    telegram_ready,
)


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


def _load_latest_scan_signals() -> tuple[ScanRun | None, list[ScanSignal]]:
    """Load the newest persisted scan results from the database."""
    try:
        with current_app.db_manager.get_session() as session:
            latest_run = session.query(ScanRun).order_by(
                ScanRun.timestamp.desc(),
                ScanRun.id.desc(),
            ).first()
            if latest_run is None:
                return None, []

            signals = session.query(ScanSignal).filter(
                ScanSignal.scan_run_id == latest_run.id
            ).order_by(
                ScanSignal.smart_rank.desc(),
                ScanSignal.symbol.asc(),
            ).all()
            return latest_run, signals
    except Exception:
        return None, []


# ==================== DASHBOARD ROUTES ====================

@dashboard_bp.route('/')
def home():
    """Simple home redirect for the SaaS dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_dashboard'))
    return redirect(url_for('dashboard.login'))


@dashboard_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Create a simple user account."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_dashboard'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not email:
            flash('Email is required.', 'error')
        elif not password:
            flash('Password is required.', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
        else:
            with current_app.db_manager.get_session() as session:
                existing_user = session.query(User).filter(User.email == email).first()
                if existing_user is not None:
                    flash('This email is already registered.', 'error')
                else:
                    user = User(email=email)
                    user.set_password(password)
                    session.add(user)
                    session.flush()
                    login_user(user)
                    flash('Account created successfully.', 'success')
                    return redirect(url_for('dashboard.user_dashboard'))

    return render_template('register.html')


@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log a user into the dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_dashboard'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        with current_app.db_manager.get_session() as session:
            user = session.query(User).filter(User.email == email).first()

        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'error')
        else:
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard.user_dashboard'))

    return render_template('login.html')


@dashboard_bp.route('/logout')
@login_required
def logout():
    """Log the current user out."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('dashboard.login'))


@dashboard_bp.route('/dashboard')
@login_required
def user_dashboard():
    """Simple authenticated dashboard page."""
    latest_run, signals = _load_latest_scan_signals()
    return render_template(
        'user_dashboard.html',
        latest_run=latest_run,
        signals=signals,
        telegram_ready=telegram_ready(),
    )


@dashboard_bp.route('/telegram/connect', methods=['GET', 'POST'])
@login_required
def telegram_connect():
    """Connect the logged-in user to Telegram."""
    token = ensure_connect_token(current_app.db_manager, current_user.id)
    connect_url = build_connect_url(token)
    bot_username = get_bot_username()

    if request.method == 'POST':
        connected = connect_user_from_telegram_updates(current_app.db_manager, current_user.id)
        if connected:
            flash('Telegram connected successfully.', 'success')
            return redirect(url_for('dashboard.user_dashboard'))
        flash('Telegram is not connected yet. Open the bot link, send /start, then try again.', 'error')

    return render_template(
        'telegram_connect.html',
        telegram_ready=telegram_ready(),
        token=token,
        connect_url=connect_url,
        bot_username=bot_username,
    )


@dashboard_bp.route('/telegram/test', methods=['POST'])
@login_required
def telegram_test():
    """Send a simple test message to the logged-in user."""
    if send_test_message(current_app.db_manager, current_user.id):
        flash('Test Telegram message sent.', 'success')
    else:
        flash('Telegram test failed. Make sure your bot token is set and your account is connected.', 'error')
    return redirect(url_for('dashboard.user_dashboard'))


@dashboard_bp.route('/telegram/dispatch', methods=['POST'])
@login_required
def telegram_dispatch():
    """Dispatch latest eligible alerts for the logged-in user only."""
    summary = dispatch_latest_snapshot_alerts(current_app.db_manager, user_ids=[current_user.id])
    if summary.get('sent', 0) > 0:
        flash(f"Sent {summary['sent']} Telegram alert(s).", 'success')
    elif summary.get('duplicates_skipped', 0) > 0:
        flash('No new alerts sent. Today’s eligible alerts were already delivered.', 'success')
    else:
        flash('No eligible STRONG ACCUMULATE alerts found in the latest scanner snapshot.', 'error')
    return redirect(url_for('dashboard.user_dashboard'))


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
    """Get current price for a symbol from the latest scan snapshot."""  # Phase 8 — GAP-1 fix
    try:
        snapshot = _load_scan_snapshot()  # Phase 8 — GAP-1 fix
        result = next((r for r in snapshot if r.get('sym') == symbol), None)  # Phase 8 — GAP-1 fix

        if result is None:
            if not snapshot:
                return jsonify({'status': 'no_scan_yet', 'message': 'Scanner has not completed a scan yet'}), 404  # Phase 8 — GAP-1 fix
            return jsonify({'success': False, 'error': f'Symbol {symbol} not found in last scan'}), 404  # Phase 8 — GAP-1 fix

        price = result.get('price', 0.0)  # Phase 8 — GAP-1 fix
        return jsonify({  # Phase 8 — GAP-1 fix
            'success':       True,
            'symbol':        symbol,
            'current_price': price,
            'scan_time':     result.get('scan_time'),
            'source':        'core_scanner_smartrank',
            'stats': {
                'entry':      result.get('entry', price),
                'stop':       result.get('stop', 0.0),
                'target':     result.get('target', 0.0),
                'smart_rank': result.get('smart_rank', 0.0),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/market/prices', methods=['POST'])
def get_market_prices():
    """Get current prices for multiple symbols from the latest scan snapshot."""  # Phase 8 — GAP-1 fix
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols provided'}), 400

        snapshot = _load_scan_snapshot()  # Phase 8 — GAP-1 fix
        if not snapshot:
            return jsonify({'status': 'no_scan_yet', 'message': 'Scanner has not completed a scan yet'}), 404  # Phase 8 — GAP-1 fix

        snap_by_sym = {r.get('sym'): r for r in snapshot}  # Phase 8 — GAP-1 fix
        prices = {sym: snap_by_sym[sym].get('price') if sym in snap_by_sym else None for sym in symbols}  # Phase 8 — GAP-1 fix

        return jsonify({  # Phase 8 — GAP-1 fix
            'success': True,
            'source':  'core_scanner_smartrank',
            'prices':  prices
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
    """Generate trading signal for a symbol using core scanner snapshot."""  # Phase 8 — GAP-1 fix
    try:
        snapshot = _load_scan_snapshot()  # Phase 8 — GAP-1 fix
        result = next((r for r in snapshot if r.get('sym') == symbol), None)  # Phase 8 — GAP-1 fix

        if result is None:
            if not snapshot:
                return jsonify({'status': 'no_scan_yet', 'message': 'Scanner has not completed a scan yet'}), 404  # Phase 8 — GAP-1 fix
            return jsonify({'success': False, 'error': f'Symbol {symbol} not found in last scan'}), 404  # Phase 8 — GAP-1 fix

        return jsonify({  # Phase 8 — GAP-1 fix
            'success': True,
            'source':  'core_scanner_smartrank',
            'signal': {
                'symbol':       result.get('sym'),
                'signal_type':  result.get('tag', 'hold'),
                'strength':     'strong' if result.get('smart_rank', 0) >= 40 else 'moderate',
                'timestamp':    result.get('scan_time'),
                'entry_price':  result.get('entry', result.get('price', 0.0)),
                'target_price': result.get('target'),
                'stop_loss':    result.get('stop'),
                'confidence':   result.get('confidence', 0.5),
                'smart_rank':   result.get('smart_rank', 0.0),
                'action':       result.get('action', 'WAIT'),
                'direction':    result.get('direction', ''),
                'sector':       result.get('sector', ''),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/batch', methods=['POST'])
def generate_signals_batch():
    """Generate signals for multiple symbols using core scanner snapshot."""  # Phase 8 — GAP-1 fix
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({'success': False, 'error': 'No symbols provided'}), 400

        snapshot = _load_scan_snapshot()  # Phase 8 — GAP-1 fix
        if not snapshot:
            return jsonify({'status': 'no_scan_yet', 'message': 'Scanner has not completed a scan yet'}), 404  # Phase 8 — GAP-1 fix

        snap_by_sym = {r.get('sym'): r for r in snapshot}  # Phase 8 — GAP-1 fix
        signals_dict = {}  # Phase 8 — GAP-1 fix
        for sym in symbols:
            r = snap_by_sym.get(sym)
            if r:
                signals_dict[sym] = {  # Phase 8 — GAP-1 fix
                    'symbol':       r.get('sym'),
                    'signal_type':  r.get('tag', 'hold'),
                    'strength':     'strong' if r.get('smart_rank', 0) >= 40 else 'moderate',
                    'timestamp':    r.get('scan_time'),
                    'entry_price':  r.get('entry', r.get('price', 0.0)),
                    'target_price': r.get('target'),
                    'stop_loss':    r.get('stop'),
                    'confidence':   r.get('confidence', 0.5),
                    'smart_rank':   r.get('smart_rank', 0.0),
                    'action':       r.get('action', 'WAIT'),
                    'direction':    r.get('direction', ''),
                    'sector':       r.get('sector', ''),
                }
            else:
                signals_dict[sym] = None

        return jsonify({  # Phase 8 — GAP-1 fix
            'success': True,
            'source':  'core_scanner_smartrank',
            'signals': signals_dict
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/signals/history/<symbol>', methods=['GET'])
def get_signal_history(symbol: str):
    """Get signal history for a symbol from scanner snapshot."""  # Phase 8 — GAP-1 fix
    try:
        limit = request.args.get('limit', 100, type=int)
        snapshot = _load_scan_snapshot()  # Phase 8 — GAP-1 fix
        result = next((r for r in snapshot if r.get('sym') == symbol), None)  # Phase 8 — GAP-1 fix

        signals = []
        if result:
            signals = [{  # Phase 8 — GAP-1 fix
                'symbol':       result.get('sym'),
                'signal_type':  result.get('tag', 'hold'),
                'strength':     'strong' if result.get('smart_rank', 0) >= 40 else 'moderate',
                'timestamp':    result.get('scan_time'),
                'entry_price':  result.get('entry', result.get('price', 0.0)),
                'target_price': result.get('target'),
                'stop_loss':    result.get('stop'),
                'confidence':   result.get('confidence', 0.5),
                'smart_rank':   result.get('smart_rank', 0.0),
                'source':       'core_scanner_smartrank',
            }]

        return jsonify({  # Phase 8 — GAP-1 fix
            'success': True,
            'symbol':  symbol,
            'count':   len(signals),
            'signals': signals[:limit]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/history', methods=['GET'])
def get_alerts():
    """Get alert history. (Alerts not yet wired to core scanner.)"""  # Phase 8 — GAP-1 fix
    try:
        return jsonify({  # Phase 8 — GAP-1 fix
            'success': True,
            'count':   0,
            'unread':  0,
            'alerts':  [],
            'note':    'Alerts will be populated once scanner alert integration is complete.',
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/alerts/mark-read', methods=['POST'])
def mark_alerts_read():
    """Mark alerts as read."""  # Phase 8 — GAP-1 fix
    try:
        return jsonify({  # Phase 8 — GAP-1 fix
            'success': True,
            'unread':  0,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/market/volatility/<symbol>', methods=['GET'])
def get_volatility(symbol: str):
    """Get volatility proxy for a symbol from the latest scan snapshot."""  # Phase 8 — GAP-1 fix
    try:
        snapshot = _load_scan_snapshot()  # Phase 8 — GAP-1 fix
        result = next((r for r in snapshot if r.get('sym') == symbol), None)  # Phase 8 — GAP-1 fix

        if result is None:
            if not snapshot:
                return jsonify({'status': 'no_scan_yet', 'message': 'Scanner has not completed a scan yet'}), 404  # Phase 8 — GAP-1 fix
            return jsonify({'success': False, 'error': f'Symbol {symbol} not found in last scan'}), 404  # Phase 8 — GAP-1 fix

        price = result.get('price') or 1.0  # avoid division by zero
        target = result.get('target', price)
        stop = result.get('stop', price)
        volatility_pct = abs(target - stop) / price * 100 if price else 0.0  # Phase 8 — GAP-1 fix

        return jsonify({  # Phase 8 — GAP-1 fix
            'success':            True,
            'symbol':             symbol,
            'volatility_percent': round(volatility_pct, 4),
            'source':             'core_scanner_smartrank',
            'sentiment': {
                'smart_rank': result.get('smart_rank', 0.0),
                'direction':  result.get('direction', ''),
                'action':     result.get('action', 'WAIT'),
                'tag':        result.get('tag', ''),
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Not found'}), 404


@api_bp.route('/backtest/missed-trades', methods=['GET'])
def get_missed_trade_analysis():
    """Return missed trade intelligence analysis from the latest backtest."""
    try:
        from egx_radar.state.app_state import STATE
        bt = getattr(STATE, "backtest_results", None) or {}
        dashboard = bt.get("dashboard", {})
        analysis = dashboard.get("missed_trade_analysis", {})
        report_text = dashboard.get("missed_trade_report", "")
        missed_info = dashboard.get("missed_trades", {})

        if not analysis or analysis.get("total_missed", 0) == 0:
            return jsonify({
                'success': False,
                'error': 'No missed trade data. Run a backtest first.',
            }), 404

        return jsonify({
            'success': True,
            'total_missed': analysis.get("total_missed", 0),
            'missed_wins': analysis.get("missed_wins", 0),
            'missed_losses': analysis.get("missed_losses", 0),
            'missed_wins_pct': analysis.get("missed_wins_pct", 0.0),
            'missed_losses_pct': analysis.get("missed_losses_pct", 0.0),
            'avg_return_pct': analysis.get("avg_return_pct", 0.0),
            'total_pnl_impact_pct': analysis.get("total_pnl_impact_pct", 0.0),
            'quality_breakdown': analysis.get("quality_breakdown", {}),
            'reason_breakdown': analysis.get("reason_breakdown", {}),
            'sector_breakdown': analysis.get("sector_breakdown", {}),
            'recommendations': analysis.get("recommendations", {}),
            'report': report_text,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/backtest/tracking-dashboard', methods=['GET'])
def get_tracking_dashboard():
    """Return the full trade tracking dashboard from the latest backtest."""
    try:
        from egx_radar.state.app_state import STATE
        bt = getattr(STATE, "backtest_results", None) or {}
        trades = bt.get("trades", [])

        # Also accept a CSV path via query param
        csv_path = request.args.get('csv', None)

        from egx_radar.backtest.tracking_dashboard import build_tracking_dashboard, format_dashboard_report, load_trades_from_csv

        all_trades = list(trades)
        if csv_path and os.path.exists(csv_path):
            all_trades.extend(load_trades_from_csv(csv_path))

        if not all_trades:
            return jsonify({
                'success': False,
                'error': 'No trade data. Run a backtest first or provide a CSV path.',
            }), 404

        all_trades.sort(key=lambda t: t.get('exit_date', ''))
        dashboard = build_tracking_dashboard(all_trades)
        dashboard['text'] = format_dashboard_report(dashboard)

        # Serialize equity curve and drawdown as lists of [date, value]
        return jsonify({
            'success': True,
            'core_metrics': dashboard['core_metrics'],
            'progress': dashboard['progress'],
            'classification': dashboard['classification'],
            'equity_curve': dashboard['equity_curve'],
            'drawdown_series': dashboard['drawdown_series'],
            'losing_streak': dashboard['losing_streak'],
            'risk': dashboard['risk'],
            'monthly': dashboard['monthly'],
            'health_score': dashboard['health_score'],
            'verdict': dashboard['verdict'],
            'report': dashboard['text'],
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'error': 'Server error'}), 500
