from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, List, Optional, Protocol


@dataclass
class FolderEntry:
    id: str
    name: str
    path: str
    web_url: Optional[str] = None


@dataclass
class FileEntry:
    id: str
    name: str
    path: str
    size: int = 0
    mime_type: Optional[str] = None
    web_url: Optional[str] = None


class DocumentSourceProvider(Protocol):
    source_name: str

    def find_client_folder(self, folder_name: str) -> FolderEntry: ...
    def list_folders(self, parent_folder_id: str) -> List[FolderEntry]: ...
    def list_files(self, parent_folder_id: str) -> List[FileEntry]: ...
    def get_file_stream(self, file_id: str) -> BinaryIO: ...
    def get_file_metadata(self, file_id: str) -> FileEntry: ...

