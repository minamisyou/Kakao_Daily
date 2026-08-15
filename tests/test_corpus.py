"""트랙 편성과 날짜 → 조각 매핑."""

from datetime import date

import pytest

from src.config import parse_track_pattern
from src.corpus import (
    Corpus,
    CorpusError,
    Segment,
    Work,
    day_index,
    position_in_track,
    select_for_day,
    track_for_day,
)

START = date(2026, 1, 1)


def make_corpus(kr_count: int = 3, en_count: int = 2) -> Corpus:
    works = {
        "kr_work": Work("kr_work", "kr", "봄·봄", "김유정", "", "https://example.test/kr"),
        "en_work": Work(
            "en_work", "en", "오만과 편견", "제인 오스틴", "Pride and Prejudice",
            "https://example.test/en",
        ),
    }
    tracks = {
        "kr": [
            Segment("kr_work", i, kr_count, f"한국 {i}") for i in range(1, kr_count + 1)
        ],
        "en": [
            Segment("en_work", i, en_count, f"english {i}", f"번역 {i}", f"해설 {i}")
            for i in range(1, en_count + 1)
        ],
    }
    return Corpus(works=works, tracks=tracks)


class TestDayIndex:
    def test_start_date_is_day_zero(self):
        assert day_index(START, START) == 0

    def test_counts_calendar_days_across_month_end(self):
        assert day_index(date(2026, 2, 1), date(2026, 1, 25)) == 7

    def test_counts_leap_day(self):
        # 2028년은 윤년이라 2월이 29일까지 있다.
        assert day_index(date(2028, 3, 1), date(2028, 2, 1)) == 29

    def test_rejects_future_start_date(self):
        with pytest.raises(CorpusError, match="미래"):
            day_index(date(2026, 1, 1), date(2026, 6, 1))


class TestTrackPattern:
    def test_alternates_daily(self):
        pattern = parse_track_pattern("kr,en")
        assert [track_for_day(i, pattern) for i in range(4)] == ["kr", "en", "kr", "en"]

    def test_supports_uneven_pattern(self):
        pattern = parse_track_pattern("kr,kr,en")
        assert [track_for_day(i, pattern) for i in range(6)] == [
            "kr", "kr", "en", "kr", "kr", "en",
        ]

    def test_each_track_keeps_its_own_progress(self):
        pattern = parse_track_pattern("kr,kr,en")
        # 6일 동안 kr은 4번, en은 2번 나왔다.
        assert position_in_track(6, pattern, "kr") == 4
        assert position_in_track(6, pattern, "en") == 2

    def test_position_advances_one_per_appearance(self):
        pattern = parse_track_pattern("kr,en")
        kr_positions = [
            position_in_track(i, pattern, "kr")
            for i in range(0, 8)
            if track_for_day(i, pattern) == "kr"
        ]
        assert kr_positions == [0, 1, 2, 3]

    def test_rejects_track_missing_from_pattern(self):
        with pytest.raises(CorpusError, match="트랙이 없습니다"):
            position_in_track(3, ("kr",), "en")


class TestSelection:
    def test_alternating_days_pick_alternating_tracks(self):
        corpus = make_corpus()
        pattern = ("kr", "en")
        tracks = [
            select_for_day(corpus, START.fromordinal(START.toordinal() + i), START, pattern).track
            for i in range(4)
        ]
        assert tracks == ["kr", "en", "kr", "en"]

    def test_same_day_gives_same_segment(self):
        corpus = make_corpus()
        today = date(2026, 3, 9)
        first = select_for_day(corpus, today, START, ("kr", "en"))
        second = select_for_day(corpus, today, START, ("kr", "en"))
        assert first.segment == second.segment

    def test_wraps_around_after_corpus_is_exhausted(self):
        corpus = make_corpus(kr_count=3)
        pattern = ("kr", "en")
        # kr 트랙은 3조각뿐이므로 4번째 등장(= 6일차)에 처음으로 돌아간다.
        first_day = select_for_day(corpus, date(2026, 1, 1), START, pattern)
        wrapped = select_for_day(corpus, date(2026, 1, 7), START, pattern)
        assert first_day.segment.seq == 1
        assert wrapped.segment.seq == 1

    def test_empty_track_reports_which_track(self):
        corpus = Corpus(works=make_corpus().works, tracks={"kr": [], "en": []})
        with pytest.raises(CorpusError, match="'kr' 트랙에 조각이 없습니다"):
            select_for_day(corpus, START, START, ("kr", "en"))

    def test_unknown_work_id_is_reported(self):
        corpus = Corpus(
            works={},
            tracks={"kr": [Segment("ghost", 1, 1, "본문")], "en": []},
        )
        with pytest.raises(CorpusError, match="알 수 없는 작품"):
            select_for_day(corpus, START, START, ("kr",))
