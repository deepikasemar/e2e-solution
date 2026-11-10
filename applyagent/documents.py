"""In-memory sample resume files for download and parser tests."""

from __future__ import annotations

import io


def text_pdf(text: str) -> bytes:
    """A one-page text PDF that pdfplumber can read. ASCII only."""
    lines: list[str] = []
    for raw in text.splitlines():
        raw = raw.replace("\t", "    ")
        if not raw.strip():
            lines.append("")
            continue
        while len(raw) > 90:
            cut = raw.rfind(" ", 0, 90)
            if cut < 20:
                cut = 90
            lines.append(raw[:cut])
            raw = raw[cut:].strip()
        lines.append(raw)
    lines = lines[:48]
    ops = ["BT", "/F1 11 Tf", "54 760 Td"]
    for index, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            ops.append("0 -14 Td")
        ops.append(f"({safe}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("ascii", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def text_docx(text: str) -> bytes:
    from docx import Document

    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
