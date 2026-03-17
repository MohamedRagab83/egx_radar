"""Data validation framework for EGX Radar."""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class DataValidator:
    """Validates data quality for backtesting."""
    
    def __init__(self, min_bars: int = 250, max_gap_days: int = 2):
        """Initialize validator with parameters."""
        self.min_bars = min_bars
        self.max_gap_days = max_gap_days
        self.errors = []
        self.warnings = []
    
    def validate_ohlc_data(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Validate OHLC/OHLCV data.
        
        Returns:
            {
                'valid': bool,
                'errors': list,
                'warnings': list,
                'metrics': dict
            }
        """
        self.errors = []
        self.warnings = []
        result = {
            'symbol': symbol,
            'valid': True,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        # Check if DataFrame is empty
        if df is None or df.empty:
            self.errors.append("Data is empty or None")
            result['valid'] = False
            result['errors'] = self.errors
            return result
        
        # Check required columns
        required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            self.errors.append(f"Missing columns: {missing_cols}")
        
        # Check minimum data points
        if len(df) < self.min_bars:
            self.warnings.append(f"Less than {self.min_bars} bars ({len(df)} found)")
        
        # Check for NaN values
        nan_count = df.isnull().sum().sum()
        if nan_count > 0:
            self.errors.append(f"Contains {nan_count} NaN values")
        
        # Check data types
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    self.errors.append(f"{col} is not numeric")
        
        # Check OHLC logical constraints
        if all(col in df.columns for col in numeric_cols):
            # High should be >= Low
            bad_hl = (df['High'] < df['Low']).sum()
            if bad_hl > 0:
                self.errors.append(f"{bad_hl} bars with High < Low")
            
            # Close should be between High and Low (mostly)
            bad_close = (
                ((df['Close'] > df['High']) | (df['Close'] < df['Low'])).sum()
            )
            if bad_close > len(df) * 0.01:  # Allow 1% exceptions
                self.warnings.append(f"{bad_close} bars with Close outside HL range")
            
            # Volume shouldn't be zero
            zero_volume = (df['Volume'] == 0).sum()
            if zero_volume > len(df) * 0.05:  # Allow 5% zero volume
                self.warnings.append(f"{zero_volume} bars with zero volume")
        
        # Check no negative prices
        for col in numeric_cols:
            if col in df.columns and (df[col] < 0).any():
                self.errors.append(f"{col} contains negative values")
        
        # Check date continuity
        if len(df) > 1:
            gaps = self._check_date_gaps(df)
            if gaps:
                self.warnings.append(f"Found {len(gaps)} gaps > {self.max_gap_days} days")
        
        # Metrics
        result['metrics'] = {
            'n_bars': len(df),
            'date_range': f"{df.index[0]} to {df.index[-1]}" if len(df) > 0 else "N/A",
            'price_range': f"{df['Close'].min():.2f} - {df['Close'].max():.2f}" 
                          if 'Close' in df.columns else "N/A",
            'avg_volume': df['Volume'].mean() if 'Volume' in df.columns else 0,
        }
        
        # Set validity
        result['valid'] = len(self.errors) == 0
        result['errors'] = self.errors
        result['warnings'] = self.warnings
        
        return result
    
    def _check_date_gaps(self, df: pd.DataFrame) -> List[Tuple]:
        """Find date gaps larger than max_gap_days."""
        if not isinstance(df.index, pd.DatetimeIndex):
            return []
        
        gaps = []
        diffs = df.index.to_series().diff()
        
        for i, gap in enumerate(diffs):
            if gap.days > self.max_gap_days:
                gaps.append((df.index[i-1], df.index[i], gap.days))
        
        return gaps
    
    def validate_metrics(self, trades: List[Dict]) -> Dict:
        """Validate trade metrics."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        if not trades:
            result['warnings'].append("No trades executed")
            result['metrics']['total_trades'] = 0
            return result
        
        # Check trade structure
        required_fields = {'symbol', 'entry_date', 'exit_date', 'pnl'}
        for i, trade in enumerate(trades):
            missing = required_fields - set(trade.keys())
            if missing:
                result['errors'].append(f"Trade {i} missing: {missing}")
        
        # Check numeric validity
        pnl_values = [t.get('pnl', 0) for t in trades if 'pnl' in t]
        if pnl_values:
            result['metrics']['total_pnl'] = sum(pnl_values)
            result['metrics']['avg_pnl'] = np.mean(pnl_values)
            result['metrics']['win_count'] = sum(1 for p in pnl_values if p > 0)
            result['metrics']['loss_count'] = sum(1 for p in pnl_values if p < 0)
        
        result['metrics']['total_trades'] = len(trades)
        result['valid'] = len(result['errors']) == 0
        
        return result


def validate_dataset(
    df: pd.DataFrame, 
    symbol: str, 
    min_bars: int = 250
) -> Dict:
    """Quick validation of a dataset."""
    validator = DataValidator(min_bars=min_bars)
    return validator.validate_ohlc_data(df, symbol)


def validate_all_symbols(
    symbol_data: Dict[str, pd.DataFrame]
) -> Dict[str, Dict]:
    """Validate multiple symbols."""
    validator = DataValidator()
    results = {}
    
    for symbol, df in symbol_data.items():
        results[symbol] = validator.validate_ohlc_data(df, symbol)
    
    return results


def generate_validation_report(results: Dict) -> str:
    """Generate a text report from validation results."""
    lines = ["=" * 60]
    lines.append("DATA VALIDATION REPORT")
    lines.append("=" * 60)
    
    total = len(results)
    valid = sum(1 for r in results.values() if r.get('valid'))
    
    lines.append(f"\nSummary: {valid}/{total} datasets valid")
    lines.append("")
    
    for symbol, result in results.items():
        status = "✓ PASS" if result['valid'] else "✗ FAIL"
        lines.append(f"{symbol:8} {status}")
        
        if result['errors']:
            for error in result['errors']:
                lines.append(f"  ERROR: {error}")
        
        if result['warnings']:
            for warning in result['warnings']:
                lines.append(f"  WARN:  {warning}")
        
        metrics = result.get('metrics', {})
        if metrics:
            lines.append(f"  Bars: {metrics.get('n_bars')}, "
                        f"Avg Vol: {metrics.get('avg_volume', 0):.0f}")
    
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
