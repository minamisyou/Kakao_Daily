#!/usr/bin/env python3
"""data/works.json + 원문/구절 → data/segments.json 빌드.

작품마다 두 갈래로 조각을 만든다.

  1. data/sources/<id>.txt 가 있으면 (한국 트랙)  → 전문을 자동 분할
  2. 없으면 data/passages/<id>.json             → 손으로 고른 구절 사용

해외 트랙은 원문과 번역이 1:1로 짝지어져 있어야 하므로 항상 2번을 쓴다.
자동 분할한 조각과 번역을 기계적으로 맞출 방법이 없기 때문이다.

마지막에 실제 발송 코드로 말풍선을 조립해 보고 200자를 넘는 조각이 하나라도
있으면 빌드를 실패시킨다. 새벽에 발송이 깨지는 것보다 빌드가 깨지는 게 낫다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import KAKAO_TEXT_LIMIT  # noqa: E402
from src.corpus import Segment, Selection, Work  # noqa: E402
from src.message import build_messages  # noqa: E402

WORKS_PATH = REPO_ROOT / "data" / "works.json"
PASSAGES_DIR = REPO_ROOT / "data" / "passages"
SOURCES_DIR = REPO_ROOT / "data" / "sources"
OUTPUT_PATH = REPO_ROOT / "data" / "segments.json"

#: 진행도 표시가 최대로 길어졌을 때를 가정해 헤더 예산을 잡는다.
WORST_CASE_PROGRESS = "(9999/9999)"

#: 문장 끝으로 인정할 문자. 한국어 인용부호와 말줄임표를 포함한다.
SENTENCE_BREAK = re.compile(r'(?<=[.!?……‥])\s+|(?<=[."”’\'」』])\s+')


class BuildError(Exception):
    pass


def load_works() -> list[dict]:
    data = json.loads(WORKS_PATH.read_text(encoding="utf-8"))
    return data["works"]


def header_budget(work_meta: dict) -> int:
    """헤더 + 빈 줄이 차지하는 글자 수. 본문에 쓸 수 있는 양은 200에서 이걸 뺀 만큼."""
    if work_meta["track"] == "en":
        title = work_meta.get("title_original") or work_meta["title"]
    else:
        title = work_meta["title"]
    header = f"📖 {title} — {work_meta['author']} {WORST_CASE_PROGRESS}"
    return len(header) + 2  # "\n\n"


def split_sentences(paragraph: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_BREAK.split(paragraph)]
    return [p for p in parts if p]


def hard_wrap(sentence: str, limit: int) -> list[str]:
    """한 문장이 통째로 예산을 넘을 때만 쓰는 최후 수단."""
    chunks: list[str] = []
    remaining = sentence
    while len(remaining) > limit:
        cut = remaining.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def split_text(full_text: str, limit: int) -> list[str]:
    """전문을 limit 글자 이하의 조각으로 나눈다.

    문단을 넘나들지 않고, 문장 중간도 자르지 않는다. 읽는 맛이 거기서 갈린다.
    """
    segments: list[str] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]

    for paragraph in paragraphs:
        buffer = ""
        for sentence in split_sentences(paragraph):
            for piece in (
                hard_wrap(sentence, limit) if len(sentence) > limit else [sentence]
            ):
                candidate = f"{buffer} {piece}".strip() if buffer else piece
                if len(candidate) <= limit:
                    buffer = candidate
                else:
                    if buffer:
                        segments.append(buffer)
                    buffer = piece
        if buffer:
            segments.append(buffer)
    return segments


def passages_from_file(work_id: str) -> list[dict] | None:
    path = PASSAGES_DIR / f"{work_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    passages = data.get("passages", [])
    return passages or None


def passages_from_source(work_id: str, limit: int) -> list[dict] | None:
    path = SOURCES_DIR / f"{work_id}.txt"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return [{"text": chunk} for chunk in split_text(text, limit)]


def build_segments_for(work_meta: dict) -> tuple[list[dict], str]:
    """(조각 목록, 출처 설명) 반환."""
    limit = KAKAO_TEXT_LIMIT - header_budget(work_meta)
    work_id = work_meta["id"]

    if work_meta["track"] == "kr":
        from_source = passages_from_source(work_id, limit)
        if from_source:
            return from_source, f"전문 자동 분할 ({len(from_source)}조각)"

    passages = passages_from_file(work_id)
    if not passages:
        return [], "원문·구절 없음"

    return list(passages), f"큐레이션 구절 ({len(passages)}조각)"


def validate(work: Work, segment: Segment) -> None:
    """실제 발송 경로로 말풍선을 조립해 본다. 여기서 터지면 빌드 실패."""
    selection = Selection(track=work.track, work=work, segment=segment, day_index=0)
    build_messages(selection)


def build() -> dict:
    works_meta = load_works()
    works_out: dict[str, dict] = {}
    tracks: dict[str, list[dict]] = {"kr": [], "en": []}
    report: list[str] = []

    for meta in works_meta:
        work_id = meta["id"]
        raw_segments, description = build_segments_for(meta)
        report.append(f"  {work_id:<28} {meta['track']}  {description}")
        if not raw_segments:
            continue

        works_out[work_id] = {
            "track": meta["track"],
            "title": meta["title"],
            "author": meta.get("author_ko") or meta["author"],
            "title_original": meta.get("title_original", ""),
            "source_url": meta["source_url"],
        }
        work = Work.from_dict({"id": work_id, **works_out[work_id]})

        total = len(raw_segments)
        for index, passage in enumerate(raw_segments, start=1):
            segment = Segment(
                work_id=work_id,
                seq=index,
                total=total,
                text=passage["text"].strip(),
                text_ko=passage.get("text_ko", "").strip(),
                note=passage.get("note", "").strip(),
            )
            validate(work, segment)
            entry = {
                "work_id": segment.work_id,
                "seq": segment.seq,
                "total": segment.total,
                "text": segment.text,
            }
            if segment.text_ko:
                entry["text_ko"] = segment.text_ko
            if segment.note:
                entry["note"] = segment.note
            tracks[meta["track"]].append(entry)

    print("작품별 빌드 결과:")
    print("\n".join(report))
    for track, items in tracks.items():
        print(f"  → {track} 트랙 총 {len(items)}조각")

    if not tracks["kr"] or not tracks["en"]:
        raise BuildError(
            "두 트랙 모두 조각이 있어야 편성이 돌아갑니다. "
            "비어 있는 트랙에 작품을 추가하세요."
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kakao_text_limit": KAKAO_TEXT_LIMIT,
        "works": works_out,
        "tracks": tracks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="코퍼스 빌드")
    parser.add_argument(
        "--check",
        action="store_true",
        help="파일을 쓰지 않고, 커밋된 segments.json이 최신인지만 확인한다 (CI용).",
    )
    args = parser.parse_args()

    try:
        corpus = build()
    except BuildError as exc:
        print(f"\n빌드 실패: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(corpus, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if not OUTPUT_PATH.exists():
            print("\nsegments.json이 없습니다.", file=sys.stderr)
            return 1
        current = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        fresh = json.loads(rendered)
        # generated_at은 실행할 때마다 바뀌므로 비교에서 뺀다.
        current.pop("generated_at", None)
        fresh.pop("generated_at", None)
        if current != fresh:
            print(
                "\nsegments.json이 최신이 아닙니다. "
                "'python scripts/build_corpus.py'를 실행하고 커밋하세요.",
                file=sys.stderr,
            )
            return 1
        print("\nsegments.json 최신 상태입니다.")
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"\n{OUTPUT_PATH.relative_to(REPO_ROOT)} 생성 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
