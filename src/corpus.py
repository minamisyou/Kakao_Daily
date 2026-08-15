"""코퍼스 로딩과 '오늘 보낼 조각' 결정.

진행 상태를 파일에 저장하지 않고 날짜에서 직접 계산한다. 덕분에 같은 날
두 번 실행해도 같은 결과가 나오고(멱등), 하루 걸러도 다음 날 알아서 제자리를
찾는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


class CorpusError(Exception):
    """코퍼스 파일이 없거나 내용이 깨졌을 때."""


@dataclass(frozen=True)
class Work:
    id: str
    track: str
    title: str
    author: str
    #: 해외 작품만 채워진다. 한국 작품은 title과 같아서 비워둔다.
    title_original: str
    source_url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Work":
        return cls(
            id=data["id"],
            track=data["track"],
            title=data["title"],
            author=data["author"],
            title_original=data.get("title_original", ""),
            source_url=data["source_url"],
        )


@dataclass(frozen=True)
class Segment:
    work_id: str
    #: 작품 내 순번 (1부터). 진행도 표시 "3/12"의 앞 숫자.
    seq: int
    total: int
    text: str
    #: 해외 트랙만 채워진다.
    text_ko: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Segment":
        return cls(
            work_id=data["work_id"],
            seq=data["seq"],
            total=data["total"],
            text=data["text"],
            text_ko=data.get("text_ko", ""),
            note=data.get("note", ""),
        )


@dataclass(frozen=True)
class Corpus:
    works: dict[str, Work]
    tracks: dict[str, list[Segment]]

    def work_for(self, segment: Segment) -> Work:
        try:
            return self.works[segment.work_id]
        except KeyError as exc:
            raise CorpusError(
                f"segments.json이 알 수 없는 작품을 가리킵니다: {segment.work_id!r}"
            ) from exc


@dataclass(frozen=True)
class Selection:
    track: str
    work: Work
    segment: Segment
    day_index: int


def load_corpus(path: Path) -> Corpus:
    if not path.exists():
        raise CorpusError(
            f"코퍼스가 없습니다: {path}\n"
            f"'python scripts/build_corpus.py'로 먼저 생성하세요."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"코퍼스 JSON을 읽을 수 없습니다: {path} ({exc})") from exc

    works = {
        work_id: Work.from_dict({"id": work_id, **meta})
        for work_id, meta in raw.get("works", {}).items()
    }
    tracks = {
        track: [Segment.from_dict(item) for item in items]
        for track, items in raw.get("tracks", {}).items()
    }
    if not any(tracks.values()):
        raise CorpusError(f"코퍼스에 조각이 하나도 없습니다: {path}")
    return Corpus(works=works, tracks=tracks)


def day_index(today: date, start_date: date) -> int:
    delta = (today - start_date).days
    if delta < 0:
        raise CorpusError(
            f"START_DATE({start_date})가 오늘({today})보다 미래입니다. "
            f"연재 시작일을 과거로 맞춰주세요."
        )
    return delta


def track_for_day(index: int, pattern: tuple[str, ...]) -> str:
    return pattern[index % len(pattern)]


def position_in_track(index: int, pattern: tuple[str, ...], track: str) -> int:
    """day_index까지 해당 트랙이 몇 번째로 등장하는지 (0부터).

    패턴이 'kr,kr,en'처럼 비대칭이어도 각 트랙이 자기 진도를 따로 지킨다.
    """
    period = len(pattern)
    per_period = pattern.count(track)
    if per_period == 0:
        raise CorpusError(f"TRACK_PATTERN에 '{track}' 트랙이 없습니다: {pattern}")
    full_periods, remainder = divmod(index, period)
    return full_periods * per_period + pattern[:remainder].count(track)


def select_for_day(
    corpus: Corpus,
    today: date,
    start_date: date,
    pattern: tuple[str, ...],
) -> Selection:
    """오늘 보낼 조각 하나를 고른다."""
    index = day_index(today, start_date)
    track = track_for_day(index, pattern)

    segments = corpus.tracks.get(track) or []
    if not segments:
        raise CorpusError(
            f"'{track}' 트랙에 조각이 없습니다. "
            f"data/passages에 해당 트랙 작품을 추가하고 코퍼스를 다시 빌드하세요."
        )

    # 코퍼스를 다 돌면 처음으로 돌아가 다시 연재한다.
    segment = segments[position_in_track(index, pattern, track) % len(segments)]
    return Selection(
        track=track,
        work=corpus.work_for(segment),
        segment=segment,
        day_index=index,
    )
