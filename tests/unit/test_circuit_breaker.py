"""
Unit Tests for Circuit Breaker Module
Tests the circuit breaker pattern implementation for API resilience
"""

import sys
import time
import pytest

# Add backend path for imports
sys.path.insert(0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/backend")

from circuit_breaker import (
    CircuitState,
    CircuitBreakerConfig,
    APIEndpoint,
    CircuitBreakerManager,
    get_circuit_breaker,
    CircuitOpenError,
)


class TestCircuitState:
    """Test CircuitState enum values"""

    def test_circuit_states_exist(self):
        """Verify all circuit states are defined"""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestAPIEndpoint:
    """Test APIEndpoint dataclass functionality"""

    def test_endpoint_creation(self):
        """Test default endpoint initialization"""
        endpoint = APIEndpoint(name="test_api")

        assert endpoint.name == "test_api"
        assert endpoint.failures == 0
        assert endpoint.successes == 0
        assert endpoint.total_calls == 0
        assert endpoint.state == CircuitState.CLOSED
        assert endpoint.rate_limit_hits == 0

    def test_record_success(self):
        """Test recording successful API calls"""
        endpoint = APIEndpoint(name="test_api")
        endpoint.record_success(latency_ms=100.0)

        assert endpoint.successes == 1
        assert endpoint.total_calls == 1
        assert endpoint.total_latency_ms == 100.0

    def test_record_failure(self):
        """Test recording failed API calls"""
        endpoint = APIEndpoint(name="test_api")
        endpoint.record_failure("ConnectionError")

        assert endpoint.failures == 1
        assert endpoint.total_calls == 1
        assert endpoint.total_errors == 1

    def test_record_rate_limit(self):
        """Test recording rate limit hits"""
        endpoint = APIEndpoint(name="test_api")
        endpoint.record_rate_limit()

        assert endpoint.rate_limit_hits == 1
        assert endpoint.failures == 1
        assert endpoint.total_calls == 1

    def test_get_success_rate_empty(self):
        """Test success rate calculation with no calls"""
        endpoint = APIEndpoint(name="test_api")

        rate = endpoint.get_success_rate()
        assert rate == 1.0  # 100% when no calls

    def test_get_success_rate_with_data(self):
        """Test success rate calculation with calls"""
        endpoint = APIEndpoint(name="test_api")
        endpoint.record_success()
        endpoint.record_success()
        endpoint.record_failure()

        rate = endpoint.get_success_rate()
        assert rate == 2.0 / 3.0

    def test_get_average_latency_empty(self):
        """Test average latency calculation with no calls"""
        endpoint = APIEndpoint(name="test_api")

        avg = endpoint.get_average_latency_ms()
        assert avg == 0.0

    def test_get_average_latency_with_data(self):
        """Test average latency calculation with calls"""
        endpoint = APIEndpoint(name="test_api")
        endpoint.record_success(latency_ms=100.0)
        endpoint.record_success(latency_ms=200.0)

        avg = endpoint.get_average_latency_ms()
        assert avg == 150.0


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 30.0
        assert config.monitoring_window == 60
        assert config.half_open_max_calls == 3

    def test_custom_config(self):
        """Test custom configuration values"""
        config = CircuitBreakerConfig(
            failure_threshold=10, success_threshold=3, timeout_seconds=60.0
        )

        assert config.failure_threshold == 10
        assert config.success_threshold == 3
        assert config.timeout_seconds == 60.0


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager class"""

    def setup_method(self):
        """Reset circuit breaker and singleton before each test"""
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

    def teardown_method(self):
        """Clean up after each test"""
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

    def test_manager_creation(self):
        """Test manager initialization"""
        manager = CircuitBreakerManager()

        assert manager is not None
        assert len(manager._endpoints) >= 4  # Default sources

    def test_can_call_closed_circuit(self):
        """Test can_call returns True for closed circuit"""
        manager = CircuitBreakerManager()

        result = manager.can_call("yahoo_finance")
        assert result is True

    def test_can_call_unknown_endpoint(self):
        """Test can_call returns True for unknown endpoint"""
        manager = CircuitBreakerManager()

        result = manager.can_call("unknown_api")
        assert result is True

    def test_record_success_closed_circuit(self):
        """Test recording success on closed circuit"""
        manager = CircuitBreakerManager()

        manager.record_success("yahoo_finance", latency_ms=50.0)

        state = manager.get_state("yahoo_finance")
        assert state["successes"] >= 1

    def test_record_failure_opens_circuit(self):
        """Test circuit opens after threshold failures"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

        manager = CircuitBreakerManager(
            config=CircuitBreakerConfig(failure_threshold=3)
        )

        # Record 3 failures on a new endpoint
        for i in range(3):
            manager.record_failure("test_endpoint", "ConnectionError")

        state = manager.get_state("test_endpoint")
        assert state["state"] == "open"

    def test_can_call_open_circuit_returns_false(self):
        """Test can_call returns False when circuit is open"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

        manager = CircuitBreakerManager(
            config=CircuitBreakerConfig(failure_threshold=1)
        )

        # Force a failure to open circuit on a new endpoint
        manager.record_failure("test_endpoint", "ConnectionError")

        # Verify state is open
        state = manager.get_state("test_endpoint")
        assert state["state"] == "open"

        # can_call should return False
        result = manager.can_call("test_endpoint")
        assert result is False

    def test_circuit_transition_open_to_half_open(self):
        """Test circuit transitions from OPEN to HALF_OPEN after timeout"""
        # Create a standalone manager with very short timeout
        # NOT using the singleton
        config = CircuitBreakerConfig(timeout_seconds=0.01, failure_threshold=3)
        manager = CircuitBreakerManager(config=config)

        endpoint_name = "test_transition_unique"

        # Open the circuit by recording 3 failures
        for i in range(3):
            manager.record_failure(endpoint_name, "ConnectionError")

        state = manager.get_state(endpoint_name)
        assert state["state"] == "open", f"Expected OPEN, got {state['state']}"

        # Wait for timeout to expire
        time.sleep(0.05)

        # can_call should return True and transition to half_open
        result = manager.can_call(endpoint_name)
        assert result is True

        state = manager.get_state(endpoint_name)
        assert state["state"] == "half_open"

    def test_get_health_report(self):
        """Test health report generation"""
        # Create a standalone manager
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config=config)

        # Make one endpoint unhealthy
        manager.force_open("unhealthy_api")

        report = manager.get_health_report()

        assert "healthy" in report
        assert "degraded" in report
        assert "unhealthy" in report
        assert "health_score" in report
        # Check that unhealthy_api is in unhealthy list
        unhealthy_count = len(report["unhealthy"])
        assert (
            unhealthy_count >= 1
        ), f"Expected at least 1 unhealthy API, got {unhealthy_count}"

    def test_record_success_half_open_closes_circuit(self):
        """Test circuit closes after successes in HALF_OPEN"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

        manager = CircuitBreakerManager(
            config=CircuitBreakerConfig(
                failure_threshold=1, success_threshold=2, timeout_seconds=0.01
            )
        )

        # Open the circuit
        manager.record_failure("test_endpoint", "ConnectionError")

        # Wait for timeout
        time.sleep(0.05)

        # Transition to half_open
        result = manager.can_call("test_endpoint")
        assert result is True

        state = manager.get_state("test_endpoint")
        assert state["state"] == "half_open"

        # Record 2 successes to close the circuit
        manager.record_success("test_endpoint", 50.0)
        manager.record_success("test_endpoint", 50.0)

        state = manager.get_state("test_endpoint")
        assert state["state"] == "closed"
        assert state["failures"] == 0  # Failures reset on close

    def test_record_failure_half_open_reopens(self):
        """Test circuit reopens on failure in HALF_OPEN"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

        manager = CircuitBreakerManager(
            config=CircuitBreakerConfig(
                failure_threshold=1, success_threshold=3, timeout_seconds=0.01
            )
        )

        # Open the circuit
        manager.record_failure("test_endpoint", "ConnectionError")

        # Wait for timeout
        time.sleep(0.05)

        # Transition to half_open
        manager.can_call("test_endpoint")

        # Record failure in half_open
        manager.record_failure("test_endpoint", "ConnectionError")

        state = manager.get_state("test_endpoint")
        assert state["state"] == "open"

    def test_record_rate_limit_opens_circuit(self):
        """Test rate limit immediately opens circuit"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

        manager = CircuitBreakerManager()

        manager.record_rate_limit("test_endpoint")

        state = manager.get_state("test_endpoint")
        assert state["state"] == "open"

    def test_force_open(self):
        """Test manually forcing circuit open"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None
        manager = CircuitBreakerManager()

        # Force open
        manager.force_open("test_endpoint")

        state = manager.get_state("test_endpoint")
        assert state["state"] == "open"

        # can_call should return False (no timeout passed yet)
        result = manager.can_call("test_endpoint")
        # After waiting, it transitions to half_open
        state = manager.get_state("test_endpoint")
        assert state["state"] in ["open", "half_open"]

    def test_force_close(self):
        """Test manually forcing circuit closed"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None
        manager = CircuitBreakerManager()

        manager.force_open("test_endpoint")
        manager.force_close("test_endpoint")

        result = manager.can_call("test_endpoint")
        assert result is True

        state = manager.get_state("test_endpoint")
        assert state["state"] == "closed"

    def test_reset_single_endpoint(self):
        """Test resetting a single endpoint"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None
        manager = CircuitBreakerManager()

        manager.record_failure("test_endpoint", "ConnectionError")
        manager.reset("test_endpoint")

        state = manager.get_state("test_endpoint")
        assert state["state"] == "closed"
        assert state["failures"] == 0

    def test_reset_all_endpoints(self):
        """Test resetting all endpoints"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None
        manager = CircuitBreakerManager()

        manager.record_failure("yahoo_finance", "ConnectionError")
        manager.record_failure("alpha_vantage", "ConnectionError")

        manager.reset()

        for name in manager._endpoints:
            state = manager.get_state(name)
            assert state["state"] == "closed"

    def test_get_all_states(self):
        """Test getting all endpoint states"""
        manager = CircuitBreakerManager()

        states = manager.get_all_states()

        assert "yahoo_finance" in states
        assert "alpha_vantage" in states
        assert "polygon" in states
        assert "alpaca" in states

    def test_get_stats(self):
        """Test getting comprehensive statistics"""
        # Create fresh manager
        global _circuit_breaker_manager
        _circuit_breaker_manager = None
        manager = CircuitBreakerManager()

        manager.record_success("test_endpoint", 100.0)
        manager.record_failure("test_endpoint", "Error")

        stats = manager.get_stats()

        assert "total_endpoints" in stats
        assert "total_calls" in stats
        assert "total_errors" in stats
        assert "open_circuits" in stats

    def test_get_health_report(self):
        """Test health report generation"""
        # Create a standalone manager
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config=config)

        # Make one endpoint unhealthy
        manager.force_open("unhealthy_api")

        report = manager.get_health_report()

        assert "healthy" in report
        assert "degraded" in report
        assert "unhealthy" in report
        assert "health_score" in report
        # Check that unhealthy list has at least 1 entry
        unhealthy_count = len(report["unhealthy"])
        assert (
            unhealthy_count >= 1
        ), f"Expected at least 1 unhealthy API, got {unhealthy_count}"


class TestGetCircuitBreaker:
    """Test get_circuit_breaker singleton function"""

    def setup_method(self):
        """Reset singleton before each test"""
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

    def test_singleton_creation(self):
        """Test singleton is created on first call"""
        global _circuit_breaker_manager
        _circuit_breaker_manager = None

        cb1 = get_circuit_breaker()
        cb2 = get_circuit_breaker()

        assert cb1 is cb2


class TestCircuitOpenError:
    """Test CircuitOpenError exception"""

    def test_error_creation(self):
        """Test error can be created with message"""
        error = CircuitOpenError("Circuit is OPEN for test_api")

        assert str(error) == "Circuit is OPEN for test_api"
        assert isinstance(error, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
