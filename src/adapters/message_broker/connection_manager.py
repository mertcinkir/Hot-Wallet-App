import time
import asyncio
import logging
import aio_pika
from enum import Enum
from pydantic import Field, computed_field
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pydantic.dataclasses import dataclass
from aiormq.exceptions import AMQPException
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection
from typing import AsyncIterator, Awaitable, Callable, Dict, Optional, AsyncGenerator, List

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Represents the current state of a connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class ConnectionMetrics:
    """Collects and provides metrics for connection and channel pool performance."""
    enable_channel_pooling: bool
    max_connection_pool_size: int
    max_channel_pool_size: int
    total_connections_created: int = 0
    total_channels_created: int = 0
    active_connections: int = 0
    active_channels: int = 0
    connection_errors: int = 0
    channel_errors: int = 0
    last_error_time: Optional[float] = None
    last_error_message: str = ""
    total_messages_published: int = 0
    total_messages_consumed: int = 0

    @computed_field
    @property
    def connection_pool_utilization(self) -> float:
        """Calculates the current utilization of the connection pool."""
        if self.max_connection_pool_size == 0:
            return 0.0
        return self.active_connections / self.max_connection_pool_size * 100

    @computed_field
    @property
    def channel_pool_utilization(self) -> float:
        """Calculates the current utilization of the channel pool."""
        if not self.enable_channel_pooling or self.max_channel_pool_size == 0:
            return 0.0
        return self.active_channels / self.max_channel_pool_size * 100


@dataclass
class HealthMetrics:
    """Provides a snapshot of the broker connection manager's health."""
    status: str
    connection_pool_size: int
    channel_pool_size: int
    dedicated_channels: int
    circuit_breaker_open: bool
    circuit_breaker_failures: int
    circuit_breaker_last_failure: float
    metrics: ConnectionMetrics
    errors: List[str]


@dataclass(config=type("Config", (), {"arbitrary_types_allowed": True}))
class PooledConnection:
    """Wrapper around an `AbstractRobustConnection` with pooling metadata."""
    connection: AbstractRobustConnection
    created_at: float = Field(default_factory=time.time)
    last_used_at: float = Field(default_factory=time.time)
    usage_count: int = 0
    state: ConnectionState = ConnectionState.CONNECTED

    def mark_used(self):
        """Updates the last used timestamp and increments usage count."""
        self.last_used_at = time.time()
        self.usage_count += 1

    @property
    def is_expired(self) -> bool:
        """Checks if the connection has exceeded its idle timeout (5 minutes)."""
        return time.time() - self.last_used_at > 300

    @property
    def is_healthy(self) -> bool:
        """Checks if the wrapped connection is currently healthy and open."""
        return (
                not self.connection.is_closed
                and self.state == ConnectionState.CONNECTED
        )


@dataclass(config=type("Config", (), {"arbitrary_types_allowed": True}))
class PooledChannel:
    """Wrapper around an `AbstractRobustChannel` with pooling metadata."""
    channel: AbstractRobustChannel
    connection_id: str  # ID of the connection this channel belongs to
    created_at: float = Field(default_factory=time.time)
    last_used_at: float = Field(default_factory=time.time)
    usage_count: int = 0
    reserved: bool = False  # True if currently in use by a consumer/publisher

    def mark_used(self):
        """Updates the last used timestamp and increments usage count."""
        self.last_used_at = time.time()
        self.usage_count += 1

    @property
    def is_expired(self) -> bool:
        """Checks if the channel has exceeded its idle timeout (2 minutes)."""
        return time.time() - self.last_used_at > 120

    @property
    def is_healthy(self) -> bool:
        """Checks if the wrapped channel is currently healthy and not reserved."""
        return not self.channel.is_closed and not self.reserved


class HealthChecker:
    """Utility class for performing health checks on AMQP connections and channels."""

    @staticmethod
    async def check_connection_health(connection: AbstractRobustConnection) -> bool:
        """
        Performs a health check on an AMQP connection.

        Attempts to create a temporary channel to verify connectivity.
        """
        try:
            if connection.is_closed:
                logger.debug("Connection health check failed: connection is closed.")
                return False
            temp_channel = await connection.channel()
            await temp_channel.close()
            return True
        except Exception as e:
            logger.debug(f"Connection health check failed: {e}")
            return False

    @staticmethod
    async def check_channel_health(channel: AbstractRobustChannel) -> bool:
        """Checks if an AMQP channel is healthy (i.e., not closed)."""
        try:
            return not channel.is_closed
        except Exception as e:
            logger.debug(f"Channel health check failed: {e}")
            return False


