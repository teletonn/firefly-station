from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
from backend import database, auth
from backend.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get comprehensive dashboard overview with key metrics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        # Get user stats
        user_stats = database.get_user_stats()

        # Get message stats
        message_stats = database.get_message_stats()

        # Get alert stats
        alert_stats = database.get_alert_stats()

        # Get zone stats
        zone_stats = database.get_zone_stats()

        # Get bot stats
        bot_stats = database.get_bot_stats()

        # Get process stats
        process_stats = database.get_process_stats()

        # Calculate trends (comparing with yesterday)
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_stats = {
            "messages": database.get_message_count_for_date(yesterday.date()),
            "alerts": database.get_alert_count_for_date(yesterday.date()),
            "users_active": database.get_active_user_count_for_date(yesterday.date())
        }

        overview = {
            "timestamp": datetime.now().isoformat(),
            "users": {
                "total": user_stats.get("total_users", 0),
                "active_today": user_stats.get("active_today", 0),
                "online_now": user_stats.get("online_now", 0),
                "trend": calculate_trend(user_stats.get("active_today", 0), yesterday_stats["users_active"])
            },
            "messages": {
                "total_today": message_stats.get("today", 0),
                "total_week": message_stats.get("week", 0),
                "bot_responses": message_stats.get("bot_responses", 0),
                "trend": calculate_trend(message_stats.get("today", 0), yesterday_stats["messages"])
            },
            "alerts": {
                "total_active": alert_stats.get("active", 0),
                "critical": alert_stats.get("critical", 0),
                "resolved_today": alert_stats.get("resolved_today", 0),
                "trend": calculate_trend(alert_stats.get("active", 0), yesterday_stats["alerts"])
            },
            "zones": {
                "total": zone_stats.get("total", 0),
                "active": zone_stats.get("active", 0),
                "users_per_zone": zone_stats.get("avg_users_per_zone", 0)
            },
            "bot": {
                "status": bot_stats.get("status", "unknown"),
                "uptime_percentage": bot_stats.get("uptime_percentage", 0),
                "response_time_avg": bot_stats.get("response_time_avg", 0)
            },
            "processes": {
                "total": process_stats.get("total", 0),
                "running": process_stats.get("running", 0),
                "completed_today": process_stats.get("completed_today", 0)
            }
        }

        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard overview: {str(e)}")

