"""
AI Dashboard Features Service

This service provides advanced analytics, predictive insights, and pattern visualization:
- AI-powered trend analysis and recommendations
- Predictive analytics for forecasting security issues
- Intelligent report generation and summarization
- Dynamic widget framework with customizable components
- Real-time anomaly detection and pattern identification
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import statistics
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import numpy as np
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Import shared middleware for rate limiting
from shared.middleware import add_rate_limiting

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key="your-openai-api-key")

# Enums
class AnalyticsType(str, Enum):
    TREND_ANALYSIS = "trend_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTIVE_FORECAST = "predictive_forecast"
    PATTERN_RECOGNITION = "pattern_recognition"
    PERFORMANCE_METRICS = "performance_metrics"

class TimeRange(str, Enum):
    LAST_HOUR = "last_hour"
    LAST_24_HOURS = "last_24_hours"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"

class WidgetType(str, Enum):
    CHART = "chart"
    MAP = "map"
    TABLE = "table"
    METRIC = "metric"
    TIMELINE = "timeline"
    HEATMAP = "heatmap"
    ALERT_FEED = "alert_feed"

class PredictionType(str, Enum):
    SECURITY_THREAT = "security_threat"
    EQUIPMENT_FAILURE = "equipment_failure"
    TRAFFIC_PATTERN = "traffic_pattern"
    OCCUPANCY_LEVEL = "occupancy_level"

# Data Models
@dataclass
class AnalyticsInsight:
    id: str
    type: AnalyticsType
    title: str
    description: str
    confidence: float
    timestamp: datetime
    data: Dict[str, Any]
    recommendations: List[str]
    impact_level: str  # low, medium, high, critical

@dataclass
class PredictiveModel:
    id: str
    name: str
    description: str
    type: PredictionType
    accuracy: float
    last_trained: datetime
    parameters: Dict[str, Any]
    predictions: List[Dict]

@dataclass
class DashboardWidget:
    id: str
    type: WidgetType
    title: str
    description: str
    configuration: Dict[str, Any]
    data_source: str
    refresh_interval: int  # seconds
    filters: Dict[str, Any]
    layout: Dict[str, Any]

@dataclass
class TrendAnalysis:
    metric: str
    direction: str  # increasing, decreasing, stable
    magnitude: float
    confidence: float
    timeframe: str
    contributing_factors: List[str]

@dataclass
class AnomalyDetection:
    id: str
    timestamp: datetime
    metric: str
    expected_value: float
    actual_value: float
    deviation: float
    severity: str
    description: str

# Request/Response Models
class AnalyticsRequest(BaseModel):
    analytics_type: AnalyticsType
    time_range: TimeRange
    custom_start: Optional[datetime] = None
    custom_end: Optional[datetime] = None
    filters: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}

class PredictionRequest(BaseModel):
    prediction_type: PredictionType
    forecast_horizon: int = 24  # hours
    confidence_threshold: float = 0.7
    include_recommendations: bool = True

class ReportGenerationRequest(BaseModel):
    report_type: str
    time_range: TimeRange
    custom_start: Optional[datetime] = None
    custom_end: Optional[datetime] = None
    sections: List[str] = []
    format: str = "html"  # html, pdf, json

class WidgetRequest(BaseModel):
    widget_type: WidgetType
    title: str
    description: str
    configuration: dict
    filters: dict = {}

# Global state
redis_client: Optional[redis.Redis] = None
db_session: Optional[AsyncSession] = None

async def get_redis_client():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url("redis://localhost:6379/8")
    return redis_client

async def get_database_session():
    """Get database session"""
    global db_session
    if not db_session:
        engine = create_async_engine("postgresql+asyncpg://user:password@localhost/surveillance")
        SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        db_session = SessionLocal()
    return db_session

# Analytics Engine
class AnalyticsEngine:
    def __init__(self):
        self.trend_cache = deque(maxlen=1000)
        self.anomaly_threshold = 2.0  # Standard deviations
        
    async def analyze_trends(self, request: AnalyticsRequest) -> List[TrendAnalysis]:
        """Analyze trends in surveillance data"""
        try:
            # Get time series data
            time_data = await self._get_time_series_data(request)
            
            trends = []
            for metric, values in time_data.items():
                if len(values) < 10:  # Need minimum data points
                    continue
                
                trend = await self._calculate_trend(metric, values, request.time_range)
                if trend:
                    trends.append(trend)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return []
    
    async def _get_time_series_data(self, request: AnalyticsRequest) -> Dict[str, List[float]]:
        """Get time series data for analysis"""
        # This would query the actual surveillance database
        # For now, return simulated data
        
        end_time = datetime.utcnow()
        if request.time_range == TimeRange.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
            data_points = 60
        elif request.time_range == TimeRange.LAST_24_HOURS:
            start_time = end_time - timedelta(hours=24)
            data_points = 24
        elif request.time_range == TimeRange.LAST_WEEK:
            start_time = end_time - timedelta(weeks=1)
            data_points = 7
        else:
            start_time = end_time - timedelta(hours=24)
            data_points = 24
        
        # Simulate time series data
        return {
            "motion_events": np.random.poisson(10, data_points).tolist(),
            "alert_count": np.random.poisson(3, data_points).tolist(),
            "camera_uptime": (np.random.normal(0.98, 0.02, data_points)).tolist(),
            "processing_latency": (np.random.exponential(100, data_points)).tolist()
        }
    
    async def _calculate_trend(self, metric: str, values: List[float], timeframe: str) -> Optional[TrendAnalysis]:
        """Calculate trend for a metric"""
        if len(values) < 2:
            return None
        
        # Calculate linear regression slope
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        slope = z[0]
        
        # Determine direction and magnitude
        if abs(slope) < 0.1:
            direction = "stable"
            magnitude = 0.0
        elif slope > 0:
            direction = "increasing"
            magnitude = abs(slope)
        else:
            direction = "decreasing"
            magnitude = abs(slope)
        
        # Calculate confidence (R-squared)
        p = np.poly1d(z)
        y_hat = p(x)
        y_bar = np.mean(values)
        ss_res = np.sum((values - y_hat) ** 2)
        ss_tot = np.sum((values - y_bar) ** 2)
        confidence = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Generate contributing factors using LLM
        contributing_factors = await self._analyze_contributing_factors(metric, direction, values)
        
        return TrendAnalysis(
            metric=metric,
            direction=direction,
            magnitude=magnitude,
            confidence=max(0.0, min(1.0, confidence)),
            timeframe=timeframe,
            contributing_factors=contributing_factors
        )
    
    async def _analyze_contributing_factors(self, metric: str, direction: str, values: List[float]) -> List[str]:
        """Analyze contributing factors for trends"""
        try:
            factors_prompt = f"""
            Analyze the contributing factors for this surveillance metric trend:
            
            Metric: {metric}
            Trend Direction: {direction}
            Data Points: {len(values)}
            Recent Values: {values[-5:] if len(values) >= 5 else values}
            
            What could be causing this {direction} trend in {metric}?
            Consider factors like:
            - Time of day/week patterns
            - Environmental conditions
            - System changes or maintenance
            - External events or incidents
            - Equipment performance
            
            Provide 3-5 specific, actionable factors in a JSON list:
            ["factor1", "factor2", "factor3"]
            """
            
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": factors_prompt}],
                temperature=0.3
            )
            
            factors = json.loads(response.choices[0].message.content)
            return factors if isinstance(factors, list) else []
            
        except Exception as e:
            logger.error(f"Error analyzing contributing factors: {e}")
            return [f"Analysis of {metric} trend patterns", f"Environmental factors affecting {metric}"]
    
    async def detect_anomalies(self, request: AnalyticsRequest) -> List[AnomalyDetection]:
        """Detect anomalies in surveillance data"""
        try:
            time_data = await self._get_time_series_data(request)
            anomalies = []
            
            for metric, values in time_data.items():
                if len(values) < 10:
                    continue
                
                metric_anomalies = await self._detect_metric_anomalies(metric, values)
                anomalies.extend(metric_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    async def _detect_metric_anomalies(self, metric: str, values: List[float]) -> List[AnomalyDetection]:
        """Detect anomalies for a specific metric"""
        anomalies = []
        
        # Calculate statistical baseline
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        
        if std_val == 0:
            return anomalies
        
        # Find outliers (values beyond threshold standard deviations)
        for i, value in enumerate(values):
            z_score = abs((value - mean_val) / std_val)
            
            if z_score > self.anomaly_threshold:
                severity = "high" if z_score > 3.0 else "medium"
                
                anomaly = AnomalyDetection(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow() - timedelta(minutes=len(values)-i),
                    metric=metric,
                    expected_value=mean_val,
                    actual_value=value,
                    deviation=z_score,
                    severity=severity,
                    description=f"{metric} value {value:.2f} deviates significantly from expected {mean_val:.2f}"
                )
                
                anomalies.append(anomaly)
        
        return anomalies

# Predictive Analytics Engine
class PredictiveEngine:
    def __init__(self):
        self.models = {}
        self.prediction_cache = {}
    
    async def generate_predictions(self, request: PredictionRequest) -> Dict[str, Any]:
        """Generate predictions based on historical data"""
        try:
            if request.prediction_type == PredictionType.SECURITY_THREAT:
                return await self._predict_security_threats(request)
            elif request.prediction_type == PredictionType.EQUIPMENT_FAILURE:
                return await self._predict_equipment_failure(request)
            elif request.prediction_type == PredictionType.TRAFFIC_PATTERN:
                return await self._predict_traffic_patterns(request)
            elif request.prediction_type == PredictionType.OCCUPANCY_LEVEL:
                return await self._predict_occupancy_levels(request)
            else:
                raise ValueError(f"Unsupported prediction type: {request.prediction_type}")
                
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
            return {"error": str(e)}
    
    async def _predict_security_threats(self, request: PredictionRequest) -> Dict[str, Any]:
        """Predict potential security threats"""
        # Simulate threat prediction model
        threat_probability = np.random.beta(2, 8)  # Skewed towards lower probability
        
        predictions = []
        for hour in range(request.forecast_horizon):
            future_time = datetime.utcnow() + timedelta(hours=hour)
            
            # Adjust probability based on time of day (higher risk at night)
            time_factor = 1.5 if 22 <= future_time.hour or future_time.hour <= 6 else 1.0
            adjusted_prob = min(threat_probability * time_factor, 1.0)
            
            if adjusted_prob >= request.confidence_threshold:
                predictions.append({
                    "timestamp": future_time.isoformat(),
                    "threat_type": "unauthorized_access",
                    "probability": adjusted_prob,
                    "risk_areas": ["parking_lot", "main_entrance"],
                    "confidence": 0.8
                })
        
        recommendations = []
        if predictions and request.include_recommendations:
            recommendations = await self._generate_threat_recommendations(predictions)
        
        return {
            "prediction_type": request.prediction_type,
            "forecast_horizon": request.forecast_horizon,
            "predictions": predictions,
            "recommendations": recommendations,
            "model_accuracy": 0.85
        }
    
    async def _predict_equipment_failure(self, request: PredictionRequest) -> Dict[str, Any]:
        """Predict equipment failure probabilities"""
        # Simulate equipment health data
        equipment_health = {
            "camera_01": 0.95,
            "camera_02": 0.78,  # Showing signs of degradation
            "server_01": 0.92,
            "storage_01": 0.85
        }
        
        predictions = []
        for equipment, health in equipment_health.items():
            if health < 0.8:  # Equipment showing issues
                failure_prob = 1.0 - health
                if failure_prob >= request.confidence_threshold:
                    predictions.append({
                        "equipment_id": equipment,
                        "failure_probability": failure_prob,
                        "estimated_failure_time": (datetime.utcnow() + timedelta(hours=int(24 * health))).isoformat(),
                        "health_score": health,
                        "recommended_action": "schedule_maintenance"
                    })
        
        return {
            "prediction_type": request.prediction_type,
            "predictions": predictions,
            "equipment_health_overview": equipment_health
        }
    
    async def _predict_traffic_patterns(self, request: PredictionRequest) -> Dict[str, Any]:
        """Predict traffic patterns"""
        # Simulate traffic prediction
        current_hour = datetime.utcnow().hour
        base_traffic = self._get_base_traffic_for_hour(current_hour)
        
        predictions = []
        for hour in range(request.forecast_horizon):
            future_hour = (current_hour + hour) % 24
            predicted_traffic = self._get_base_traffic_for_hour(future_hour)
            
            predictions.append({
                "hour": future_hour,
                "predicted_vehicle_count": int(predicted_traffic),
                "confidence": 0.8,
                "peak_times": self._identify_peak_times(future_hour)
            })
        
        return {
            "prediction_type": request.prediction_type,
            "predictions": predictions,
            "traffic_summary": {
                "peak_hours": [8, 9, 17, 18],
                "low_hours": [2, 3, 4, 5]
            }
        }
    
    def _get_base_traffic_for_hour(self, hour: int) -> float:
        """Get base traffic count for a given hour"""
        # Simulate daily traffic pattern
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
            return np.random.normal(50, 10)
        elif 10 <= hour <= 16:  # Day time
            return np.random.normal(25, 5)
        elif 20 <= hour <= 22:  # Evening
            return np.random.normal(15, 3)
        else:  # Night
            return np.random.normal(5, 2)
    
    def _identify_peak_times(self, hour: int) -> List[str]:
        """Identify if hour is during peak times"""
        peaks = []
        if 7 <= hour <= 9:
            peaks.append("morning_rush")
        if 17 <= hour <= 19:
            peaks.append("evening_rush")
        if 12 <= hour <= 13:
            peaks.append("lunch_hour")
        return peaks
    
    async def _predict_occupancy_levels(self, request: PredictionRequest) -> Dict[str, Any]:
        """Predict occupancy levels in different areas"""
        areas = ["lobby", "parking_lot", "cafeteria", "office_floor_1", "office_floor_2"]
        
        predictions = []
        for hour in range(min(request.forecast_horizon, 24)):  # Max 24 hours for occupancy
            future_time = datetime.utcnow() + timedelta(hours=hour)
            
            for area in areas:
                occupancy = self._predict_area_occupancy(area, future_time.hour)
                predictions.append({
                    "area": area,
                    "timestamp": future_time.isoformat(),
                    "predicted_occupancy": occupancy,
                    "capacity_utilization": occupancy / 100,  # Assuming max capacity of 100
                    "confidence": 0.75
                })
        
        return {
            "prediction_type": request.prediction_type,
            "predictions": predictions,
            "area_capacities": {area: 100 for area in areas}
        }
    
    def _predict_area_occupancy(self, area: str, hour: int) -> int:
        """Predict occupancy for a specific area and hour"""
        if area == "parking_lot":
            if 8 <= hour <= 18:  # Work hours
                return int(np.random.normal(75, 10))
            else:
                return int(np.random.normal(20, 5))
        elif area in ["office_floor_1", "office_floor_2"]:
            if 9 <= hour <= 17:  # Office hours
                return int(np.random.normal(60, 15))
            else:
                return int(np.random.normal(5, 2))
        elif area == "cafeteria":
            if hour in [12, 13]:  # Lunch time
                return int(np.random.normal(80, 10))
            elif 8 <= hour <= 17:
                return int(np.random.normal(15, 5))
            else:
                return int(np.random.normal(2, 1))
        else:  # lobby
            if 8 <= hour <= 18:
                return int(np.random.normal(30, 8))
            else:
                return int(np.random.normal(8, 3))
    
    async def _generate_threat_recommendations(self, predictions: List[Dict]) -> List[str]:
        """Generate recommendations based on threat predictions"""
        recommendations_prompt = f"""
        Based on these security threat predictions, provide actionable recommendations:
        
        Predictions: {json.dumps(predictions, indent=2)}
        
        Generate 3-5 specific, actionable security recommendations.
        Focus on prevention, monitoring, and response strategies.
        
        Return as JSON list: ["recommendation1", "recommendation2", ...]
        """
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": recommendations_prompt}],
                temperature=0.3
            )
            
            recommendations = json.loads(response.choices[0].message.content)
            return recommendations if isinstance(recommendations, list) else []
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Increase security patrols during high-risk periods", "Review camera coverage in identified risk areas"]

# Report Generation Engine
class ReportGenerator:
    async def generate_report(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Generate intelligent surveillance reports"""
        try:
            # Collect data for report
            report_data = await self._collect_report_data(request)
            
            # Generate AI summary
            summary = await self._generate_ai_summary(report_data, request)
            
            # Generate insights and recommendations
            insights = await self._generate_insights(report_data)
            
            report = {
                "id": str(uuid.uuid4()),
                "type": request.report_type,
                "generated_at": datetime.utcnow().isoformat(),
                "time_range": {
                    "start": request.custom_start.isoformat() if request.custom_start else None,
                    "end": request.custom_end.isoformat() if request.custom_end else None,
                    "range_type": request.time_range
                },
                "summary": summary,
                "insights": insights,
                "data": report_data,
                "format": request.format
            }
            
            # Store report
            redis_client = await get_redis_client()
            await redis_client.hset(
                "reports",
                report["id"],
                json.dumps(report, default=str)
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}
    
    async def _collect_report_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Collect data for report generation"""
        # This would query actual surveillance data
        # For now, return simulated data
        
        return {
            "alerts_summary": {
                "total_alerts": 45,
                "high_priority": 8,
                "medium_priority": 22,
                "low_priority": 15,
                "resolved": 40,
                "pending": 5
            },
            "camera_performance": {
                "total_cameras": 12,
                "operational": 11,
                "maintenance_required": 1,
                "uptime_percentage": 98.5
            },
            "security_events": {
                "motion_detections": 234,
                "unauthorized_access_attempts": 3,
                "false_positives": 12,
                "confirmed_incidents": 8
            },
            "system_metrics": {
                "average_response_time": "2.3s",
                "storage_usage": "78%",
                "processing_load": "65%"
            }
        }
    
    async def _generate_ai_summary(self, report_data: Dict[str, Any], request: ReportGenerationRequest) -> str:
        """Generate AI-powered report summary"""
        summary_prompt = f"""
        Generate a comprehensive surveillance report summary based on this data:
        
        Report Type: {request.report_type}
        Time Range: {request.time_range}
        Data: {json.dumps(report_data, indent=2)}
        
        Provide a clear, executive-level summary that includes:
        - Key findings and trends
        - Notable incidents or patterns
        - System performance highlights
        - Areas of concern
        - Overall security posture assessment
        
        Keep it concise but informative (200-300 words).
        """
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return "Summary generation unavailable - manual review recommended."
    
    async def _generate_insights(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from report data"""
        insights_prompt = f"""
        Analyze this surveillance data and generate actionable insights:
        
        Data: {json.dumps(report_data, indent=2)}
        
        Provide 3-5 key insights in JSON format:
        [
            {{
                "title": "insight title",
                "description": "detailed description",
                "impact": "high|medium|low",
                "recommendations": ["action1", "action2"],
                "metrics": {{"key": "value"}}
            }}
        ]
        """
        
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": insights_prompt}],
                temperature=0.3
            )
            
            insights = json.loads(response.choices[0].message.content)
            return insights if isinstance(insights, list) else []
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []

