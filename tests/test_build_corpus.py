"""전문 자동 분할 로직."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_corpus import header_budget, hard_wrap, split_sentences, split_text  # noqa: E402


class TestSplitSentences:
    def test_splits_korean_sentences_on_periods(self):
        assert split_sentences("첫 문장이다. 둘째 문장이다.") == [
            "첫 문장이다.",
            "둘째 문장이다.",
        ]

    def test_keeps_closing_quote_with_its_sentence(self):
        assert split_sentences('"인제 저⋯" 하고 말했다.') == ['"인제 저⋯"', "하고 말했다."]

    def test_single_sentence_stays_whole(self):
        assert split_sentences("자를 데가 없는 한 문장") == ["자를 데가 없는 한 문장"]


class TestSplitText:
    def test_packs_multiple_sentences_up_to_the_limit(self):
        text = "가나다라. 마바사아. 자차카타."  # 17자
        assert split_text(text, limit=12) == ["가나다라. 마바사아.", "자차카타."]

    def test_text_within_the_limit_stays_in_one_piece(self):
        text = "가나다라. 마바사아. 자차카타."
        assert split_text(text, limit=20) == [text]

    def test_never_exceeds_the_limit(self):
        text = " ".join(f"문장 번호 {i}입니다." for i in range(40))
        for chunk in split_text(text, limit=50):
            assert len(chunk) <= 50

    def test_does_not_merge_across_paragraphs(self):
        text = "짧은 문단.\n\n다른 문단."
        assert split_text(text, limit=100) == ["짧은 문단.", "다른 문단."]

    def test_drops_blank_paragraphs(self):
        assert split_text("첫 문단.\n\n\n\n둘째 문단.", limit=100) == [
            "첫 문단.",
            "둘째 문단.",
        ]

    def test_oversized_single_sentence_is_wrapped_rather_than_dropped(self):
        sentence = " ".join(["단어"] * 60) + "."
        chunks = split_text(sentence, limit=40)
        assert chunks, "긴 문장이 통째로 사라지면 안 된다."
        assert all(len(chunk) <= 40 for chunk in chunks)

    def test_wrapping_preserves_every_word(self):
        sentence = " ".join(f"w{i}" for i in range(50))
        rejoined = " ".join(hard_wrap(sentence, 20))
        assert rejoined.split() == sentence.split()


class TestHeaderBudget:
    def test_reserves_room_for_the_longest_progress_label(self):
        meta = {"track": "kr", "title": "봄·봄", "author": "김유정"}
        # "📖 봄·봄 — 김유정 (9999/9999)" + 빈 줄
        assert header_budget(meta) == len("📖 봄·봄 — 김유정 (9999/9999)") + 2

    def test_foreign_work_budgets_for_the_original_title(self):
        # 해외 트랙의 원문 말풍선 헤더에는 번역 제목이 아니라 원제가 들어간다.
        meta = {
            "track": "en",
            "title": "오만과 편견",
            "title_original": "Pride and Prejudice",
            "author": "Jane Austen",
        }
        assert header_budget(meta) == len("📖 Pride and Prejudice — Jane Austen (9999/9999)") + 2

    def test_budget_falls_back_to_the_korean_title_when_no_original(self):
        meta = {"track": "en", "title": "오만과 편견", "author": "Jane Austen"}
        assert header_budget(meta) == len("📖 오만과 편견 — Jane Austen (9999/9999)") + 2