@router.get("/users/analytics")
async def get_user_analytics(
    period: str = Query("7d", regex="^(1h|24h|7d|30d|90d)$"),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get detailed user analytics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        days = parse_period(period)
        start_date = datetime.now() - timedelta(days=days)
        logger.info(f"Getting user analytics for period {period}, days {days}, start_date {start_date}")

        # User registration trends
        logger.info("Calling get_user_registration_trends")
        registration_trends = database.get_user_registration_trends(start_date)
        logger.info(f"Got registration_trends: {len(registration_trends)} entries")

        # User activity patterns
        activity_patterns = database.get_user_activity_patterns(days)

        # Geographic distribution
        geo_distribution = database.get_user_geographic_distribution()

        # Device types
        device_stats = database.get_user_device_stats()

        return {
            "period": period,
            "registration_trends": registration_trends,
            "activity_patterns": activity_patterns,
            "geographic_distribution": geo_distribution,
            "device_stats": device_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user analytics: {str(e)}")

@router.get("/messages/analytics")
async def get_message_analytics(
    period: str = Query("7d", regex="^(1h|24h|7d|30d|90d)$"),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get detailed message analytics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        days = parse_period(period)
        start_date = datetime.now() - timedelta(days=days)

        # Message volume trends
        volume_trends = database.get_message_volume_trends(start_date)

        # Message types distribution
        type_distribution = database.get_message_type_distribution(days)

        # Response times
        response_times = database.get_message_response_times(days)

        # Peak usage times
        peak_times = database.get_message_peak_times(days)

        # Bot interaction quality
        bot_quality = database.get_bot_interaction_quality(days)

        return {
            "period": period,
            "volume_trends": volume_trends,
            "type_distribution": type_distribution,
            "response_times": response_times,
            "peak_times": peak_times,
            "bot_quality": bot_quality
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting message analytics: {str(e)}")

@router.get("/alerts/analytics")
async def get_alert_analytics(
    period: str = Query("7d", regex="^(1h|24h|7d|30d|90d)$"),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get detailed alert analytics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        days = parse_period(period)
        start_date = datetime.now() - timedelta(days=days)

        # Alert trends
        alert_trends = database.get_alert_trends(start_date)

        # Alert types distribution
        type_distribution = database.get_alert_type_distribution(days)

        # Response times
        response_times = database.get_alert_response_times(days)

        # False positive rate
        false_positives = database.get_alert_false_positive_rate(days)

        # Zone-based alerts
        zone_alerts = database.get_zone_based_alerts(days)

        return {
            "period": period,
            "alert_trends": alert_trends,
            "type_distribution": type_distribution,
            "response_times": response_times,
            "false_positives": false_positives,
            "zone_alerts": zone_alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alert analytics: {str(e)}")

@router.get("/geolocation/analytics")
async def get_geolocation_analytics(
    period: str = Query("7d", regex="^(1h|24h|7d|30d|90d)$"),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get detailed geolocation analytics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        days = parse_period(period)
        start_date = datetime.now() - timedelta(days=days)

        # Movement patterns
        movement_patterns = database.get_movement_patterns(days)

        # Zone dwell times
        dwell_times = database.get_zone_dwell_times(days)

        # Heatmap data
        heatmap_data = database.get_location_heatmap_data(days)

        # Predictive analytics
        predictions = database.get_location_predictions()

        # Speed analysis
        speed_analysis = database.get_speed_analysis(days)

        return {
            "period": period,
            "movement_patterns": movement_patterns,
            "dwell_times": dwell_times,
            "heatmap_data": heatmap_data,
            "predictions": predictions,
            "speed_analysis": speed_analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting geolocation analytics: {str(e)}")

@router.get("/geolocation/heatmap")
async def get_geolocation_heatmap(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get location heatmap data."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        heatmap_data = database.get_location_heatmap_data(days)
        return heatmap_data
    except Exception as e:
        logger.error(f"Error getting heatmap data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve heatmap data.")

@router.get("/performance/metrics")
async def get_performance_metrics(
    period: str = Query("24h", regex="^(1h|24h|7d|30d|90d)$"),
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Get system performance metrics."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        logger.info(f"Getting performance metrics for period {period}")
        days = parse_period(period)
        start_date = datetime.now() - timedelta(days=days)
        logger.info(f"Parsed period to {days} days, start_date {start_date}")

        # System performance
        logger.info("Calling get_system_performance_metrics")
        system_perf = database.get_system_performance_metrics(days)
        logger.info(f"Got system_perf: {system_perf}")

        # API response times
        api_times = database.get_api_response_times(days)

        # Database performance
        db_perf = database.get_database_performance_metrics(days)

        # WebSocket metrics
        ws_metrics = database.get_websocket_metrics(days)

        return {
            "period": period,
            "system_performance": system_perf,
            "api_response_times": api_times,
            "database_performance": db_perf,
            "websocket_metrics": ws_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance metrics: {str(e)}")

@router.get("/reports/generate")
async def generate_analytics_report(
    report_type: str = Query(..., regex="^(daily|weekly|monthly|custom)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(auth.get_current_active_user)
):
    """Generate comprehensive analytics report."""
    if not auth.check_permission(current_user, "analytics:read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        if report_type == "custom" and (not start_date or not end_date):
            raise HTTPException(status_code=400, detail="start_date and end_date required for custom reports")

        # Calculate date range
        if report_type == "daily":
            start = datetime.now() - timedelta(days=1)
            end = datetime.now()
        elif report_type == "weekly":
            start = datetime.now() - timedelta(days=7)
            end = datetime.now()
        elif report_type == "monthly":
            start = datetime.now() - timedelta(days=30)
            end = datetime.now()
        else:  # custom
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)

        # Generate report data
        report_data = {
            "report_type": report_type,
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "overview": await get_dashboard_overview(current_user),
                "users": await get_user_analytics(f"{(end - start).days}d", current_user),
                "messages": await get_message_analytics(f"{(end - start).days}d", current_user),
                "alerts": await get_alert_analytics(f"{(end - start).days}d", current_user),
                "geolocation": await get_geolocation_analytics(f"{(end - start).days}d", current_user),
                "performance": await get_performance_metrics(f"{(end - start).days}d", current_user)
            }
        }

        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

def calculate_trend(current: float, previous: float) -> Dict[str, Any]:
    """Calculate trend percentage and direction."""
    if previous == 0:
        return {"percentage": 0, "direction": "stable"}

    change = ((current - previous) / previous) * 100
    direction = "up" if change > 0 else "down" if change < 0 else "stable"

    return {
        "percentage": round(abs(change), 2),
        "direction": direction
    }

def parse_period(period: str) -> int:
    """Parse period string to days."""
    logger.info(f"Parsing period: {period}")
    period_map = {
        "1h": 1/24,
        "24h": 1,
        "7d": 7,
        "30d": 30,
        "90d": 90
    }
    days = period_map.get(period, 7)
    logger.info(f"Parsed period {period} to {days} days")
    return days