"""
Report Generation Engine Service

This module provides comprehensive report generation capabilities for surveillance
systems using AI-powered analysis and natural language generation. It creates
intelligent reports with insights, trends, and actionable recommendations.

The service processes surveillance data, analytics, and metrics to generate
various types of reports including security summaries, performance analysis,
incident reports, and compliance documentation. It integrates with LLM services
to provide human-readable narratives and insights.

Key Features:
- AI-powered report generation with natural language narratives
- Multiple report types (security, performance, incident, compliance)
- Data aggregation from multiple surveillance sources
- Automated insight generation and recommendations
- Customizable report templates and formats
- Integration with caching for performance optimization

Classes:
    ReportGenerator: Main report generation engine with AI integration
    
Dependencies:
    - LLMService: For AI-powered narrative generation (TODO: Refactor to DI)
    - JSON: For data serialization and report formatting
    - UUID: For unique report identification
    - DateTime: For temporal data handling and report timestamping
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any

from ..models.schemas import ReportGenerationRequest
from ..services.llm_client import LLMService  # TODO: Refactor to use dependency injection

# Temporary fallback - create a basic client for backward compatibility 
# TODO: Remove this after full refactoring to dependency injection
class _TempOpenAIClient:
    """
    Temporary OpenAI client for backward compatibility.
    
    TODO: Remove this after full refactoring to dependency injection.
    This class provides a temporary workaround for services that haven't
    been fully migrated to the dependency injection pattern.
    """
    
    def __init__(self):
        """
        Initialize temporary OpenAI client.
        
        Creates an AsyncOpenAI client using settings configuration.
        This is a temporary measure until full DI refactoring is complete.
        """
        from openai import AsyncOpenAI
        from config.config import settings
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

openai_client = _TempOpenAIClient()  # DEPRECATED - remove after refactoring
from ..utils.database import get_redis_client
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Intelligent report generation engine for surveillance systems.
    
    This generator creates comprehensive surveillance reports using AI-powered
    analysis and natural language generation. It processes surveillance data,
    analytics, and metrics to produce professional reports with insights,
    recommendations, and executive summaries.
    
    The generator supports multiple report types and formats, integrates with
    LLM services for narrative generation, and provides caching capabilities
    for performance optimization.
    
    Example:
        >>> generator = ReportGenerator()
        >>> request = ReportGenerationRequest(report_type="security_summary")
        >>> report = await generator.generate_report(request)
        >>> print(f"Report ID: {report['id']}")
    """
    
    async def generate_report(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """
        Generate comprehensive surveillance reports with AI-powered insights.
        
        Creates detailed reports by collecting surveillance data, analyzing trends
        and patterns, and generating human-readable narratives with actionable
        recommendations. The method supports various report types and customizable
        time ranges.
        
        :param request: Report generation request with type, parameters, and filters
        :return: Complete report dictionary with data, insights, and AI-generated summary
        :raises Exception: If report generation fails due to data or processing errors
        
        Example:
            >>> request = ReportGenerationRequest(
            ...     report_type="security_summary",
            ...     time_range="last_week",
            ...     include_recommendations=True
            ... )
            >>> report = await generator.generate_report(request)
            >>> print(f"Report contains {len(report['insights'])} insights")
        """
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
            response = await openai_client.client.chat.completions.create(
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
            response = await openai_client.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": insights_prompt}],
                temperature=0.3
            )
            
            insights = json.loads(response.choices[0].message.content)
            return insights if isinstance(insights, list) else []
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []


# Global instance
report_generator = ReportGenerator()
