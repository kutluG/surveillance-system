"""
Comprehensive End-to-End Tests for the Predictive Service

These tests validate the entire predictive service functionality including:
- API endpoints with realistic data
- Model training workflows
- Database integration scenarios
- Error handling
- Performance under load
"""

import pytest
import asyncio
import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import tempfile
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
TEST_BASE_URL = "http://localhost:8013"  # Predictive service port in docker-compose


class TestPredictiveServiceE2E:
    """End-to-end tests for the predictive service"""
    
    @pytest.fixture(scope="class")
    def service_available(self):
        """Check if the predictive service is running"""
        try:
            response = requests.get(f"{TEST_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        
        pytest.skip("Predictive service not available for E2E testing")
    
    def test_health_endpoint(self, service_available):
        """Test health check endpoint"""
        response = requests.get(f"{TEST_BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "model_loaded" in data
        assert "prophet_available" in data
    
    def test_status_endpoint(self, service_available):
        """Test status endpoint"""
        response = requests.get(f"{TEST_BASE_URL}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "last_training_date" in data
        assert "model_performance" in data
        assert "next_training_time" in data
    
    def test_prediction_endpoint_without_training(self, service_available):
        """Test prediction endpoint behavior without trained model"""
        response = requests.get(f"{TEST_BASE_URL}/predict/next-day")
        
        # Should either return a prediction (if model exists) or trigger training
        assert response.status_code in [200, 500]  # 500 if no data available
        
        if response.status_code == 200:
            data = response.json()
            assert "predicted_count" in data
            assert "date" in data
            assert isinstance(data["predicted_count"], (int, float))
    
    def test_training_endpoint(self, service_available):
        """Test manual training trigger"""
        response = requests.post(f"{TEST_BASE_URL}/train")
        
        # Training might fail if no data is available, which is expected
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "performance" in data
            assert "timestamp" in data
    
    def test_history_endpoint(self, service_available):
        """Test historical data endpoint"""
        response = requests.get(f"{TEST_BASE_URL}/predict/history?days=7")
        
        # Should either return data or handle gracefully if no model/data
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "total_days" in data
            assert isinstance(data["data"], list)


class TestPredictiveServiceMockedE2E:
    """End-to-end tests with mocked dependencies for comprehensive coverage"""
    
    def test_complete_prediction_workflow(self):
        """Test the complete prediction workflow with mocked data"""
        
        # Generate realistic training data
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        intrusion_counts = []
        
        for i, date in enumerate(dates):
            # Create realistic patterns
            base_count = 10
            
            # Weekly pattern (more intrusions on weekends)
            if date.weekday() >= 5:  # Weekend
                base_count += 5
            
            # Seasonal pattern (more in summer)
            if date.month in [6, 7, 8]:
                base_count += 3
            
            # Add noise
            noise = np.random.normal(0, 2)
            count = max(0, int(base_count + noise))
            intrusion_counts.append(count)
        
        training_df = pd.DataFrame({
            'day': dates,
            'count': intrusion_counts
        })
        
        # Test the complete workflow
        from predictive_service import PredictiveModel
        
        with patch('predictive_service.fetch_intrusion_data') as mock_fetch:
            mock_fetch.return_value = training_df
            
            model = PredictiveModel()
            
            # Test training
            performance = model.train(training_df)
            assert 'mae' in performance
            assert 'mape' in performance
            assert model.model is not None
            
            # Test prediction
            prediction = model.predict_next_day()
            assert 'predicted_count' in prediction
            assert 'date' in prediction
            assert prediction['predicted_count'] >= 0
            
            # Test historical predictions
            history = model.get_historical_predictions(days=30)
            assert len(history) <= 30
            assert all('date' in item for item in history)
            assert all('actual_count' in item for item in history)
    
    def test_model_persistence_workflow(self):
        """Test model saving and loading workflow"""
        from predictive_service import PredictiveModel
          # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'day': dates,
            'count': np.random.poisson(15, 100)  # Poisson distribution for count data
        })
        
        with tempfile.TemporaryDirectory() as temp_dir:
            from pathlib import Path
            with patch('predictive_service.MODEL_DIR', Path(temp_dir)):
                # Train and save model
                model1 = PredictiveModel()
                performance1 = model1.train(df)
                model_path = model1.save_model()
                
                assert os.path.exists(model_path)
                assert 'prophet_' in os.path.basename(model_path)
                
                # Load model in new instance
                model2 = PredictiveModel()
                success = model2.load_latest_model()
                
                assert success
                assert model2.model is not None
                assert model2.model_date == model1.model_date
                assert model2.performance_metrics == model1.performance_metrics
    
    def test_performance_under_different_data_scenarios(self):
        """Test model performance under different data scenarios"""
        from predictive_service import PredictiveModel
        
        scenarios = [
            {
                'name': 'stable_pattern',
                'data': [10, 12, 11, 13, 10, 11, 12] * 20,
                'expected_mae_threshold': 3.0
            },
            {
                'name': 'increasing_trend',
                'data': list(range(5, 150, 1)),
                'expected_mae_threshold': 10.0
            },
            {
                'name': 'noisy_data',
                'data': np.random.poisson(20, 140).tolist(),
                'expected_mae_threshold': 15.0
            }
        ]
        
        for scenario in scenarios:
            dates = pd.date_range(start='2024-01-01', periods=len(scenario['data']), freq='D')
            df = pd.DataFrame({
                'day': dates,
                'count': scenario['data']
            })
            
            model = PredictiveModel()
            performance = model.train(df)
            
            # Verify model trains successfully
            assert model.model is not None
            assert 'mae' in performance
            assert 'mape' in performance
            
            # Check if performance is reasonable for the data type
            assert performance['mae'] >= 0
            assert performance['mape'] >= 0
            
            # Test prediction works
            prediction = model.predict_next_day()
            assert prediction['predicted_count'] >= 0
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        from predictive_service import PredictiveModel
        
        model = PredictiveModel()
        
        # Test with empty dataframe
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError, match="No data available for training"):
            model.prepare_data(empty_df)        # Test with insufficient data
        single_point_df = pd.DataFrame({
            'day': [datetime.now()],
            'count': [5]
        })
        
        # Both prepare_data and train should fail with insufficient data
        with pytest.raises(ValueError, match="Need at least 2 data points for training"):
            model.prepare_data(single_point_df)
        
        with pytest.raises(ValueError, match="Need at least 2 data points for training"):
            model.train(single_point_df)
        
        # Test prediction without trained model
        empty_model = PredictiveModel()
        with pytest.raises(ValueError, match="Model not trained yet"):
            empty_model.predict_next_day()


