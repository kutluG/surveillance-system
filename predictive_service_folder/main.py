"""
Predictive Service for Time-Series Forecasting

This service provides next-day intrusion count predictions using Prophet forecasting model.
Features:
- Daily training on last 365 days of intrusion data
- Model persistence and versioning
- REST API for predictions and historical analysis
- Automated nightly training via APScheduler
"""

import os
import pickle
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import asyncio
from contextlib import asynccontextmanager
import pytz

# Database imports
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# Scheduling
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Prophet for time series forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    # Fallback to statsmodels if Prophet not available
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    PROPHET_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/surveillance")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MODEL_DIR.mkdir(exist_ok=True)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Pydantic models
class PredictionResponse(BaseModel):
    """Response model for next-day prediction"""
    date: str = Field(..., description="Prediction date in YYYY-MM-DD format")
    predicted_count: float = Field(..., description="Predicted intrusion count")
    confidence_interval_lower: Optional[float] = Field(None, description="Lower bound of 95% confidence interval")
    confidence_interval_upper: Optional[float] = Field(None, description="Upper bound of 95% confidence interval")
    model_date: str = Field(..., description="Date when model was trained")

class HistoryDataPoint(BaseModel):
    """Single data point in historical data"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    actual_count: Optional[int] = Field(None, description="Actual intrusion count")
    predicted_count: Optional[float] = Field(None, description="Model predicted count")

class HistoryResponse(BaseModel):
    """Response model for historical data"""
    data: List[HistoryDataPoint] = Field(..., description="Historical data points")
    total_days: int = Field(..., description="Total number of days returned")

class TrainingStatus(BaseModel):
    """Training status response"""
    status: str = Field(..., description="Training status")
    last_training_date: Optional[str] = Field(None, description="Last successful training date")
    model_performance: Optional[Dict[str, float]] = Field(None, description="Model performance metrics")
    next_training_time: Optional[str] = Field(None, description="Next scheduled training time")

# Global scheduler
scheduler = None

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PredictiveModel:
    """Time-series forecasting model wrapper"""
    
    def __init__(self):
        self.model = None
        self.training_data = None
        self.model_date = None
        self.performance_metrics = {}
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for Prophet model"""
        if df.empty:
            raise ValueError("No data available for training")
        
        # Prophet expects columns named 'ds' (datestamp) and 'y' (value)
        df_prophet = df.copy()
        df_prophet = df_prophet.rename(columns={'day': 'ds', 'count': 'y'})
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])
        
        # Ensure we have at least 2 data points
        if len(df_prophet) < 2:
            raise ValueError("Need at least 2 data points for training")
        
        return df_prophet
    
    def train(self, df: pd.DataFrame) -> Dict[str, float]:
        """Train the forecasting model"""
        try:
            prepared_data = self.prepare_data(df)
            self.training_data = prepared_data
            
            if PROPHET_AVAILABLE:
                # Use Prophet for forecasting
                self.model = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=True,
                    changepoint_prior_scale=0.05,
                    interval_width=0.95
                )
                self.model.fit(prepared_data)
                
                # Calculate performance metrics (in-sample)
                forecast = self.model.predict(prepared_data)
                mae = np.mean(np.abs(forecast['yhat'] - prepared_data['y']))
                mape = np.mean(np.abs((prepared_data['y'] - forecast['yhat']) / prepared_data['y'])) * 100
                
                self.performance_metrics = {
                    'mae': float(mae),
                    'mape': float(mape),
                    'training_samples': len(prepared_data)
                }
            else:
                # Fallback to exponential smoothing
                self.model = ExponentialSmoothing(
                    prepared_data['y'],
                    trend='add',
                    seasonal='add',
                    seasonal_periods=7  # Weekly seasonality
                ).fit()
                
                fitted_values = self.model.fittedvalues
                mae = np.mean(np.abs(fitted_values - prepared_data['y']))
                mape = np.mean(np.abs((prepared_data['y'] - fitted_values) / prepared_data['y'])) * 100
                
                self.performance_metrics = {
                    'mae': float(mae),
                    'mape': float(mape),
                    'training_samples': len(prepared_data),
                    'model_type': 'exponential_smoothing'
                }
            
            self.model_date = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"Model trained successfully. MAE: {self.performance_metrics['mae']:.2f}, MAPE: {self.performance_metrics['mape']:.2f}%")
            
            return self.performance_metrics
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def predict_next_day(self) -> Dict[str, Any]:
        """Predict intrusion count for next day"""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        try:
            tomorrow = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow.strftime('%Y-%m-%d')
            
            if PROPHET_AVAILABLE:
                # Create future dataframe for tomorrow
                future = pd.DataFrame({'ds': [tomorrow]})
                forecast = self.model.predict(future)
                
                prediction = {
                    'date': tomorrow_str,
                    'predicted_count': float(max(0, forecast['yhat'].iloc[0])),
                    'confidence_interval_lower': float(max(0, forecast['yhat_lower'].iloc[0])),
                    'confidence_interval_upper': float(max(0, forecast['yhat_upper'].iloc[0])),
                    'model_date': self.model_date
                }
            else:
                # Exponential smoothing prediction
                forecast = self.model.forecast(steps=1)
                prediction = {
                    'date': tomorrow_str,
                    'predicted_count': float(max(0, forecast[0])),
                    'model_date': self.model_date
                }
            
            logger.info(f"Prediction for {tomorrow_str}: {prediction['predicted_count']:.2f}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            raise
    
    def get_historical_predictions(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical data with model predictions"""
        if self.model is None or self.training_data is None:
            raise ValueError("Model not trained yet")
        
        try:
            # Get last N days from training data
            end_date = self.training_data['ds'].max()
            start_date = end_date - timedelta(days=days-1)
            
            historical_data = self.training_data[
                (self.training_data['ds'] >= start_date) & 
                (self.training_data['ds'] <= end_date)
            ].copy()
            
            if PROPHET_AVAILABLE:
                # Get model predictions for historical period
                forecast = self.model.predict(historical_data[['ds']])
                historical_data['predicted'] = forecast['yhat']
            else:
                # For exponential smoothing, use fitted values
                fitted_values = self.model.fittedvalues
                historical_data['predicted'] = fitted_values[-len(historical_data):]
            
            # Format response
            result = []
            for _, row in historical_data.iterrows():
                result.append({
                    'date': row['ds'].strftime('%Y-%m-%d'),
                    'actual_count': int(row['y']),
                    'predicted_count': float(max(0, row['predicted']))
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting historical predictions: {e}")
            raise
    
    def save_model(self) -> str:
        """Save model to disk"""
        if self.model is None:
            raise ValueError("No model to save")
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d')
            model_path = MODEL_DIR / f"prophet_{timestamp}.pkl"
            
            model_data = {
                'model': self.model,
                'training_data': self.training_data,
                'model_date': self.model_date,
                'performance_metrics': self.performance_metrics,
                'prophet_available': PROPHET_AVAILABLE
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {model_path}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def load_latest_model(self) -> bool:
        """Load the most recent model from disk"""
        try:
            # Find the most recent model file
            model_files = list(MODEL_DIR.glob("prophet_*.pkl"))
            if not model_files:
                logger.warning("No saved models found")
                return False
            
            latest_model = max(model_files, key=os.path.getctime)
            
            with open(latest_model, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.training_data = model_data['training_data']
            self.model_date = model_data['model_date']
            self.performance_metrics = model_data.get('performance_metrics', {})
            
            logger.info(f"Model loaded from {latest_model}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

# Global model instance
predictive_model = PredictiveModel()

async def fetch_intrusion_data(days: int = 365) -> pd.DataFrame:
    """Fetch intrusion event data from database"""
    try:
        with SessionLocal() as db:            # Calculate start date
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            query = text("""
                SELECT date_trunc('day', timestamp) AS day, COUNT(*) AS count
                FROM events
                WHERE event_type = 'detection'
                  AND timestamp >= :start_date
                  AND timestamp <= :end_date
                  AND (
                    detections::text ILIKE '%person%' OR
                    detections::text ILIKE '%intruder%' OR
                    detections::text ILIKE '%human%'
                  )
                GROUP BY day
                ORDER BY day
            """)
            
            result = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            
            data = result.fetchall()
            
            if not data:
                logger.warning("No intrusion data found in database")
                # Create dummy data for testing
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                df = pd.DataFrame({
                    'day': dates,
                    'count': np.random.poisson(5, len(dates))  # Random Poisson-distributed counts
                })
                return df
            
            df = pd.DataFrame(data, columns=['day', 'count'])
            logger.info(f"Fetched {len(df)} days of intrusion data")
            return df
            
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching intrusion data: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error fetching intrusion data: {e}")
        raise

async def train_model():
    """Train the forecasting model"""
    try:
        logger.info("Starting model training...")
        
        # Fetch training data
        df = await fetch_intrusion_data(days=365)
        
        # Train model
        performance = predictive_model.train(df)
        
        # Save model
        model_path = predictive_model.save_model()
        
        logger.info(f"Model training completed. Performance: {performance}")
        logger.info(f"Model saved to: {model_path}")
        
        return performance
        
    except Exception as e:
        logger.error(f"Error in model training: {e}")
        raise

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global scheduler
    
    # Startup
    logger.info("Starting Predictive Service...")
    
    # Load existing model if available
    if not predictive_model.load_latest_model():
        logger.info("No existing model found, will train on first request")
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule nightly training at 03:00
    scheduler.add_job(
        train_model,
        CronTrigger(hour=3, minute=0),
        id="nightly_training",
        name="Nightly Model Training",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started - nightly training at 03:00")
    
    yield
    
    # Shutdown
    if scheduler:
        scheduler.shutdown()
    logger.info("Predictive Service stopped")

# FastAPI app
app = FastAPI(
    title="Predictive Service",
    description="Time-series forecasting for intrusion count predictions",
    version="1.0.0",
    openapi_prefix="/api/v1",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Predictive Service",
        "version": "1.0.0",
        "description": "Time-series forecasting for intrusion predictions",
        "endpoints": ["/predict/next-day", "/predict/history", "/train", "/status"]
    }

@app.get("/predict/next-day", response_model=PredictionResponse)
async def predict_next_day():
    """Get next-day intrusion count prediction"""
    try:
        # Ensure model is loaded/trained
        if predictive_model.model is None:
            logger.info("No model available, training new model...")
            await train_model()
        
        prediction = predictive_model.predict_next_day()
        return PredictionResponse(**prediction)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in next-day prediction: {e}")
        raise HTTPException(status_code=500, detail="Prediction error")

@app.get("/predict/history", response_model=HistoryResponse)
async def predict_history(days: int = Query(default=30, ge=1, le=365, description="Number of days to return")):
    """Get historical data with model predictions"""
    try:
        # Ensure model is loaded/trained
        if predictive_model.model is None:
            logger.info("No model available, training new model...")
            await train_model()
        
        history_data = predictive_model.get_historical_predictions(days)
        
        return HistoryResponse(
            data=[HistoryDataPoint(**point) for point in history_data],
            total_days=len(history_data)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in history prediction: {e}")
        raise HTTPException(status_code=500, detail="History prediction error")

@app.post("/train")
async def trigger_training():
    """Manually trigger model training"""
    try:
        performance = await train_model()
        return {
            "status": "success",
            "message": "Model training completed",
            "performance": performance,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in manual training: {e}")
        raise HTTPException(status_code=500, detail="Training error")

@app.get("/status", response_model=TrainingStatus)
async def get_status():
    """Get service status and model information"""
    try:
        # Get next training time
        next_run = None
        if scheduler:
            job = scheduler.get_job("nightly_training")
            if job:
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
        
        return TrainingStatus(
            status="healthy",
            last_training_date=predictive_model.model_date,
            model_performance=predictive_model.performance_metrics,
            next_training_time=next_run
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Status error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": predictive_model.model is not None,
        "prophet_available": PROPHET_AVAILABLE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
