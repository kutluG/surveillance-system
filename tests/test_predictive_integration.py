"""
Integration tests for the predictive service with mocked dependencies.
Tests API endpoints, database integration, and model training workflows.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

# Import the predictive service components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictive_service import (
    app, 
    PredictiveModel, 
    PredictionResponse, 
    HistoryResponse,
    TrainingStatus,
    HistoryDataPoint
)


class TestPredictiveServiceIntegration:
    """Integration tests for the predictive service API and components."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_intrusion_data(self):
        """Sample intrusion data for testing."""
        base_date = datetime.now() - timedelta(days=30)
        data = []
        for i in range(30):
            date = base_date + timedelta(days=i)
            # Create realistic intrusion patterns with some noise
            base_count = 15 + (i % 7) * 3  # Weekly pattern
            noise = np.random.randint(-5, 6)
            count = max(0, base_count + noise)
            data.append({
                'date': date.date(),
                'count': count
            })
        return data
    
    @pytest.fixture
    def mock_prophet_model(self):
        """Mock Prophet model for testing."""
        model = MagicMock()
        model.fit = MagicMock()
        
        # Mock prediction results
        future_df = pd.DataFrame({
            'ds': [datetime.now() + timedelta(days=1)],
            'yhat': [18.5],
            'yhat_lower': [12.3],
            'yhat_upper': [24.7]
        })
        model.predict.return_value = future_df
          return model
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test the health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self):
        """Test the status endpoint."""
        with patch('predictive_service.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with TestClient(app) as client:
                response = client.get("/status")
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert "last_training_date" in data
                assert "model_performance" in data
      @pytest.mark.asyncio
    async def test_predict_next_day_endpoint(self, sample_intrusion_data, mock_prophet_model):
        """Test the next day prediction endpoint."""
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch, \
             patch('predictive_service.Prophet') as mock_prophet_class, \
             patch('predictive_service.os.path.exists') as mock_exists, \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Setup mocks
            mock_prophet_class.return_value = mock_prophet_model
            mock_exists.return_value = True
            
            # Mock data fetching
            df_data = pd.DataFrame([
                {'day': data['date'], 'count': data['count']} 
                for data in sample_intrusion_data
            ])
            mock_fetch.return_value = df_data
            
            with TestClient(app) as client:
                response = client.get("/predict/next-day")
                assert response.status_code == 200
                
                data = response.json()
                assert "predicted_count" in data
                assert "confidence_interval_lower" in data
                assert "confidence_interval_upper" in data
                assert "model_date" in data
                assert "date" in data
                
                # Validate prediction structure
                assert isinstance(data["predicted_count"], (int, float))
                assert isinstance(data["confidence_interval_lower"], (int, float))
                assert isinstance(data["confidence_interval_upper"], (int, float))
      @pytest.mark.asyncio
    async def test_predict_history_endpoint(self, sample_intrusion_data):
        """Test the prediction history endpoint."""
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch:
            # Mock data fetching
            df_data = pd.DataFrame([
                {'day': data['date'], 'count': data['count']} 
                for data in sample_intrusion_data
            ])
            mock_fetch.return_value = df_data
            
            with TestClient(app) as client:
                response = client.get("/predict/history?days=30")
                assert response.status_code == 200
                
                data = response.json()
                assert "data" in data
                assert "total_days" in data
                
                # Validate historical data structure
                assert len(data["data"]) <= 30
                for item in data["data"]:
                    assert "date" in item
                    assert "actual_count" in item
      @pytest.mark.asyncio
    async def test_train_endpoint(self, sample_intrusion_data, mock_prophet_model):
        """Test the model training endpoint."""
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch, \
             patch('predictive_service.Prophet') as mock_prophet_class, \
             patch('predictive_service.pickle.dump') as mock_pickle_dump, \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Setup mocks
            mock_prophet_class.return_value = mock_prophet_model
            
            # Mock data fetching
            df_data = pd.DataFrame([
                {'day': data['date'], 'count': data['count']} 
                for data in sample_intrusion_data
            ])
            mock_fetch.return_value = df_data
            
            with TestClient(app) as client:
                response = client.post("/train")
                assert response.status_code == 200
                
                data = response.json()
                assert "status" in data
                assert "message" in data
                assert "performance" in data
                assert "timestamp" in data
                
                # Validate training response
                assert data["status"] == "success"
                assert "mae" in data["performance"]
                assert "mape" in data["performance"]
      @pytest.mark.asyncio
    async def test_prediction_with_insufficient_data(self):
        """Test prediction behavior with insufficient historical data."""
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch:
            # Mock insufficient data
            mock_fetch.return_value = pd.DataFrame()  # Empty dataframe
            
            with TestClient(app) as client:
                response = client.get("/predict/next-day")
                assert response.status_code == 500  # Internal server error due to insufficient data
    
    @pytest.mark.asyncio
    async def test_training_with_database_error(self):
        """Test training behavior when database errors occur."""
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch:
            # Setup mock to raise database error
            mock_fetch.side_effect = Exception("Database connection failed")
            
            with TestClient(app) as client:
                response = client.post("/train")
                assert response.status_code == 500
                
                data = response.json()
                assert "detail" in data
                assert "error" in data["detail"].lower()


class TestPredictiveModel:
    """Unit tests for the PredictiveModel class with mocking."""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Sample DataFrame for testing."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        return pd.DataFrame({
            'ds': dates,
            'y': np.random.randint(10, 30, 30)  # Random intrusion counts
        })
      @pytest.mark.asyncio
    async def test_model_initialization(self):
        """Test PredictiveModel initialization."""
        model = PredictiveModel()
        assert model.model is None
        assert model.training_data is None
        assert model.model_date is None
        assert model.performance_metrics == {}
    
    @pytest.mark.asyncio
    async def test_prepare_data(self):
        """Test data preparation logic."""
        model = PredictiveModel()
        
        # Sample DataFrame (not raw data)
        raw_df = pd.DataFrame({
            'day': [datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)],
            'count': [15, 18, 12]
        })
        
        df = model.prepare_data(raw_df)
        
        assert len(df) == 3
        assert list(df.columns) == ['ds', 'y']
        assert df['y'].tolist() == [15, 18, 12]
        assert pd.api.types.is_datetime64_any_dtype(df['ds'])
      @pytest.mark.asyncio
    async def test_prophet_training(self, sample_dataframe):
        """Test Prophet model training."""
        with patch('predictive_service.Prophet') as mock_prophet_class:
            mock_model = MagicMock()
            mock_prophet_class.return_value = mock_model
            
            # Mock prediction results for performance metrics
            mock_forecast = pd.DataFrame({
                'yhat': [15.5, 18.2, 12.8] * 10  # Match sample_dataframe length
            })
            mock_model.predict.return_value = mock_forecast
            
            model = PredictiveModel()
            performance = model.train(sample_dataframe)
            
            # Verify Prophet was called correctly
            mock_prophet_class.assert_called_once()
            mock_model.fit.assert_called_once()
            assert model.model == mock_model
            assert model.model_date is not None
            assert 'mae' in performance
            assert 'mape' in performance
      @pytest.mark.asyncio
    async def test_exponential_smoothing_fallback(self, sample_dataframe):
        """Test fallback to exponential smoothing when Prophet fails."""
        with patch('predictive_service.Prophet') as mock_prophet_class, \
             patch('predictive_service.ExponentialSmoothing') as mock_exp_class:
            
            # Make Prophet fail
            mock_prophet_class.side_effect = Exception("Prophet failed")
            
            mock_exp_model = MagicMock()
            mock_fitted = MagicMock()
            mock_fitted.fittedvalues = pd.Series([15.5, 18.2, 12.8] * 10)
            mock_exp_model.fit.return_value = mock_fitted
            mock_exp_class.return_value = mock_exp_model
            
            model = PredictiveModel()
            performance = model.train(sample_dataframe)
            
            # Verify fallback was used
            mock_exp_class.assert_called_once()
            mock_exp_model.fit.assert_called_once()
            assert model.model == mock_fitted
            assert 'mae' in performance
            assert 'model_type' in performance
      @pytest.mark.asyncio
    async def test_prediction_with_prophet(self, sample_dataframe):
        """Test prediction using Prophet model."""
        with patch('predictive_service.Prophet') as mock_prophet_class:
            mock_model = MagicMock()
            mock_prophet_class.return_value = mock_model
            
            # Mock prediction results
            future_df = pd.DataFrame({
                'yhat': [20.5],
                'yhat_lower': [15.2],
                'yhat_upper': [25.8]
            })
            mock_model.predict.return_value = future_df
            
            model = PredictiveModel()
            # First train the model
            model.train(sample_dataframe)
            
            prediction = model.predict_next_day()
            
            assert prediction["predicted_count"] == 20.5
            assert prediction["confidence_interval_lower"] == 15.2
            assert prediction["confidence_interval_upper"] == 25.8
      @pytest.mark.asyncio
    async def test_model_persistence(self, sample_dataframe):
        """Test model saving and loading."""
        with patch('predictive_service.Prophet') as mock_prophet_class, \
             patch('predictive_service.pickle.dump') as mock_dump, \
             patch('predictive_service.pickle.load') as mock_load, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('predictive_service.MODEL_DIR') as mock_model_dir:
            
            mock_model = MagicMock()
            mock_prophet_class.return_value = mock_model
            mock_model_dir.__truediv__ = lambda self, other: f"models/{other}"
            
            model = PredictiveModel()
            model.train(sample_dataframe)
            
            # Test saving
            filename = model.save_model()
            assert "prophet_" in filename
            assert ".pkl" in filename
            mock_dump.assert_called_once()
            
            # Test loading
            mock_load.return_value = {
                'model': mock_model,
                'training_data': sample_dataframe,
                'model_date': '2024-01-01',
                'performance_metrics': {'mae': 1.5},
                'prophet_available': True
            }
            
            new_model = PredictiveModel()
            success = new_model.load_latest_model()
            assert success
            assert new_model.model == mock_model
      @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self):
        """Test performance metrics calculation."""
        # This is tested as part of the training process
        # The PredictiveModel doesn't have a separate calculate_performance_metrics method
        model = PredictiveModel()
        
        # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'day': dates,
            'count': [10, 15, 20, 25, 30, 12, 18, 22, 28, 35]
        })
        
        with patch('predictive_service.Prophet') as mock_prophet:
            mock_model = MagicMock()
            mock_prophet.return_value = mock_model
            
            # Mock prediction for metrics calculation
            mock_forecast = pd.DataFrame({
                'yhat': [12, 14, 22, 23, 28, 14, 19, 21, 27, 33]
            })
            mock_model.predict.return_value = mock_forecast
            
            performance = model.train(df)
            
            assert "mae" in performance
            assert "mape" in performance
            assert isinstance(performance["mae"], float)
            assert isinstance(performance["mape"], float)
            assert performance["mae"] >= 0
            assert performance["mape"] >= 0


