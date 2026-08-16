"""위키문헌·Gutenberg 원문 정제 로직.

여기서 놓치면 원문이 조용히 잘려나간 채로 커밋된다 — 실제로 한 번
그랬다: "== 1 ==", "== 2 =="처럼 장 번호로 나뉜 작품(탈출기·뽕)에서
2장 헤딩을 "== 라이선스 ==" 같은 상용구로 오인해 2장부터 통째로
잘라낸 적이 있다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_sources import (  # noqa: E402
    _TRAILING_SECTION,
    _clean_gutenberg_text,
    extract_excerpt,
    FetchError,
)


class TestTrailingSectionRegex:
    def test_strips_known_boilerplate_heading(self):
        text = "본문 내용입니다.\n\n== 라이선스 ==\n\n이 저작물은..."
        match = _TRAILING_SECTION.search(text)
        assert match is not None
        assert text[: match.start()].strip() == "본문 내용입니다."

    def test_strips_copyright_heading_case_insensitively(self):
        text = "본문.\n\n== License ==\n\nCC-BY-SA"
        assert _TRAILING_SECTION.search(text) is not None

    def test_does_not_strip_numbered_chapter_headings(self):
        # 실제로 터졌던 버그: "== 2 =="를 상용구로 오인해 2장부터 날아갔다.
        text = "== 1 ==\n1장 내용입니다.\n\n== 2 ==\n2장 내용입니다."
        assert _TRAILING_SECTION.search(text) is None

    def test_does_not_strip_arbitrary_story_headings(self):
        text = "== 프롤로그 ==\n시작.\n\n== 1화 ==\n본편."
        assert _TRAILING_SECTION.search(text) is None


class TestExtractExcerpt:
    def test_slices_between_markers(self):
        # after 문자열 자체는 결과에 포함된다 — 실제로 excerpt_after에는
        # "True!—nervous..."처럼 작품의 진짜 첫 단어를 넣기 때문이다.
        text = "머리말\n\nSTART본문 내용입니다END\n\n꼬리말"
        assert extract_excerpt(text, "START", "END") == "START본문 내용입니다"

    def test_searches_for_before_marker_after_the_after_marker(self):
        # 목차에도 같은 제목이 나오므로, before는 반드시 after 위치부터 찾아야
        # 목차(앞쪽)가 아니라 다음 작품 제목(뒤쪽)을 잡는다.
        text = "목차: END\n\nSTART본문END\n\n다음 장"
        assert extract_excerpt(text, "START", "END") == "START본문"

    def test_missing_after_marker_raises(self):
        with pytest.raises(FetchError, match="excerpt_after"):
            extract_excerpt("아무 내용", "START", "END")

    def test_missing_before_marker_raises(self):
        with pytest.raises(FetchError, match="excerpt_before"):
            extract_excerpt("STARTonly", "START", "END")


class TestCleanGutenbergText:
    def test_rewraps_fixed_width_paragraphs_into_one_line(self):
        text = "  This is a line\n  that wraps.\n\n  Second paragraph\n  continues."
        cleaned = _clean_gutenberg_text(text)
        assert cleaned == "This is a line that wraps.\n\nSecond paragraph continues."

    def test_strips_italic_markup(self):
        assert "_word_" not in _clean_gutenberg_text("This is _word_ emphasized.")
        assert "word" in _clean_gutenberg_text("This is _word_ emphasized.")

    def test_normalizes_windows_line_endings(self):
        assert "\r" not in _clean_gutenberg_text("line one\r\nline two\r\n")