class TestPredictiveServiceLoadTest:
    """Load testing for the predictive service"""
    
    @pytest.mark.slow
    def test_concurrent_prediction_requests(self):
        """Test handling multiple concurrent prediction requests"""
        from predictive_service import PredictiveModel
        import threading
        import queue
        
        # Set up a trained model
        dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
        df = pd.DataFrame({
            'day': dates,
            'count': np.random.poisson(12, 365)
        })
        
        model = PredictiveModel()
        model.train(df)
        
        # Function to make prediction and store result
        def make_prediction(result_queue):
            try:
                prediction = model.predict_next_day()
                result_queue.put(('success', prediction))
            except Exception as e:
                result_queue.put(('error', str(e)))
        
        # Run concurrent requests
        num_threads = 10
        results = queue.Queue()
        threads = []
        
        for _ in range(num_threads):
            thread = threading.Thread(target=make_prediction, args=(results,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        error_count = 0
        
        while not results.empty():
            status, result = results.get()
            if status == 'success':
                success_count += 1
                assert 'predicted_count' in result
                assert result['predicted_count'] >= 0
            else:
                error_count += 1
        
        # Most requests should succeed
        assert success_count >= num_threads * 0.8  # At least 80% success rate
    
    @pytest.mark.slow  
    def test_memory_usage_during_training(self):
        """Test memory usage doesn't grow excessively during training"""
        import psutil
        import gc
        
        from predictive_service import PredictiveModel
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Train multiple models to test memory management
        for i in range(5):
            dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
            df = pd.DataFrame({
                'day': dates,
                'count': np.random.poisson(15, 365)
            })
            
            model = PredictiveModel()
            performance = model.train(df)
            
            # Force garbage collection
            del model
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory shouldn't grow excessively (less than 100MB per iteration)
            assert memory_increase < 100 * (i + 1), f"Memory usage increased by {memory_increase}MB"


if __name__ == "__main__":
    # Run tests with appropriate markers
    pytest.main([
        __file__, 
        "-v", 
        "-m", "not slow",  # Skip slow tests by default
        "--tb=short"
    ])
