"""
Unit Tests for Lifecycle Manager

Tests the module lifecycle management system including:
- Module registration and unregistration
- Lifecycle hooks (onInit, onShow, onHide, onDestroy)
- Memory leak detection
- Resource cleanup
- Tab switching integration
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import json

# Add frontend path for imports
sys.path.insert(
    0, "/home/ubuntupunk/Projects/stock-analyzer/infrastructure/frontend/modules"
)


class TestLifecycleManagerInitialization:
    """Test LifecycleManager initialization"""

    def test_initialization_creates_empty_state(self):
        """Test LifecycleManager initializes with empty state"""
        from LifecycleManager import LifecycleManager

        eventBus = Mock()
        manager = LifecycleManager(eventBus)

        assert manager.modules.size == 0
        assert manager.activeModule is None
        assert manager.visibilityState == "visible"

    def test_setup_global_error_handlers(self):
        """Test global error handlers are set up"""
        from LifecycleManager import LifecycleManager

        eventBus = Mock()

        with patch("window.addEventListener") as mock_add_listener:
            manager = LifecycleManager(eventBus)

            # Should have set up visibility tracking
            assert mock_add_listener.called


class TestModuleRegistration:
    """Test module registration and unregistration"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_register_module_success(self):
        """Test successful module registration"""
        moduleInstance = Mock()
        hooks = {
            "onInit": Mock(),
            "onShow": Mock(),
            "onHide": Mock(),
            "onDestroy": Mock(),
        }

        self.manager.registerModule("testModule", moduleInstance, hooks)

        assert self.manager.modules.has("testModule")
        moduleInfo = self.manager.modules.get("testModule")
        assert moduleInfo.name == "testModule"
        assert moduleInfo.state == "uninitialized"

    def test_register_module_emits_event(self):
        """Test registration emits event"""
        self.manager.registerModule("testModule", Mock())

        self.eventBus.emit.assert_called_with(
            "lifecycle:moduleRegistered",
            {
                "moduleName": "testModule",
                "timestamp": pytest.approx(Date.now(), abs=1000),
            },
        )

    def test_register_duplicate_module_warns(self):
        """Test registering duplicate module logs warning"""
        self.manager.registerModule("testModule", Mock())

        with patch("console.warn") as mock_warn:
            self.manager.registerModule("testModule", Mock())
            mock_warn.assert_called()

    def test_unregister_module_success(self):
        """Test successful module unregistration"""
        self.manager.registerModule("testModule", Mock())
        self.manager.unregisterModule("testModule")

        assert not self.manager.modules.has("testModule")

    def test_unregister_module_calls_destroy(self):
        """Test unregistering module calls destroy"""
        hooks = {"onDestroy": Mock()}
        self.manager.registerModule("testModule", Mock(), hooks)

        with patch.object(self.manager, "destroyModule") as mock_destroy:
            self.manager.unregisterModule("testModule")
            mock_destroy.assert_called_once_with("testModule")


class TestLifecycleHooks:
    """Test lifecycle hook execution"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_init_module_calls_oninit(self):
        """Test initModule calls onInit hook"""
        onInit = Mock()
        self.manager.registerModule("testModule", Mock(), {"onInit": onInit})

        self.manager.initModule("testModule")

        onInit.assert_called_once()
        moduleInfo = self.manager.modules.get("testModule")
        assert moduleInfo.state == "initialized"

    def test_show_module_calls_onshow(self):
        """Test showModule calls onShow hook"""
        onShow = Mock()
        self.manager.registerModule("testModule", Mock(), {"onShow": onShow})

        self.manager.showModule("testModule")

        onShow.assert_called_once()
        moduleInfo = self.manager.modules.get("testModule")
        assert moduleInfo.state == "visible"

    def test_hide_module_calls_onhide(self):
        """Test hideModule calls onHide hook"""
        onHide = Mock()
        self.manager.registerModule("testModule", Mock(), {"onHide": onHide})
        self.manager.showModule("testModule")  # Must show first

        self.manager.hideModule("testModule")

        onHide.assert_called_once()
        moduleInfo = self.manager.modules.get("testModule")
        assert moduleInfo.state == "hidden"

    def test_destroy_module_calls_ondestroy(self):
        """Test destroyModule calls onDestroy hook"""
        onDestroy = Mock()
        self.manager.registerModule("testModule", Mock(), {"onDestroy": onDestroy})

        self.manager.destroyModule("testModule")

        onDestroy.assert_called_once()
        moduleInfo = self.manager.modules.get("testModule")
        assert moduleInfo.state == "destroyed"

    def test_lifecycle_hook_error_handling(self):
        """Test errors in hooks don't crash"""
        onShow = Mock(side_effect=Exception("Hook error"))
        self.manager.registerModule("testModule", Mock(), {"onShow": onShow})

        # Should not raise
        self.manager.showModule("testModule")

        self.eventBus.emit.assert_any_call(
            "lifecycle:moduleShowError",
            {"moduleName": "testModule", "error": pytest.any, "timestamp": pytest.any},
        )


