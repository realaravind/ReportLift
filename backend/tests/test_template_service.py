"""Tests for branding template service."""

import io
import json
import os
import tempfile
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.branding_template import BrandingTemplate
from app.services.template_service import (
    validate_template_file,
    upload_template,
    delete_template,
    get_current_template,
    get_template_info,
    get_template_theme,
    TemplateValidationError,
    MAX_TEMPLATE_SIZE_MB,
)


@pytest.fixture
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def create_valid_pbit(content: dict = None) -> io.BytesIO:
    """Create a valid PBIT file in memory.

    Args:
        content: Optional content for Layout file

    Returns:
        BytesIO containing a valid PBIT ZIP structure
    """
    buffer = io.BytesIO()

    layout_content = content or {
        "config": json.dumps({
            "themeCollection": {
                "baseTheme": {
                    "name": "Test Theme",
                    "dataColors": ["#FF0000", "#00FF00", "#0000FF"],
                    "background": "#FFFFFF",
                    "foreground": "#000000",
                }
            }
        }),
        "sections": [],
    }

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("Report/Layout", json.dumps(layout_content))
        zf.writestr("Settings", "{}")
        zf.writestr("Metadata", "{}")

    buffer.seek(0)
    return buffer


def create_invalid_zip() -> io.BytesIO:
    """Create an invalid (non-ZIP) file."""
    buffer = io.BytesIO()
    buffer.write(b"This is not a ZIP file")
    buffer.seek(0)
    return buffer


def create_zip_without_layout() -> io.BytesIO:
    """Create a ZIP file missing the Layout component."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("Settings", "{}")
    buffer.seek(0)
    return buffer


class TestValidateTemplateFile:
    """Tests for validate_template_file function."""

    def test_valid_pbit_file(self):
        """Test validation of a valid PBIT file."""
        file = create_valid_pbit()
        result = validate_template_file(file, "template.pbit")

        assert result.is_valid is True
        assert result.error_message is None
        assert result.file_size > 0
        assert result.theme_metadata is not None
        assert result.theme_metadata.get("name") == "Test Theme"

    def test_invalid_extension(self):
        """Test rejection of non-.pbit extension."""
        file = create_valid_pbit()
        result = validate_template_file(file, "template.pbix")

        assert result.is_valid is False
        assert result.error_code == "INVALID_EXTENSION"
        assert ".pbit" in result.error_message

    def test_empty_file(self):
        """Test rejection of empty file."""
        file = io.BytesIO()
        result = validate_template_file(file, "template.pbit")

        assert result.is_valid is False
        assert result.error_code == "EMPTY_FILE"

    def test_invalid_zip_structure(self):
        """Test rejection of invalid ZIP file."""
        file = create_invalid_zip()
        result = validate_template_file(file, "template.pbit")

        assert result.is_valid is False
        assert result.error_code == "BAD_ZIP"

    def test_missing_layout_component(self):
        """Test rejection of ZIP without Layout."""
        file = create_zip_without_layout()
        result = validate_template_file(file, "template.pbit")

        assert result.is_valid is False
        assert result.error_code == "MISSING_LAYOUT"

    def test_uppercase_extension(self):
        """Test acceptance of uppercase .PBIT extension."""
        file = create_valid_pbit()
        result = validate_template_file(file, "template.PBIT")

        assert result.is_valid is True

    def test_mixed_case_extension(self):
        """Test acceptance of mixed case .pBiT extension."""
        file = create_valid_pbit()
        result = validate_template_file(file, "template.pBiT")

        assert result.is_valid is True


class TestUploadTemplate:
    """Tests for upload_template function."""

    def test_upload_new_template(self, db_session, monkeypatch):
        """Test uploading a new template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("TEMPLATE_STORAGE_PATH", tmpdir)
            # Reload the module to pick up the new path
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_valid_pbit()
            template = upload_template(
                db=db_session,
                file=file,
                filename="test_template.pbit",
            )

            assert template.id is not None
            assert template.name == "test_template.pbit"
            assert template.is_active is True
            assert template.file_size > 0
            assert os.path.exists(template.file_path)

    def test_upload_replaces_existing(self, db_session, monkeypatch):
        """Test that uploading a new template replaces the existing one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            # Upload first template
            file1 = create_valid_pbit()
            template1 = upload_template(
                db=db_session,
                file=file1,
                filename="template1.pbit",
            )

            # Upload second template
            file2 = create_valid_pbit()
            template2 = upload_template(
                db=db_session,
                file=file2,
                filename="template2.pbit",
                replace_existing=True,
            )

            # First template should be inactive
            db_session.refresh(template1)
            assert template1.is_active is False

            # Second template should be active
            assert template2.is_active is True
            assert template2.name == "template2.pbit"

    def test_upload_fails_without_replace_flag(self, db_session, monkeypatch):
        """Test that upload fails if template exists and replace_existing=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            # Upload first template
            file1 = create_valid_pbit()
            upload_template(
                db=db_session,
                file=file1,
                filename="template1.pbit",
            )

            # Try to upload second without replace flag
            file2 = create_valid_pbit()
            with pytest.raises(TemplateValidationError) as exc_info:
                upload_template(
                    db=db_session,
                    file=file2,
                    filename="template2.pbit",
                    replace_existing=False,
                )

            assert exc_info.value.code == "TEMPLATE_EXISTS"

    def test_upload_invalid_file_raises_error(self, db_session, monkeypatch):
        """Test that uploading invalid file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_invalid_zip()
            with pytest.raises(TemplateValidationError) as exc_info:
                upload_template(
                    db=db_session,
                    file=file,
                    filename="invalid.pbit",
                )

            assert exc_info.value.code == "BAD_ZIP"


class TestDeleteTemplate:
    """Tests for delete_template function."""

    def test_delete_existing_template(self, db_session, monkeypatch):
        """Test deleting an existing template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            # Upload template
            file = create_valid_pbit()
            template = upload_template(
                db=db_session,
                file=file,
                filename="template.pbit",
            )
            template_id = template.id
            file_path = template.file_path

            # Delete it
            result = delete_template(db_session, template_id)

            assert result is True
            assert not os.path.exists(file_path)

            # Verify it's gone from database
            deleted = db_session.query(BrandingTemplate).filter(
                BrandingTemplate.id == template_id
            ).first()
            assert deleted is None

    def test_delete_nonexistent_template(self, db_session):
        """Test deleting a template that doesn't exist."""
        result = delete_template(db_session, 9999)
        assert result is False


