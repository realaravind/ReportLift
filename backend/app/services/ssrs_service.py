"""SSRS Service - Handles communication with SQL Server Reporting Services."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests
from requests_ntlm import HttpNtlmAuth

logger = logging.getLogger(__name__)

# Default timeout for SSRS API calls (seconds)
DEFAULT_TIMEOUT = 10


class SSRSErrorCode(str, Enum):
    """Error codes for SSRS connection failures."""

    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT = "TIMEOUT"
    AUTH_FAILED = "AUTH_FAILED"
    NOT_FOUND = "NOT_FOUND"
    SSL_ERROR = "SSL_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SERVER_ERROR = "SERVER_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class SSRSTestResult:
    """Result of an SSRS connection test."""

    success: bool
    message: str
    server_version: str | None = None
    response_time_ms: int = 0
    root_folder_accessible: bool = False
    error_code: SSRSErrorCode | None = None
    suggestions: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "success": self.success,
            "message": self.message,
            "details": {
                "server_version": self.server_version,
                "response_time_ms": self.response_time_ms,
                "root_folder_accessible": self.root_folder_accessible,
            },
        }
        if self.error_code:
            result["details"]["error_code"] = self.error_code.value
        if self.suggestions:
            result["suggestions"] = self.suggestions
        return result


# Error suggestions mapping
ERROR_SUGGESTIONS = {
    SSRSErrorCode.CONNECTION_ERROR: [
        "Check that the Report Server URL is correct",
        "Verify the SSRS server is running and accessible",
        "Check network connectivity to the server",
    ],
    SSRSErrorCode.TIMEOUT: [
        "Connection timed out - check network connectivity",
        "The server may be under heavy load, try again",
        "Verify firewall rules allow access to the server",
    ],
    SSRSErrorCode.AUTH_FAILED: [
        "Your Windows credentials could not authenticate",
        "Verify you have been granted access to SSRS",
        "Contact your administrator to check SSRS permissions",
    ],
    SSRSErrorCode.NOT_FOUND: [
        "Report Server endpoint not found at the specified URL",
        "Verify the URL path (should end with /ReportServer)",
        "Check that SSRS is installed and configured correctly",
    ],
    SSRSErrorCode.SSL_ERROR: [
        "SSL certificate error - the server certificate may not be trusted",
        "Verify the server's SSL certificate is valid",
        "Contact your administrator if using a self-signed certificate",
    ],
    SSRSErrorCode.PERMISSION_DENIED: [
        "Access denied to the Report Server root folder",
        "Verify you have at least Browser role on the root folder",
        "Contact your SSRS administrator for permissions",
    ],
    SSRSErrorCode.SERVER_ERROR: [
        "The Report Server returned an error",
        "Check the SSRS server logs for more details",
        "The server may be experiencing issues, try again later",
    ],
    SSRSErrorCode.UNKNOWN: [
        "An unexpected error occurred",
        "Check the server URL and try again",
        "Contact your administrator if the problem persists",
    ],
}


def _build_ssrs_api_url(base_url: str) -> str:
    """Build the SSRS REST API URL from the base Report Server URL.

    Args:
        base_url: The Report Server URL (e.g., https://server/ReportServer)

    Returns:
        The SSRS REST API folders endpoint URL
    """
    # Remove trailing slash
    url = base_url.rstrip("/")

    # SSRS 2016+ REST API endpoint
    # The API is at {ReportServer}/api/v2.0/Folders
    return f"{url}/api/v2.0/Folders"


def test_ssrs_connection(
    report_server_url: str,
    username: str | None = None,
    password: str | None = None,
    domain: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> SSRSTestResult:
    """Test connection to SSRS Report Server.

    This function attempts to connect to the SSRS REST API and list the root
    folders. It uses NTLM authentication with the provided credentials or
    the current user's Windows credentials.

    Args:
        report_server_url: The Report Server URL (e.g., https://server/ReportServer)
        username: Optional username for authentication
        password: Optional password for authentication
        domain: Optional domain for NTLM authentication
        timeout: Request timeout in seconds

    Returns:
        SSRSTestResult with connection status and details
    """
    start_time = time.time()

    try:
        api_url = _build_ssrs_api_url(report_server_url)
        logger.info("Testing SSRS connection to: %s", api_url)

        # Set up NTLM authentication
        auth = None
        if username and password:
            # Use explicit credentials
            ntlm_username = f"{domain}\\{username}" if domain else username
            auth = HttpNtlmAuth(ntlm_username, password)
            logger.debug("Using explicit credentials for NTLM auth")
        # If no credentials provided, requests-ntlm will try to use
        # the current user's Windows credentials (if available)

        # Make the request to the SSRS API
        response = requests.get(
            api_url,
            auth=auth,
            timeout=timeout,
            verify=True,  # Verify SSL certificates
            headers={
                "Accept": "application/json",
            },
        )

        response_time_ms = int((time.time() - start_time) * 1000)

        # Extract server version from headers if available
        server_version = response.headers.get("X-SSRS-Version")
        if not server_version:
            # Try alternative header
            server_version = response.headers.get("Server")

        # Check response status
        if response.status_code == 200:
            logger.info("SSRS connection successful")
            return SSRSTestResult(
                success=True,
                message="Connected to SSRS successfully",
                server_version=server_version,
                response_time_ms=response_time_ms,
                root_folder_accessible=True,
            )

        elif response.status_code == 401:
            logger.warning("SSRS authentication failed: 401 Unauthorized")
            return SSRSTestResult(
                success=False,
                message="Authentication failed - Windows credentials not accepted",
                response_time_ms=response_time_ms,
                error_code=SSRSErrorCode.AUTH_FAILED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.AUTH_FAILED],
            )

        elif response.status_code == 403:
            logger.warning("SSRS access denied: 403 Forbidden")
            return SSRSTestResult(
                success=False,
                message="Access denied - insufficient permissions on Report Server",
                response_time_ms=response_time_ms,
                error_code=SSRSErrorCode.PERMISSION_DENIED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.PERMISSION_DENIED],
            )

        elif response.status_code == 404:
            logger.warning("SSRS endpoint not found: 404")
            return SSRSTestResult(
                success=False,
                message="Report Server not found at the specified URL",
                response_time_ms=response_time_ms,
                error_code=SSRSErrorCode.NOT_FOUND,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.NOT_FOUND],
            )

        elif response.status_code >= 500:
            logger.error("SSRS server error: %d", response.status_code)
            return SSRSTestResult(
                success=False,
                message=f"Report Server error (HTTP {response.status_code})",
                response_time_ms=response_time_ms,
                error_code=SSRSErrorCode.SERVER_ERROR,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.SERVER_ERROR],
            )

        else:
            logger.warning("Unexpected SSRS response: %d", response.status_code)
            return SSRSTestResult(
                success=False,
                message=f"Unexpected response from Report Server (HTTP {response.status_code})",
                response_time_ms=response_time_ms,
                error_code=SSRSErrorCode.UNKNOWN,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
            )

    except requests.exceptions.Timeout:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("SSRS connection timed out after %dms", response_time_ms)
        return SSRSTestResult(
            success=False,
            message=f"Connection timed out after {timeout} seconds",
            response_time_ms=response_time_ms,
            error_code=SSRSErrorCode.TIMEOUT,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.TIMEOUT],
        )

    except requests.exceptions.SSLError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("SSRS SSL error: %s", str(e))
        return SSRSTestResult(
            success=False,
            message="SSL certificate verification failed",
            response_time_ms=response_time_ms,
            error_code=SSRSErrorCode.SSL_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.SSL_ERROR],
        )

    except requests.exceptions.ConnectionError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("SSRS connection error: %s", str(e))
        return SSRSTestResult(
            success=False,
            message="Unable to connect to Report Server",
            response_time_ms=response_time_ms,
            error_code=SSRSErrorCode.CONNECTION_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.CONNECTION_ERROR],
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.exception("Unexpected error testing SSRS connection: %s", str(e))
        return SSRSTestResult(
            success=False,
            message=f"Unexpected error: {str(e)}",
            response_time_ms=response_time_ms,
            error_code=SSRSErrorCode.UNKNOWN,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
        )


@dataclass
class SSRSFolder:
    """Represents a folder in the SSRS catalog."""

    name: str
    path: str
    has_children: bool
    description: str | None = None


@dataclass
class SSRSFoldersResult:
    """Result of an SSRS folder listing operation."""

    success: bool
    message: str
    folders: list[SSRSFolder] | None = None
    error_code: SSRSErrorCode | None = None
    suggestions: list[str] | None = None


def list_ssrs_folders(
    report_server_url: str,
    path: str = "/",
    username: str | None = None,
    password: str | None = None,
    domain: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> SSRSFoldersResult:
    """List folders at a given path in the SSRS catalog.

    Uses the SSRS REST API (v2.0) to fetch catalog items of type 'Folder'.

    Args:
        report_server_url: The Report Server URL (e.g., https://server/ReportServer)
        path: The folder path to list (default "/" for root)
        username: Optional username for authentication
        password: Optional password for authentication
        domain: Optional domain for NTLM authentication
        timeout: Request timeout in seconds

    Returns:
        SSRSFoldersResult with list of folders or error details
    """
    try:
        # Build the API URL
        base_url = report_server_url.rstrip("/")

        # Use CatalogItems endpoint with filter for folders
        # For root path, we get top-level folders
        # For subpaths, we filter by ParentId
        if path == "/" or path == "":
            # Get all top-level folders (those without a parent folder path prefix)
            api_url = f"{base_url}/api/v2.0/Folders"
        else:
            # URL encode the path for the API query
            encoded_path = path.replace("'", "''")  # Escape single quotes
            api_url = f"{base_url}/api/v2.0/CatalogItems"

        logger.info("Listing SSRS folders at path: %s", path)

        # Set up NTLM authentication
        auth = None
        if username and password:
            ntlm_username = f"{domain}\\{username}" if domain else username
            auth = HttpNtlmAuth(ntlm_username, password)

        # Make the request
        params = {}
        if path != "/" and path != "":
            # Filter for folders with a specific parent path
            params["$filter"] = f"Type eq 'Folder' and startswith(Path, '{encoded_path}/')"

        response = requests.get(
            api_url,
            auth=auth,
            params=params if params else None,
            timeout=timeout,
            verify=True,
            headers={"Accept": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get("value", [])

            folders = []
            for item in items:
                item_path = item.get("Path", "")
                item_name = item.get("Name", "")

                # For non-root queries, filter to direct children only
                if path != "/" and path != "":
                    # Check if this is a direct child
                    parent_path = path.rstrip("/")
                    if not item_path.startswith(parent_path + "/"):
                        continue
                    # Skip if it's a deeper nested folder
                    relative_path = item_path[len(parent_path) + 1:]
                    if "/" in relative_path:
                        continue
                else:
                    # For root, only include top-level folders
                    if item_path.count("/") > 1:
                        continue

                folders.append(SSRSFolder(
                    name=item_name,
                    path=item_path,
                    has_children=item.get("HasChildren", True),  # Default to True, will be checked
                    description=item.get("Description"),
                ))

            logger.info("Found %d folders at path: %s", len(folders), path)
            return SSRSFoldersResult(
                success=True,
                message=f"Found {len(folders)} folder(s)",
                folders=folders,
            )

        elif response.status_code == 401:
            return SSRSFoldersResult(
                success=False,
                message="Authentication failed - Windows credentials not accepted",
                error_code=SSRSErrorCode.AUTH_FAILED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.AUTH_FAILED],
            )

        elif response.status_code == 403:
            return SSRSFoldersResult(
                success=False,
                message="Access denied - insufficient permissions",
                error_code=SSRSErrorCode.PERMISSION_DENIED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.PERMISSION_DENIED],
            )

        elif response.status_code == 404:
            return SSRSFoldersResult(
                success=False,
                message="Folder path not found",
                error_code=SSRSErrorCode.NOT_FOUND,
                suggestions=["Verify the folder path exists", "Check your permissions"],
            )

        else:
            return SSRSFoldersResult(
                success=False,
                message=f"Unexpected response from Report Server (HTTP {response.status_code})",
                error_code=SSRSErrorCode.UNKNOWN,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
            )

    except requests.exceptions.Timeout:
        logger.warning("SSRS folder listing timed out")
        return SSRSFoldersResult(
            success=False,
            message=f"Connection timed out after {timeout} seconds",
            error_code=SSRSErrorCode.TIMEOUT,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.TIMEOUT],
        )

    except requests.exceptions.SSLError as e:
        logger.warning("SSRS SSL error: %s", str(e))
        return SSRSFoldersResult(
            success=False,
            message="SSL certificate verification failed",
            error_code=SSRSErrorCode.SSL_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.SSL_ERROR],
        )

    except requests.exceptions.ConnectionError as e:
        logger.warning("SSRS connection error: %s", str(e))
        return SSRSFoldersResult(
            success=False,
            message="Unable to connect to Report Server",
            error_code=SSRSErrorCode.CONNECTION_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.CONNECTION_ERROR],
        )

    except Exception as e:
        logger.exception("Unexpected error listing SSRS folders: %s", str(e))
        return SSRSFoldersResult(
            success=False,
            message=f"Unexpected error: {str(e)}",
            error_code=SSRSErrorCode.UNKNOWN,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
        )


@dataclass
class SSRSReport:
    """Represents a report in the SSRS catalog."""

    id: str
    name: str
    path: str
    description: str | None = None
    modified_date: str | None = None
    size_bytes: int = 0
    created_by: str | None = None


@dataclass
class SSRSReportsResult:
    """Result of an SSRS report listing operation."""

    success: bool
    message: str
    reports: list[SSRSReport] | None = None
    error_code: SSRSErrorCode | None = None
    suggestions: list[str] | None = None


def list_ssrs_reports(
    report_server_url: str,
    path: str,
    username: str | None = None,
    password: str | None = None,
    domain: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> SSRSReportsResult:
    """List reports at a given folder path in the SSRS catalog.

    Uses the SSRS REST API (v2.0) to fetch catalog items of type 'Report'.

    Args:
        report_server_url: The Report Server URL (e.g., https://server/ReportServer)
        path: The folder path to list reports from
        username: Optional username for authentication
        password: Optional password for authentication
        domain: Optional domain for NTLM authentication
        timeout: Request timeout in seconds

    Returns:
        SSRSReportsResult with list of reports or error details
    """
    try:
        # Build the API URL
        base_url = report_server_url.rstrip("/")

        # Use CatalogItems endpoint with filter for reports in this folder
        api_url = f"{base_url}/api/v2.0/CatalogItems"

        logger.info("Listing SSRS reports at path: %s", path)

        # Set up NTLM authentication
        auth = None
        if username and password:
            ntlm_username = f"{domain}\\{username}" if domain else username
            auth = HttpNtlmAuth(ntlm_username, password)

        # Escape single quotes in path for OData filter
        escaped_path = path.replace("'", "''")

        # Filter for reports that start with this path
        # We need to find reports where the parent folder is our path
        params = {
            "$filter": f"Type eq 'Report' and startswith(Path, '{escaped_path}/')"
        }

        response = requests.get(
            api_url,
            auth=auth,
            params=params,
            timeout=timeout,
            verify=True,
            headers={"Accept": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get("value", [])

            reports = []
            for item in items:
                item_path = item.get("Path", "")
                item_name = item.get("Name", "")

                # Only include direct children of the requested path
                parent_path = path.rstrip("/")
                if not item_path.startswith(parent_path + "/"):
                    continue

                # Skip if this is in a subfolder
                relative_path = item_path[len(parent_path) + 1:]
                if "/" in relative_path:
                    continue

                reports.append(SSRSReport(
                    id=item.get("Id", ""),
                    name=item_name,
                    path=item_path,
                    description=item.get("Description"),
                    modified_date=item.get("ModifiedDate"),
                    size_bytes=item.get("Size", 0),
                    created_by=item.get("CreatedBy"),
                ))

            logger.info("Found %d reports at path: %s", len(reports), path)
            return SSRSReportsResult(
                success=True,
                message=f"Found {len(reports)} report(s)",
                reports=reports,
            )

        elif response.status_code == 401:
            return SSRSReportsResult(
                success=False,
                message="Authentication failed - Windows credentials not accepted",
                error_code=SSRSErrorCode.AUTH_FAILED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.AUTH_FAILED],
            )

        elif response.status_code == 403:
            return SSRSReportsResult(
                success=False,
                message="Access denied - insufficient permissions",
                error_code=SSRSErrorCode.PERMISSION_DENIED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.PERMISSION_DENIED],
            )

        elif response.status_code == 404:
            return SSRSReportsResult(
                success=False,
                message="Folder path not found",
                error_code=SSRSErrorCode.NOT_FOUND,
                suggestions=["Verify the folder path exists", "Check your permissions"],
            )

        else:
            return SSRSReportsResult(
                success=False,
                message=f"Unexpected response from Report Server (HTTP {response.status_code})",
                error_code=SSRSErrorCode.UNKNOWN,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
            )

    except requests.exceptions.Timeout:
        logger.warning("SSRS report listing timed out")
        return SSRSReportsResult(
            success=False,
            message=f"Connection timed out after {timeout} seconds",
            error_code=SSRSErrorCode.TIMEOUT,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.TIMEOUT],
        )

    except requests.exceptions.SSLError as e:
        logger.warning("SSRS SSL error: %s", str(e))
        return SSRSReportsResult(
            success=False,
            message="SSL certificate verification failed",
            error_code=SSRSErrorCode.SSL_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.SSL_ERROR],
        )

    except requests.exceptions.ConnectionError as e:
        logger.warning("SSRS connection error: %s", str(e))
        return SSRSReportsResult(
            success=False,
            message="Unable to connect to Report Server",
            error_code=SSRSErrorCode.CONNECTION_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.CONNECTION_ERROR],
        )

    except Exception as e:
        logger.exception("Unexpected error listing SSRS reports: %s", str(e))
        return SSRSReportsResult(
            success=False,
            message=f"Unexpected error: {str(e)}",
            error_code=SSRSErrorCode.UNKNOWN,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
        )


@dataclass
class SSRSRdlResult:
    """Result of fetching an RDL file from SSRS."""

    success: bool
    message: str
    rdl_content: str | None = None
    report_id: str | None = None
    error_code: SSRSErrorCode | None = None
    suggestions: list[str] | None = None
    response_time_ms: int = 0


def fetch_report_rdl(
    report_server_url: str,
    report_path: str,
    username: str | None = None,
    password: str | None = None,
    domain: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> SSRSRdlResult:
    """Fetch the RDL (Report Definition Language) content for a report.

    Uses the SSRS REST API (v2.0) to download the report definition XML.

    Args:
        report_server_url: The Report Server URL (e.g., https://server/ReportServer)
        report_path: The full path to the report (e.g., /Sales/MonthlyReport)
        username: Optional username for authentication
        password: Optional password for authentication
        domain: Optional domain for NTLM authentication
        timeout: Request timeout in seconds

    Returns:
        SSRSRdlResult with RDL content or error details
    """
    start_time = time.time()

    try:
        base_url = report_server_url.rstrip("/")

        # URL encode the path for the API
        # SSRS API uses Path in the URL: /CatalogItems(Path='{path}')/Content/$value
        from urllib.parse import quote

        encoded_path = quote(report_path, safe="")
        api_url = f"{base_url}/api/v2.0/CatalogItems(Path='{encoded_path}')/Content/$value"

        logger.info("Fetching RDL for report: %s", report_path)

        # Set up NTLM authentication
        auth = None
        if username and password:
            ntlm_username = f"{domain}\\{username}" if domain else username
            auth = HttpNtlmAuth(ntlm_username, password)

        # Make the request
        response = requests.get(
            api_url,
            auth=auth,
            timeout=timeout,
            verify=True,
            headers={"Accept": "application/xml, application/octet-stream"},
        )

        response_time_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            rdl_content = response.text
            logger.info(
                "Successfully fetched RDL for %s (%d bytes in %dms)",
                report_path,
                len(rdl_content),
                response_time_ms,
            )

            # Try to get report ID from a separate call
            report_id = None
            try:
                info_url = f"{base_url}/api/v2.0/CatalogItems(Path='{encoded_path}')"
                info_response = requests.get(
                    info_url,
                    auth=auth,
                    timeout=5,
                    verify=True,
                    headers={"Accept": "application/json"},
                )
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    report_id = info_data.get("Id")
            except Exception:
                pass  # Non-critical, continue without report ID

            return SSRSRdlResult(
                success=True,
                message="Successfully retrieved report definition",
                rdl_content=rdl_content,
                report_id=report_id,
                response_time_ms=response_time_ms,
            )

        elif response.status_code == 401:
            return SSRSRdlResult(
                success=False,
                message="Authentication failed - Windows credentials not accepted",
                error_code=SSRSErrorCode.AUTH_FAILED,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.AUTH_FAILED],
                response_time_ms=response_time_ms,
            )

        elif response.status_code == 403:
            return SSRSRdlResult(
                success=False,
                message="Access denied - insufficient permissions to read report definition",
                error_code=SSRSErrorCode.PERMISSION_DENIED,
                suggestions=[
                    "You need 'Read Report Definition' permission on this report",
                    "Contact your SSRS administrator for access",
                ],
                response_time_ms=response_time_ms,
            )

        elif response.status_code == 404:
            return SSRSRdlResult(
                success=False,
                message="Report not found at the specified path",
                error_code=SSRSErrorCode.NOT_FOUND,
                suggestions=[
                    "Verify the report path is correct",
                    "The report may have been moved or deleted",
                ],
                response_time_ms=response_time_ms,
            )

        else:
            return SSRSRdlResult(
                success=False,
                message=f"Unexpected response from Report Server (HTTP {response.status_code})",
                error_code=SSRSErrorCode.UNKNOWN,
                suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
                response_time_ms=response_time_ms,
            )

    except requests.exceptions.Timeout:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("RDL fetch timed out after %dms", response_time_ms)
        return SSRSRdlResult(
            success=False,
            message=f"Connection timed out after {timeout} seconds",
            error_code=SSRSErrorCode.TIMEOUT,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.TIMEOUT],
            response_time_ms=response_time_ms,
        )

    except requests.exceptions.SSLError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("RDL fetch SSL error: %s", str(e))
        return SSRSRdlResult(
            success=False,
            message="SSL certificate verification failed",
            error_code=SSRSErrorCode.SSL_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.SSL_ERROR],
            response_time_ms=response_time_ms,
        )

    except requests.exceptions.ConnectionError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("RDL fetch connection error: %s", str(e))
        return SSRSRdlResult(
            success=False,
            message="Unable to connect to Report Server",
            error_code=SSRSErrorCode.CONNECTION_ERROR,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.CONNECTION_ERROR],
            response_time_ms=response_time_ms,
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.exception("Unexpected error fetching RDL: %s", str(e))
        return SSRSRdlResult(
            success=False,
            message=f"Unexpected error: {str(e)}",
            error_code=SSRSErrorCode.UNKNOWN,
            suggestions=ERROR_SUGGESTIONS[SSRSErrorCode.UNKNOWN],
            response_time_ms=response_time_ms,
        )
