"""FastMCP server: Financial Cents + SharePoint tools with JSON string responses."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from financial_cents.client_tasks import (
    ClientTaskOrderByField,
    ClientTaskSearchField,
    list_client_tasks,
)
from financial_cents.clients import (
    OrderByField,
    OrderDirection,
    SearchField,
    SearchOperation,
    create_client,
    get_client,
    list_clients,
)
from financial_cents.client_resources import (
    ClientResourceOrderByField,
    ClientResourceSearchField,
    list_client_resources,
)
from financial_cents.config import FinancialCentsSettings
from financial_cents.invoices import InvoiceOrderByField, list_invoices
from financial_cents.project_resources import (
    ProjectResourceOrderByField,
    ProjectResourceSearchField,
    list_project_resources,
)
from financial_cents.projects import (
    ProjectOrderByField,
    ProjectSearchField,
    ProjectStatusFilter,
    list_projects,
)
from financial_cents.time_activities import list_time_activities
from mcp_fc.pdf_tools import extract_pdf_text
from sharepoint.sharepoint_provider import SharePointProvider

_JSON_INDENT = 2
_MAX_INLINE_BYTES = 512_000
# Force a stable default local download directory on this Windows machine.
# Note: callers can still pass download_path, but Linux-y auto-filled paths
_DEFAULT_DOWNLOAD_DIR = r"D:\SSP\MCP-Financial-Cents\downloads\Financial Cents Document"
_DEFAULT_TY_FOLDER_ENV = "SHAREPOINT_TY_FOLDER"


_FILENAME_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")


def _sanitize_filename(name: str) -> str:
    cleaned = _FILENAME_SAFE_CHARS.sub("_", (name or "").strip())
    cleaned = cleaned.strip(" .")
    return cleaned or "file"


def _download_base_dir(download_path: str | None) -> Path:
    """
    Return a local directory to write downloads into.

    - If download_path is provided: use it as-is (unless it's an auto-filled
      Linux path on Windows, which we ignore).
    - Otherwise default to the configured default directory.
    """
    raw = (str(download_path) if download_path is not None else "").strip()
    if raw:
        # Many clients auto-fill Linux-y paths even when running on Windows.
        if os.name == "nt" and (raw.startswith("/mnt/") or raw.startswith("/")):
            return Path(_DEFAULT_DOWNLOAD_DIR)
        return Path(raw).expanduser()
    return Path(_DEFAULT_DOWNLOAD_DIR)


def _safe_join(base_dir: Path, *parts: str) -> Path:
    """
    Join paths while preventing directory traversal outside base_dir.
    """
    base = base_dir.resolve()
    candidate = base.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as e:
        raise ValueError("Invalid download path (attempted to escape base directory).") from e
    return candidate


def _write_stream_to_file(*, stream: Any, target_path: Path) -> int:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(target_path, "wb") as f:
        while True:
            chunk = stream.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            written += len(chunk)
    return written


def _repo_root() -> Path:
    # mcp_fc/server.py -> repo root is parent of mcp_fc/
    return Path(__file__).resolve().parents[1]


def _settings() -> FinancialCentsSettings:
    return FinancialCentsSettings.from_env()


def _ok_payload(data: Any) -> str:
    return json.dumps(data, indent=_JSON_INDENT, default=str)


def _error_payload(error: str, detail: str, **extra: Any) -> str:
    body: dict[str, Any] = {"error": error, "detail": detail}
    body.update(extra)
    return json.dumps(body, indent=_JSON_INDENT, default=str)


def _http_error_detail(exc: httpx.HTTPStatusError) -> str:
    resp = exc.response
    if resp is None:
        return str(exc)
    try:
        parsed = resp.json()
        if isinstance(parsed, (dict, list)):
            return json.dumps(parsed, indent=_JSON_INDENT, default=str)[:2000]
    except (ValueError, TypeError):
        pass
    text = (resp.text or "").strip()
    return text[:2000] if text else f"HTTP {resp.status_code}"


def _call_api(func: Any) -> str:
    try:
        return _ok_payload(func())
    except ValueError as e:
        return _error_payload("configuration_error", str(e))
    except httpx.HTTPStatusError as e:
        code = e.response.status_code if e.response is not None else None
        return _error_payload(
            "http_error",
            _http_error_detail(e),
            status_code=code,
        )
    except httpx.RequestError as e:
        return _error_payload("request_error", str(e))
    except (TypeError, OSError) as e:
        return _error_payload("unexpected_error", str(e))


mcp = FastMCP(
    "Financial Cents",
    instructions=(
        "Tools for the Financial Cents REST API and SharePoint (via Microsoft Graph). "
        "Financial Cents: clients, client resources, projects, project resources, client tasks, time activities. "
        "SharePoint: list folders/files and fetch file metadata/content. "
        "SharePoint env: TENANT_ID/CLIENT_ID/CLIENT_SECRET (or AZURE_TENANT_ID/AZURE_CLIENT_ID/AZURE_CLIENT_SECRET), "
        "and SHAREPOINT_SITE_HOST/SHAREPOINT_SITE_PATH/SHAREPOINT_DRIVE_NAME."
    ),
)


@mcp.tool()
def financial_cents_check_connection() -> str:
    """Verify API token and network with a lightweight GET /clients?page=1."""

    def run() -> dict[str, Any]:
        cfg = _settings()
        list_clients(page=1, settings=cfg)
        return {
            "ok": True,
            "base_url": cfg.base_url,
            "message": "API reachable",
        }

    return _call_api(run)


@mcp.tool()
def financial_cents_list_clients(
    order_by: OrderByField | None = "name",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    search_field: SearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
) -> str:
    """List clients (paginated). Search params are used only when all three are set."""

    def run() -> dict[str, Any]:
        return list_clients(
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            search_field=search_field,
            search_operation=search_operation,
            search_value=search_value,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_get_client(client_id: str | int) -> str:
    """Fetch a single client by ID."""

    def run() -> dict[str, Any]:
        return get_client(client_id, settings=_settings())

    return _call_api(run)


@mcp.tool()
def financial_cents_create_client(
    display_name: str,
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_address: str | None = None,
    contact_notes: str | None = None,
) -> str:
    """Create a client (POST /clients) using form fields."""

    def run() -> dict[str, Any]:
        return create_client(
            display_name=display_name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_address=contact_address,
            contact_notes=contact_notes,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_list_projects(
    order_by: ProjectOrderByField | None = "created_at",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    search_field: ProjectSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
    status: ProjectStatusFilter | None = "all",
) -> str:
    """List projects (paginated). Uses API fields ``is_closed`` / ``closed_at`` / ``closed_by`` for status.

    Set ``status`` to ``open`` or ``closed`` to return only those rows (filtered on this page).
    Search params are used only when all three search arguments are set."""

    def run() -> dict[str, Any]:
        return list_projects(
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            search_field=search_field,
            search_operation=search_operation,
            search_value=search_value,
            status=status,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_list_project_resources(
    project_id: str | int,
    order_by: ProjectResourceOrderByField | None = None,
    order_dir: OrderDirection | None = None,
    search_field: ProjectResourceSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
) -> str:
    """List resources (links) for a project (GET /projects/{project_id}/resources).

    Optional sort: ``order_by`` one of ``created_at``, ``label``, ``list_index``;
    ``order_dir`` ``asc`` or ``desc``. Search applies only when ``search_field``,
    ``search_operation``, and ``search_value`` are all set (search field is typically ``label``)."""

    def run() -> dict[str, Any]:
        return list_project_resources(
            project_id,
            order_by=order_by,
            order_dir=order_dir,
            search_field=search_field,
            search_operation=search_operation,
            search_value=search_value,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_list_client_resources(
    client_id: str | int,
    order_by: ClientResourceOrderByField | None = None,
    order_dir: OrderDirection | None = None,
    search_field: ClientResourceSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
) -> str:
    """List resources (links) for a client (GET /clients/{client_id}/resources).

    Optional sort: ``order_by`` one of ``created_at``, ``label``, ``list_index``;
    ``order_dir`` ``asc`` or ``desc``. Search applies only when ``search_field``,
    ``search_operation``, and ``search_value`` are all set (search field is typically ``label``)."""

    def run() -> dict[str, Any]:
        return list_client_resources(
            client_id,
            order_by=order_by,
            order_dir=order_dir,
            search_field=search_field,
            search_operation=search_operation,
            search_value=search_value,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_list_client_tasks(
    order_by: ClientTaskOrderByField | None = "due_date",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    project_status: ProjectStatusFilter | None = "all",
    is_completed: bool | None = None,
    limit: int | None = None,
    search_field: ClientTaskSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
) -> str:
    """List client tasks (GET /client-tasks). Optional ``project_status`` filters by open/closed parent project.

    Sort by ``due_date``; optional ``is_completed``, ``limit`` (often 10–200), search on ``title`` or ``client_name``.
    Search params are used only when all three search arguments are set."""

    def run() -> dict[str, Any]:
        return list_client_tasks(
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            project_status=project_status,
            is_completed=is_completed,
            limit=limit,
            search_field=search_field,
            search_operation=search_operation,
            search_value=search_value,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_list_time_activities(
    date_range_start: str | None = None,
    date_range_end: str | None = None,
    client_id: int | None = None,
    user_id: int | None = None,
) -> str:
    """List time entries (GET /time-activities). Optional filters: date range (YYYY-MM-DD), client, user."""

    def run() -> dict[str, Any]:
        return list_time_activities(
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            client_id=client_id,
            user_id=user_id,
            settings=_settings(),
        )

    return _call_api(run)


@mcp.tool()
def financial_cents_list_invoices(
    order_by: InvoiceOrderByField | None = "due_date",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
) -> str:
    """List invoices (paginated) (GET /invoices)."""

    def run() -> dict[str, Any]:
        return list_invoices(
            order_by=order_by,
            order_dir=order_dir,
            page=page,
            settings=_settings(),
        )

    return _call_api(run)


# -------------------------
# SharePoint (Microsoft Graph) tools
# -------------------------


@mcp.tool()
def sharepoint_check_connection() -> str:
    """Resolve SharePoint site+drive using env and return basic info."""

    def run() -> dict[str, Any]:
        p = SharePointProvider()
        site_id, drive_id = p._resolve_site_and_drive()
        return {
            "ok": True,
            "site": {"host": p.site_host, "path": p.site_path, "id": site_id},
            "drive": {"name": p.drive_name, "id": drive_id},
        }

    # SharePointProvider raises RuntimeError for config/auth errors
    try:
        return _ok_payload(run())
    except RuntimeError as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_list_root() -> str:
    """List folders/files under the SharePoint drive root."""

    try:
        p = SharePointProvider()
        folders, files = p.list_folder_children("root")
        return _ok_payload(
            {"folders": [f.__dict__ for f in folders], "files": [f.__dict__ for f in files]}
        )
    except RuntimeError as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_list_folder(folder_id: str) -> str:
    """List children under a SharePoint folder id (use 'root' for drive root)."""

    try:
        p = SharePointProvider()
        folders, files = p.list_folder_children(folder_id)
        return _ok_payload(
            {
                "folder_id": folder_id,
                "folders": [f.__dict__ for f in folders],
                "files": [f.__dict__ for f in files],
            }
        )
    except (RuntimeError, FileNotFoundError) as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_find_client_folder(folder_name: str) -> str:
    """Find a folder by name anywhere under the drive (Graph search)."""

    try:
        p = SharePointProvider()
        folder = p.find_client_folder(folder_name)
        return _ok_payload({"folder": folder.__dict__})
    except (RuntimeError, FileNotFoundError) as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_resolve_folder_chain(folder_names: list[str]) -> str:
    """Resolve nested folders under root by exact segment names."""

    try:
        p = SharePointProvider()
        folder = p.resolve_folder_chain("root", folder_names)
        return _ok_payload({"folder": folder.__dict__})
    except (RuntimeError, FileNotFoundError) as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_get_file_metadata(file_id: str) -> str:
    """Get SharePoint file metadata by item id."""

    try:
        p = SharePointProvider()
        meta = p.get_file_metadata(file_id)
        return _ok_payload({"file": meta.__dict__})
    except (RuntimeError, FileNotFoundError) as e:
        return _error_payload("sharepoint_error", str(e))


def _coalesce_file_id(*, file_id: str | None = None, item_id: str | None = None) -> str:
    """Accept both parameter names used by different clients (Claude often uses item_id)."""
    fid = (file_id or "").strip()
    iid = (item_id or "").strip()
    chosen = fid or iid
    if not chosen:
        raise ValueError("file_id is required (alias: item_id).")
    if any(ch in chosen for ch in ("<", ">", "\"", "'", " ")):
        raise ValueError(
            "Invalid file_id/item_id. Use the real Graph item id (no '<FILE_ID>' placeholders)."
        )
    return chosen


def _find_file_by_name_in_folder(
    *,
    provider: SharePointProvider,
    folder_id: str,
    file_name: str,
) -> dict[str, Any]:
    """
    Find a file (case-insensitive) among direct children of a folder.
    Returns FileEntry.__dict__ of the match.
    """
    _, files = provider.list_folder_children(folder_id)
    target = (file_name or "").strip().lower()
    if not target:
        raise FileNotFoundError("file_name is required.")
    for f in files:
        if (f.name or "").strip().lower() == target:
            return f.__dict__
    raise FileNotFoundError(f"File not found in folder: {file_name}")


@mcp.tool()
def sharepoint_list_ty_folder() -> str:
    """
    List folders/files under the configured TY folder name.

    Env: SHAREPOINT_TY_FOLDER (default: 'Financial Cents Document').
    """
    try:
        p = SharePointProvider()
        ty_name = (os.getenv(_DEFAULT_TY_FOLDER_ENV, "Financial Cents Document") or "").strip()
        folder = p.find_client_folder(ty_name)
        folders, files = p.list_folder_children(folder.id)
        return _ok_payload(
            {
                "folder_name": ty_name,
                "folder_id": folder.id,
                "folders": [x.__dict__ for x in folders],
                "files": [x.__dict__ for x in files],
            }
        )
    except (RuntimeError, FileNotFoundError) as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_download_file(
    file_id: str | None = None,
    *,
    item_id: str | None = None,
    download_path: str | None = None,
    contact_key: str | None = None,
    overwrite: bool = False,
) -> str:
    """
    Download a SharePoint file (drive item id) to local disk.

    - **file_id**: Graph driveItem id (alias: item_id)
    - **download_path**: local directory; defaults to <repo>/downloads
    - **contact_key**: optional subfolder name to group downloads
    - **overwrite**: if false and file exists, returns skipped
    """
    try:
        fid = _coalesce_file_id(file_id=file_id, item_id=item_id)
        p = SharePointProvider()
        meta = p.get_file_metadata(fid)

        base_dir = _download_base_dir(download_path)
        subdir = _sanitize_filename(contact_key) if contact_key else ""
        safe_name = _sanitize_filename(meta.name)
        out_path = _safe_join(base_dir, subdir, safe_name) if subdir else _safe_join(base_dir, safe_name)

        if out_path.exists() and not overwrite:
            return _ok_payload(
                {
                    "status": "skipped",
                    "reason": "file_exists",
                    "file_id": fid,
                    "file_name": meta.name,
                    "local_path": str(out_path),
                    "bytes_written": 0,
                }
            )

        stream = p.get_file_stream(fid)
        bytes_written = _write_stream_to_file(stream=stream, target_path=out_path)
        return _ok_payload(
            {
                "status": "success",
                "file_id": fid,
                "file_name": meta.name,
                "expected_size": getattr(meta, "size", None),
                "bytes_written": bytes_written,
                "local_path": str(out_path),
            }
        )
    except (RuntimeError, FileNotFoundError, ValueError, OSError) as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def sharepoint_download_file_by_name(
    file_name: str,
    *,
    folder_id: str | None = None,
    ty_folder_name: str | None = None,
    download_path: str | None = None,
    contact_key: str | None = None,
    overwrite: bool = False,
) -> str:
    """
    Download a file by name from a folder.

    If **folder_id** is omitted, resolves the TY folder first using:
    - ty_folder_name (if provided), else env SHAREPOINT_TY_FOLDER, else default.
    """
    try:
        p = SharePointProvider()
        effective_folder_id = (folder_id or "").strip()
        if not effective_folder_id:
            name = (
                (ty_folder_name or "").strip()
                or (os.getenv(_DEFAULT_TY_FOLDER_ENV, "Financial Cents Document") or "").strip()
            )
            folder = p.find_client_folder(name)
            effective_folder_id = folder.id

        file_entry = _find_file_by_name_in_folder(
            provider=p,
            folder_id=effective_folder_id,
            file_name=file_name,
        )
        fid = str(file_entry.get("id") or "").strip()
        if not fid:
            raise FileNotFoundError(f"Unable to resolve file id for: {file_name}")

        return sharepoint_download_file(
            file_id=fid,
            download_path=download_path,
            contact_key=contact_key,
            overwrite=overwrite,
        )
    except (RuntimeError, FileNotFoundError, ValueError, OSError) as e:
        return _error_payload("sharepoint_error", str(e))


def _download_folder_recursive(
    *,
    provider: SharePointProvider,
    folder_id: str,
    base_dir: Path,
    relative_dir_parts: list[str],
    recursive: bool,
    overwrite: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Returns (downloaded_files, errors).
    """
    downloaded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    folders, files = provider.list_folder_children(folder_id)
    for f in files:
        try:
            safe_name = _sanitize_filename(f.name)
            target_dir = _safe_join(base_dir, *relative_dir_parts) if relative_dir_parts else base_dir.resolve()
            out_path = _safe_join(target_dir, safe_name)

            if out_path.exists() and not overwrite:
                downloaded.append(
                    {
                        "status": "skipped",
                        "reason": "file_exists",
                        "file_id": f.id,
                        "file_name": f.name,
                        "local_path": str(out_path),
                        "bytes_written": 0,
                    }
                )
                continue

            stream = provider.get_file_stream(f.id)
            bytes_written = _write_stream_to_file(stream=stream, target_path=out_path)
            downloaded.append(
                {
                    "status": "success",
                    "file_id": f.id,
                    "file_name": f.name,
                    "local_path": str(out_path),
                    "bytes_written": bytes_written,
                }
            )
        except Exception as e:  # keep walking the folder
            errors.append(
                {
                    "folder_id": folder_id,
                    "file_id": getattr(f, "id", None),
                    "file_name": getattr(f, "name", None),
                    "error": str(e),
                }
            )

    if recursive:
        for sub in folders:
            try:
                sub_dir_parts = [*relative_dir_parts, _sanitize_filename(sub.name)]
                d2, e2 = _download_folder_recursive(
                    provider=provider,
                    folder_id=sub.id,
                    base_dir=base_dir,
                    relative_dir_parts=sub_dir_parts,
                    recursive=True,
                    overwrite=overwrite,
                )
                downloaded.extend(d2)
                errors.extend(e2)
            except Exception as e:
                errors.append(
                    {
                        "folder_id": folder_id,
                        "subfolder_id": getattr(sub, "id", None),
                        "subfolder_name": getattr(sub, "name", None),
                        "error": str(e),
                    }
                )

    return downloaded, errors


