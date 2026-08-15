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
    """한 문장이 통째로 예산을 넘을 때만 쓰는 최후 수단.

    매번 한도 끝까지 채우고 남는 만큼만 마지막 조각으로 떼어내면, 그
    마지막 조각이 "eye forever." 처럼 몇 글자짜리 꼬리가 되기 쉽다. 필요한
    조각 수를 먼저 정하고 그만큼 고르게 나눠, 꼬리가 뭉텅 짧아지는 일을
    막는다.
    """
    if len(sentence) <= limit:
        return [sentence]

    piece_count = -(-len(sentence) // limit)  # ceil
    target = -(-len(sentence) // piece_count)  # ceil, 조각마다 고르게

    chunks: list[str] = []
    remaining = sentence
    while len(remaining) > target:
        cut = remaining.rfind(" ", 0, target + 1)
        if cut <= 0:
            cut = target
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def split_into_bubbles(full_text: str, limit: int) -> list[str]:
    """전문을 limit 글자 이하의 조각으로 나눈다. 문장 중간은 자르지 않는다.

    문단 경계는 들어맞으면 그대로 살리되(버블 안에 "\\n\\n"으로 남는다),
    강제로 거기서 버블을 끊지는 않는다. 강제로 끊으면, 긴 문장이 문단 끝에서
    hard_wrap으로 잘려 짧은 꼬리만 남았을 때 그 꼬리가 다음 문단과 합쳐질
    기회를 잃고 혼자 작은 말풍선이 돼 버린다.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]

    # (조각, 새 문단의 시작인가) 목록으로 문단 구조 전체를 한 줄로 편다.
    items: list[tuple[str, bool]] = []
    for para_index, paragraph in enumerate(paragraphs):
        for sent_index, sentence in enumerate(split_sentences(paragraph)):
            pieces = hard_wrap(sentence, limit) if len(sentence) > limit else [sentence]
            for piece_index, piece in enumerate(pieces):
                starts_paragraph = para_index > 0 and sent_index == 0 and piece_index == 0
                items.append((piece, starts_paragraph))

    bubbles: list[str] = []
    buffer = ""
    for piece, starts_paragraph in items:
        if buffer:
            separator = "\n\n" if starts_paragraph else " "
            candidate = f"{buffer}{separator}{piece}"
        else:
            candidate = piece
        if len(candidate) <= limit:
            buffer = candidate
        else:
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
