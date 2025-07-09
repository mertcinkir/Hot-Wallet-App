from typing import  List
from datetime import datetime
import time
from pydantic.dataclasses import dataclass
from src.adapters.message_broker.connection_manager import AbstractConnectionManager, ConnectionMetrics, HealthMetrics


@dataclass
class AlertsResponse:
    timestamp: datetime
    critical_alerts: List[str]
    warning_alerts: List[str]
    info_alerts: List[str]


async def get_health_status(conn: AbstractConnectionManager) -> HealthMetrics:
    """Get comprehensive health check status"""
    return await conn.health_check()

async def get_metrics(conn: AbstractConnectionManager) -> ConnectionMetrics:
    """Get detailed metrics for monitoring"""
    return conn.get_metrics()

async def get_prometheus_metrics(conn: AbstractConnectionManager) -> str:
    """Generate Prometheus-compatible metrics"""
    status = await conn.health_check()

    return f"""
    # HELP rabbitmq_connections_total Total number of connections created
    # TYPE rabbitmq_connections_total counter
    rabbitmq_connections_total {status.metrics.total_connections_created}

    # HELP rabbitmq_channels_total Total number of channels created
    # TYPE rabbitmq_channels_total counter
    rabbitmq_channels_total {status.metrics.total_channels_created}

    # HELP rabbitmq_connections_active Current number of active connections
    # TYPE rabbitmq_connections_active gauge
    rabbitmq_connections_active {status.metrics.active_connections}

    # HELP rabbitmq_channels_active Current number of active channels
    # TYPE rabbitmq_channels_active gauge
    rabbitmq_channels_active {status.metrics.active_channels}

    # HELP rabbitmq_connection_errors_total Total number of connection errors
    # TYPE rabbitmq_connection_errors_total counter
    rabbitmq_connection_errors_total {status.metrics.connection_errors}

    # HELP rabbitmq_channel_errors_total Total number of channel errors
    # TYPE rabbitmq_channel_errors_total counter  
    rabbitmq_channel_errors_total {status.metrics.channel_errors}

    # HELP rabbitmq_messages_published_total Total number of messages published
    # TYPE rabbitmq_messages_published_total counter
    rabbitmq_messages_published_total {status.metrics.total_messages_published}

    # HELP rabbitmq_messages_consumed_total Total number of messages consumed
    # TYPE rabbitmq_messages_consumed_total counter
    rabbitmq_messages_consumed_total {status.metrics.total_messages_consumed}
    
    # HELP rabbitmq_last_error_timestamp_seconds Timestamp of last error
    # TYPE rabbitmq_last_error_timestamp_seconds gauge
    rabbitmq_last_error_timestamp_seconds {status.metrics.last_error_time or 0}
    
    # HELP rabbitmq_last_error_message message of last error
    # TYPE rabbitmq_last_error_message gauge
    rabbitmq_last_error_message {status.metrics.last_error_message or ""}

    # HELP rabbitmq_connection_pool_utilization Connection pool utilization ratio
    # TYPE rabbitmq_connection_pool_utilization gauge
    rabbitmq_connection_pool_utilization {status.metrics.connection_pool_utilization:.4f}

    # HELP rabbitmq_channel_pool_utilization Channel pool utilization ratio
    # TYPE rabbitmq_channel_pool_utilization gauge
    rabbitmq_channel_pool_utilization {status.metrics.channel_pool_utilization:.4f}

    # HELP rabbitmq_circuit_breaker_open Circuit breaker status (1 = open, 0 = closed)
    # TYPE rabbitmq_circuit_breaker_open gauge
    rabbitmq_circuit_breaker_open {status.circuit_breaker_open}

    # HELP rabbitmq_circuit_breaker_failures Circuit breaker failure count
    # TYPE rabbitmq_circuit_breaker_failures gauge
    rabbitmq_circuit_breaker_failures {status.circuit_breaker_failures}
    
    # HELP rabbitmq_circuit_breaker_last_failure Circuit breaker last failure timestamp
    # TYPE rabbitmq_circuit_breaker_last_failure gauge
    rabbitmq_circuit_breaker_last_failure {status.circuit_breaker_last_failure}
    
    # HELP rabbitmq_errors Circuit breaker last failure timestamp
    # TYPE rabbitmq_errors gauge
    rabbitmq_errors {status.errors}
"""

async def get_alerts(conn: AbstractConnectionManager) -> AlertsResponse:
    """Get current alerts based on system status"""
    status = await conn.health_check()
    current_time = time.time()

    critical_alerts = []
    warning_alerts = []
    info_alerts = []

    # Critical alerts
    if status.circuit_breaker_open:
        critical_alerts.append("Circuit breaker is OPEN - RabbitMQ connections are failing")

    if status.metrics.active_connections == 0:
        critical_alerts.append("No active connections available")

    if status.metrics.connection_pool_utilization > 0.8:
        warning_alerts.append(f"Connection pool utilization high: {status.metrics.connection_pool_utilization:.1%}")

        if status.metrics.channel_pool_utilization > 0.8:
            warning_alerts.append(f"Channel pool utilization high: {status.metrics.channel_pool_utilization:.1%}")

    if status.metrics.last_error_time and (current_time - status.metrics.last_error_time) < 300:
        warning_alerts.append(f"Recent error: {status.metrics.last_error_message}")

    if status.circuit_breaker_failures > 0:
        warning_alerts.append(
            f"Circuit breaker has {status.circuit_breaker_failures} failures"
        )

    # Info alerts
    if status.metrics.connection_pool_utilization > 0.5:
        info_alerts.append(f"Connection pool utilization: {status.metrics.connection_pool_utilization:.1%}")

    if status.dedicated_channels > 5:
        info_alerts.append(f"High number of dedicated channels: {status.dedicated_channels}")

    return AlertsResponse(
        timestamp=datetime.now(),
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        info_alerts=info_alerts
    )
