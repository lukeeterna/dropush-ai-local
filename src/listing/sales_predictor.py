"""
Sales prediction con Facebook Prophet
Basato su: facebook/prophet
Ref: https://github.com/facebook/prophet
"""
from prophet import Prophet
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

class SalesPredictor:
    """
    Predittore vendite basato su Prophet + features custom
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.model = None
        
    def train(self, historical_data: pd.DataFrame):
        """
        Train model su dati storici
        Expected columns: ds (date), y (sales)
        """
        # Initialize Prophet with custom parameters
        self.model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_mode='multiplicative',
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False
        )
        
        # Add custom seasonalities
        self.model.add_seasonality(
            name='monthly',
            period=30.5,
            fourier_order=5
        )
        
        # Add country holidays (Italy)
        self.model.add_country_holidays(country_name='IT')
        
        # Fit model
        self.model.fit(historical_data)
        
    def predict(
        self,
        periods: int = 30,
        include_history: bool = False
    ) -> pd.DataFrame:
        """Predici vendite future"""
        if not self.model:
            raise ValueError("Model not trained")
            
        # Make future dataframe
        future = self.model.make_future_dataframe(
            periods=periods,
            include_history=include_history
        )
        
        # Predict
        forecast = self.model.predict(future)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
        
    def analyze_product_potential(
        self,
        product_features: Dict[str, Any],
        market_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Analizza potenziale vendite per nuovo prodotto
        """
        base_sales = 10  # Base sales per new product
        
        # Category multipliers
        category_multipliers = {
            'jewelry': 1.5,
            'electronics': 2.0,
            'home': 1.2,
            'health': 1.8
        }
        
        category = product_features.get('category', 'other')
        multiplier = category_multipliers.get(category, 1.0)
        
        # Price elasticity
        price = product_features.get('price', 50)
        if price < 20:
            multiplier *= 1.5  # Low price = higher volume
        elif price > 100:
            multiplier *= 0.7  # High price = lower volume
            
        # Competition factor
        competition = product_features.get('competition_level', 'medium')
        if competition == 'low':
            multiplier *= 1.3
        elif competition == 'high':
            multiplier *= 0.8
            
        # Calculate estimates
        estimated_daily = base_sales * multiplier
        estimated_monthly = estimated_daily * 30
        
        # Confidence based on data availability
        confidence = 0.5
        if market_data is not None and len(market_data) > 30:
            confidence = 0.8
            
        return {
            'estimated_daily_sales': round(estimated_daily, 1),
            'estimated_monthly_sales': round(estimated_monthly, 1),
            'confidence': confidence,
            'factors': {
                'category_impact': category_multipliers.get(category, 1.0),
                'price_impact': multiplier / category_multipliers.get(category, 1.0),
                'competition_impact': 1.0
            }
        }
