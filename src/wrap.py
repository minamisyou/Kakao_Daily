"""문장 경계를 지키며 텍스트를 글자 수 제한 조각으로 나눈다.

빌드 시점(작품 전문을 회차 단위로 묶을 때)과 발송 시점(한 회차를 카카오
200자 말풍선 여러 통으로 쪼갤 때) 양쪽에서 같은 로직을 쓴다.
"""

from __future__ import annotations

import re

#: 문장 끝으로 인정할 문자. 한국어 인용부호와 말줄임표를 포함한다.
_SENTENCE_BREAK = re.compile(r'(?<=[.!?……‥])\s+|(?<=[."”’\'」』])\s+')


def split_sentences(paragraph: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_BREAK.split(paragraph)]
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


def split_into_bubbles(full_text: str, limit: int) -> list[str]:
    """전문을 limit 글자 이하의 조각으로 나눈다.

    문단을 넘나들지 않고, 문장 중간도 자르지 않는다. 읽는 맛이 거기서 갈린다.
    """
    bubbles: list[str] = []
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
                        bubbles.append(buffer)
                    buffer = piece
        if buffer:
            bubbles.append(buffer)
    return bubbles


def bundle_into_installments(
    full_text: str, target_chars: int, hard_cap_chars: int
) -> list[str]:
    """전문을 target_chars 안팎(최대 hard_cap_chars)의 '회차'로 묶는다.

    말풍선 분할과 달리 문단 경계를 넘나들 수 있다 — 대화체가 많은 소설은
    문단이 짧아서, 문단 단위로만 묶으면 회차가 너무 잘게 쪼개진다. 문장
    중간은 여전히 자르지 않는다.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]
    installments: list[str] = []
    buffer_paragraphs: list[str] = []
    buffer_len = 0

    def flush() -> None:
        nonlocal buffer_paragraphs, buffer_len
        if buffer_paragraphs:
            installments.append("\n\n".join(buffer_paragraphs))
        buffer_paragraphs = []
        buffer_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > hard_cap_chars:
            # 문단 하나가 이미 상한을 넘으면(긴 독백 등) 그 문단만 따로 쪼갠다.
            flush()
            installments.extend(split_into_bubbles(paragraph, hard_cap_chars))
            continue

        added_len = len(paragraph) + (2 if buffer_paragraphs else 0)
        if buffer_len + added_len > hard_cap_chars:
            flush()
            buffer_paragraphs = [paragraph]
            buffer_len = len(paragraph)
        else:
            buffer_paragraphs.append(paragraph)
            buffer_len += added_len
            if buffer_len >= target_chars:
                flush()

    flush()
    return installments
