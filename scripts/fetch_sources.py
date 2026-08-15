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


#: 이보다 짧으면 실제 본문이 아니라 '라이선스' 같은 상용구 스텁만 받아온 것으로
#: 본다 — 위키문헌이 소설을 하위 문서(예: "작품명/1")로 나눠 놓아
#: extracts API가 서문만 돌려주는 경우 이런 일이 생긴다. 조용히 성공한 것처럼
#: 커밋하면 그 스텁이 그대로 발송에 실려 나가므로, 여기서 실패로 취급한다.
MIN_EXTRACT_CHARS = 500

#: 위키문헌은 본문 뒤에 "== 라이선스 ==" 같은 상용구 섹션을 붙인다.
#: 소설 본문에는 MediaWiki 섹션 헤딩이 나올 일이 없으므로, 이런 줄을
#: 만나면 그 앞까지만 본문으로 친다.
_TRAILING_SECTION = re.compile(r"\n==+\s*[^\n=]+\s*==+\n")


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

    trailing = _TRAILING_SECTION.search(extract)
    if trailing:
        extract = extract[: trailing.start()].strip()

    if not extract:
        raise FetchError(f"'{page}' 문서 본문이 비어 있습니다.")
    if len(extract) < MIN_EXTRACT_CHARS:
        raise FetchError(
            f"'{page}' 문서가 {len(extract)}자밖에 안 됩니다 (최소 {MIN_EXTRACT_CHARS}자). "
            f"본문이 하위 문서로 나뉘어 있어 서문만 받아왔을 가능성이 높습니다. "
            f"실제 문서 구조를 확인하고 필요하면 하위 문서 제목을 각각 받아 이어 붙이세요."
        )
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
        return _clean_gutenberg_text(text.strip())

    raise FetchError(f"Gutenberg #{ebook_id} 내려받기 실패: {last_error}")


#: Gutenberg 평문의 이탤릭 표시(_word_)를 걷어낸다. 발송에는 강조 마크업이
#: 그대로 노출되면 오타처럼 보인다.
_ITALIC_MARKUP = re.compile(r"_(\S+?)_")


def _clean_gutenberg_text(text: str) -> str:
    """고정폭으로 줄바꿈된 원문을 문단 하나가 한 줄이 되도록 다시 흐른다."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    joined = []
    for paragraph in paragraphs:
        line = " ".join(l.strip() for l in paragraph.splitlines())
        joined.append(re.sub(r"\s+", " ", line).strip())
    return _ITALIC_MARKUP.sub(r"\1", "\n\n".join(joined))


def extract_excerpt(text: str, after: str, before: str) -> str:
    """앤솔러지 한 권에서 작품 하나만 잘라낸다.

    Gutenberg에 단편 하나만 담긴 판본이 없고 전집으로만 있는 경우에 쓴다
    (예: 포의 단편들은 "The Works of Edgar Allan Poe" 여러 권에만 있다).
    `after` 뒤부터, 그 뒤에 처음 나오는 `before` 앞까지를 잘라낸다 — 목차에도
    같은 제목이 나오므로 `before` 검색은 반드시 `after` 위치부터 시작해야
    앞쪽(목차)이 아니라 뒤쪽(다음 작품 제목)을 잡는다.
    """
    start = text.find(after)
    if start < 0:
        raise FetchError(f"excerpt_after 문자열을 원문에서 찾지 못했습니다: {after!r}")
    end = text.find(before, start)
    if end < 0:
        raise FetchError(f"excerpt_before 문자열을 원문에서 찾지 못했습니다: {before!r}")
    return text[start:end].strip()


def fetch_one(work: dict) -> str:
    source = work["source"]
    kind = source["type"]
    if kind == "wikisource":
        return fetch_wikisource(source["page"], source.get("lang", "ko"))
    if kind == "gutenberg":
        text = fetch_gutenberg(int(source["ebook_id"]))
        after, before = source.get("excerpt_after"), source.get("excerpt_before")
        if after and before:
            text = extract_excerpt(text, after, before)
        return text
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