@mcp.tool()
def sharepoint_download_folder(
    folder_id: str,
    *,
    download_path: str | None = None,
    local_subdir: str | None = None,
    recursive: bool = True,
    overwrite: bool = False,
) -> str:
    """
    Download all files in a SharePoint folder to local disk.

    - **folder_id**: Graph driveItem id of the folder (use 'root' for drive root)
    - **download_path**: local base directory (default: <repo>/downloads)
    - **local_subdir**: optional local subfolder under download_path
    - **recursive**: if true, downloads subfolders recursively
    - **overwrite**: if false, skip files that already exist locally
    """
    try:
        if not (folder_id or "").strip():
            raise ValueError("folder_id is required.")

        p = SharePointProvider()
        base_dir = _download_base_dir(download_path)
        parts: list[str] = []
        if local_subdir and local_subdir.strip():
            parts = [_sanitize_filename(local_subdir)]
        effective_base = _safe_join(base_dir, *parts) if parts else base_dir
        effective_base.mkdir(parents=True, exist_ok=True)

        downloaded, errors = _download_folder_recursive(
            provider=p,
            folder_id=folder_id.strip(),
            base_dir=effective_base,
            relative_dir_parts=[],
            recursive=bool(recursive),
            overwrite=bool(overwrite),
        )
        return _ok_payload(
            {
                "status": "success",
                "folder_id": folder_id,
                "download_path": str(effective_base),
                "recursive": bool(recursive),
                "overwrite": bool(overwrite),
                "downloaded_count": len([x for x in downloaded if x.get("status") == "success"]),
                "skipped_count": len([x for x in downloaded if x.get("status") == "skipped"]),
                "error_count": len(errors),
                "files": downloaded,
                "errors": errors,
            }
        )
    except (RuntimeError, FileNotFoundError, ValueError, OSError) as e:
        return _error_payload("sharepoint_error", str(e))


