from __future__ import annotations

from pathlib import Path

import pytest

from mcp_fc.pdf_tools import extract_pdf_text


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "rel_path",
    [
        Path("downloads") / "f1065-1.pdf",
        Path("downloads") / "2024 1065 _GOODOB LLC_.pdf",
    ],
)
def test_extract_pdf_text_smoke(rel_path: Path) -> None:
    p = (_repo_root() / rel_path).resolve()
    if not p.exists():
        pytest.skip(f"Test PDF not present: {p}")

    result = extract_pdf_text(p, max_pages=2, max_chars=50_000, include_pages=True)

    assert result.file_path.lower().endswith(".pdf")
    assert result.page_count >= 1
    assert result.extracted_char_count == len(result.text)
    assert result.pages is not None


def test_extract_pdf_text_rejects_non_pdf(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        extract_pdf_text(f)

