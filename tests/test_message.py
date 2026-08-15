"""말풍선 조립과 200자 제한."""

import pytest

from src.config import KAKAO_TEXT_LIMIT
from src.corpus import Segment, Selection, Work
from src.message import MessageTooLongError, OutgoingMessage, build_messages

KR_WORK = Work("kr_work", "kr", "운수 좋은 날", "현진건", "", "https://example.test/kr")
EN_WORK = Work(
    "en_work", "en", "오만과 편견", "제인 오스틴", "Pride and Prejudice",
    "https://example.test/en",
)


def kr_selection(text: str = "얼다가 만 비가 추적추적 내리었다.") -> Selection:
    return Selection("kr", KR_WORK, Segment("kr_work", 3, 12, text), 0)


def en_selection(note: str = "소설의 첫 문장.") -> Selection:
    return Selection(
        "en",
        EN_WORK,
        Segment("en_work", 2, 6, "It is a truth universally acknowledged", "누구나 인정하는 진리다", note),
        1,
    )


class TestKoreanTrack:
    def test_sends_a_single_bubble(self):
        assert len(build_messages(kr_selection())) == 1

    def test_header_carries_title_author_and_progress(self):
        message = build_messages(kr_selection())[0]
        assert message.text.startswith("📖 운수 좋은 날 — 현진건 (3/12)")

    def test_body_follows_a_blank_line(self):
        message = build_messages(kr_selection())[0]
        assert "\n\n얼다가 만 비가" in message.text

    def test_links_to_the_source(self):
        message = build_messages(kr_selection())[0]
        assert message.link_url == "https://example.test/kr"
        assert message.button_title == "원문 읽기"


class TestForeignTrack:
    def test_sends_original_then_reading(self):
        messages = build_messages(en_selection())
        assert len(messages) == 2
        assert messages[0].text.startswith("📖 Pride and Prejudice")
        assert messages[1].text.startswith("🔎 오만과 편견")

    def test_original_bubble_uses_the_original_title(self):
        original = build_messages(en_selection())[0]
        assert "Pride and Prejudice" in original.text
        assert "오만과 편견" not in original.text

    def test_reading_bubble_carries_translation_and_note(self):
        reading = build_messages(en_selection())[1]
        assert "누구나 인정하는 진리다" in reading.text
        assert "— 소설의 첫 문장." in reading.text

    def test_note_is_optional(self):
        reading = build_messages(en_selection(note=""))[1]
        assert "—" not in reading.text
        assert reading.text.endswith("누구나 인정하는 진리다")

    def test_both_bubbles_link_to_the_source(self):
        for message in build_messages(en_selection()):
            assert message.link_url == "https://example.test/en"

    def test_missing_translation_is_rejected(self):
        selection = Selection(
            "en", EN_WORK, Segment("en_work", 1, 1, "original only"), 1
        )
        with pytest.raises(ValueError, match="번역"):
            build_messages(selection)


class TestLengthLimit:
    def test_message_at_the_limit_is_allowed(self):
        OutgoingMessage("가" * KAKAO_TEXT_LIMIT, "https://example.test", "원문 읽기")

    def test_message_over_the_limit_is_rejected(self):
        with pytest.raises(MessageTooLongError, match="201자"):
            OutgoingMessage("가" * (KAKAO_TEXT_LIMIT + 1), "https://example.test", "원문 읽기")

    def test_long_body_is_caught_when_building(self):
        with pytest.raises(MessageTooLongError):
            build_messages(kr_selection(text="가" * KAKAO_TEXT_LIMIT))
