"""Live signal generation from market data."""

import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
import json
from enum import Enum

from egx_radar.market_data.manager import get_market_data_manager


class SignalStrength(str, Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SignalType(str, Enum):
    """Types of trading signals."""
    BUY = "buy"
    SELL = "sell"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
    HOLD = "hold"


@dataclass
class TradingSignal:
    """A single trading signal with all relevant data."""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    timestamp: datetime
    entry_price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence: float = 0.5  # 0.0 to 1.0
    
    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bollinger_band_position: Optional[float] = None  # -1 to 1 (lower to upper)
    moving_avg_crossover: Optional[float] = None
    volume_surge: bool = False
    
    # Market sentiment
    momentum: Optional[float] = None
    trend: Optional[str] = None
    
    # Metadata
    reason: str = ""
    indicators_used: List[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['signal_type'] = self.signal_type.value
        d['strength'] = self.strength.value
        d['timestamp'] = self.timestamp.isoformat()
        return d
    
    @staticmethod
    def from_dict(data: Dict) -> 'TradingSignal':
        """Create from dictionary."""
        data['signal_type'] = SignalType(data['signal_type'])
        data['strength'] = SignalStrength(data['strength'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return TradingSignal(**data)


class LiveSignalGenerator:
    """Generates real-time trading signals from market data."""
    
    def __init__(self, lookback_days: int = 30):
        """Initialize signal generator.
        
        Args:
            lookback_days: Days of historical data to use for calculations
        """
        self.lookback_days = lookback_days
        self.market_data = get_market_data_manager()
        self._signal_history: Dict[str, List[TradingSignal]] = {}
    
    def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Generate trading signal for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            TradingSignal or None if unable to generate
        """
        try:
            # Get historical data
            data = self.market_data.get_historical_data(
                symbol, 
                days=self.lookback_days
            )
            
            if data.empty or len(data) < 10:
                return None
            
            # Get current price
            current_price = float(data['Close'].iloc[-1])
            timestamp = data.index[-1]
            if hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()
            
            # Calculate indicators
            rsi = self._calculate_rsi(data['Close'])
            macd, signal_line = self._calculate_macd(data['Close'])
            bb_position = self._calculate_bollinger_position(data['Close'])
            
            # Calculate moving averages
            sma_20 = data['Close'].rolling(20).mean()
            sma_50 = data['Close'].rolling(50).mean() if len(data) >= 50 else None
            sma_20_val = float(sma_20.iloc[-1]) if sma_20 is not None and not pd.isna(sma_20.iloc[-1]) else None
            sma_50_val = float(sma_50.iloc[-1]) if sma_50 is not None and not pd.isna(sma_50.iloc[-1]) else None
            
            momentum = self._calculate_momentum(data['Close'])
            sentiment = self.market_data.get_sentiment_indicators(symbol)
            
            # Generate signal based on indicators
            signal_type, strength, confidence, reason = self._evaluate_signals(
                rsi=rsi,
                macd=macd,
                macd_signal=signal_line,
                bb_position=bb_position,
                sma_20=sma_20_val,
                sma_50=sma_50_val,
                momentum=momentum,
                sentiment=sentiment
            )
            
            # Calculate targets
            volatility = self.market_data.get_intraday_volatility(symbol)
            atr = self._calculate_atr(data) if 'High' in data.columns else None
            
            target_price = None
            stop_loss = None
            
            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                if volatility:
                    target_price = current_price * (1 + volatility / 100)
                    stop_loss = current_price * (1 - volatility / 100 * 0.5)
            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                if volatility:
                    target_price = current_price * (1 - volatility / 100)
                    stop_loss = current_price * (1 + volatility / 100 * 0.5)
            
            # Create signal object
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                timestamp=datetime.now(),
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                confidence=confidence,
                rsi=rsi,
                macd=macd,
                bollinger_band_position=bb_position,
                moving_avg_crossover=momentum,
                momentum=sentiment.get('momentum'),
                trend=sentiment.get('trend'),
                reason=reason,
                indicators_used=['RSI', 'MACD', 'Bollinger Bands', 'Moving Averages', 'Momentum']
            )
            
            # Store in history
            if symbol not in self._signal_history:
                self._signal_history[symbol] = []
            self._signal_history[symbol].append(signal)
            
            return signal
        
        except Exception as e:
            print(f"Error generating signal for {symbol}: {e}")
            return None
    
    def generate_signals_batch(self, symbols: List[str]) -> Dict[str, Optional[TradingSignal]]:
        """Generate signals for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to signals
        """
        signals = {}
        for symbol in symbols:
            signals[symbol] = self.generate_signal(symbol)
        return signals
    
    def get_signal_history(self, symbol: str, limit: int = 100) -> List[TradingSignal]:
        """Get signal history for a symbol.
        
        Args:
            symbol: Stock symbol
            limit: Maximum signals to return
            
        Returns:
            List of recent signals
        """
        if symbol not in self._signal_history:
            return []
        return self._signal_history[symbol][-limit:]
    
    # ==================== INDICATOR CALCULATIONS ====================
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss if loss.iloc[-1] != 0 else 0
        rsi_value = 100 - (100 / (1 + rs.iloc[-1]))
        return float(rsi_value) if not pd.isna(rsi_value) else 50.0
    
    @staticmethod
    def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float]:
        """Calculate MACD and signal line."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        
        macd_val = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0.0
        signal_val = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else 0.0
        return macd_val, signal_val
    
    @staticmethod
    def _calculate_bollinger_position(prices: pd.Series, period: int = 20, std_dev: int = 2) -> float:
        """Calculate position within Bollinger Bands (-1 to 1).
        -1 = lower band, 0 = middle, 1 = upper band
        """
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        current = float(prices.iloc[-1])
        band_range = float(upper.iloc[-1]) - float(lower.iloc[-1])
        
        if band_range == 0:
            return 0.0
        
        position = 2 * (current - float(lower.iloc[-1])) / band_range - 1
        return float(max(-1, min(1, position)))
    
    @staticmethod
    def _calculate_momentum(prices: pd.Series, period: int = 10) -> float:
        """Calculate price momentum."""
        if len(prices) < period:
            return 0.0
        momentum = (float(prices.iloc[-1]) - float(prices.iloc[-period])) / float(prices.iloc[-period]) * 100
        return float(momentum)
    
    @staticmethod
    def _calculate_atr(data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        atr_val = float(atr.iloc[-1]) if not atr.isna().all() else 0.0
        return atr_val
    
    @staticmethod
    def _evaluate_signals(
        rsi: float,
        macd: float,
        macd_signal: float,
        bb_position: float,
        sma_20: Optional[float],
        sma_50: Optional[float],
        momentum: float,
        sentiment: Dict
    ) -> Tuple[SignalType, SignalStrength, float, str]:
        """Evaluate all indicators to generate signal."""
        
        buy_signals = 0
        sell_signals = 0
        confidence_factors = []
        reasons = []
        
        # RSI analysis
        if rsi < 30:
            buy_signals += 2
            confidence_factors.append(0.8)
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:
            sell_signals += 2
            confidence_factors.append(0.8)
            reasons.append(f"RSI overbought ({rsi:.1f})")
        
        # MACD analysis
        if macd > macd_signal:
            buy_signals += 1
            confidence_factors.append(0.6)
            reasons.append("MACD positive crossover")
        else:
            sell_signals += 1
            confidence_factors.append(0.6)
            reasons.append("MACD negative crossover")
        
        # Bollinger Bands analysis
        if bb_position < -0.5:
            buy_signals += 1
            confidence_factors.append(0.7)
            reasons.append("Price near lower Bollinger Band")
        elif bb_position > 0.5:
            sell_signals += 1
            confidence_factors.append(0.7)
            reasons.append("Price near upper Bollinger Band")
        
        # Moving Average analysis
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                buy_signals += 1
                confidence_factors.append(0.5)
                reasons.append("SMA 20 > SMA 50")
            else:
                sell_signals += 1
                confidence_factors.append(0.5)
                reasons.append("SMA 20 < SMA 50")
        
        # Momentum analysis
        if momentum > 2:
            buy_signals += 1
            confidence_factors.append(0.6)
            reasons.append(f"Positive momentum ({momentum:.1f}%)")
        elif momentum < -2:
            sell_signals += 1
            confidence_factors.append(0.6)
            reasons.append(f"Negative momentum ({momentum:.1f}%)")
        
        # Market sentiment
        if sentiment.get('rsi', 50) > 70:
            sell_signals += 0.5
        elif sentiment.get('rsi', 50) < 30:
            buy_signals += 0.5
        
        # Determine signal type and strength
        signal_diff = buy_signals - sell_signals
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
        
        if signal_diff > 4:
            return SignalType.STRONG_BUY, SignalStrength.VERY_STRONG, min(0.95, confidence), " + ".join(reasons)
        elif signal_diff > 2:
            return SignalType.BUY, SignalStrength.STRONG, min(0.85, confidence), " + ".join(reasons)
        elif signal_diff > 0:
            return SignalType.BUY, SignalStrength.MODERATE, confidence, " + ".join(reasons)
        elif signal_diff < -4:
            return SignalType.STRONG_SELL, SignalStrength.VERY_STRONG, min(0.95, confidence), " + ".join(reasons)
        elif signal_diff < -2:
            return SignalType.SELL, SignalStrength.STRONG, min(0.85, confidence), " + ".join(reasons)
        elif signal_diff < 0:
            return SignalType.SELL, SignalStrength.MODERATE, confidence, " + ".join(reasons)
        else:
            return SignalType.HOLD, SignalStrength.WEAK, 0.5, "No clear signal"


# Global instance
_signal_generator: Optional[LiveSignalGenerator] = None


def get_signal_generator() -> LiveSignalGenerator:
    """Get or create global signal generator."""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = LiveSignalGenerator()
    return _signal_generator
