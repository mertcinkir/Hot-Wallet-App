from src.service_layer import views
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from src.adapters.message_broker.connection_manager import AbstractConnectionManager, HealthMetrics, ConnectionMetrics


router = APIRouter(
    prefix="/broker",
    tags=["Broker Monitoring"],
    responses={404: {"description": "Source not found."}},
)


def get_connection_manager(request: Request) -> AbstractConnectionManager:
    """"
    Dependency to retrieve the connection manager instance from the application state.

    Returns:
        AbstractConnectionManager: The active connection manager instance.
    """
    return request.app.state.connection_manager


@router.get("/health", response_model=HealthMetrics)
async def health_check(conn: AbstractConnectionManager = Depends(get_connection_manager)):
    """
    Provides a comprehensive health check for the message broker.

    Returns:
        HealthMetrics: An object containing various health indicators.
    """
    return await views.get_health_status(conn)


@router.get("/metrics", response_model=ConnectionMetrics)
async def get_metrics(conn: AbstractConnectionManager = Depends(get_connection_manager)):
    """
    Retrieves detailed connection metrics for monitoring dashboards.

    Returns:
        ConnectionMetrics: An object containing detailed connection statistics.
    """
    return await views.get_metrics(conn)


@router.get("/prometheus")
async def prometheus_metrics(conn: AbstractConnectionManager = Depends(get_connection_manager)):
    """
    Exposes metrics in a Prometheus-compatible format for scraping.

    Returns:
        PlainTextResponse: A plain text response with Prometheus-formatted metrics.
    """
    metrics_text = await views.get_prometheus_metrics(conn)
    return PlainTextResponse(content=metrics_text, media_type="text/plain")

@router.get("/alerts", response_model=views.AlertsResponse)
async def get_alerts(conn: AbstractConnectionManager = Depends(get_connection_manager)):
    """
    Retrieves current alerts based on the system's status.

    Returns:
        views.AlertsResponse: An object containing any active alerts.
    """
    return await views.get_alerts(conn)
