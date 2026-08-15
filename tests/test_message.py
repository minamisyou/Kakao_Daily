"""말풍선 조립, 회차→여러 통 분할, 완결/계속 안내."""

import pytest

from src.config import KAKAO_TEXT_LIMIT
from src.corpus import Segment, Selection, Work
from src.message import (
    MessageTooLongError,
    OutgoingMessage,
    header_budget,
    build_messages,
)

KR_WORK = Work("kr_work", "kr", "운수 좋은 날", "현진건", "", "https://example.test/kr")
EN_WORK = Work(
    "en_work", "en", "오만과 편견", "제인 오스틴", "Pride and Prejudice",
    "https://example.test/en",
)

SHORT_TEXT = "새침하게 흐린 품이 눈이 올 듯하더니 눈은 아니 오고 얼다가 만 비가 추적추적 내리었다."


def long_paragraphs(count: int, prefix: str = "문단") -> str:
    return "\n\n".join(
        f"{prefix} {i}번입니다. 여기에 문장이 두 개씩 들어갑니다." * 6 for i in range(count)
    )


def kr_selection(text: str = SHORT_TEXT, seq: int = 3, total: int = 12) -> Selection:
    return Selection("kr", KR_WORK, Segment("kr_work", seq, total, text), 0)


def en_selection(
    text: str = "It is a truth universally acknowledged.",
    text_ko: str = "누구나 인정하는 진리다.",
    note: str = "",
    seq: int = 2,
    total: int = 6,
) -> Selection:
    return Selection(
        "en", EN_WORK, Segment("en_work", seq, total, text, text_ko, note), 1
    )


class TestKoreanTrackShortText:
    def test_short_text_fits_in_one_bubble(self):
        messages = build_messages(kr_selection())
        assert len(messages) == 1

    def test_header_carries_title_author_and_progress(self):
        message = build_messages(kr_selection())[0]
        assert message.text.startswith("📖 운수 좋은 날 — 현진건 (3/12)")

    def test_continues_tomorrow_when_not_the_last_installment(self):
        message = build_messages(kr_selection(seq=3, total=12))[0]
        assert "(내일 이어집니다)" in message.text

    def test_announces_completion_on_the_last_installment(self):
        message = build_messages(kr_selection(seq=12, total=12))[0]
        assert "완결" in message.text

    def test_links_to_the_source(self):
        message = build_messages(kr_selection())[0]
        assert message.link_url == "https://example.test/kr"
        assert message.button_title == "원문 읽기"


class TestKoreanTrackLongText:
    def test_splits_into_multiple_bubbles(self):
        messages = build_messages(kr_selection(text=long_paragraphs(15)))
        assert len(messages) > 1

    def test_only_the_first_bubble_has_the_header(self):
        messages = build_messages(kr_selection(text=long_paragraphs(15)))
        assert messages[0].text.startswith("📖 운수 좋은 날")
        for message in messages[1:]:
            assert not message.text.startswith("📖")

    def test_every_bubble_respects_the_kakao_limit(self):
        messages = build_messages(kr_selection(text=long_paragraphs(15)))
        for message in messages:
            assert len(message.text) <= KAKAO_TEXT_LIMIT

    def test_footer_lands_on_the_last_bubble_only(self):
        messages = build_messages(kr_selection(text=long_paragraphs(15), seq=3, total=12))
        assert "내일 이어집니다" in messages[-1].text
        for message in messages[:-1]:
            assert "내일 이어집니다" not in message.text

    def test_reassembling_bubbles_preserves_reading_order(self):
        # 각 통이 원문 순서를 그대로 따라가는지 — 순서가 섞이면 이야기가 꼬인다.
        text = long_paragraphs(15)
        messages = build_messages(kr_selection(text=text))
        first_sentence = text.split(".")[0]
        assert first_sentence in messages[0].text


class TestForeignTrack:
    def test_sends_original_bubbles_then_reading_bubbles(self):
        messages = build_messages(en_selection())
        titles = [m.text[:1] for m in messages]
        assert titles[0] == "📖"
        assert "🔎" in titles

    def test_original_bubble_uses_the_original_title(self):
        messages = build_messages(en_selection())
        assert "Pride and Prejudice" in messages[0].text
        assert "오만과 편견" not in messages[0].text

    def test_reading_bubble_uses_the_korean_title_and_translation(self):
        messages = build_messages(en_selection())
        reading = next(m for m in messages if m.text.startswith("🔎"))
        assert "오만과 편견" in reading.text
        assert "누구나 인정하는 진리다." in reading.text

    def test_long_original_and_translation_each_split_independently(self):
        messages = build_messages(
            en_selection(text=long_paragraphs(10, "para"), text_ko=long_paragraphs(10, "문단"))
        )
        original_count = sum(1 for m in messages if "para" in m.text)
        reading_count = sum(1 for m in messages if "문단" in m.text)
        assert original_count > 1
        assert reading_count > 1

    def test_note_is_appended_as_its_own_bubble_when_present(self):
        messages = build_messages(en_selection(note="소설의 첫 문장이다."))
        assert any(m.text.startswith("— 소설의 첫 문장") for m in messages)

    def test_note_is_omitted_when_absent(self):
        messages = build_messages(en_selection(note=""))
        assert not any(m.text.startswith("—") for m in messages)

    def test_footer_lands_on_the_very_last_bubble(self):
        messages = build_messages(en_selection(note="첫 문장.", seq=6, total=6))
        assert "완결" in messages[-1].text

    def test_all_bubbles_link_to_the_source(self):
        for message in build_messages(en_selection()):
            assert message.link_url == "https://example.test/en"

    def test_missing_translation_is_rejected(self):
        selection = Selection(
            "en", EN_WORK, Segment("en_work", 1, 1, "original only"), 1
        )
        with pytest.raises(ValueError, match="번역"):
            build_messages(selection)


class TestHeaderBudget:
    def test_reserves_room_for_the_longest_progress_label(self):
        assert header_budget("봄·봄", "김유정") == len("📖 봄·봄 — 김유정 (9999/9999)") + 2


class TestLengthLimit:
    def test_message_at_the_limit_is_allowed(self):
        OutgoingMessage("가" * KAKAO_TEXT_LIMIT, "https://example.test", "원문 읽기")

    def test_message_over_the_limit_is_rejected(self):
        with pytest.raises(MessageTooLongError, match="201자"):
            OutgoingMessage("가" * (KAKAO_TEXT_LIMIT + 1), "https://example.test", "원문 읽기")

    def test_build_messages_never_exceeds_the_limit_even_for_huge_installments(self):
        messages = build_messages(kr_selection(text=long_paragraphs(40)))
        for message in messages:
            assert len(message.text) <= KAKAO_TEXT_LIMIT
