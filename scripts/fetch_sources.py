#!/usr/bin/env python3
"""위키문헌 / Project Gutenberg에서 작품 전문을 받아 data/sources에 저장한다.

네트워크가 열린 곳에서 실행해야 한다. GitHub Actions의 build-corpus 워크플로가
이 스크립트를 대신 돌려주므로, 로컬에 파이썬 환경이 없어도 된다.

  python scripts/fetch_sources.py                # 전부
  python scripts/fetch_sources.py --work 봄봄     # 일부 (id 부분 일치)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKS_PATH = REPO_ROOT / "data" / "works.json"
SOURCES_DIR = REPO_ROOT / "data" / "sources"

USER_AGENT = "Kakao_Daily/1.0 (public-domain literature; +https://github.com)"
TIMEOUT = 30
POLITE_DELAY_SECONDS = 1.0

GUTENBERG_START = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE
)
GUTENBERG_END = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE
)


class FetchError(Exception):
    pass


def fetch_wikisource(page: str, lang: str = "ko") -> str:
    """위키문헌 문서의 본문을 평문으로 받아온다."""
    response = requests.get(
        f"https://{lang}.wikisource.org/w/api.php",
        params={
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "titles": page,
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        raise FetchError(f"위키문헌에 '{page}' 문서가 없습니다. 제목을 확인하세요.")
    extract = (pages[0].get("extract") or "").strip()
    if not extract:
        raise FetchError(f"'{page}' 문서 본문이 비어 있습니다.")
    return extract


def fetch_gutenberg(ebook_id: int) -> str:
    """Gutenberg 평문본을 받아 머리말/꼬리말을 잘라낸다."""
    urls = [
        f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt",
        f"https://www.gutenberg.org/files/{ebook_id}/{ebook_id}-0.txt",
    ]
    last_error: Exception | None = None
    for url in urls:
        try:
            response = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            last_error = exc
            continue

        response.encoding = response.encoding or "utf-8"
        text = response.text

        start = GUTENBERG_START.search(text)
        if start:
            text = text[start.end() :]
        end = GUTENBERG_END.search(text)
        if end:
            text = text[: end.start()]
        return text.strip()

    raise FetchError(f"Gutenberg #{ebook_id} 내려받기 실패: {last_error}")


def fetch_one(work: dict) -> str:
    source = work["source"]
    kind = source["type"]
    if kind == "wikisource":
        return fetch_wikisource(source["page"], source.get("lang", "ko"))
    if kind == "gutenberg":
        return fetch_gutenberg(int(source["ebook_id"]))
    raise FetchError(f"알 수 없는 출처 형식: {kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description="작품 전문 수집")
    parser.add_argument("--work", help="작품 id 부분 문자열로 대상을 좁힌다.")
    args = parser.parse_args()

    works = json.loads(WORKS_PATH.read_text(encoding="utf-8"))["works"]
    if args.work:
        works = [w for w in works if args.work in w["id"]]
        if not works:
            print(f"'{args.work}'에 해당하는 작품이 없습니다.", file=sys.stderr)
            return 1

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0

    for index, work in enumerate(works):
        if index:
            time.sleep(POLITE_DELAY_SECONDS)
        try:
            text = fetch_one(work)
        except (FetchError, requests.RequestException) as exc:
            print(f"  ✗ {work['id']}: {exc}", file=sys.stderr)
            failures += 1
            continue

        target = SOURCES_DIR / f"{work['id']}.txt"
        target.write_text(text + "\n", encoding="utf-8")
        print(f"  ✓ {work['id']}: {len(text):,}자 → {target.relative_to(REPO_ROOT)}")

    if failures:
        print(f"\n{failures}개 작품을 받지 못했습니다.", file=sys.stderr)
        return 1
    print("\n수집 완료. 이제 'python scripts/build_corpus.py'를 실행하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
