"""커밋된 실제 코퍼스(data/segments.json)를 검사한다.

여기서 막지 못하면 새벽에 발송이 깨진다.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from src.config import KAKAO_TEXT_LIMIT, DEFAULT_SEGMENTS_PATH
from src.corpus import Selection, load_corpus
from src.message import build_messages

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKS_PATH = REPO_ROOT / "data" / "works.json"

#: 저작권 보호기간(사후 70년). 이 해 이후에 사망한 작가는 실을 수 없다.
COPYRIGHT_TERM_YEARS = 70

CORPUS = load_corpus(DEFAULT_SEGMENTS_PATH)
WORKS_META = json.loads(WORKS_PATH.read_text(encoding="utf-8"))["works"]

ALL_SEGMENTS = [
    (track, segment)
    for track, segments in CORPUS.tracks.items()
    for segment in segments
]


def test_both_tracks_have_segments():
    assert CORPUS.tracks["kr"], "한국 트랙이 비어 있으면 짝수 날 발송이 실패한다."
    assert CORPUS.tracks["en"], "해외 트랙이 비어 있으면 홀수 날 발송이 실패한다."


@pytest.mark.parametrize("track,segment", ALL_SEGMENTS, ids=lambda v: getattr(v, "work_id", v))
def test_every_segment_fits_in_a_kakao_bubble(track, segment):
    work = CORPUS.work_for(segment)
    for message in build_messages(Selection(track, work, segment, 0)):
        assert len(message.text) <= KAKAO_TEXT_LIMIT


@pytest.mark.parametrize("segment", CORPUS.tracks["en"], ids=lambda s: f"{s.work_id}#{s.seq}")
def test_every_foreign_segment_has_a_translation(segment):
    assert segment.text_ko, f"{segment.work_id} #{segment.seq}에 번역이 없다."


@pytest.mark.parametrize("segment", CORPUS.tracks["kr"], ids=lambda s: f"{s.work_id}#{s.seq}")
def test_korean_segments_carry_no_translation_fields(segment):
    # 한국 트랙은 원문 그대로 한 통만 나간다.
    assert not segment.text_ko


@pytest.mark.parametrize("track,segment", ALL_SEGMENTS, ids=lambda v: getattr(v, "work_id", v))
def test_every_segment_points_at_a_known_work(track, segment):
    assert CORPUS.work_for(segment).track == track


def test_progress_numbering_is_contiguous_per_work():
    by_work: dict[str, list[int]] = {}
    for _, segment in ALL_SEGMENTS:
        by_work.setdefault(segment.work_id, []).append(segment.seq)

    for work_id, seqs in by_work.items():
        total = {s.total for _, s in ALL_SEGMENTS if s.work_id == work_id}
        assert len(total) == 1, f"{work_id}의 total이 조각마다 다르다: {total}"
        assert sorted(seqs) == list(range(1, total.pop() + 1)), f"{work_id} 순번에 구멍이 있다."


@pytest.mark.parametrize("meta", WORKS_META, ids=lambda m: m["id"])
def test_work_is_out_of_copyright(meta):
    latest_allowed = date.today().year - COPYRIGHT_TERM_YEARS
    assert meta["author_death"] <= latest_allowed, (
        f"{meta['id']}: {meta['author']}는 {meta['author_death']}년 사망으로 "
        f"아직 보호기간(사후 {COPYRIGHT_TERM_YEARS}년) 안에 있다."
    )


@pytest.mark.parametrize("meta", WORKS_META, ids=lambda m: m["id"])
def test_work_records_where_the_text_came_from(meta):
    assert meta["source_url"].startswith("https://")
    assert meta["source"]["type"] in {"wikisource", "gutenberg"}
