"""Knowledge-base parsing tests (no model involved)."""

from app.kb import all_sections, kb_fingerprint, parse_guide, slugify

EXPECTED_GUIDES = {"vpn-connection", "dns-resolution", "shared-drive-access", "printer-connectivity",
                   "backup-restore"}


def test_all_expected_guides_are_loaded(guides):
    assert {g.doc_id for g in guides} == EXPECTED_GUIDES


def test_every_guide_has_escalation_criteria(guides):
    for guide in guides:
        assert "escalation-criteria" in {s.anchor for s in guide.sections}, guide.doc_id


def test_section_ids_are_unique_and_link_to_anchors(guides):
    sections = all_sections(guides)
    ids = [s.id for s in sections]
    assert len(ids) == len(set(ids))
    for section in sections:
        assert section.id == f"{section.doc_id}#{section.anchor}"
        assert section.url == f"/kb/{section.doc_id}#{section.anchor}"
        assert section.text.strip(), section.id


def test_slugify():
    assert slugify("Escalation criteria") == "escalation-criteria"
    assert slugify("Reconnecting the S: drive") == "reconnecting-the-s-drive"


def test_fingerprint_changes_when_content_changes(tmp_path, guides):
    original = guides[0].path.read_text(encoding="utf-8")
    copy = tmp_path / guides[0].path.name
    modified = original.replace("## Escalation criteria", "## Escalation criteria\n\nExtra line.")
    assert modified != original
    copy.write_text(modified, encoding="utf-8")
    changed = [parse_guide(copy)] + guides[1:]
    assert kb_fingerprint(changed) != kb_fingerprint(guides)
