"""Market data and live signals module."""

from egx_radar.market_data.manager import (
    MarketDataManager,
    get_market_data_manager
)

from egx_radar.market_data.signals import (
    LiveSignalGenerator,
    TradingSignal,
    SignalType,
    SignalStrength,
    get_signal_generator
)

from egx_radar.market_data.notifications import (
    NotificationManager,
    SignalAlertGenerator,
    Alert,
    AlertType,
    AlertLevel,
    get_notification_manager,
    get_alert_generator
)

__all__ = [
    'MarketDataManager',
    'get_market_data_manager',
    'LiveSignalGenerator',
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    'get_signal_generator',
    'NotificationManager',
    'SignalAlertGenerator',
    'Alert',
    'AlertType',
    'AlertLevel',
    'get_notification_manager',
    'get_alert_generator',
]
