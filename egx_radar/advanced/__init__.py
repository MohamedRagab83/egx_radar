"""Advanced features: ML predictions, options, risk management, portfolio optimization."""

from egx_radar.advanced.ml_predictor import (
    MLPricePredictor,
    EnsemblePredictor,
    get_ensemble_predictor
)

from egx_radar.advanced.options import (
    OptionType,
    OptionStrategy,
    BlackScholesCalculator,
    OptionsPortfolio,
    GreeksData,
    get_options_calculator
)

from egx_radar.advanced.risk_management import (
    RiskManager,
    RiskMetrics,
    PositionSizer,
    get_risk_manager
)

from egx_radar.advanced.portfolio_optimization import (
    PortfolioOptimizer,
    OptimalAllocation,
    get_portfolio_optimizer
)

__all__ = [
    # ML Predictor
    'MLPricePredictor',
    'EnsemblePredictor',
    'get_ensemble_predictor',
    
    # Options
    'OptionType',
    'OptionStrategy',
    'BlackScholesCalculator',
    'OptionsPortfolio',
    'GreeksData',
    'get_options_calculator',
    
    # Risk Management
    'RiskManager',
    'RiskMetrics',
    'PositionSizer',
    'get_risk_manager',
    
    # Portfolio Optimization
    'PortfolioOptimizer',
    'OptimalAllocation',
    'get_portfolio_optimizer',
]