# Initialize engines
analytics_engine = AnalyticsEngine()
predictive_engine = PredictiveEngine()
report_generator = ReportGenerator()

# FastAPI App
app = FastAPI(
    title="AI Dashboard Features",
    description="Advanced analytics, predictions, and intelligent reporting",
    version="1.0.0",
    openapi_prefix="/api/v1"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
add_rate_limiting(app, service_name="ai_dashboard_service")

# API Endpoints
@app.post("/api/v1/analytics/trends")
async def analyze_trends(request: AnalyticsRequest):
    """Analyze trends in surveillance data"""
    try:
        trends = await analytics_engine.analyze_trends(request)
        return {
            "trends": [asdict(trend) for trend in trends],
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analytics/anomalies")
async def detect_anomalies(request: AnalyticsRequest):
    """Detect anomalies in surveillance data"""
    try:
        anomalies = await analytics_engine.detect_anomalies(request)
        return {
            "anomalies": [asdict(anomaly) for anomaly in anomalies],
            "detection_timestamp": datetime.utcnow().isoformat(),
            "total_anomalies": len(anomalies)
        }
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predictions")
async def generate_predictions(request: PredictionRequest):
    """Generate predictive analytics"""
    try:
        predictions = await predictive_engine.generate_predictions(request)
        return predictions
    except Exception as e:
        logger.error(f"Error generating predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/reports/generate")
async def generate_report(request: ReportGenerationRequest):
    """Generate intelligent surveillance report"""
    try:
        report = await report_generator.generate_report(request)
        return report
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reports/{report_id}")
async def get_report(report_id: str):
    """Get generated report by ID"""
    try:
        redis_client = await get_redis_client()
        report_data = await redis_client.hget("reports", report_id)
        
        if not report_data:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return json.loads(report_data)
        
    except Exception as e:
        logger.error(f"Error retrieving report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/insights/realtime")
async def get_realtime_insights():
    """Get real-time AI insights"""
    try:
        # Generate current insights
        current_time = datetime.utcnow()
        
        insights = [
            AnalyticsInsight(
                id=str(uuid.uuid4()),
                type=AnalyticsType.ANOMALY_DETECTION,
                title="Unusual Activity Detected",
                description="Motion detected in restricted area during off-hours",
                confidence=0.85,
                timestamp=current_time,
                data={"location": "restricted_zone_a", "time": "02:30 AM"},
                recommendations=["Investigate immediately", "Review camera footage"],
                impact_level="high"
            ),
            AnalyticsInsight(
                id=str(uuid.uuid4()),
                type=AnalyticsType.TREND_ANALYSIS,
                title="Increasing Alert Volume",
                description="Alert volume has increased 25% over the past week",
                confidence=0.92,
                timestamp=current_time,
                data={"trend": "increasing", "magnitude": 0.25},
                recommendations=["Review alert thresholds", "Investigate root causes"],
                impact_level="medium"
            )
        ]
        
        return {
            "insights": [asdict(insight) for insight in insights],
            "generated_at": current_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/widgets/create")
async def create_widget(request: WidgetRequest):
    """Create a new dashboard widget"""
    try:
        widget = DashboardWidget(
            id=str(uuid.uuid4()),
            type=request.widget_type,
            title=request.title,
            description=request.description,
            configuration=request.configuration,
            data_source="analytics_api",
            refresh_interval=30,
            filters=request.filters,
            layout={"x": 0, "y": 0, "w": 4, "h": 3}
        )
        
        # Store widget configuration
        redis_client = await get_redis_client()
        await redis_client.hset(
            "widgets",
            widget.id,
            json.dumps(asdict(widget))
        )
        
        return {
            "widget_id": widget.id,
            "widget": asdict(widget)
        }
        
    except Exception as e:
        logger.error(f"Error creating widget: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/widgets")
async def list_widgets():
    """List all dashboard widgets"""
    try:
        redis_client = await get_redis_client()
        widgets_data = await redis_client.hgetall("widgets")
        
        widgets = []
        for widget_id, widget_json in widgets_data.items():
            widget = json.loads(widget_json)
            widgets.append(widget)
        
        return {"widgets": widgets}
        
    except Exception as e:
        logger.error(f"Error listing widgets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary():
    """Get AI-powered dashboard summary"""
    try:
        # Get current metrics
        analytics_request = AnalyticsRequest(
            analytics_type=AnalyticsType.PERFORMANCE_METRICS,
            time_range=TimeRange.LAST_24_HOURS
        )
        
        # Get trends and anomalies
        trends = await analytics_engine.analyze_trends(analytics_request)
        anomalies = await analytics_engine.detect_anomalies(analytics_request)
        
        # Generate summary
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_status": "operational",
            "active_alerts": len(anomalies),
            "trend_summary": f"{len(trends)} trends identified",
            "key_metrics": {
                "cameras_online": 11,
                "total_cameras": 12,
                "uptime": "98.5%",
                "alerts_24h": 23
            },
            "ai_insights": [
                "System performance within normal parameters",
                "No critical anomalies detected",
                "Traffic patterns show expected daily variation"
            ]
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
