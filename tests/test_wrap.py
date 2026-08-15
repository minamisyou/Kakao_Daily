"""문장 경계를 지키는 텍스트 분할 (말풍선 단위 + 회차 단위)."""

from src.wrap import bundle_into_installments, hard_wrap, split_into_bubbles, split_sentences


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


class TestSplitIntoBubbles:
    def test_packs_multiple_sentences_up_to_the_limit(self):
        text = "가나다라. 마바사아. 자차카타."  # 17자
        assert split_into_bubbles(text, limit=12) == ["가나다라. 마바사아.", "자차카타."]

    def test_text_within_the_limit_stays_in_one_piece(self):
        text = "가나다라. 마바사아. 자차카타."
        assert split_into_bubbles(text, limit=20) == [text]

    def test_never_exceeds_the_limit(self):
        text = " ".join(f"문장 번호 {i}입니다." for i in range(40))
        for chunk in split_into_bubbles(text, limit=50):
            assert len(chunk) <= 50

    def test_merges_short_paragraphs_when_they_fit_together(self):
        # 문단 경계에서 강제로 끊으면, 긴 문장이 문단 끝에서 hard_wrap으로
        # 잘렸을 때 그 짧은 꼬리가 다음 문단과 합쳐질 기회를 잃는다.
        text = "짧은 문단.\n\n다른 문단."
        assert split_into_bubbles(text, limit=100) == ["짧은 문단.\n\n다른 문단."]

    def test_preserves_the_paragraph_break_inside_a_merged_bubble(self):
        text = "짧은 문단.\n\n다른 문단."
        assert split_into_bubbles(text, limit=100)[0] == "짧은 문단.\n\n다른 문단."

    def test_splits_at_a_paragraph_boundary_when_they_do_not_fit_together(self):
        text = "첫 문단 내용입니다.\n\n둘째 문단 내용입니다."
        bubbles = split_into_bubbles(text, limit=15)
        assert bubbles == ["첫 문단 내용입니다.", "둘째 문단 내용입니다."]

    def test_drops_blank_paragraphs(self):
        assert split_into_bubbles("첫 문단.\n\n\n\n둘째 문단.", limit=100) == [
            "첫 문단.\n\n둘째 문단."
        ]

    def test_stranded_hard_wrap_tail_merges_into_the_next_paragraph(self):
        # 실제로 터졌던 버그: 긴 문장이 문단 끝에서 hard_wrap으로 잘리면
        # 짧은 꼬리가 문단 경계에 막혀 혼자 작은 말풍선이 됐었다.
        long_sentence = " ".join(["단어"] * 40) + " 마지막꼬리."
        text = f"{long_sentence}\n\n다음 문단은 짧다."
        bubbles = split_into_bubbles(text, limit=60)
        assert not any(len(b) < 15 for b in bubbles), (
            f"고아 말풍선이 있다: {[b for b in bubbles if len(b) < 15]}"
        )

    def test_oversized_single_sentence_is_wrapped_rather_than_dropped(self):
        sentence = " ".join(["단어"] * 60) + "."
        chunks = split_into_bubbles(sentence, limit=40)
        assert chunks, "긴 문장이 통째로 사라지면 안 된다."
        assert all(len(chunk) <= 40 for chunk in chunks)

    def test_wrapping_preserves_every_word(self):
        sentence = " ".join(f"w{i}" for i in range(50))
        rejoined = " ".join(hard_wrap(sentence, 20))
        assert rejoined.split() == sentence.split()


class TestBundleIntoInstallments:
    def test_packs_short_paragraphs_up_to_the_target(self):
        # 문단마다 짧은 대화체는 문단 경계를 넘나들며 묶여야 한다.
        text = "\n\n".join(f"짧은 대사 {i}." for i in range(20))
        installments = bundle_into_installments(text, target_chars=50, hard_cap_chars=80)
        assert len(installments) < 20, "문단 경계에서만 나눴다면 20개가 나왔을 것이다."
        for installment in installments:
            assert len(installment) <= 80

    def test_never_exceeds_the_hard_cap(self):
        text = "\n\n".join(f"문단 {i} 내용입니다. 문장이 두 개씩 있습니다." for i in range(30))
        for installment in bundle_into_installments(text, target_chars=100, hard_cap_chars=150):
            assert len(installment) <= 150

    def test_short_text_becomes_a_single_installment(self):
        text = "문단 하나뿐인 아주 짧은 글입니다."
        assert bundle_into_installments(text, target_chars=2000, hard_cap_chars=2500) == [text]

    def test_oversized_paragraph_is_split_rather_than_exceeding_the_cap(self):
        huge_paragraph = " ".join(["단어"] * 200) + "."
        for installment in bundle_into_installments(huge_paragraph, target_chars=50, hard_cap_chars=60):
            assert len(installment) <= 60

    def test_preserves_paragraph_breaks_within_an_installment(self):
        text = "첫 문단.\n\n둘째 문단."
        installments = bundle_into_installments(text, target_chars=2000, hard_cap_chars=2500)
        assert installments == ["첫 문단.\n\n둘째 문단."]