class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to prevent cascading failures.

    Opens the circuit when a threshold of failures is reached, preventing
    further operations for a defined timeout period.
    """

    def __init__(self, threshold: int, timeout: int):
        self.circuit_breaker_threshold = threshold
        self.circuit_breaker_timeout = timeout
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_failure = 0
        self.circuit_breaker_open = False

    def check_circuit_breaker(self) -> bool:
        """
        Checks if the circuit breaker is currently open.

        If the timeout has passed, attempts to reset the circuit.
        """
        if not self.circuit_breaker_open:
            return False

        if time.time() - self.circuit_breaker_last_failure > self.circuit_breaker_timeout:
            self.circuit_breaker_open = False
            self.circuit_breaker_failures = 0
            logger.info("Circuit breaker reset to closed state.")
            return False

        return True

    def record_failure(self):
        """Records a failure and increments the failure count."""
        self.circuit_breaker_failures += 1
        self.circuit_breaker_last_failure = time.time()

        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            self.circuit_breaker_open = True
            logger.warning(
                f"Circuit breaker opened due to {self.circuit_breaker_failures} repeated failures. "
                f"Will reset in {self.circuit_breaker_timeout} seconds."
            )

    def record_success(self):
        """Records a success, reducing the failure count if greater than zero."""
        if self.circuit_breaker_failures > 0:
            self.circuit_breaker_failures = max(0, self.circuit_breaker_failures - 1)


class AbstractConnectionManager(ABC):
    """Abstract base class for managing AMQP connections and channels."""

    @abstractmethod
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AbstractRobustConnection, None]:
        """
        Abstract method to get a connection.

        Yields:
            AbstractRobustConnection: An active AMQP connection.
        """
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_channel(self, prefetch_count: int = 1) -> AsyncGenerator[AbstractRobustChannel, None]:
        """
        Abstract method to get a general-purpose channel.

        Args:
            prefetch_count (int): The maximum number of messages to prefetch.

        Yields:
            AbstractRobustChannel: An active AMQP channel.
        """
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_dedicated_channel(self, prefetch_count: int = 1) -> AsyncGenerator[AbstractRobustChannel, None]:
        """
        Abstract method to get a long-lived dedicated channel, typically for consumers.

        Args:
            prefetch_count (int): The maximum number of messages to prefetch.

        Yields:
            AbstractRobustChannel: An active, dedicated AMQP channel.
        """
        pass

    @abstractmethod
    def get_metrics(self) -> ConnectionMetrics:
        """
        Abstract method to retrieve current connection and channel metrics.

        Returns:
            ConnectionMetrics: An object containing connection pool metrics.
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthMetrics:
        """
        Abstract method to perform a comprehensive health check of the manager.

        Returns:
            HealthMetrics: An object detailing the health status.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Abstract method to close all managed connections and channels."""
        pass