class TestGetCurrentTemplate:
    """Tests for get_current_template function."""

    def test_no_template_returns_none(self, db_session):
        """Test that no template returns None."""
        result = get_current_template(db_session)
        assert result is None

    def test_returns_active_template(self, db_session, monkeypatch):
        """Test that active template is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_valid_pbit()
            template = upload_template(
                db=db_session,
                file=file,
                filename="template.pbit",
            )

            result = get_current_template(db_session)
            assert result is not None
            assert result.id == template.id
            assert result.is_active is True


class TestGetTemplateInfo:
    """Tests for get_template_info function."""

    def test_no_template_returns_none(self, db_session):
        """Test that no template returns None."""
        result = get_template_info(db_session)
        assert result is None

    def test_returns_template_info(self, db_session, monkeypatch):
        """Test that template info is returned correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_valid_pbit()
            template = upload_template(
                db=db_session,
                file=file,
                filename="my_template.pbit",
            )

            info = get_template_info(db_session)
            assert info is not None
            assert info.id == template.id
            assert info.name == "my_template.pbit"
            assert info.file_size > 0
            assert info.file_size_mb >= 0  # Small test files round to 0.0 MB
            assert info.file_size_mb == round(info.file_size / (1024 * 1024), 2)
            assert info.is_active is True


class TestGetTemplateTheme:
    """Tests for get_template_theme function."""

    def test_no_template_returns_none(self, db_session):
        """Test that no template returns None."""
        result = get_template_theme(db_session)
        assert result is None

    def test_returns_theme_metadata(self, db_session, monkeypatch):
        """Test that theme metadata is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_valid_pbit()
            upload_template(
                db=db_session,
                file=file,
                filename="template.pbit",
            )

            theme = get_template_theme(db_session)
            assert theme is not None
            assert theme.get("name") == "Test Theme"
            assert len(theme.get("dataColors", [])) == 3


class TestBrandingTemplateModel:
    """Tests for BrandingTemplate model."""

    def test_file_size_mb_property(self, db_session, monkeypatch):
        """Test file_size_mb property calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_valid_pbit()
            template = upload_template(
                db=db_session,
                file=file,
                filename="template.pbit",
            )

            assert template.file_size_mb == round(template.file_size / (1024 * 1024), 2)

    def test_repr(self, db_session, monkeypatch):
        """Test model __repr__."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import app.services.template_service as ts
            monkeypatch.setattr(ts, "TEMPLATE_STORAGE_PATH", tmpdir)

            file = create_valid_pbit()
            template = upload_template(
                db=db_session,
                file=file,
                filename="my_template.pbit",
            )

            repr_str = repr(template)
            assert "my_template.pbit" in repr_str
            assert "active=True" in repr_str
