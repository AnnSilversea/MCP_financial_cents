from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PdfExtractResult:
    file_path: str
    page_count: int
    extracted_char_count: int
    text: str
    pages: list[dict[str, Any]] | None = None


def _clamp_int(value: int | None, *, default: int, min_value: int, max_value: int) -> int:
    if value is None:
        return default
    v = int(value)
    if v < min_value:
        return min_value
    if v > max_value:
        return max_value
    return v


def extract_pdf_text(
    pdf_path: str | Path,
    *,
    max_pages: int | None = 25,
    max_chars: int | None = 200_000,
    include_pages: bool = False,
) -> PdfExtractResult:
    """
    Extract text from a PDF on disk.

    Notes:
    - This is text extraction (not OCR). Scanned PDFs may return little/no text.
    - Output is bounded by max_pages and max_chars for MCP payload safety.
    """

    # Local import to keep server startup light for non-PDF use cases.
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: pypdf. Install it (e.g., `uv add pypdf` or `pip install pypdf`)."
        ) from e

    p = Path(pdf_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"PDF not found: {p}")
    if not p.is_file():
        raise ValueError(f"Path is not a file: {p}")
    if p.suffix.lower() != ".pdf":
        raise ValueError("Only .pdf files are supported.")

    effective_max_pages = _clamp_int(max_pages, default=25, min_value=1, max_value=500)
    effective_max_chars = _clamp_int(max_chars, default=200_000, min_value=1_000, max_value=2_000_000)

    reader = PdfReader(str(p))
    total_pages = len(getattr(reader, "pages", []) or [])
    take_pages = min(total_pages, effective_max_pages)

    out_text_parts: list[str] = []
    pages_out: list[dict[str, Any]] | None = [] if include_pages else None

    char_budget = effective_max_chars
    for i in range(take_pages):
        page = reader.pages[i]
        try:
            page_text = page.extract_text() or ""
        except Exception:
            # Some PDFs have malformed content streams; keep going.
            page_text = ""

        if not page_text:
            if include_pages and pages_out is not None:
                pages_out.append({"page_index": i, "char_count": 0, "text": ""})
            continue

        if len(page_text) > char_budget:
            page_text = page_text[:char_budget]

        out_text_parts.append(page_text)
        char_budget -= len(page_text)

        if include_pages and pages_out is not None:
            pages_out.append({"page_index": i, "char_count": len(page_text), "text": page_text})

        if char_budget <= 0:
            break

    combined = "\n\n".join(out_text_parts).strip()
    return PdfExtractResult(
        file_path=str(p),
        page_count=total_pages,
        extracted_char_count=len(combined),
        text=combined,
        pages=pages_out,
    )

