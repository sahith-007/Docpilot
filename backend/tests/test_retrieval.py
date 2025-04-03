from app.services.retrieval import LocalClinicalIndex


class FakeNote:
    id = "note-1"
    case_id = "case-1"
    note_type = "progress_note"
    note_date = "2026-01-01"
    title = "Progress"
    body = "BNP is elevated and chest x-ray shows vascular congestion. Plan is IV furosemide."


def test_local_index_returns_case_matched_evidence():
    index = LocalClinicalIndex()
    index.rebuild([FakeNote()])

    result = index.search("case-1", "heart failure BNP furosemide", limit=3)

    assert len(result) == 1
    assert result[0].note_id == "note-1"
    assert result[0].score > 0

