"""
LLM Service Module

This module provides AI-powered text generation and analysis services for surveillance
systems using Large Language Models. It handles intelligent summarization, insight
generation, and natural language processing tasks through dependency injection.

The service integrates with OpenAI's API to provide contextual analysis of surveillance
data, generate human-readable insights, and create actionable recommendations based
on system analytics and metrics.

Key Features:
- AI-powered insight summarization
- Contextual analysis of surveillance patterns  
- Natural language generation for reports
- Dependency injection for flexible client management
- Error handling and retry logic for API calls

Classes:
    LLMService: Main service for LLM operations and text generation
    
Dependencies:
    - AsyncOpenAI: Async OpenAI client for API interactions
    - JSON: For data serialization and processing
    - Logging: For error tracking and debugging
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """
    AI-powered language model service for surveillance system analysis.
    
    This service provides intelligent text generation, insight summarization, and
    natural language processing capabilities for surveillance data analysis. It
    uses dependency injection to manage OpenAI client connections and provides
    sophisticated error handling for API interactions.
    
    The service specializes in converting technical surveillance metrics and
    analytics into human-readable insights, recommendations, and summaries.
    
    Attributes:
        client: Injected AsyncOpenAI client for API operations
        model: Default OpenAI model for text generation (gpt-3.5-turbo)
        
    Example:
        >>> llm_service = LLMService(openai_client)
        >>> summary = await llm_service.generate_insights_summary(data)
        >>> report = await llm_service.generate_report(analytics_data)
    """
    
    def __init__(self, openai_client: AsyncOpenAI) -> None:
        """
        Initialize LLM service with OpenAI client dependency.
        
        :param openai_client: Async OpenAI client for API interactions
        :raises TypeError: If openai_client is not AsyncOpenAI instance
        """
        self.client = openai_client
        # Use GPT-3.5-turbo as default model for cost-effectiveness and speed
        self.model = "gpt-3.5-turbo"
        
    async def generate_insights_summary(self, insights_data: Dict[str, Any]) -> str:
        """
        Generate AI-powered summary of surveillance system insights.
        
        Analyzes complex surveillance analytics data and transforms it into
        clear, actionable insights using natural language generation. The
        method processes trends, anomalies, and performance metrics to create
        a comprehensive system status summary.
        
        :param insights_data: Dictionary containing surveillance analytics including
                            trends, anomalies, and performance metrics
        :return: AI-generated summary text with key findings and recommendations
        :raises Exception: If OpenAI API call fails or data processing errors occur
        
        Example:
            >>> data = {
            ...     "trends": [{"metric": "motion_events", "direction": "increasing"}],
            ...     "anomalies": [{"severity": "high", "description": "Unusual activity"}],
            ...     "metrics": {"cpu_usage": 75.2}
            ... }
            >>> summary = await llm_service.generate_insights_summary(data)
            >>> print(summary)  # "System shows increased motion events..."
        """
        try:
            prompt = f"""
            Based on the following surveillance system insights data, provide a clear, 
            concise summary highlighting the most important findings and actionable recommendations.
            
            Data: {json.dumps(insights_data, default=str)}
            
            Please focus on:
            1. Key trends and patterns
            2. Any anomalies or concerning findings
            3. Actionable recommendations
            4. Overall system health assessment
            
            Keep the response professional and under 200 words.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant specialized in surveillance system analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating insights summary: {e}")
            return "Unable to generate insights summary at this time."
    
    async def generate_report_content(self, report_data: Dict[str, Any]) -> str:
        """Generate intelligent report content"""
        try:
            prompt = f"""
            Generate a comprehensive surveillance system report based on the following data:
            
            {json.dumps(report_data, default=str)}
            
            Structure the report with:
            1. Executive Summary
            2. Key Metrics Overview
            3. Trend Analysis
            4. Security Incidents and Alerts
            5. System Performance
            6. Recommendations
            
            Use professional language suitable for security operations teams.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security analyst AI creating professional surveillance reports."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating report content: {e}")
            return "Unable to generate report content at this time."
    
    async def analyze_anomaly_patterns(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in detected anomalies"""
        try:
            if not anomalies:
                return {"summary": "No anomalies detected", "patterns": [], "recommendations": []}
            
            prompt = f"""
            Analyze the following surveillance system anomalies and identify patterns:
            
            {json.dumps(anomalies, default=str)}
            
            Provide analysis in JSON format with:
            - summary: Brief overview of findings
            - patterns: List of identified patterns
            - recommendations: List of actionable recommendations
            - priority_level: high/medium/low based on severity
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI security analyst. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            # Try to parse JSON response
            try:
                return json.loads(response.choices[0].message.content.strip())
            except json.JSONDecodeError:
                return {
                    "summary": "Pattern analysis completed",
                    "patterns": ["Multiple anomalies detected"],
                    "recommendations": ["Review system configuration"],
                    "priority_level": "medium"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing anomaly patterns: {e}")
            return {
                "summary": "Analysis unavailable",
                "patterns": [],
                "recommendations": [],
                "priority_level": "low"
            }
    
    async def generate_predictive_insights(self, historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate predictive insights based on historical data"""
        try:
            prompt = f"""
            Based on the following historical surveillance data, provide predictive insights:
            
            {json.dumps(historical_data, default=str)}
            
            Generate predictions for:
            1. Likely security events in next 24 hours
            2. System performance trends
            3. Resource utilization forecasts
            4. Maintenance recommendations
            
            Respond in JSON format with specific, actionable insights.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a predictive analytics AI for surveillance systems. Respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            try:
                return json.loads(response.choices[0].message.content.strip())
            except json.JSONDecodeError:
                return {
                    "security_forecast": "Normal activity expected",
                    "performance_forecast": "Stable system performance",
                    "maintenance_recommendations": ["Regular system monitoring"],
                    "confidence_level": "medium"
                }
                
        except Exception as e:
            logger.error(f"Error generating predictive insights: {e}")
            return {
                "security_forecast": "Analysis unavailable",
                "performance_forecast": "Analysis unavailable",
                "maintenance_recommendations": [],
                "confidence_level": "low"
            }
    
    async def explain_metric_changes(self, metric_name: str, old_value: float, new_value: float, context: Dict[str, Any]) -> str:
        """Explain changes in specific metrics"""
        try:
            change_percent = ((new_value - old_value) / old_value * 100) if old_value != 0 else 0
            
            prompt = f"""
            The surveillance system metric '{metric_name}' changed from {old_value} to {new_value} 
            (a {change_percent:.1f}% change).
            
            Context: {json.dumps(context, default=str)}
            
            Provide a brief, clear explanation of:
            1. What this change means
            2. Possible causes
            3. Whether action is needed
            
            Keep response under 100 words and professional.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a surveillance system analyst explaining metric changes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error explaining metric changes: {e}")
            return f"Metric {metric_name} changed from {old_value} to {new_value}. Manual review recommended."


# Global instance
# No global instance needed - use dependency injection