class RabbitMQConnectionManager(AbstractConnectionManager):
    """
    Manages RabbitMQ connections and channels with pooling, health monitoring,
    metrics collection, and circuit breaker functionality.
    """

    def __init__(
            self,
            connection_url: str,
            max_connection_pool_size: int = 5,
            max_channel_pool_size: int = 20,
            min_connection_pool_size: int = 1,  # Not explicitly used in current logic, but kept for future expansion
            heartbeat: int = 300,
            connection_factory: Callable[..., Awaitable[AbstractRobustConnection]] = aio_pika.connect_robust,
            enable_channel_pooling: bool = True,
            pool_cleanup_interval: int = 60,
            max_connection_age: int = 3600,  # 1 hour
            circuit_breaker_threshold: int = 5,
            circuit_breaker_timeout: int = 30,
    ):
        """
        Initializes the RabbitMQ connection manager.

        Args:
            connection_url (str): The RabbitMQ connection URI.
            max_connection_pool_size (int): Maximum connections in the pool.
            max_channel_pool_size (int): Maximum channels in the pool (if pooling enabled).
            min_connection_pool_size (int): Minimum connections to maintain (currently not fully utilized).
            heartbeat (int): AMQP heartbeat interval in seconds.
            connection_factory (Callable): Function to create robust AMQP connections.
            enable_channel_pooling (bool): Whether to enable channel pooling.
            pool_cleanup_interval (int): Interval in seconds for background pool cleanup.
            max_connection_age (int): Maximum age (in seconds) for a connection before it's recycled.
            circuit_breaker_threshold (int): Number of failures to open the circuit breaker.
            circuit_breaker_timeout (int): Duration (in seconds) the circuit breaker remains open.
        """
        self._connection_url = connection_url
        self._heartbeat = heartbeat
        self._factory = connection_factory
        self._max_conn_pool_size = max_connection_pool_size
        self._max_channel_pool_size = max_channel_pool_size
        self._min_conn_pool_size = min_connection_pool_size
        self._enable_channel_pooling = enable_channel_pooling
        self._pool_cleanup_interval = pool_cleanup_interval
        self._max_connection_age = max_connection_age

        self._connection_pool: Dict[str, PooledConnection] = {}
        self._connection_pool_lock = asyncio.Lock()
        self._connection_semaphore = asyncio.Semaphore(max_connection_pool_size)

        self._channel_pool: Dict[str, PooledChannel] = {}
        self._channel_pool_lock = asyncio.Lock()
        self._channel_semaphore = asyncio.Semaphore(max_channel_pool_size)

        self._dedicated_channels: Dict[str, PooledChannel] = {}  # For consumers
        self._dedicated_channels_lock = asyncio.Lock()

        self._circuit_breaker = CircuitBreaker(circuit_breaker_threshold, circuit_breaker_timeout)

        self._metrics = ConnectionMetrics(enable_channel_pooling, max_connection_pool_size, max_channel_pool_size)
        self._closed = False

        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_background_tasks()
        logger.info("RabbitMQConnectionManager initialized.")

    def _start_background_tasks(self):
        """Starts background tasks for pool maintenance."""
        self._cleanup_task = asyncio.create_task(self._pool_cleanup_loop())
        logger.debug("Background pool cleanup task started.")

    async def _pool_cleanup_loop(self):
        """
        Periodically runs the pool cleanup process.

        This task runs in the background to remove expired or unhealthy
        connections and channels from the pools.
        """
        while not self._closed:
            try:
                await asyncio.sleep(self._pool_cleanup_interval)
                await self._cleanup_expired_resources()
            except asyncio.CancelledError:
                logger.info("Pool cleanup loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Pool cleanup error: {e}", exc_info=True)

    async def _cleanup_expired_resources(self):
        """
        Removes expired or unhealthy connections and channels from their pools.
        """
        current_time = time.time()

        # Cleanup expired connections
        async with self._connection_pool_lock:
            expired_conn_ids = []
            for conn_id, pooled_conn in list(self._connection_pool.items()):  # Use list to allow dict modification
                if (
                        pooled_conn.is_expired
                        or not pooled_conn.is_healthy
                        or (current_time - pooled_conn.created_at) > self._max_connection_age
                ):
                    expired_conn_ids.append(conn_id)

            for conn_id in expired_conn_ids:
                pooled_conn = self._connection_pool.pop(conn_id)
                try:
                    await pooled_conn.connection.close()
                    self._metrics.active_connections -= 1
                    logger.debug(f"Closed and removed expired/unhealthy connection: {conn_id}")
                except Exception as e:
                    logger.error(f"Error closing connection {conn_id} during cleanup: {e}")

        # Cleanup expired channels
        if self._enable_channel_pooling:
            async with self._channel_pool_lock:
                expired_channel_ids = []
                for channel_id, pooled_channel in list(self._channel_pool.items()):  # Use list for safe iteration
                    if pooled_channel.is_expired or not pooled_channel.is_healthy:
                        expired_channel_ids.append(channel_id)

                for channel_id in expired_channel_ids:
                    pooled_channel = self._channel_pool.pop(channel_id)
                    try:
                        await pooled_channel.channel.close()
                        self._metrics.active_channels -= 1
                        logger.debug(f"Closed and removed expired/unhealthy channel: {channel_id}")
                    except Exception as e:
                        logger.error(f"Error closing channel {channel_id} during cleanup: {e}")

    async def _create_connection(self) -> AbstractRobustConnection:
        """
        Creates a new RabbitMQ connection.

        Raises:
            AMQPException: If the circuit breaker is open or connection fails.
        """
        if self._circuit_breaker.check_circuit_breaker():
            logger.warning("Connection creation blocked: Circuit breaker is open.")
            raise AMQPException("Circuit breaker is open, preventing new connections.")

        try:
            logger.debug(f"Attempting to create a new RabbitMQ connection to {self._connection_url}...")
            conn = await self._factory(self._connection_url, heartbeat=self._heartbeat)

            self._metrics.total_connections_created += 1
            self._metrics.active_connections += 1
            self._circuit_breaker.record_success()
            logger.info("Successfully created new RabbitMQ connection.")
            return conn
        except Exception as e:
            self._metrics.connection_errors += 1
            self._metrics.last_error_time = time.time()
            self._metrics.last_error_message = str(e)
            self._circuit_breaker.record_failure()
            logger.error(f"Failed to create RabbitMQ connection: {e}", exc_info=True)
            raise

    async def _acquire_connection(self) -> PooledConnection:
        """
        Acquires a connection from the pool or creates a new one if necessary.
        """
        async with self._connection_pool_lock:
            # Try to find an existing healthy connection
            for conn_id, pooled_conn in list(self._connection_pool.items()):
                if pooled_conn.is_healthy and not pooled_conn.is_expired:
                    pooled_conn.mark_used()
                    logger.debug(f"Reusing existing connection from pool: {conn_id}")
                    return pooled_conn
                else:
                    # Remove unhealthy or expired connections from the pool
                    self._connection_pool.pop(conn_id)
                    try:
                        if not pooled_conn.connection.is_closed:
                            await pooled_conn.connection.close()
                        self._metrics.active_connections -= 1
                        logger.debug(f"Removed unhealthy/expired connection {conn_id} from pool.")
                    except Exception as e:
                        logger.error(f"Error closing unhealthy connection {conn_id}: {e}")

            # If no healthy connection found, create a new one if allowed by pool size
            if len(self._connection_pool) < self._max_conn_pool_size:
                connection = await self._create_connection()
                conn_id = f"conn_{id(connection)}"  # Unique ID for the pooled connection
                pooled_conn = PooledConnection(connection=connection)
                self._connection_pool[conn_id] = pooled_conn
                logger.debug(f"Added new connection to pool: {conn_id}")
                return pooled_conn
            else:
                logger.warning("Connection pool exhausted: no healthy connections available and max pool size reached.")
                raise AMQPException("Connection pool exhausted and no healthy connections available")

    async def _release_connection(self, pooled_conn: PooledConnection):
        """
        Releases a connection back to the pool.

        In this pooling strategy, connections are not physically closed on release
        but are kept in the pool for reuse. Cleanup happens via a background task.
        """
        pooled_conn.mark_used()  # Update usage
        logger.debug(f"Connection {id(pooled_conn.connection)} marked as released to pool.")
        # Actual cleanup happens in _cleanup_expired_resources

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AbstractRobustConnection, None]:
        """
        Provides an AMQP connection from the pool.

        Uses an async context manager to acquire and release connections
        from the internal pool, respecting connection limits.

        Yields:
            AbstractRobustConnection: An active connection object.
        """
        await self._connection_semaphore.acquire()
        pooled_conn: Optional[PooledConnection] = None

        try:
            pooled_conn = await self._acquire_connection()
            yield pooled_conn.connection
        except Exception as e:
            logger.warning(f"Failed to get connection: {e}")
            raise
        finally:
            if pooled_conn:
                await self._release_connection(pooled_conn)
            self._connection_semaphore.release()
            logger.debug("Connection semaphore released.")

    async def _create_channel(self, connection: AbstractRobustConnection,
                              prefetch_count: int = 1) -> AbstractRobustChannel:
        """
        Creates a new channel on a given connection and sets QoS.
        """
        try:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=prefetch_count)

            self._metrics.total_channels_created += 1
            self._metrics.active_channels += 1
            logger.debug(f"Created new channel on connection {id(connection)} with prefetch: {prefetch_count}")
            return channel
        except Exception as e:
            self._metrics.channel_errors += 1
            self._metrics.last_error_time = time.time()
            self._metrics.last_error_message = str(e)
            logger.error(f"Failed to create channel: {e}", exc_info=True)
            raise

    @asynccontextmanager
    async def get_channel(self, prefetch_count: int = 1) -> AsyncGenerator[AbstractRobustChannel, None]:
        """
        Provides an AMQP channel from the pool or creates a new one.

        If channel pooling is disabled, a new channel is created and closed per use.
        Otherwise, it manages channels from an internal pool, respecting limits.

        Args:
            prefetch_count (int): The maximum number of messages to prefetch.

        Yields:
            AbstractRobustChannel: An active channel object.
        """
        if not self._enable_channel_pooling:
            logger.debug("Channel pooling disabled. Creating a new transient channel.")
            async with self.get_connection() as connection:
                channel = await self._create_channel(connection, prefetch_count)
                try:
                    yield channel
                finally:
                    if not channel.is_closed:
                        try:
                            await channel.close()
                            self._metrics.active_channels -= 1
                            logger.debug("Closed transient channel.")
                        except Exception as e:
                            logger.error(f"Error closing transient channel: {e}")
            return

        # Channel pooling logic
        await self._channel_semaphore.acquire()
        pooled_channel: Optional[PooledChannel] = None

        try:
            async with self._channel_pool_lock:
                # Find an available healthy channel
                for channel_id, pooled_ch in list(self._channel_pool.items()):
                    if (
                            pooled_ch.is_healthy
                            and not pooled_ch.reserved
                            and not pooled_ch.is_expired
                    ):
                        pooled_ch.reserved = True  # Mark as in use
                        pooled_ch.mark_used()
                        pooled_channel = pooled_ch
                        logger.debug(f"Reusing channel from pool: {channel_id}")
                        break

                # Create a new channel if none available or healthy
                if not pooled_channel:
                    if len(self._channel_pool) >= self._max_channel_pool_size:
                        logger.warning("Channel pool exhausted: max channel pool size reached.")
                        raise AMQPException("Channel pool exhausted")

                    async with self.get_connection() as connection:
                        channel = await self._create_channel(connection, prefetch_count)
                        channel_id = f"ch_{id(channel)}"
                        conn_id = f"conn_{id(connection)}"  # Associate channel with its connection
                        pooled_channel = PooledChannel(
                            channel=channel,
                            connection_id=conn_id,
                            reserved=True  # Mark as in use immediately
                        )
                        self._channel_pool[channel_id] = pooled_channel
                        logger.debug(f"Created and added new channel to pool: {channel_id}")

            yield pooled_channel.channel

        except Exception as e:
            logger.warning(f"Failed to get channel: {e}")
            raise
        finally:
            if pooled_channel:
                async with self._channel_pool_lock:
                    pooled_channel.reserved = False  # Mark as available for reuse
            self._channel_semaphore.release()
            logger.debug("Channel semaphore released.")

    @asynccontextmanager
    async def get_dedicated_channel(self, prefetch_count: int = 1) -> AsyncIterator[AbstractRobustChannel]:
        """
        Provides a dedicated, long-lived channel, typically for consumers.

        Channels obtained this way are not released back to the general pool
        but are managed separately and persist for the lifetime of the calling task.
        """
        channel_key = f"dedicated_ch_{asyncio.current_task().get_name() or id(asyncio.current_task())}"

        async with self._dedicated_channels_lock:
            pooled_channel = self._dedicated_channels.get(channel_key)

            if pooled_channel and pooled_channel.is_healthy:
                pooled_channel.mark_used()
                logger.debug(f"Reusing dedicated channel: {channel_key}")
                yield pooled_channel.channel
                return
            elif pooled_channel:
                # Dedicated channel found but unhealthy, close and remove it
                logger.warning(f"Dedicated channel {channel_key} found unhealthy. Closing and recreating.")
                del self._dedicated_channels[channel_key]
                try:
                    if not pooled_channel.channel.is_closed:
                        await pooled_channel.channel.close()
                    self._metrics.active_channels -= 1
                except Exception as e:
                    logger.error(f"Error closing unhealthy dedicated channel {channel_key}: {e}")

            # Create a new dedicated channel
            async with self.get_connection() as connection:
                channel = await self._create_channel(connection, prefetch_count)
                conn_id = f"conn_{id(connection)}"
                pooled_channel = PooledChannel(
                    channel=channel,
                    connection_id=conn_id
                )
                self._dedicated_channels[channel_key] = pooled_channel
                logger.info(f"Created new dedicated channel: {channel_key}")

            try:
                yield channel
            finally:
                # Dedicated channels are kept alive for the task's lifetime.
                # They are closed during manager shutdown or if found unhealthy on next request.
                pass

    def get_metrics(self) -> ConnectionMetrics:
        """
        Retrieves the current operational metrics for the connection manager.

        Returns:
            ConnectionMetrics: An object containing connection and channel usage statistics.
        """
        return self._metrics

    async def health_check(self) -> HealthMetrics:
        """
        Performs a comprehensive health check of the RabbitMQ connection manager.

        Includes checks on connection pool status, circuit breaker state, and a
        test connection attempt.

        Returns:
            HealthMetrics: An object detailing the current health status, metrics, and any errors.
        """
        health_status = HealthMetrics(
            status="healthy",
            connection_pool_size=len(self._connection_pool),
            channel_pool_size=len(self._channel_pool),
            dedicated_channels=len(self._dedicated_channels),
            circuit_breaker_open=self._circuit_breaker.circuit_breaker_open,
            circuit_breaker_failures=self._circuit_breaker.circuit_breaker_failures,
            circuit_breaker_last_failure=self._circuit_breaker.circuit_breaker_last_failure,
            metrics=self._metrics,
            errors=[]
        )

        # Attempt to get a connection to verify underlying connectivity
        try:
            async with self.get_connection() as conn:
                if not await HealthChecker.check_connection_health(conn):
                    health_status.status = "unhealthy"
                    health_status.errors.append("Failed basic connection health check.")
                else:
                    logger.debug("Health check: Successfully acquired and tested a connection.")
        except Exception as e:
            health_status.status = "unhealthy"
            health_status.errors.append(f"Connection test failed during health check: {str(e)}")
            logger.warning(f"Health check encountered connection error: {e}")

        # Check circuit breaker status
        if self._circuit_breaker.circuit_breaker_open:
            health_status.status = "degraded"  # Or "unhealthy" depending on severity
            health_status.errors.append("Circuit breaker is open, operations may be limited.")

        return health_status

    async def close(self) -> None:
        """
        Closes all managed connections and channels, and stops background tasks.

        Ensures a graceful shutdown by closing all resources in a controlled manner.
        """
        if self._closed:
            logger.info("Connection Manager is already closed.")
            return

        logger.info("Initiating RabbitMQ Connection Manager shutdown...")
        self._closed = True

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
                logger.debug("Background cleanup task cancelled successfully.")
            except asyncio.CancelledError:
                pass  # Expected cancellation during shutdown

        # Close dedicated channels
        async with self._dedicated_channels_lock:
            for channel_key, pooled_channel in list(self._dedicated_channels.items()):
                try:
                    if not pooled_channel.channel.is_closed:
                        await pooled_channel.channel.close()
                    logger.debug(f"Closed dedicated channel: {channel_key}")
                except Exception as e:
                    logger.error(f"Error closing dedicated channel {channel_key} during shutdown: {e}")
            self._dedicated_channels.clear()
            self._metrics.active_channels = max(0, self._metrics.active_channels - len(self._dedicated_channels))

        # Close pooled channels
        if self._enable_channel_pooling:
            async with self._channel_pool_lock:
                for channel_id, pooled_channel in list(self._channel_pool.items()):
                    try:
                        if not pooled_channel.channel.is_closed:
                            await pooled_channel.channel.close()
                        logger.debug(f"Closed pooled channel: {channel_id}")
                    except Exception as e:
                        logger.error(f"Error closing pooled channel {channel_id} during shutdown: {e}")
                self._channel_pool.clear()
                self._metrics.active_channels = 0  # All pooled channels are now closed

        # Close pooled connections
        async with self._connection_pool_lock:
            for conn_id, pooled_conn in list(self._connection_pool.items()):
                try:
                    if not pooled_conn.connection.is_closed:
                        await pooled_conn.connection.close()
                    logger.debug(f"Closed pooled connection: {conn_id}")
                except Exception as e:
                    logger.error(f"Error closing pooled connection {conn_id} during shutdown: {e}")
            self._connection_pool.clear()
            self._metrics.active_connections = 0  # All pooled connections are now closed

        logger.info("RabbitMQ Connection Manager shut down complete.")
