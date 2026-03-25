"""Utilities for turning a policy PDF into clause-ready ingestion objects.

This module owns the *document structuring* half of the pipeline:
PDF -> raw text -> normalized text -> clause chunks -> PolicyClause.
It does not try to understand rule meaning yet. That happens later in the
policy extraction layer.
"""

import re
from pathlib import Path

from pypdf import PdfReader

from models.policy_ingestion import PolicyClause


def extract_pdf_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Read a text-based PDF and return non-empty page text.

    Each item in the returned list is `(page_number, text)`.
    Keeping page numbers here is important because later extracted clauses
    and rules should remain traceable back to the source document.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []

    # Read one page at a time so we preserve source-page traceability.
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()

        if not text:
            continue

        pages.append((page_number, text))

    return pages


def normalize_pdf_text(text: str) -> str:
    """Clean PDF text while preserving useful document structure.

    We normalize whitespace, but we deliberately keep line breaks because
    headings and policy bullets often depend on line structure.
    """
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\t", " ")

    cleaned_lines = []

    # Clean each line without turning the whole page into one long sentence.
    for line in text.splitlines():
        line = re.sub(r"[ ]{2,}", " ", line.strip())
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    # Large blank gaps are usually PDF formatting noise, so compress them.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def look_like_heading(line: str) -> bool:
    """Heuristically decide whether a line is a section heading.

    This is intentionally lightweight. We only need a good first pass that
    catches obvious headings such as "Reporting Thresholds" and avoids
    treating full policy sentences as headings.
    """
    words = line.split()

    if not words:
        return False
    
    if len(words) > 8:
        return False
    
    if len(line) > 80:
        return False
    
    if line.endswith((".", ";", )):
        return False
    
    if any(char.isdigit() for char in line):
        return False
    
    # Sentences containing policy verbs are more likely to be real clauses
    # than headings.
    policy_words = {"must", "should", "shall", "required", "review", "flagged", "monitor"}

    if any(word.lower() in policy_words for word in words):
        return False
    
    capitalized_words = sum(1 for word in words if word[:1].isupper())
    return capitalized_words >= max(1, len(words) - 1) 


def split_sentence_like_parts(line: str) -> list[str]:
    """Split a line into sentence-like parts.

    This catches the common case where one PDF line actually contains multiple
    policy rules, such as a threshold sentence followed by a format sentence.
    """
    parts = re.split(r"(?<=[.;:])\s+", line)
    return [part.strip() for part in parts if part.strip()]


def split_text_into_clauses(page_text: str) -> list[tuple[str, str | None]]:
    """Split one normalized page into clause-sized chunks.

    Returns a list of `(clause_text, section_heading)` pairs.
    The section heading is carried forward so later stages can preserve
    document context for rule extraction and review.
    """

    clauses: list[tuple[str, str | None]] = []
    current_section_heading: str | None = None

    for raw_line in page_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        # Headings are stored as context for later clauses, not emitted as
        # clauses themselves.
        if look_like_heading(line):
            current_section_heading = line
            continue

        # Split obvious multi-sentence lines even when the overall line is short.
        sentence_parts = split_sentence_like_parts(line)
        if len(sentence_parts) >= 2:
            for part in sentence_parts:
                clauses.append((part, current_section_heading))
            continue

        # Keep short single-sentence lines as one clause.
        if len(line) <= 130:
            clauses.append((line, current_section_heading))
            continue

        # Long lines are often paragraph-like, so break them into smaller
        # sentence-style pieces before wrapping them as clauses.
        for part in sentence_parts:
            part = part.strip()
            if not part:
                continue
            clauses.append((part, current_section_heading))

    return clauses


def build_policy_clauses(
    source_document: str, pages: list[tuple[int, str]]
  ) -> list[PolicyClause]:
    """Convert page text into structured PolicyClause objects.

    This is the final boundary in Step 2 of the ingestion pipeline:
    we move from plain text into domain objects that later extraction stages
    can consume.
    """
    clauses: list[PolicyClause] = []

    for page_number, page_text in pages:
        normalized_text = normalize_pdf_text(page_text)
        page_clauses = split_text_into_clauses(normalized_text)

        for clause_index, (clause_text, section_heading) in enumerate(page_clauses, start=1):
            # Build stable, human-readable ids to make debugging and tracing
            # extracted clauses easier during development.
            clause_id = f"{Path(source_document).stem}_p{page_number}_c{clause_index}"
            clauses.append(
                PolicyClause(
                    clause_id=clause_id,
                    text=clause_text,
                    source_document=source_document,
                    page_number=page_number,
                    section_heading=section_heading,
                )
            )

    return clauses