@mcp.tool()
def local_extract_pdf_text(
    local_path: str,
    *,
    max_pages: int | None = 25,
    max_chars: int | None = 200_000,
    include_pages: bool = False,
) -> str:
    """
    Extract text from a local PDF file path and return JSON.

    This is text extraction (not OCR). For scanned PDFs, extracted text may be empty.
    """
    try:
        result = extract_pdf_text(
            local_path,
            max_pages=max_pages,
            max_chars=max_chars,
            include_pages=bool(include_pages),
        )
        return _ok_payload(
            {
                "status": "success",
                "file_path": result.file_path,
                "page_count": result.page_count,
                "extracted_char_count": result.extracted_char_count,
                "text": result.text,
                "pages": result.pages,
            }
        )
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as e:
        return _error_payload("pdf_extract_error", str(e))


@mcp.tool()
def sharepoint_download_and_extract_pdf_text(
    file_id: str | None = None,
    *,
    item_id: str | None = None,
    download_path: str | None = None,
    contact_key: str | None = None,
    overwrite: bool = False,
    max_pages: int | None = 25,
    max_chars: int | None = 200_000,
    include_pages: bool = False,
) -> str:
    """
    Download a SharePoint PDF and extract text (no OCR).

    Parameters:
    - file_id (alias: item_id): Graph driveItem id
    - download_path/contact_key/overwrite: same as sharepoint_download_file
    - max_pages/max_chars/include_pages: bounds for extracted text payload
    """
    downloaded = json.loads(
        sharepoint_download_file(
            file_id=file_id,
            item_id=item_id,
            download_path=download_path,
            contact_key=contact_key,
            overwrite=overwrite,
        )
    )

    if downloaded.get("error"):
        return _ok_payload({"download": downloaded, "extract": None})

    local_path = str(downloaded.get("local_path") or "").strip()
    if not local_path:
        return _error_payload("pdf_extract_error", "Download did not return local_path.")

    extracted = json.loads(
        local_extract_pdf_text(
            local_path,
            max_pages=max_pages,
            max_chars=max_chars,
            include_pages=include_pages,
        )
    )
    return _ok_payload({"download": downloaded, "extract": extracted})




