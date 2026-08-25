from __future__ import annotations

import io
from typing import Iterable

from pypdf import PdfReader, PdfWriter


class PDFMergeError(Exception):
    def __init__(self, code: str, label: str = ''):
        self.code=code;self.label=label
        super().__init__(f'{code}:{label}' if label else code)


def _reader(data: bytes, label: str) -> PdfReader:
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise PDFMergeError('invalid_pdf', label)
    try:
        reader = PdfReader(io.BytesIO(bytes(data)), strict=True)
    except Exception as exc:
        raise PDFMergeError('invalid_pdf', label) from exc
    if reader.is_encrypted:
        raise PDFMergeError('encrypted_pdf_not_supported', label)
    try:
        # Force page-tree parsing before the writer is touched.
        len(reader.pages)
    except Exception as exc:
        raise PDFMergeError('invalid_pdf', label) from exc
    return reader


def merge_pdf_documents(
    base_pdf: bytes,
    attachments: Iterable[tuple[str, bytes]],
    *,
    max_attachment_bytes: int = 15 * 1024 * 1024,
    max_total_bytes: int = 40 * 1024 * 1024,
    max_total_pages: int = 250,
) -> bytes:
    """Append validated PDF attachments to a generated base document.

    The function is deliberately fail-closed: malformed/encrypted documents,
    size-budget violations, and page-budget violations abort the whole merge so
    a generated meeting pack can never silently omit configured evidence.
    """
    if max_attachment_bytes < 1 or max_total_bytes < 1 or max_total_pages < 1:
        raise ValueError('pdf_merge_limits_must_be_positive')

    base = bytes(base_pdf or b'')
    if len(base) > max_total_bytes:
        raise PDFMergeError('pdf_bundle_too_large', 'base')
    base_reader = _reader(base, 'base')
    writer = PdfWriter()
    metadata=dict(base_reader.metadata or {})
    if metadata:
        writer.add_metadata({str(k):str(v) for k,v in metadata.items() if k and v is not None})
    total_bytes = len(base)
    total_pages = len(base_reader.pages)
    if total_pages > max_total_pages:
        raise PDFMergeError('pdf_page_limit_exceeded', 'base')
    for page in base_reader.pages:
        writer.add_page(page)

    for raw_label, raw_data in attachments:
        label = str(raw_label or 'attachment')[:160]
        data = bytes(raw_data or b'')
        if len(data) > max_attachment_bytes:
            raise PDFMergeError('pdf_attachment_too_large', label)
        total_bytes += len(data)
        if total_bytes > max_total_bytes:
            raise PDFMergeError('pdf_bundle_too_large', label)
        reader = _reader(data, label)
        total_pages += len(reader.pages)
        if total_pages > max_total_pages:
            raise PDFMergeError('pdf_page_limit_exceeded', label)
        for page in reader.pages:
            writer.add_page(page)

    output = io.BytesIO()
    try:
        writer.write(output)
    except Exception as exc:
        raise PDFMergeError('pdf_merge_failed') from exc
    merged = output.getvalue()
    if not merged.startswith(b'%PDF-'):
        raise PDFMergeError('pdf_merge_failed')
    return merged
