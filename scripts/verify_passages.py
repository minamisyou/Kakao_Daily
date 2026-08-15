#!/usr/bin/env python3
"""손으로 고른 구절이 실제 원문과 글자 단위로 일치하는지 대조한다.

data/passages/*.json의 원문(text)이 data/sources/<id>.txt 안에 그대로
들어 있는지 확인한다. 통과하면 --write로 해당 파일의 verified를 true로 올린다.

  python scripts/fetch_sources.py          # 먼저 전문을 받고
  python scripts/verify_passages.py --write

대조 전 구절은 verified=false로 남아 있으므로, 어떤 구절이 아직 검증되지
않았는지 저장소만 봐도 알 수 있다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKS_PATH = REPO_ROOT / "data" / "works.json"
PASSAGES_DIR = REPO_ROOT / "data" / "passages"
SOURCES_DIR = REPO_ROOT / "data" / "sources"

#: 판본마다 갈리는 문장부호는 한 형태로 모아서 비교한다.
PUNCTUATION_FOLD = {
    "‘": "'", "’": "'", "‛": "'",
    "“": '"', "”": '"', "‟": '"',
    "‐": "-", "‑": "-", "‒": "-",
    "–": "-", "—": "-", "―": "-",
    "…": "...", "‥": "..", "⋯": "...",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    for src, dst in PUNCTUATION_FOLD.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


def verify_work(work_id: str) -> tuple[bool, list[str]]:
    """(모두 일치했는가, 문제 목록) 반환."""
    passages_path = PASSAGES_DIR / f"{work_id}.json"
    source_path = SOURCES_DIR / f"{work_id}.txt"

    if not passages_path.exists():
        return True, []  # 손으로 고른 구절이 없으면 대조할 것도 없다.
    if not source_path.exists():
        return False, [f"원문이 없습니다: {source_path.name} (fetch_sources.py 먼저 실행)"]

    data = json.loads(passages_path.read_text(encoding="utf-8"))
    haystack = normalize(source_path.read_text(encoding="utf-8"))

    problems = []
    for index, passage in enumerate(data.get("passages", []), start=1):
        if normalize(passage["text"]) not in haystack:
            preview = passage["text"].replace("\n", " ")[:60]
            problems.append(f"#{index} 원문에서 찾지 못함: {preview}…")

    return not problems, problems


def main() -> int:
    parser = argparse.ArgumentParser(description="구절 원문 대조")
    parser.add_argument(
        "--write",
        action="store_true",
        help="전부 일치한 작품의 verified를 true로 기록한다.",
    )
    args = parser.parse_args()

    works = json.loads(WORKS_PATH.read_text(encoding="utf-8"))["works"]
    failed = 0

    for work in works:
        work_id = work["id"]
        passages_path = PASSAGES_DIR / f"{work_id}.json"
        if not passages_path.exists():
            continue

        ok, problems = verify_work(work_id)
        if ok:
            print(f"  ✓ {work_id}")
            if args.write:
                data = json.loads(passages_path.read_text(encoding="utf-8"))
                data["verified"] = True
                passages_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        else:
            failed += 1
            print(f"  ✗ {work_id}", file=sys.stderr)
            for problem in problems:
                print(f"      {problem}", file=sys.stderr)

    if failed:
        print(
            f"\n{failed}개 작품에서 원문과 다른 구절이 있습니다. "
            f"해당 구절을 원문에 맞게 고치거나 삭제하세요.",
            file=sys.stderr,
        )
        return 1

    print("\n모든 구절이 원문과 일치합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
