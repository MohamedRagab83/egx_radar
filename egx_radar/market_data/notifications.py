"""Notification and alert system for trading signals."""

from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
import threading


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    SIGNAL = "signal"
    TRADE = "trade"
    RISK = "risk"
    SYSTEM = "system"
    PRICE_ALERT = "price_alert"


@dataclass
class Alert:
    """A single notification/alert."""
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    symbol: Optional[str] = None
    price: Optional[float] = None
    value: Optional[float] = None  # For alerts with numerical values
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['alert_type'] = self.alert_type.value
        d['level'] = self.level.value
        d['timestamp'] = self.timestamp.isoformat()
        d['metadata'] = self.metadata or {}
        return d
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class NotificationManager:
    """Manages alerts and notifications."""
    
    def __init__(self, max_alert_history: int = 10000):
        """Initialize notification manager.
        
        Args:
            max_alert_history: Maximum alerts to keep in memory
        """
        self.max_alert_history = max_alert_history
        self._alert_history = deque(maxlen=max_alert_history)
        self._subscribers: Dict[AlertType, List[Callable]] = {}
        self._level_subscribers: Dict[AlertLevel, List[Callable]] = {}
        self._symbol_subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._unread_count = 0
    
    def create_alert(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        title: str,
        message: str,
        symbol: Optional[str] = None,
        price: Optional[float] = None,
        value: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> Alert:
        """Create and dispatch an alert.
        
        Args:
            alert_type: Type of alert
            level: Alert severity
            title: Alert title
            message: Alert message
            symbol: Stock symbol (if applicable)
            price: Current price (if applicable)
            value: Numerical value associated with alert
            metadata: Additional metadata
            
        Returns:
            Created Alert object
        """
        alert = Alert(
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            symbol=symbol,
            price=price,
            value=value,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._alert_history.append(alert)
            self._unread_count += 1
        
        # Dispatch to subscribers
        self._dispatch_alert(alert)
        
        return alert
    
    def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to all subscribers."""
        # Type subscribers
        if alert.alert_type in self._subscribers:
            for callback in self._subscribers[alert.alert_type]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in alert callback: {e}")
        
        # Level subscribers
        if alert.level in self._level_subscribers:
            for callback in self._level_subscribers[alert.level]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in level callback: {e}")
        
        # Symbol subscribers
        if alert.symbol and alert.symbol in self._symbol_subscribers:
            for callback in self._symbol_subscribers[alert.symbol]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in symbol callback: {e}")
    
    def subscribe_to_type(self, alert_type: AlertType, callback: Callable) -> None:
        """Subscribe to alerts of a specific type.
        
        Args:
            alert_type: Type to subscribe to
            callback: Function to call on alerts
        """
        if alert_type not in self._subscribers:
            self._subscribers[alert_type] = []
        self._subscribers[alert_type].append(callback)
    
    def subscribe_to_level(self, level: AlertLevel, callback: Callable) -> None:
        """Subscribe to alerts at a specific severity level.
        
        Args:
            level: Alert level to subscribe to
            callback: Function to call on alerts
        """
        if level not in self._level_subscribers:
            self._level_subscribers[level] = []
        self._level_subscribers[level].append(callback)
    
    def subscribe_to_symbol(self, symbol: str, callback: Callable) -> None:
        """Subscribe to alerts for a specific symbol.
        
        Args:
            symbol: Stock symbol
            callback: Function to call on alerts
        """
        if symbol not in self._symbol_subscribers:
            self._symbol_subscribers[symbol] = []
        self._symbol_subscribers[symbol].append(callback)
    
    def unsubscribe_from_type(self, alert_type: AlertType, callback: Callable) -> None:
        """Unsubscribe from type alerts."""
        if alert_type in self._subscribers:
            self._subscribers[alert_type] = [
                cb for cb in self._subscribers[alert_type] if cb != callback
            ]
    
    def unsubscribe_from_level(self, level: AlertLevel, callback: Callable) -> None:
        """Unsubscribe from level alerts."""
        if level in self._level_subscribers:
            self._level_subscribers[level] = [
                cb for cb in self._level_subscribers[level] if cb != callback
            ]
    
    def unsubscribe_from_symbol(self, symbol: str, callback: Callable) -> None:
        """Unsubscribe from symbol alerts."""
        if symbol in self._symbol_subscribers:
            self._symbol_subscribers[symbol] = [
                cb for cb in self._symbol_subscribers[symbol] if cb != callback
            ]
    
    def get_alert_history(self, limit: int = 100, alert_type: Optional[AlertType] = None) -> List[Alert]:
        """Get alert history.
        
        Args:
            limit: Maximum alerts to return
            alert_type: Filter by alert type (optional)
            
        Returns:
            List of recent alerts
        """
        with self._lock:
            alerts = list(self._alert_history)
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        return alerts[-limit:]
    
    def get_unread_count(self) -> int:
        """Get number of unread alerts."""
        with self._lock:
            return self._unread_count
    
    def mark_as_read(self, count: int = 1) -> None:
        """Mark alerts as read.
        
        Args:
            count: Number to mark as read
        """
        with self._lock:
            self._unread_count = max(0, self._unread_count - count)
    
    def clear_history(self) -> None:
        """Clear all alert history."""
        with self._lock:
            self._alert_history.clear()
            self._unread_count = 0


class SignalAlertGenerator:
    """Generates alerts from trading signals."""
    
    def __init__(self, notification_manager: NotificationManager):
        """Initialize alert generator.
        
        Args:
            notification_manager: NotificationManager instance
        """
        self.notification_manager = notification_manager
    
    def signal_alert(self, signal: 'TradingSignal') -> Alert:  # noqa: F821
        """Create alert from trading signal.
        
        Args:
            signal: TradingSignal object
            
        Returns:
            Created Alert
        """
        from egx_radar.market_data.signals import SignalType, SignalStrength
        
        # Determine alert level based on signal strength
        level_map = {
            SignalStrength.WEAK: AlertLevel.INFO,
            SignalStrength.MODERATE: AlertLevel.WARNING,
            SignalStrength.STRONG: AlertLevel.CRITICAL,
            SignalStrength.VERY_STRONG: AlertLevel.CRITICAL,
        }
        level = level_map.get(signal.strength, AlertLevel.INFO)
        
        # Create title and message
        signal_text = signal.signal_type.value.replace('_', ' ').title()
        title = f"{signal_text}: {signal.symbol}"
        message = (
            f"{signal_text} signal at ${signal.entry_price:.2f}\n"
            f"Strength: {signal.strength.value}\n"
            f"Confidence: {signal.confidence*100:.1f}%\n"
            f"Target: ${signal.target_price:.2f} | Stop: ${signal.stop_loss:.2f}"
        )
        
        # Create metadata
        metadata = {
            'signal_type': signal.signal_type.value,
            'rsi': signal.rsi,
            'macd': signal.macd,
            'confidence': signal.confidence,
            'reason': signal.reason,
        }
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.SIGNAL,
            level=level,
            title=title,
            message=message,
            symbol=signal.symbol,
            price=signal.entry_price,
            metadata=metadata
        )
    
    def trade_alert(self, symbol: str, trade_type: str, price: float, quantity: int) -> Alert:
        """Create alert for executed trade.
        
        Args:
            symbol: Stock symbol
            trade_type: 'buy' or 'sell'
            price: Execution price
            quantity: Number of shares
            
        Returns:
            Created Alert
        """
        title = f"Trade Executed: {trade_type.upper()} {symbol}"
        message = f"{trade_type.title()} {quantity} shares at ${price:.2f}"
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.TRADE,
            level=AlertLevel.WARNING,
            title=title,
            message=message,
            symbol=symbol,
            price=price,
            value=float(price * quantity),
            metadata={'quantity': quantity, 'type': trade_type}
        )
    
    def price_alert(self, symbol: str, price: float, alert_condition: str) -> Alert:
        """Create alert for price level.
        
        Args:
            symbol: Stock symbol
            price: Current/trigger price
            alert_condition: Description of condition (e.g., "above $100")
            
        Returns:
            Created Alert
        """
        title = f"Price Alert: {symbol}"
        message = f"Price {alert_condition} at ${price:.2f}"
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.PRICE_ALERT,
            level=AlertLevel.INFO,
            title=title,
            message=message,
            symbol=symbol,
            price=price
        )
    
    def risk_alert(self, symbol: str, risk_type: str, value: float) -> Alert:
        """Create alert for risk event.
        
        Args:
            symbol: Stock symbol
            risk_type: Type of risk (e.g., "Stop Loss Hit", "Daily Loss Limit")
            value: Associated value
            
        Returns:
            Created Alert
        """
        title = f"Risk Alert: {symbol}"
        message = f"{risk_type} triggered at {value:.2f}%"
        
        return self.notification_manager.create_alert(
            alert_type=AlertType.RISK,
            level=AlertLevel.CRITICAL,
            title=title,
            message=message,
            symbol=symbol,
            value=value
        )


# Global instances
_notification_manager: Optional[NotificationManager] = None
_alert_generator: Optional[SignalAlertGenerator] = None


def get_notification_manager() -> NotificationManager:
    """Get or create global notification manager."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def get_alert_generator() -> SignalAlertGenerator:
    """Get or create global alert generator."""
    global _alert_generator
    if _alert_generator is None:
        _alert_generator = SignalAlertGenerator(get_notification_manager())
    return _alert_generator
