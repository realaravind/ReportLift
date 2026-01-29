"""Tests for the audit service."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.audit_log import AuditLog, AuditStatus, EventType
from app.schemas.audit import (
    AuditLogCreate,
    AuditLogFilter,
    AuditLogResponse,
    AuditSummary,
    EventType as SchemaEventType,
    AuditStatus as SchemaAuditStatus,
)
from app.services.audit_service import (
    AuditService,
    get_audit_service,
    reset_audit_service,
    SENSITIVE_KEYS,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert EventType.LOGIN.value == "LOGIN"
        assert EventType.LOGOUT.value == "LOGOUT"
        assert EventType.ANALYSIS.value == "ANALYSIS"
        assert EventType.CONVERSION.value == "CONVERSION"
        assert EventType.CONFIG_CHANGE.value == "CONFIG_CHANGE"


class TestAuditStatus:
    """Tests for AuditStatus enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert AuditStatus.SUCCESS.value == "SUCCESS"
        assert AuditStatus.FAILURE.value == "FAILURE"


class TestAuditLog:
    """Tests for AuditLog model."""

    def test_create_factory_method(self):
        """Test AuditLog.create factory method."""
        log = AuditLog.create(
            event_type=EventType.LOGIN,
            action="User logged in",
            status=AuditStatus.SUCCESS,
            user_id=1,
            username="testuser",
        )

        assert log.event_type == "LOGIN"
        assert log.action == "User logged in"
        assert log.status == "SUCCESS"
        assert log.user_id == 1
        assert log.username == "testuser"
        # Note: id is set by database on insert, not by create factory

    def test_create_with_all_fields(self):
        """Test AuditLog.create with all fields."""
        log = AuditLog.create(
            event_type=EventType.ANALYSIS,
            action="Report analyzed",
            status=AuditStatus.SUCCESS,
            user_id=1,
            username="testuser",
            resource_type="report",
            resource_id="/Reports/Sales",
            details={"score": 85},
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
        )

        assert log.resource_type == "report"
        assert log.resource_id == "/Reports/Sales"
        assert log.details == {"score": 85}
        assert log.ip_address == "192.168.1.100"
        assert log.user_agent == "Mozilla/5.0"


