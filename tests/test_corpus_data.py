"""커밋된 실제 코퍼스(data/segments.json)를 검사한다.

여기서 막지 못하면 새벽에 발송이 깨진다.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from src.config import KAKAO_TEXT_LIMIT, DEFAULT_SEGMENTS_PATH
from src.corpus import Selection, load_corpus
from src.message import MAX_BUBBLES_PER_DAY, build_messages

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKS_PATH = REPO_ROOT / "data" / "works.json"

#: 저작권 보호기간(사후 70년). 이 해 이후에 사망한 작가는 실을 수 없다.
COPYRIGHT_TERM_YEARS = 70

CORPUS = load_corpus(DEFAULT_SEGMENTS_PATH)
WORKS_META = json.loads(WORKS_PATH.read_text(encoding="utf-8"))["works"]

QUEUE_WITH_TRACK = [
    (CORPUS.work_for(segment).track, segment) for segment in CORPUS.queue
]


def test_queue_is_not_empty():
    assert CORPUS.queue, "큐가 비어 있으면 발송할 게 없다."


def test_both_languages_appear_somewhere_in_the_queue():
    tracks = {track for track, _ in QUEUE_WITH_TRACK}
    assert "kr" in tracks, "한국 트랙 작품이 큐에 하나도 없다."
    assert "en" in tracks, "해외 트랙 작품이 큐에 하나도 없다."


@pytest.mark.parametrize(
    "track,segment", QUEUE_WITH_TRACK, ids=lambda v: getattr(v, "work_id", v)
)
def test_every_bubble_in_a_days_send_fits_the_kakao_limit(track, segment):
    work = CORPUS.work_for(segment)
    for message in build_messages(Selection(track, work, segment, 0)):
        assert len(message.text) <= KAKAO_TEXT_LIMIT


@pytest.mark.parametrize(
    "track,segment", QUEUE_WITH_TRACK, ids=lambda v: getattr(v, "work_id", v)
)
def test_a_days_send_does_not_spam_too_many_bubbles(track, segment):
    work = CORPUS.work_for(segment)
    messages = build_messages(Selection(track, work, segment, 0))
    assert len(messages) <= MAX_BUBBLES_PER_DAY, (
        f"{segment.work_id} #{segment.seq}가 하루에 {len(messages)}통을 보낸다."
    )


@pytest.mark.parametrize(
    "segment",
    [s for track, s in QUEUE_WITH_TRACK if track == "en"],
    ids=lambda s: f"{s.work_id}#{s.seq}",
)
def test_every_foreign_segment_has_a_translation(segment):
    assert segment.text_ko, f"{segment.work_id} #{segment.seq}에 번역이 없다."


@pytest.mark.parametrize(
    "segment",
    [s for track, s in QUEUE_WITH_TRACK if track == "kr"],
    ids=lambda s: f"{s.work_id}#{s.seq}",
)
def test_korean_segments_carry_no_translation_fields(segment):
    # 한국 트랙은 원문 그대로 한 통만 나간다.
    assert not segment.text_ko


@pytest.mark.parametrize(
    "track,segment", QUEUE_WITH_TRACK, ids=lambda v: getattr(v, "work_id", v)
)
def test_every_segment_points_at_a_known_work(track, segment):
    assert CORPUS.work_for(segment).track == track


def test_progress_numbering_is_contiguous_per_work():
    by_work: dict[str, list[int]] = {}
    for segment in CORPUS.queue:
        by_work.setdefault(segment.work_id, []).append(segment.seq)

    for work_id, seqs in by_work.items():
        total = {s.total for s in CORPUS.queue if s.work_id == work_id}
        assert len(total) == 1, f"{work_id}의 total이 조각마다 다르다: {total}"
        assert sorted(seqs) == list(range(1, total.pop() + 1)), f"{work_id} 순번에 구멍이 있다."


def test_each_work_appears_as_one_unbroken_run_in_the_queue():
    """작품 하나가 완결되기 전에는 다른 작품이 끼어들면 안 된다.

    큐를 work_id로 압축했을 때(연속된 같은 값은 하나로) 각 work_id가
    정확히 한 번씩만 나타나야 한다 — 두 번 나타난다면 중간에 다른 작품이
    끼어들어 이야기가 끊겼다는 뜻이다.
    """
    compressed: list[str] = []
    for segment in CORPUS.queue:
        if not compressed or compressed[-1] != segment.work_id:
            compressed.append(segment.work_id)

    seen = set()
    for work_id in compressed:
        assert work_id not in seen, f"{work_id}가 큐에서 두 번 이상 끊겨서 나타난다."
        seen.add(work_id)


def test_language_only_switches_between_different_works():
    """언어가 바뀌는 지점은 반드시 앞 작품이 끝난 자리여야 한다."""
    for prev, cur in zip(CORPUS.queue, CORPUS.queue[1:]):
        if CORPUS.work_for(prev).track != CORPUS.work_for(cur).track:
            assert prev.seq == prev.total, (
                f"{prev.work_id}가 {prev.seq}/{prev.total}에서 끝나지 않았는데 "
                f"{cur.work_id}로 언어가 바뀌었다."
            )


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
