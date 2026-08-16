#!/usr/bin/env python3
"""data/works.json + 원문/구절 → data/segments.json 빌드.

작품마다 두 갈래로 회차(하루 분량, ~2,000~2,500자)를 만든다.

  1. data/sources/<id>.txt 가 있으면 (한국 트랙)  → 전문을 회차 단위로 자동으로 묶는다
  2. 없으면 data/passages/<id>.json             → 손으로 채운 회차를 그대로 쓴다

해외 트랙은 원문과 번역이 1:1로 짝지어져 있어야 하므로 항상 2번을 쓴다.
번역은 사람(또는 이 저장소를 채우는 사람)이 직접 써야 하기 때문이다.

편성은 요일로 언어를 나누지 않는다. **작품 하나가 완결돼야만 언어가
바뀐다** — 다른 트랙에 아직 안 읽은 작품이 있으면 그쪽으로 넘어가고,
없으면 지금 트랙에서 다음 작품으로 계속 이어간다. 그렇게 만든 하나의
발송 순서(queue)를 segments.json에 그대로 저장하고, 발송 시점에는
day_index로 그 큐를 인덱싱하기만 하면 된다.

한 회차는 발송 시점에 카카오 200자 말풍선 여러 통으로 쪼개진다(src/message.py).
여기서는 그 쪼개기가 실제로 성공하는지, 하루 발송이 너무 길어지지 않는지만
미리 검증한다. 새벽에 발송이 깨지는 것보다 빌드가 깨지는 게 낫다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import KAKAO_TEXT_LIMIT  # noqa: E402
from src.corpus import Segment, Selection, Work  # noqa: E402
from src.message import MAX_BUBBLES_PER_DAY, build_messages  # noqa: E402
from src.wrap import bundle_into_installments  # noqa: E402

WORKS_PATH = REPO_ROOT / "data" / "works.json"
PASSAGES_DIR = REPO_ROOT / "data" / "passages"
SOURCES_DIR = REPO_ROOT / "data" / "sources"
OUTPUT_PATH = REPO_ROOT / "data" / "segments.json"

#: 회차 하나의 목표 분량. 200자 말풍선 기준 10~15통 정도가 되는 크기로 잡았다.
INSTALLMENT_TARGET_CHARS = 2200
INSTALLMENT_HARD_CAP_CHARS = 2800

#: 두 트랙 다 작품이 남아 있을 때, 어느 쪽부터 시작할지.
START_TRACK = "kr"


class BuildError(Exception):
    pass


def load_works() -> list[dict]:
    data = json.loads(WORKS_PATH.read_text(encoding="utf-8"))
    return data["works"]


def installments_from_source(work_id: str) -> list[dict] | None:
    path = SOURCES_DIR / f"{work_id}.txt"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    chunks = bundle_into_installments(
        text, INSTALLMENT_TARGET_CHARS, INSTALLMENT_HARD_CAP_CHARS
    )
    return [{"text": chunk} for chunk in chunks]


def installments_from_file(work_id: str) -> list[dict] | None:
    path = PASSAGES_DIR / f"{work_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    passages = data.get("passages", [])
    return passages or None


def build_segments_for(work_meta: dict) -> tuple[list[dict], str]:
    """(회차 목록, 출처 설명) 반환."""
    work_id = work_meta["id"]

    if work_meta["track"] == "kr":
        from_source = installments_from_source(work_id)
        if from_source:
            return from_source, f"전문 자동 회차 분할 ({len(from_source)}회차)"

    passages = installments_from_file(work_id)
    if not passages:
        return [], "원문·회차 없음"

    return list(passages), f"큐레이션 회차 ({len(passages)}회차)"


def merge_into_queue(
    works_by_track: dict[str, list[tuple[str, list[dict]]]],
    start_track: str = START_TRACK,
) -> list[tuple[str, str, dict]]:
    """작품이 끝나야 언어가 바뀌는 순서로 병합한다.

    지금 트랙의 작품 하나를 다 넣고 나서, 다른 트랙에 아직 안 읽은 작품이
    있으면 그쪽으로 넘어간다. 없으면(예: 해외 트랙에 완역작이 하나뿐일 때)
    지금 트랙에서 계속 다음 작품으로 이어간다. 두 트랙 다 바닥나면 멈춘다 —
    그 뒤로는 day_index % len(queue)로 처음부터 반복된다.

    반환값은 (track, work_id, 원본 회차 dict)의 리스트.
    """
    tracks = [t for t in works_by_track if works_by_track[t]]
    if not tracks:
        return []
    active = start_track if start_track in tracks else tracks[0]
    pointers = {t: 0 for t in tracks}
    queue: list[tuple[str, str, dict]] = []

    while True:
        if pointers[active] >= len(works_by_track[active]):
            candidates = [t for t in tracks if pointers[t] < len(works_by_track[t])]
            if not candidates:
                break
            active = candidates[0]
            continue

        work_id, segments = works_by_track[active][pointers[active]]
        queue.extend((active, work_id, seg) for seg in segments)
        pointers[active] += 1

        other_candidates = [
            t for t in tracks if t != active and pointers[t] < len(works_by_track[t])
        ]
        if other_candidates:
            active = other_candidates[0]

    return queue


def validate(work: Work, segment: Segment) -> None:
    """실제 발송 경로로 말풍선을 조립해 본다. 여기서 터지면 빌드 실패."""
    selection = Selection(track=work.track, work=work, segment=segment, day_index=0)
    messages = build_messages(selection)
    if len(messages) > MAX_BUBBLES_PER_DAY:
        raise BuildError(
            f"{segment.work_id} #{segment.seq}가 하루에 {len(messages)}통이나 "
            f"보냅니다 (상한 {MAX_BUBBLES_PER_DAY}통). 회차를 더 짧게 나누세요."
        )
    for message in messages:
        if len(message.text) > KAKAO_TEXT_LIMIT:
            raise BuildError(
                f"{segment.work_id} #{segment.seq}에 {len(message.text)}자짜리 "
                f"말풍선이 있습니다 (제한 {KAKAO_TEXT_LIMIT}자)."
            )


def build() -> dict:
    works_meta = load_works()
    works_out: dict[str, dict] = {}
    works_by_track: dict[str, list[tuple[str, list[dict]]]] = {}
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
        works_by_track.setdefault(meta["track"], []).append((work_id, raw_segments))

    print("작품별 빌드 결과:")
    print("\n".join(report))

    if len(works_by_track) < 2 or any(not v for v in works_by_track.values()):
        raise BuildError(
            "두 트랙 모두 작품이 있어야 편성이 돌아갑니다. "
            "비어 있는 트랙에 작품을 추가하세요."
        )

    ordered_queue = merge_into_queue(works_by_track)
    total_by_work: dict[str, int] = {}
    for _track, work_id, _passage in ordered_queue:
        total_by_work[work_id] = total_by_work.get(work_id, 0) + 1

    queue_out: list[dict] = []
    seq_by_work: dict[str, int] = {}
    run_order: list[str] = []
    for track, work_id, passage in ordered_queue:
        work = Work.from_dict({"id": work_id, **works_out[work_id]})
        seq_by_work[work_id] = seq_by_work.get(work_id, 0) + 1
        segment = Segment(
            work_id=work_id,
            seq=seq_by_work[work_id],
            total=total_by_work[work_id],
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
        queue_out.append(entry)
        if not run_order or run_order[-1] != work_id:
            run_order.append(work_id)

    total_chars = sum(len(item["text"]) for item in queue_out)
    print(f"\n발송 순서: {' → '.join(run_order)}")
    print(f"총 {len(queue_out)}일치, {total_chars:,}자")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kakao_text_limit": KAKAO_TEXT_LIMIT,
        "works": works_out,
        "queue": queue_out,
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