class TestScheduledTasks:
    """Test scheduled tasks and automation."""
      @pytest.mark.asyncio
    async def test_scheduled_training_trigger(self):
        """Test that scheduled training can be triggered."""
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch, \
             patch('predictive_service.Prophet') as mock_prophet_class, \
             patch('predictive_service.pickle.dump') as mock_pickle_dump, \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Setup mocks
            mock_model = MagicMock()
            mock_prophet_class.return_value = mock_model
            
            # Mock some historical data
            dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
            mock_df = pd.DataFrame({
                'day': dates,
                'count': [15 + i for i in range(30)]
            })
            mock_fetch.return_value = mock_df
            
            # Import and call the scheduled training function
            from predictive_service import train_model
            
            # This should not raise an exception
            performance = await train_model()
            
            # Verify training was attempted
            mock_fetch.assert_called_once()
            mock_prophet_class.assert_called_once()
            assert isinstance(performance, dict)
    
    @pytest.mark.asyncio 
    async def test_model_version_generation(self):
        """Test model version string generation."""
        from predictive_service import PredictiveModel
        
        model = PredictiveModel()
        
        # Test that model date is generated correctly during training
        dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'day': dates,
            'count': [10, 15, 12, 18, 20]
        })
        
        with patch('predictive_service.Prophet') as mock_prophet:
            mock_model_instance = MagicMock()
            mock_prophet.return_value = mock_model_instance
            
            # Mock prediction for metrics
            mock_forecast = pd.DataFrame({'yhat': [12, 14, 13, 17, 19]})
            mock_model_instance.predict.return_value = mock_forecast
            
            test_date = datetime(2024, 3, 15)
            with patch('predictive_service.datetime') as mock_datetime:
                mock_datetime.now.return_value = test_date
                
                model.train(df)
                assert model.model_date == "2024-03-15"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
