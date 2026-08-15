"""카카오 말풍선에 들어갈 텍스트 조립.

한 회차(segment)는 챕터 한 도막 분량(~2,000~2,500자)이라 카카오 200자
제한 안에 못 들어간다. 그래서 회차 하나를 여러 통으로 쪼개 연달아 보낸다.
첫 통에만 제목·저자·진행도 헤더를 달고, 나머지는 본문만 이어 보낸다.

해외 트랙은 원문 회차 전체(여러 통) 다음에 번역 회차 전체(여러 통)를
잇달아 보낸다. 마지막 통에는 "내일 계속" 또는 "완결" 안내를 덧붙인다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import KAKAO_TEXT_LIMIT
from .corpus import Segment, Selection, Work
from .wrap import split_into_bubbles

ORIGINAL_BUTTON = "원문 읽기"

#: 진행도 표시가 최대로 길어졌을 때를 가정해 헤더 예산을 잡는다.
_WORST_CASE_PROGRESS = "(9999/9999)"

#: 하루 발송이 통제 불능으로 길어지는 걸 막는 안전선. 빌드 검증에서만 쓴다.
MAX_BUBBLES_PER_DAY = 24


class MessageTooLongError(ValueError):
    """조립한 말풍선이 카카오 200자 제한을 넘었을 때."""


@dataclass(frozen=True)
class OutgoingMessage:
    text: str
    link_url: str
    button_title: str

    def __post_init__(self) -> None:
        if len(self.text) > KAKAO_TEXT_LIMIT:
            raise MessageTooLongError(
                f"말풍선이 {len(self.text)}자로 카카오 제한({KAKAO_TEXT_LIMIT}자)을 "
                f"넘었습니다. 조각을 더 짧게 나누세요:\n{self.text}"
            )


def _progress(segment: Segment) -> str:
    return f"({segment.seq}/{segment.total})"


def header_budget(title: str, author: str) -> int:
    """헤더 + 빈 줄이 차지하는 글자 수. 본문에 쓸 수 있는 양은 200에서 이걸 뺀 만큼."""
    header = f"📖 {title} — {author} {_WORST_CASE_PROGRESS}"
    return len(header) + 2  # "\n\n"


def _continuation_footer(segment: Segment) -> str:
    if segment.seq >= segment.total:
        return "\n\n(오늘로 완결입니다. 내일부터 다음 이야기가 이어집니다)"
    return "\n\n(내일 이어집니다)"


def _bubble_texts(icon: str, title: str, author: str, segment: Segment, body: str) -> list[str]:
    """헤더 달린 첫 통 + 본문만 있는 나머지 통들. 하나도 못 만들면 빈 리스트."""
    if not body:
        return []

    limit = KAKAO_TEXT_LIMIT - header_budget(title, author)
    chunks = split_into_bubbles(body, limit)
    if not chunks:
        return []

    header = f"{icon} {title} — {author} {_progress(segment)}"
    texts = [f"{header}\n\n{chunks[0]}"]
    texts.extend(chunks[1:])
    return texts


def _append_footer(texts: list[str], footer: str) -> list[str]:
    candidate = texts[-1] + footer
    if len(candidate) <= KAKAO_TEXT_LIMIT:
        return [*texts[:-1], candidate]
    return [*texts, footer.strip()]


def _korean_messages(work: Work, segment: Segment) -> list[OutgoingMessage]:
    texts = _bubble_texts("📖", work.title, work.author, segment, segment.text)
    texts = _append_footer(texts, _continuation_footer(segment))
    return [
        OutgoingMessage(text=t, link_url=work.source_url, button_title=ORIGINAL_BUTTON)
        for t in texts
    ]


def _foreign_messages(work: Work, segment: Segment) -> list[OutgoingMessage]:
    original_title = work.title_original or work.title
    original_texts = _bubble_texts("📖", original_title, work.author, segment, segment.text)

    reading_body = segment.text_ko
    reading_texts = _bubble_texts("🔎", work.title, work.author, segment, reading_body)
    if segment.note:
        note = f"— {segment.note}"
        if len(note) <= KAKAO_TEXT_LIMIT:
            reading_texts.append(note)

    all_texts = _append_footer(original_texts + reading_texts, _continuation_footer(segment))
    return [
        OutgoingMessage(text=t, link_url=work.source_url, button_title=ORIGINAL_BUTTON)
        for t in all_texts
    ]


def build_messages(selection: Selection) -> list[OutgoingMessage]:
    """오늘 보낼 말풍선 목록. 보낼 순서대로 반환한다."""
    work, segment = selection.work, selection.segment
    if selection.track == "en":
        if not segment.text_ko:
            raise ValueError(
                f"해외 트랙 조각에 번역(text_ko)이 없습니다: "
                f"{segment.work_id} #{segment.seq}"
            )
        return _foreign_messages(work, segment)
    return _korean_messages(work, segment)