class TestResourceManagement:
    """Test resource cleanup and management"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_clear_module_resources(self):
        """Test clearing module resources"""
        self.manager.registerModule("testModule", Mock())
        moduleInfo = self.manager.modules.get("testModule")

        # Add some mock resources
        moduleInfo.intervals = [1, 2, 3]
        moduleInfo.timeouts = [4, 5]

        with (
            patch("clearInterval") as mock_clear_interval,
            patch("clearTimeout") as mock_clear_timeout,
        ):
            self.manager.clearModuleResources("testModule")

            assert mock_clear_interval.call_count == 3
            assert mock_clear_timeout.call_count == 2
            assert moduleInfo.intervals == []
            assert moduleInfo.timeouts == []

    def test_pause_module_operations(self):
        """Test pausing module operations"""
        self.manager.registerModule("testModule", Mock())
        moduleInfo = self.manager.modules.get("testModule")
        moduleInfo.intervals = [1, 2]
        moduleInfo.timeouts = [3]

        with patch("clearInterval"), patch("clearTimeout"):
            self.manager.pauseModuleOperations("testModule")
            # Should not throw

    def test_save_and_restore_state(self):
        """Test saving and restoring module state"""
        moduleInstance = Mock()
        moduleInstance.getState = Mock(return_value={"key": "value"})
        moduleInstance.setState = Mock()

        self.manager.registerModule("testModule", moduleInstance)
        self.manager.showModule("testModule")

        # Save state
        self.manager.saveModuleState("testModule")
        moduleInfo = self.manager.modules.get("testModule")
        assert moduleInfo.stateData == {"key": "value"}

        # Restore state
        self.manager.restoreModuleState("testModule")
        moduleInstance.setState.assert_called_once_with({"key": "value"})


class TestMemoryManagement:
    """Test memory leak detection"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_take_memory_snapshot(self):
        """Test taking memory snapshots"""
        with patch("performance.memory", {"usedJSHeapSize": 1000000}):
            self.manager.takeMemorySnapshot("testModule", "beforeShow")

            key = "testModule_beforeShow"
            assert self.manager.memorySnapshots.has(key)
            snapshot = self.manager.memorySnapshots.get(key)
            assert snapshot["usedJSHeapSize"] == 1000000

    def test_detect_memory_leak(self):
        """Test memory leak detection"""
        # Setup snapshots with large increase
        self.manager.memorySnapshots.set(
            "testModule_beforeHide",
            {"usedJSHeapSize": 1000000, "timestamp": Date.now()},
        )
        self.manager.memorySnapshots.set(
            "testModule_afterHide",
            {
                "usedJSHeapSize": 12000000,  # 11MB increase
                "timestamp": Date.now(),
            },
        )

        self.manager.registerModule("testModule", Mock())

        with patch("console.warn") as mock_warn:
            self.manager.detectMemoryLeak("testModule")

            # Should warn about potential leak (>10MB)
            mock_warn.assert_called()
            args = mock_warn.call_args[0]
            assert "Potential memory leak" in args[0]

    def test_no_memory_leak_small_increase(self):
        """Test no warning for small memory increase"""
        self.manager.memorySnapshots.set(
            "testModule_beforeHide",
            {"usedJSHeapSize": 1000000, "timestamp": Date.now()},
        )
        self.manager.memorySnapshots.set(
            "testModule_afterHide",
            {
                "usedJSHeapSize": 2000000,  # 1MB increase - normal
                "timestamp": Date.now(),
            },
        )

        self.manager.registerModule("testModule", Mock())

        with patch("console.warn") as mock_warn:
            self.manager.detectMemoryLeak("testModule")
            mock_warn.assert_not_called()