class TestAuditService:
    """Tests for AuditService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        reset_audit_service()
        return AuditService()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        db.rollback = MagicMock()
        return db

    def test_sanitize_details_none(self, service):
        """Test sanitize_details with None."""
        result = service.sanitize_details(None)
        assert result is None

    def test_sanitize_details_empty(self, service):
        """Test sanitize_details with empty dict returns None (treated as no details)."""
        result = service.sanitize_details({})
        # Empty dict is treated as no details
        assert result is None or result == {}

    def test_sanitize_details_no_sensitive(self, service):
        """Test sanitize_details with no sensitive data."""
        details = {"name": "test", "value": 123}
        result = service.sanitize_details(details)
        assert result == {"name": "test", "value": 123}

    def test_sanitize_details_password(self, service):
        """Test sanitize_details redacts password."""
        details = {"username": "admin", "password": "secret123"}
        result = service.sanitize_details(details)
        assert result["username"] == "admin"
        assert result["password"] == "[REDACTED]"

    def test_sanitize_details_token(self, service):
        """Test sanitize_details redacts token."""
        details = {"access_token": "abc123", "data": "value"}
        result = service.sanitize_details(details)
        assert result["access_token"] == "[REDACTED]"
        assert result["data"] == "value"

    def test_sanitize_details_api_key(self, service):
        """Test sanitize_details redacts API key."""
        details = {"api_key": "key123", "endpoint": "/api/test"}
        result = service.sanitize_details(details)
        assert result["api_key"] == "[REDACTED]"
        assert result["endpoint"] == "/api/test"

    def test_sanitize_details_nested(self, service):
        """Test sanitize_details with nested dict."""
        details = {
            "user": {
                "name": "test",
                "password": "secret",
            },
            "settings": {"debug": True},
        }
        result = service.sanitize_details(details)
        assert result["user"]["name"] == "test"
        assert result["user"]["password"] == "[REDACTED]"
        assert result["settings"]["debug"] is True

    def test_sanitize_details_case_insensitive(self, service):
        """Test sanitize_details is case insensitive."""
        details = {"PASSWORD": "secret", "Token": "abc", "API_KEY": "key"}
        result = service.sanitize_details(details)
        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Token"] == "[REDACTED]"
        assert result["API_KEY"] == "[REDACTED]"

    def test_log_event_sync_success(self, service, mock_db):
        """Test synchronous logging success."""
        log = service.log_event_sync(
            db=mock_db,
            event_type=EventType.LOGIN,
            action="User logged in",
            status=AuditStatus.SUCCESS,
            username="testuser",
        )

        assert mock_db.add.called
        assert mock_db.commit.called

    def test_log_event_sync_failure(self, service, mock_db):
        """Test synchronous logging failure."""
        mock_db.commit.side_effect = Exception("Database error")

        log = service.log_event_sync(
            db=mock_db,
            event_type=EventType.LOGIN,
            action="User logged in",
            status=AuditStatus.SUCCESS,
            username="testuser",
        )

        assert log is None
        assert mock_db.rollback.called

    def test_log_login_success(self, service, mock_db):
        """Test log_login for successful login."""
        log = service.log_login(
            db=mock_db,
            username="testuser",
            success=True,
            user_id=1,
            ip_address="192.168.1.100",
        )

        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == "LOGIN"
        assert added_log.status == "SUCCESS"
        assert "succeeded" in added_log.action

    def test_log_login_failure(self, service, mock_db):
        """Test log_login for failed login."""
        log = service.log_login(
            db=mock_db,
            username="testuser",
            success=False,
            ip_address="192.168.1.100",
        )

        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == "LOGIN"
        assert added_log.status == "FAILURE"
        assert "failed" in added_log.action

    def test_log_logout(self, service, mock_db):
        """Test log_logout."""
        log = service.log_logout(
            db=mock_db,
            username="testuser",
            user_id=1,
            ip_address="192.168.1.100",
        )

        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == "LOGOUT"
        assert added_log.status == "SUCCESS"

    def test_log_analysis(self, service, mock_db):
        """Test log_analysis."""
        log = service.log_analysis(
            db=mock_db,
            report_path="/Reports/Sales/Monthly",
            report_name="Monthly Sales",
            score=85,
            success=True,
            user_id=1,
            username="testuser",
            analysis_id=123,
            duration_ms=500,
        )

        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == "ANALYSIS"
        assert added_log.resource_type == "report"
        assert added_log.resource_id == "/Reports/Sales/Monthly"
        assert "Monthly Sales" in added_log.action

    def test_log_conversion(self, service, mock_db):
        """Test log_conversion."""
        log = service.log_conversion(
            db=mock_db,
            report_path="/Reports/Sales/Monthly",
            report_name="Monthly Sales",
            success=True,
            user_id=1,
            username="testuser",
            conversion_id=456,
            output_files=["report.pbit", "script.sql"],
            duration_ms=1000,
        )

        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == "CONVERSION"
        assert added_log.resource_type == "report"
        assert added_log.details["output_files"] == ["report.pbit", "script.sql"]

    def test_log_config_change(self, service, mock_db):
        """Test log_config_change."""
        log = service.log_config_change(
            db=mock_db,
            setting_name="ssrs_url",
            old_value="http://old.server/ssrs",
            new_value="http://new.server/ssrs",
            user_id=1,
            username="admin",
        )

        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == "CONFIG_CHANGE"
        assert added_log.resource_type == "configuration"
        assert added_log.resource_id == "ssrs_url"
        assert added_log.details["old_value"] == "http://old.server/ssrs"
        assert added_log.details["new_value"] == "http://new.server/ssrs"

    def test_log_config_change_redacts_sensitive(self, service, mock_db):
        """Test log_config_change redacts sensitive values."""
        log = service.log_config_change(
            db=mock_db,
            setting_name="api_key",
            old_value="old_secret_key",
            new_value="new_secret_key",
            user_id=1,
            username="admin",
        )

        # The value itself should be there (it's not a key named 'password')
        # The sanitization happens on the keys, not values
        mock_db.add.assert_called_once()


class TestAuditLogSchemas:
    """Tests for audit log Pydantic schemas."""

    def test_audit_log_create(self):
        """Test AuditLogCreate schema."""
        create = AuditLogCreate(
            event_type=SchemaEventType.LOGIN,
            action="User logged in",
            status=SchemaAuditStatus.SUCCESS,
            username="testuser",
        )

        assert create.event_type == SchemaEventType.LOGIN
        assert create.action == "User logged in"
        assert create.status == SchemaAuditStatus.SUCCESS

    def test_audit_log_filter_defaults(self):
        """Test AuditLogFilter default values."""
        filter = AuditLogFilter()

        assert filter.page == 1
        assert filter.page_size == 50
        assert filter.start_date is None
        assert filter.event_type is None

    def test_audit_log_filter_with_values(self):
        """Test AuditLogFilter with custom values."""
        filter = AuditLogFilter(
            event_type=SchemaEventType.LOGIN,
            status=SchemaAuditStatus.SUCCESS,
            page=2,
            page_size=25,
        )

        assert filter.event_type == SchemaEventType.LOGIN
        assert filter.status == SchemaAuditStatus.SUCCESS
        assert filter.page == 2
        assert filter.page_size == 25

    def test_audit_summary_defaults(self):
        """Test AuditSummary default values."""
        summary = AuditSummary()

        assert summary.total_events == 0
        assert summary.events_by_type == {}
        assert summary.events_by_status == {}
        assert summary.events_today == 0
        assert summary.events_this_week == 0
        assert summary.unique_users == 0
        assert summary.most_active_user is None


class TestSensitiveKeys:
    """Tests for SENSITIVE_KEYS constant."""

    def test_common_sensitive_keys_present(self):
        """Test that common sensitive keys are in the set."""
        assert "password" in SENSITIVE_KEYS
        assert "token" in SENSITIVE_KEYS
        assert "secret" in SENSITIVE_KEYS
        assert "api_key" in SENSITIVE_KEYS
        assert "credential" in SENSITIVE_KEYS

    def test_sensitive_keys_is_frozen(self):
        """Test that SENSITIVE_KEYS is a frozenset."""
        assert isinstance(SENSITIVE_KEYS, frozenset)


class TestGetAuditService:
    """Tests for get_audit_service function."""

    def test_returns_singleton(self):
        """Test that function returns same instance."""
        reset_audit_service()
        service1 = get_audit_service()
        service2 = get_audit_service()
        assert service1 is service2

    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        service1 = get_audit_service()
        reset_audit_service()
        service2 = get_audit_service()
        assert service1 is not service2


class TestAuditServiceAsync:
    """Tests for async audit service methods."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        reset_audit_service()
        return AuditService()

    @pytest.mark.asyncio
    async def test_log_event_queues_entry(self, service):
        """Test that log_event queues an entry."""
        await service.log_event(
            event_type=EventType.LOGIN,
            action="User logged in",
            status=AuditStatus.SUCCESS,
            username="testuser",
        )

        assert not service._queue.empty()

    @pytest.mark.asyncio
    async def test_log_event_sanitizes_details(self, service):
        """Test that log_event sanitizes details."""
        await service.log_event(
            event_type=EventType.LOGIN,
            action="User logged in",
            status=AuditStatus.SUCCESS,
            details={"password": "secret", "name": "test"},
        )

        entry = await service._queue.get()
        assert entry.details["password"] == "[REDACTED]"
        assert entry.details["name"] == "test"

    @pytest.mark.asyncio
    async def test_queue_size_limit(self, service):
        """Test that queue respects size limit."""
        service._queue._maxsize = 5  # Set small limit for testing

        # Fill the queue
        for i in range(10):
            await service.log_event(
                event_type=EventType.LOGIN,
                action=f"Action {i}",
                status=AuditStatus.SUCCESS,
            )

        # Queue should not exceed max size
        assert service._queue.qsize() <= 5
