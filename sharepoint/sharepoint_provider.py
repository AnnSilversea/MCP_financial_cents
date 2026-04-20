from __future__ import annotations

import base64
import io
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import msal

from .base import FileEntry, FolderEntry


class SharePointProvider:
    source_name = "sharepoint"

    _graph_lock = threading.Lock()
    _msal_lock = threading.Lock()
    _msal_apps: Dict[Tuple[str, str], msal.ConfidentialClientApplication] = {}
    _resolved_key: Optional[Tuple[str, str, str, str, str]] = None
    _site_id_cached: Optional[str] = None
    _drive_id_cached: Optional[str] = None

    _http_lock = threading.Lock()
    _http_client: Optional[httpx.Client] = None
    _http_client_redirects: Optional[httpx.Client] = None

    _token_lock = threading.Lock()
    # key: (tenant_id, client_id) -> (token, expires_at_epoch_seconds)
    _token_cache: Dict[Tuple[str, str], Tuple[str, float]] = {}

    def __init__(self) -> None:
        self.tenant_id = self._require("TENANT_ID")
        self.client_id = self._require("CLIENT_ID")
        self.client_secret = self._require("CLIENT_SECRET")
        self.site_host = os.getenv("SHAREPOINT_SITE_HOST", "1vwr10.sharepoint.com").strip()
        self.site_path = os.getenv("SHAREPOINT_SITE_PATH", "/sites/Automation").strip()
        self.drive_name = os.getenv("SHAREPOINT_DRIVE_NAME", "Documents").strip()
        self.timeout = int(os.getenv("SHAREPOINT_TIMEOUT_SECONDS", "60"))

    @staticmethod
    def _require(name: str) -> str:
        # Backward/compat: allow AZURE_* envs used elsewhere
        fallback_map = {
            "TENANT_ID": "AZURE_TENANT_ID",
            "CLIENT_ID": "AZURE_CLIENT_ID",
            "CLIENT_SECRET": "AZURE_CLIENT_SECRET",
        }
        value = os.getenv(name) or os.getenv(fallback_map.get(name, ""), "")
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value

    def _msal_app(self) -> msal.ConfidentialClientApplication:
        key = (self.tenant_id, self.client_id)
        with SharePointProvider._msal_lock:
            app = SharePointProvider._msal_apps.get(key)
            if app is None:
                authority = f"https://login.microsoftonline.com/{self.tenant_id}"
                app = msal.ConfidentialClientApplication(
                    client_id=self.client_id,
                    authority=authority,
                    client_credential=self.client_secret,
                )
                SharePointProvider._msal_apps[key] = app
            return app

    def _shared_http(self, *, follow_redirects: bool) -> httpx.Client:
        """
        Return shared HTTP client(s) for Graph calls to keep connections warm.
        """
        with SharePointProvider._http_lock:
            if follow_redirects:
                c = SharePointProvider._http_client_redirects
                if c is None or c.is_closed:
                    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
                    c = httpx.Client(timeout=self.timeout, follow_redirects=True, limits=limits)
                    SharePointProvider._http_client_redirects = c
                else:
                    c.timeout = self.timeout
                return c

            c = SharePointProvider._http_client
            if c is None or c.is_closed:
                limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
                c = httpx.Client(timeout=self.timeout, limits=limits)
                SharePointProvider._http_client = c
            else:
                c.timeout = self.timeout
            return c

    def _get_token(self) -> str:
        """
        Acquire and cache a Graph access token.

        MSAL has its own internal token cache, but caching here avoids repeated
        work across short-lived provider instances and reduces latency.
        """
        key = (self.tenant_id, self.client_id)
        now = time.time()
        with SharePointProvider._token_lock:
            cached = SharePointProvider._token_cache.get(key)
            if cached:
                token, expires_at = cached
                # 60s safety margin to avoid mid-request expiry.
                if token and (expires_at - 60) > now:
                    return token

        result = self._msal_app().acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        token = result.get("access_token")
        if not token:
            detail = result.get("error_description") or result.get("error") or "unknown"
            raise RuntimeError(f"Unable to acquire Graph access token: {detail}")

        expires_in = result.get("expires_in")
        try:
            ttl = float(expires_in) if expires_in is not None else 3600.0
        except (TypeError, ValueError):
            ttl = 3600.0
        expires_at = now + max(60.0, ttl)
        with SharePointProvider._token_lock:
            SharePointProvider._token_cache[key] = (token, expires_at)
        return token

    def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Accept"] = "application/json"

        def _do_request(token: str):
            call_headers = dict(headers)
            call_headers["Authorization"] = f"Bearer {token}"
            client = self._shared_http(follow_redirects=False)
            return client.request(method, url, headers=call_headers, **kwargs)

        token = self._get_token()
        response = _do_request(token)
        if response.status_code == 401:
            token = self._get_token()
            response = _do_request(token)

        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
                err = payload["error"]
                code = err.get("code") or "unknown"
                message = err.get("message") or "unknown"
                inner = err.get("innerError") or {}
                req_id = inner.get("request-id") or inner.get("requestId")
                date = inner.get("date")
                extra = []
                if req_id:
                    extra.append(f"request-id={req_id}")
                if date:
                    extra.append(f"date={date}")
                hint = ""
                if response.status_code in (401, 403):
                    hint = (
                        " Check Azure AD app permissions (Microsoft Graph application permissions like "
                        "Sites.Read.All / Sites.ReadWrite.All and grant admin consent), and verify "
                        "TENANT_ID/CLIENT_ID/CLIENT_SECRET are for the same tenant."
                    )
                extra_txt = f" ({', '.join(extra)})" if extra else ""
                raise RuntimeError(f"Graph API {response.status_code} {code}: {message}{extra_txt}.{hint}")
            raise RuntimeError(f"Graph API {response.status_code}: {payload}")

        if response.status_code == 204 or not response.text.strip():
            return {}
        return response.json()

    def _resolution_cache_key(self) -> Tuple[str, str, str, str, str]:
        return (
            self.tenant_id,
            self.client_id,
            self.site_host.lower(),
            self.site_path,
            self.drive_name.lower(),
        )

    def _resolve_site_and_drive(self) -> Tuple[str, str]:
        key = self._resolution_cache_key()
        with SharePointProvider._graph_lock:
            if (
                SharePointProvider._resolved_key == key
                and SharePointProvider._site_id_cached
                and SharePointProvider._drive_id_cached
            ):
                return SharePointProvider._site_id_cached, SharePointProvider._drive_id_cached

        url_site = f"https://graph.microsoft.com/v1.0/sites/{self.site_host}:{self.site_path}"
        payload_site = self._request("GET", url_site)
        site_id = payload_site.get("id")
        if not site_id:
            raise RuntimeError("Could not resolve SharePoint site id.")

        url_drives = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        payload_drives = self._request("GET", url_drives)
        drives = payload_drives.get("value") or []
        if not drives:
            raise RuntimeError("No drives found in SharePoint site.")

        selected = None
        for drive in drives:
            if (drive.get("name") or "").strip().lower() == self.drive_name.lower():
                selected = drive
                break
        if not selected:
            selected = drives[0]
        drive_id = selected.get("id")
        if not drive_id:
            raise RuntimeError("Could not resolve SharePoint drive id.")

        with SharePointProvider._graph_lock:
            if (
                SharePointProvider._resolved_key == key
                and SharePointProvider._site_id_cached
                and SharePointProvider._drive_id_cached
            ):
                return SharePointProvider._site_id_cached, SharePointProvider._drive_id_cached
            SharePointProvider._resolved_key = key
            SharePointProvider._site_id_cached = site_id
            SharePointProvider._drive_id_cached = drive_id

        return site_id, drive_id

    def _resolve_site_id(self) -> str:
        return self._resolve_site_and_drive()[0]

    def _resolve_drive_id(self) -> str:
        return self._resolve_site_and_drive()[1]

    @staticmethod
    def _display_path_from_graph(full_path: str) -> str:
        """Strip Graph drive prefix (segment before root:) so UI shows only the folder path."""
        fp = (full_path or "").strip().strip("/")
        idx = fp.lower().find("root:")
        if idx != -1:
            return fp[idx + len("root:") :].lstrip("/")
        return fp

    @staticmethod
    def _folder_entry(item: Dict[str, Any]) -> FolderEntry:
        parent_path = ((item.get("parentReference") or {}).get("path") or "").strip()
        raw = f"{parent_path}/{item.get('name', '')}".strip("/")
        full_path = SharePointProvider._display_path_from_graph(raw)
        return FolderEntry(
            id=str(item.get("id") or ""),
            name=str(item.get("name") or ""),
            path=full_path,
            web_url=item.get("webUrl"),
        )

    @staticmethod
    def _file_entry(item: Dict[str, Any]) -> FileEntry:
        parent_path = ((item.get("parentReference") or {}).get("path") or "").strip()
        raw = f"{parent_path}/{item.get('name', '')}".strip("/")
        full_path = SharePointProvider._display_path_from_graph(raw)
        return FileEntry(
            id=str(item.get("id") or ""),
            name=str(item.get("name") or ""),
            path=full_path,
            size=int(item.get("size") or 0),
            mime_type=((item.get("file") or {}).get("mimeType")),
            web_url=item.get("webUrl"),
        )

    def find_client_folder(self, folder_name: str) -> FolderEntry:
        drive_id = self._resolve_drive_id()
        query = folder_name.replace("'", "''")
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{query}')?$top=200"
        payload = self._request("GET", url)
        items = payload.get("value") or []
        target = folder_name.strip().lower()

        exact_match = None
        for item in items:
            if not item.get("folder"):
                continue
            name = (item.get("name") or "").strip().lower()
            if name == target:
                exact_match = item
                break

        if not exact_match:
            raise FileNotFoundError(f"SharePoint client folder not found: {folder_name}")
        return self._folder_entry(exact_match)

    def list_folder_children(self, parent_folder_id: str) -> Tuple[List[FolderEntry], List[FileEntry]]:
        """
        Single Graph children request for both folders and files (avoids duplicate round-trips).
        """
        drive_id = self._resolve_drive_id()
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_folder_id}/children"
            "?$top=999&$select=id,name,webUrl,parentReference,size,folder,file"
        )
        payload = self._request("GET", url)
        values = payload.get("value") or []
        folders = [self._folder_entry(x) for x in values if x.get("folder")]
        files = [self._file_entry(x) for x in values if x.get("file")]
        folders.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())
        return folders, files

    def list_folders(self, parent_folder_id: str) -> List[FolderEntry]:
        return self.list_folder_children(parent_folder_id)[0]

    def list_files(self, parent_folder_id: str) -> List[FileEntry]:
        return self.list_folder_children(parent_folder_id)[1]

    def find_child_folder_by_name(self, parent_folder_id: str, folder_name: str) -> FolderEntry:
        """Find a direct child folder under parent by case-insensitive name."""
        target = (folder_name or "").strip().lower()
        if not target:
            raise FileNotFoundError("Folder name is required.")

        for folder in self.list_folders(parent_folder_id):
            if (folder.name or "").strip().lower() == target:
                return folder
        raise FileNotFoundError(f"Folder not found: {folder_name}")

    def resolve_folder_chain(self, root_folder_id: str, folder_names: List[str]) -> FolderEntry:
        """
        Resolve nested path by exact segment names:
        e.g. ["Tax", "TY 2025", "PBC Documents"].
        """
        current_id = root_folder_id
        current_folder: Optional[FolderEntry] = None
        for name in folder_names:
            current_folder = self.find_child_folder_by_name(current_id, name)
            current_id = current_folder.id
        if not current_folder:
            raise FileNotFoundError("Folder chain could not be resolved.")
        return current_folder

    def get_file_metadata(self, file_id: str) -> FileEntry:
        drive_id = self._resolve_drive_id()
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}"
            "?$select=id,name,webUrl,parentReference,size,file"
        )
        payload = self._request("GET", url)
        if not payload.get("file"):
            raise FileNotFoundError(f"Item is not a file: {file_id}")
        return self._file_entry(payload)

    def get_file_stream(self, file_id: str) -> io.BytesIO:
        drive_id = self._resolve_drive_id()
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
        headers = {"Accept": "*/*"}

        def _download(token: str):
            call_headers = dict(headers)
            call_headers["Authorization"] = f"Bearer {token}"
            client = self._shared_http(follow_redirects=True)
            return client.get(url, headers=call_headers)

        response = _download(self._get_token())
        if response.status_code == 401:
            response = _download(self._get_token())
        if response.status_code >= 400:
            raise RuntimeError(f"Failed to download file {file_id}: {response.status_code} {response.text}")
        return io.BytesIO(response.content)

    @staticmethod
    def _encode_share_url_to_share_id(share_url: str) -> str:
        """
        Convert a SharePoint sharing URL into a Graph /shares/{shareId} id.

        Graph expects: shareId = "u!" + base64url(share_url) with '=' padding removed.
        """
        raw = (share_url or "").strip()
        if not raw:
            raise ValueError("share_url is required.")
        b64 = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
        return "u!" + b64.rstrip("=")

    def resolve_drive_item_from_share_url(self, share_url: str) -> FileEntry:
        """
        Resolve a SharePoint sharing link to a driveItem, and return it as a FileEntry.
        """
        share_id = self._encode_share_url_to_share_id(share_url)
        url = (
            f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem"
            "?$select=id,name,webUrl,parentReference,size,file"
        )
        payload = self._request("GET", url)
        if not payload.get("file"):
            item_id = payload.get("id") or "(unknown)"
            raise FileNotFoundError(f"Shared link does not resolve to a file: {item_id}")
        return self._file_entry(payload)