class TestTabSwitching:
    """Test tab switching integration"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_handle_tab_switch_shows_module(self):
        """Test tab switch shows corresponding module"""
        self.manager.registerModule("stockManager", Mock())

        with patch.object(self.manager, "showModule") as mock_show:
            self.manager.handleTabSwitch("popular-stocks")
            mock_show.assert_called_once_with("stockManager")

    def test_handle_unknown_tab(self):
        """Test handling unknown tab name"""
        # Should not throw for unknown tab
        self.manager.handleTabSwitch("unknown-tab")

    def test_show_module_hides_previous(self):
        """Test showing module hides previous active module"""
        self.manager.registerModule("module1", Mock())
        self.manager.registerModule("module2", Mock())

        self.manager.showModule("module1")

        with patch.object(self.manager, "hideModule") as mock_hide:
            self.manager.showModule("module2")
            mock_hide.assert_called_once_with("module1")


class TestStatusReporting:
    """Test module status reporting"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_get_module_status(self):
        """Test getting single module status"""
        self.manager.registerModule("testModule", Mock())
        self.manager.showModule("testModule")

        status = self.manager.getModuleStatus("testModule")

        assert status["name"] == "testModule"
        assert status["state"] == "visible"
        assert status["showCount"] == 1
        assert "resourceCounts" in status

    def test_get_all_module_statuses(self):
        """Test getting all module statuses"""
        self.manager.registerModule("module1", Mock())
        self.manager.registerModule("module2", Mock())

        statuses = self.manager.getAllModuleStatuses()

        assert "module1" in statuses
        assert "module2" in statuses

    def test_get_unknown_module_status(self):
        """Test getting status of unknown module"""
        status = self.manager.getModuleStatus("unknown")
        assert status is None


class TestCleanup:
    """Test cleanup operations"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_cleanup_all_modules(self):
        """Test cleanup destroys all modules"""
        self.manager.registerModule("module1", Mock())
        self.manager.registerModule("module2", Mock())

        with patch.object(self.manager, "destroyModule") as mock_destroy:
            self.manager.cleanupAll()
            assert mock_destroy.call_count == 2

    def test_cleanup_clears_collections(self):
        """Test cleanup clears internal collections"""
        self.manager.registerModule("testModule", Mock())
        self.manager.memorySnapshots.set("key", {})

        self.manager.cleanup()

        assert self.manager.modules.size == 0
        assert self.manager.memorySnapshots.size == 0
        assert self.manager.eventBus is None


class TestIntegration:
    """Integration tests"""

    def setup_method(self):
        from LifecycleManager import LifecycleManager

        self.eventBus = Mock()
        self.manager = LifecycleManager(self.eventBus)

    def test_full_lifecycle_workflow(self):
        """Test complete module lifecycle"""
        hooks = {
            "onInit": Mock(),
            "onShow": Mock(),
            "onHide": Mock(),
            "onDestroy": Mock(),
        }

        self.manager.registerModule("testModule", Mock(), hooks)

        # Full lifecycle
        self.manager.initModule("testModule")
        assert hooks["onInit"].called

        self.manager.showModule("testModule")
        assert hooks["onShow"].called
        assert self.manager.activeModule == "testModule"

        self.manager.hideModule("testModule")
        assert hooks["onHide"].called

        self.manager.destroyModule("testModule")
        assert hooks["onDestroy"].called

    def test_multiple_tab_switches(self):
        """Test multiple tab switches don't leak memory"""
        self.manager.registerModule("module1", Mock())
        self.manager.registerModule("module2", Mock())

        # Switch tabs multiple times
        for i in range(5):
            self.manager.showModule("module1")
            self.manager.showModule("module2")

        module1 = self.manager.modules.get("module1")
        module2 = self.manager.modules.get("module2")

        assert module1.showCount == 5
        assert module2.showCount == 5
        assert module1.hideCount == 5
        assert module2.hideCount == 4  # Last one not hidden yet


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
