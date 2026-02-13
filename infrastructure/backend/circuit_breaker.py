"""
Circuit Breaker Pattern Implementation for Backend API Calls
Prevents cascading failures when external APIs are unavailable
"""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from constants import (
    CB_DEFAULT_FAILURE_THRESHOLD,
    CB_DEFAULT_HALF_OPEN_MAX_CALLS,
    CB_DEFAULT_LATENCY,
    CB_DEFAULT_MONITORING_WINDOW,
    CB_DEFAULT_SUCCESS_RATE,
    CB_DEFAULT_SUCCESS_THRESHOLD,
    CB_DEFAULT_TIMEOUT_SECONDS,
    CB_ERROR_TYPE_UNKNOWN,
    CB_METRIC_AVG_LATENCY_MS,
    CB_METRIC_FAILURES,
    CB_METRIC_LAST_FAILURE,
    CB_METRIC_LAST_SUCCESS,
    CB_METRIC_RATE_LIMIT_HITS,
    CB_METRIC_STATE,
    CB_METRIC_SUCCESS_RATE,
    CB_METRIC_SUCCESSES,
    CB_METRIC_TOTAL_CALLS,
    CB_METRIC_TOTAL_ERRORS,
    CB_MONITORING_WINDOW_SECONDS,
    CB_MSG_CALL_BLOCKED,
    CB_MSG_CIRCUIT_CLOSED,
    CB_MSG_CIRCUIT_HALF_OPEN,
    CB_MSG_CIRCUIT_OPENED,
    CB_MSG_FAILURE_RECORDED,
    CB_MSG_SUCCESS_RECORDED,
    CB_STATE_CLOSED,
    CB_STATE_HALF_OPEN,
    CB_STATE_OPEN,
)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = CB_STATE_CLOSED  # Normal operation
    OPEN = CB_STATE_OPEN  # Circuit tripped, fail fast
    HALF_OPEN = CB_STATE_HALF_OPEN  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = CB_DEFAULT_FAILURE_THRESHOLD
    success_threshold: int = CB_DEFAULT_SUCCESS_THRESHOLD
    timeout_seconds: float = CB_DEFAULT_TIMEOUT_SECONDS
    monitoring_window: int = CB_DEFAULT_MONITORING_WINDOW
    half_open_max_calls: int = CB_DEFAULT_HALF_OPEN_MAX_CALLS


@dataclass
class APIEndpoint:
    """Track metrics for a single API endpoint"""

    name: str
    failures: int = 0
    successes: int = 0
    last_failure_time: float = CB_DEFAULT_LATENCY
    last_success_time: float = CB_DEFAULT_LATENCY
    total_calls: int = 0
    total_errors: int = 0
    total_latency_ms: float = CB_DEFAULT_LATENCY
    rate_limit_hits: int = 0
    state: CircuitState = CircuitState.CLOSED

    def record_success(self, latency_ms: float = CB_DEFAULT_LATENCY):
        """Record a successful API call"""
        self.successes += 1
        self.total_calls += 1
        self.total_latency_ms += latency_ms
        self.last_success_time = time.time()

    def record_failure(self, error_type: str = CB_ERROR_TYPE_UNKNOWN):
        """Record a failed API call"""
        self.failures += 1
        self.total_calls += 1
        self.total_errors += 1
        self.last_failure_time = time.time()

    def record_rate_limit(self):
        """Record a rate limit hit"""
        self.rate_limit_hits += 1
        self.failures += 1
        self.total_calls += 1
        self.last_failure_time = time.time()

    def get_success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        if self.total_calls == 0:
            return CB_DEFAULT_SUCCESS_RATE
        return self.successes / self.total_calls

    def get_average_latency_ms(self) -> float:
        """Calculate average latency in milliseconds"""
        if self.total_calls == 0:
            return CB_DEFAULT_LATENCY
        return self.total_latency_ms / self.total_calls

    def should_open(self, failure_threshold: int) -> bool:
        """Check if circuit should open based on failures"""
        recent_failures = self._get_recent_failures()
        return recent_failures >= failure_threshold

    def _get_recent_failures(self) -> int:
        """Count failures within monitoring window"""
        if self.last_failure_time == CB_DEFAULT_LATENCY:
            return 0

        time_since_failure = time.time() - self.last_failure_time
        if time_since_failure > CB_MONITORING_WINDOW_SECONDS:
            return 0

        return self.failures


