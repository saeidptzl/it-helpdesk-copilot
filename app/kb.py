"""Load the Markdown knowledge base and split each guide into sections.

Every guide is a Markdown file with a small front-matter block. Each `## Heading` becomes one
retrievable section with a stable id of the form `<guide-id>#<heading-anchor>`. The same anchor
is used in the rendered guide page, so a citation link always points at the cited section.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Section:
    id: str
    doc_id: str
    doc_title: str
    heading: str
    anchor: str
    text: str

    @property
    def url(self) -> str:
        return f"/kb/{self.doc_id}#{self.anchor}"

    def embedding_text(self) -> str:
        return f"{self.doc_title} - {self.heading}\n{self.text}"


@dataclass
class Guide:
    doc_id: str
    title: str
    path: Path
    meta: dict[str, str]
    intro: str
    sections: list[Section] = field(default_factory=list)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def _split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---\n"):
        return {}, raw
    end = raw.find("\n---\n", 4)
    if end == -1:
        return {}, raw
    meta: dict[str, str] = {}
    for line in raw[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, raw[end + 5 :]


def parse_guide(path: Path) -> Guide:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    doc_id = meta.get("id") or path.stem
    title = meta.get("title", "")

    intro_lines: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in body.splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            intro_lines.append(line)

    title = title or doc_id
    seen: set[str] = set()
    parsed: list[Section] = []
    for heading, lines in sections:
        anchor = slugify(heading)
        if anchor in seen:
            raise ValueError(f"{path.name}: duplicate section heading '{heading}'")
        seen.add(anchor)
        parsed.append(
            Section(
                id=f"{doc_id}#{anchor}",
                doc_id=doc_id,
                doc_title=title,
                heading=heading,
                anchor=anchor,
                text="\n".join(lines).strip(),
            )
        )
    return Guide(doc_id=doc_id, title=title, path=path, meta=meta,
                 intro="\n".join(intro_lines).strip(), sections=parsed)


def load_guides(kb_dir: Path) -> list[Guide]:
    guides = [parse_guide(p) for p in sorted(Path(kb_dir).glob("*.md"))]
    ids = [g.doc_id for g in guides]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Duplicate guide ids: {sorted(duplicates)}")
    return guides


def all_sections(guides: list[Guide]) -> list[Section]:
    return [s for g in guides for s in g.sections]


def kb_fingerprint(guides: list[Guide]) -> str:
    digest = hashlib.sha256()
    for section in all_sections(guides):
        digest.update(section.id.encode())
        digest.update(b"\0")
        digest.update(section.embedding_text().encode())
        digest.update(b"\0")
    return digest.hexdigest()[:16]
