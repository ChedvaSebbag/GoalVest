"""חלוקה ל-chunks של 800 תווים עם חפיפה של 120."""

from worker.chunking import split_text


def test_chunks_keep_size_and_overlap():
    chunks = split_text("א" * 2000)
    assert len(chunks) > 1
    assert all(len(chunk) <= 800 for chunk in chunks)
    assert len(chunks[0]) == 800
    assert chunks[1][:120] == chunks[0][-120:]


def test_split_prefers_a_paragraph_boundary():
    chunks = split_text(("א" * 500) + "\n\n" + ("ב" * 500))
    assert chunks[0].endswith("א")
    assert "ב" not in chunks[0]
    assert any("ב" in chunk for chunk in chunks[1:])


def test_empty_text_has_no_chunks():
    assert split_text("   \n\n  ") == []
