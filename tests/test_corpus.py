"""날짜 → 발송 큐 인덱싱."""

from datetime import date

import pytest

import json

from src.corpus import (
    Corpus,
    CorpusError,
    Segment,
    Work,
    day_index,
    load_corpus,
    select_for_day,
)

START = date(2026, 1, 1)


def make_corpus() -> Corpus:
    works = {
        "kr_work": Work("kr_work", "kr", "봄·봄", "김유정", "", "https://example.test/kr"),
        "en_work": Work(
            "en_work", "en", "오만과 편견", "제인 오스틴", "Pride and Prejudice",
            "https://example.test/en",
        ),
    }
    # 실제 빌드 결과처럼, 한 작품이 끝나야 언어가 바뀌는 순서로 미리 엮여 있다.
    queue = [
        Segment("kr_work", 1, 3, "한국 1"),
        Segment("kr_work", 2, 3, "한국 2"),
        Segment("kr_work", 3, 3, "한국 3"),
        Segment("en_work", 1, 2, "english 1", "번역 1", "해설 1"),
        Segment("en_work", 2, 2, "english 2", "번역 2", "해설 2"),
    ]
    return Corpus(works=works, queue=queue)


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


class TestSelection:
    def test_first_day_picks_the_first_entry_in_the_queue(self):
        corpus = make_corpus()
        selection = select_for_day(corpus, START, START)
        assert selection.track == "kr"
        assert selection.segment.seq == 1

    def test_the_same_work_continues_day_after_day_until_it_finishes(self):
        # 큐 안에서는 요일이 아니라 큐 순서 그대로 진행된다 — 작품이
        # 완결되기 전까지는 같은 트랙이 이어져야 한다.
        corpus = make_corpus()
        tracks_and_seqs = [
            (select_for_day(corpus, date(2026, 1, 1 + i), START).track,
             select_for_day(corpus, date(2026, 1, 1 + i), START).segment.seq)
            for i in range(5)
        ]
        assert tracks_and_seqs == [
            ("kr", 1), ("kr", 2), ("kr", 3), ("en", 1), ("en", 2)
        ]

    def test_language_only_switches_when_the_current_work_finishes(self):
        corpus = make_corpus()
        # 한국 작품 3회차(day 2)까지는 여전히 kr이어야 하고, en은 그 뒤에야 나온다.
        assert select_for_day(corpus, date(2026, 1, 3), START).track == "kr"
        assert select_for_day(corpus, date(2026, 1, 4), START).track == "en"

    def test_same_day_gives_same_segment(self):
        corpus = make_corpus()
        today = date(2026, 1, 2)
        first = select_for_day(corpus, today, START)
        second = select_for_day(corpus, today, START)
        assert first.segment == second.segment

    def test_wraps_around_after_the_whole_queue_is_exhausted(self):
        corpus = make_corpus()
        # 큐 길이가 5이므로 6일째(day_index=5)에 처음으로 돌아간다.
        first_day = select_for_day(corpus, date(2026, 1, 1), START)
        wrapped = select_for_day(corpus, date(2026, 1, 6), START)
        assert first_day.segment == wrapped.segment

    def test_unknown_work_id_is_reported(self):
        corpus = Corpus(
            works={},
            queue=[Segment("ghost", 1, 1, "본문")],
        )
        with pytest.raises(CorpusError, match="알 수 없는 작품"):
            select_for_day(corpus, START, START)


class TestLoadCorpus:
    def test_missing_file_is_reported(self, tmp_path):
        with pytest.raises(CorpusError, match="코퍼스가 없습니다"):
            load_corpus(tmp_path / "missing.json")

    def test_empty_queue_is_rejected(self, tmp_path):
        path = tmp_path / "segments.json"
        path.write_text(json.dumps({"works": {}, "queue": []}), encoding="utf-8")
        with pytest.raises(CorpusError, match="조각이 하나도 없습니다"):
            load_corpus(path)

    def test_loads_works_and_queue(self, tmp_path):
        path = tmp_path / "segments.json"
        path.write_text(
            json.dumps(
                {
                    "works": {
                        "kr_work": {
                            "track": "kr", "title": "봄·봄", "author": "김유정",
                            "source_url": "https://example.test/kr",
                        }
                    },
                    "queue": [
                        {"work_id": "kr_work", "seq": 1, "total": 1, "text": "본문"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        corpus = load_corpus(path)
        assert corpus.queue[0].text == "본문"
        assert corpus.works["kr_work"].title == "봄·봄"
