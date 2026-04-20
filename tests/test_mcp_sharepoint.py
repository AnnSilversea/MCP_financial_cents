"""Tests for SharePoint tools inside mcp_fc (mocked provider)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from mcp_fc import server as sp_server
from sharepoint.base import FileEntry, FolderEntry


class TestSharePointMcp(unittest.TestCase):
    @patch("mcp_fc.server.SharePointProvider")
    def test_check_connection(self, provider_cls: MagicMock) -> None:
        inst = MagicMock()
        inst.site_host = "x.sharepoint.com"
        inst.site_path = "/sites/ClientHub"
        inst.drive_name = "Documents"
        inst._resolve_site_and_drive.return_value = ("site1", "drive1")
        provider_cls.return_value = inst

        raw = sp_server.sharepoint_check_connection()
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["site"]["id"], "site1")
        self.assertEqual(data["drive"]["id"], "drive1")

    @patch("mcp_fc.server.SharePointProvider")
    def test_list_root(self, provider_cls: MagicMock) -> None:
        inst = MagicMock()
        inst.list_folder_children.return_value = ([], [])
        provider_cls.return_value = inst

        raw = sp_server.sharepoint_list_root()
        data = json.loads(raw)
        self.assertEqual(data["folders"], [])
        self.assertEqual(data["files"], [])
        inst.list_folder_children.assert_called_once_with("root")

    @patch("mcp_fc.server.SharePointProvider")
    def test_download_file_writes_to_dir(self, provider_cls: MagicMock) -> None:
        inst = MagicMock()
        meta = MagicMock()
        meta.name = "example.txt"
        meta.size = 5
        inst.get_file_metadata.return_value = meta
        inst.get_file_stream.return_value = __import__("io").BytesIO(b"hello")
        provider_cls.return_value = inst

        with tempfile.TemporaryDirectory() as tmp:
            # ensure env var doesn't affect this test
            with patch.dict("os.environ", {"SHAREPOINT_TY_FOLDER": ""}, clear=False):
                raw = sp_server.sharepoint_download_file(
                    file_id="file-1",
                    download_path=tmp,
                    contact_key="c1",
                )
                data = json.loads(raw)
                self.assertEqual(data["status"], "success")
                self.assertTrue(os.path.isfile(data["local_path"]))
                with open(data["local_path"], "rb") as f:
                    self.assertEqual(f.read(), b"hello")

    


if __name__ == "__main__":
    unittest.main()