class CircuitBreakerManager:
    """
    Manages circuit breakers for multiple API sources

    Usage:
        cb_manager = CircuitBreakerManager()

        # Check if API is available
        if cb_manager.can_call('yahoo_finance'):
            try:
                result = call_api()
                cb_manager.record_success('yahoo_finance', latency_ms=100)
            except Exception as err:
                cb_manager.record_failure('yahoo_finance', str(err))
        else:
            print("Circuit is OPEN for yahoo_finance")
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._endpoints: Dict[str, APIEndpoint] = {}
        self._lock = threading.RLock()

        # Initialize default API sources
        self._init_default_sources()

    def _init_default_sources(self):
        """Initialize circuit breakers for known API sources"""
        default_sources = ["yahoo_finance", "alpha_vantage", "polygon", "alpaca"]

        with self._lock:
            for source in default_sources:
                if source not in self._endpoints:
                    self._endpoints[source] = APIEndpoint(name=source)

    def register_endpoint(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ):
        """Register a new API endpoint with the circuit breaker"""
        with self._lock:
            if name not in self._endpoints:
                endpoint_config = config or self.config
                self._endpoints[name] = APIEndpoint(name=name)

    def can_call(self, endpoint_name: str) -> bool:
        """
        Check if an API call is allowed based on circuit state

        Args:
            endpoint_name: Name of the API endpoint

        Returns:
            True if call is allowed, False if circuit is OPEN
        """
        with self._lock:
            if endpoint_name not in self._endpoints:
                # Unknown endpoint - allow by default
                self._endpoints[endpoint_name] = APIEndpoint(name=endpoint_name)
                return True

            endpoint = self._endpoints[endpoint_name]

            # Check state transitions
            if endpoint.state == CircuitState.OPEN:
                # Check if timeout has passed - transition to HALF_OPEN
                if (
                    time.time() - endpoint.last_failure_time
                    > self.config.timeout_seconds
                ):
                    endpoint.state = CircuitState.HALF_OPEN
                    print(
                        f"CircuitBreaker: {endpoint_name} transitioning OPEN → HALF_OPEN"
                    )
                    return True
                return False

            elif endpoint.state == CircuitState.HALF_OPEN:
                # In half_open state, allow limited calls
                return True

            # CLOSED state - allow calls
            return True

    def record_success(self, endpoint_name: str, latency_ms: float = 0):
        """Record a successful API call"""
        with self._lock:
            if endpoint_name not in self._endpoints:
                return

            endpoint = self._endpoints[endpoint_name]
            endpoint.record_success(latency_ms)

            # State transitions
            if endpoint.state == CircuitState.HALF_OPEN:
                # Check if we should close the circuit
                if endpoint.successes >= self.config.success_threshold:
                    endpoint.state = CircuitState.CLOSED
                    endpoint.failures = 0  # Reset failure count
                    print(
                        f"CircuitBreaker: {endpoint_name} transitioning HALF_OPEN → CLOSED"
                    )

            # In CLOSED state, also check if we should open
            elif endpoint.state == CircuitState.CLOSED:
                if endpoint.should_open(self.config.failure_threshold):
                    endpoint.state = CircuitState.OPEN
                    print(
                        f"CircuitBreaker: {endpoint_name} transitioning CLOSED → OPEN"
                    )

    def record_failure(self, endpoint_name: str, error_type: str = "unknown"):
        """Record a failed API call"""
        with self._lock:
            if endpoint_name not in self._endpoints:
                self._endpoints[endpoint_name] = APIEndpoint(name=endpoint_name)

            endpoint = self._endpoints[endpoint_name]
            endpoint.record_failure(error_type)

            # State transitions
            if endpoint.state == CircuitState.HALF_OPEN:
                # Any failure in half_open opens the circuit again
                endpoint.state = CircuitState.OPEN
                print(f"CircuitBreaker: {endpoint_name} failure in HALF_OPEN → OPEN")

            elif endpoint.state == CircuitState.CLOSED:
                # Check if we should open the circuit
                if endpoint.should_open(self.config.failure_threshold):
                    endpoint.state = CircuitState.OPEN
                    print(f"CircuitBreaker: {endpoint_name} too many failures → OPEN")

    def record_rate_limit(self, endpoint_name: str):
        """Record a rate limit hit for an endpoint"""
        with self._lock:
            if endpoint_name not in self._endpoints:
                self._endpoints[endpoint_name] = APIEndpoint(name=endpoint_name)

            endpoint = self._endpoints[endpoint_name]
            endpoint.record_rate_limit()

            # Rate limit immediately opens the circuit
            if endpoint.state == CircuitState.CLOSED:
                endpoint.state = CircuitState.OPEN
                print(f"CircuitBreaker: {endpoint_name} rate limited → OPEN")

    def force_open(self, endpoint_name: str):
        """Manually open a circuit (for maintenance, etc.)"""
        with self._lock:
            if endpoint_name in self._endpoints:
                self._endpoints[endpoint_name].state = CircuitState.OPEN
            else:
                endpoint = APIEndpoint(name=endpoint_name, state=CircuitState.OPEN)
                self._endpoints[endpoint_name] = endpoint
            print(f"CircuitBreaker: {endpoint_name} forcibly OPENED")

    def force_close(self, endpoint_name: str):
        """Manually close a circuit"""
        with self._lock:
            if endpoint_name in self._endpoints:
                self._endpoints[endpoint_name].state = CircuitState.CLOSED
                self._endpoints[endpoint_name].failures = 0
            print(f"CircuitBreaker: {endpoint_name} forcibly CLOSED")

    def reset(self, endpoint_name: Optional[str] = None):
        """Reset circuit breaker for an endpoint or all endpoints"""
        with self._lock:
            if endpoint_name:
                if endpoint_name in self._endpoints:
                    self._endpoints[endpoint_name] = APIEndpoint(name=endpoint_name)
            else:
                # Reset all
                for name in list(self._endpoints.keys()):
                    self._endpoints[name] = APIEndpoint(name=name)
            print(
                f"CircuitBreaker: Reset {'all' if endpoint_name is None else endpoint_name}"
            )

    def get_state(self, endpoint_name: str) -> Dict:
        """Get the current state of an endpoint"""
        with self._lock:
            if endpoint_name not in self._endpoints:
                return {"state": "unknown", "error": "Endpoint not registered"}

            endpoint = self._endpoints[endpoint_name]
            return {
                "state": endpoint.state.value,
                "failures": endpoint.failures,
                "successes": endpoint.successes,
                "total_calls": endpoint.total_calls,
                "success_rate": f"{endpoint.get_success_rate() * 100:.1f}%",
                "avg_latency_ms": f"{endpoint.get_average_latency_ms():.1f}",
                "rate_limit_hits": endpoint.rate_limit_hits,
                "last_failure": endpoint.last_failure_time,
                "last_success": endpoint.last_success_time,
            }

    def get_all_states(self) -> Dict[str, Dict]:
        """Get states for all registered endpoints"""
        with self._lock:
            states = {}
            for name, endpoint in self._endpoints.items():
                states[name] = {
                    "state": endpoint.state.value,
                    "failures": endpoint.failures,
                    "successes": endpoint.successes,
                    "success_rate": f"{endpoint.get_success_rate() * 100:.1f}%",
                }
            return states

    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        with self._lock:
            total_calls = sum(
                endpoint.total_calls for endpoint in self._endpoints.values()
            )
            total_errors = sum(
                endpoint.total_errors for endpoint in self._endpoints.values()
            )
            total_latency = sum(
                endpoint.total_latency_ms for endpoint in self._endpoints.values()
            )
            open_circuits = sum(
                1
                for endpoint in self._endpoints.values()
                if endpoint.state == CircuitState.OPEN
            )

            return {
                "total_endpoints": len(self._endpoints),
                "total_calls": total_calls,
                "total_errors": total_errors,
                "overall_success_rate": (
                    f"{(1 - total_errors/total_calls * 100) if total_calls > 0 else 100:.1f}%"
                    if total_calls > 0
                    else "N/A"
                ),
                "average_latency_ms": (
                    f"{total_latency / total_calls:.1f}" if total_calls > 0 else "N/A"
                ),
                "open_circuits": open_circuits,
                "closed_circuits": len(self._endpoints) - open_circuits,
                "endpoints": self.get_all_states(),
            }

    def get_health_report(self) -> Dict:
        """Get a health report suitable for monitoring"""
        with self._lock:
            healthy = []
            degraded = []
            unhealthy = []

            for name, endpoint in self._endpoints.items():
                status = {
                    "name": name,
                    "state": endpoint.state.value,
                    "success_rate": endpoint.get_success_rate(),
                    "avg_latency_ms": endpoint.get_average_latency_ms(),
                }

                if endpoint.state == CircuitState.OPEN:
                    unhealthy.append(status)
                elif (
                    endpoint.state == CircuitState.HALF_OPEN
                    or endpoint.get_success_rate() < 0.9
                ):
                    degraded.append(status)
                else:
                    healthy.append(status)

            return {
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "health_score": len(healthy) / max(len(self._endpoints), 1),
            }


# Singleton instance for application-wide use
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker() -> CircuitBreakerManager:
    """Get or create the singleton circuit breaker manager"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


def circuit_breaker_decorator(endpoint_name: str, timeout_seconds: float = 30.0):
    """
    Decorator to add circuit breaker protection to a function

    Usage:
        @circuit_breaker_decorator('my_api', timeout_seconds=30.0)
        def call_api():
            # Your API call here
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            cb = get_circuit_breaker()

            if not cb.can_call(endpoint_name):
                raise CircuitOpenError(f"Circuit is OPEN for {endpoint_name}")

            import time

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                cb.record_success(endpoint_name, latency_ms)
                return result
            except Exception as err:
                cb.record_failure(endpoint_name, type(err).__name__)
                raise

        return wrapper

    return decorator


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""

    pass
