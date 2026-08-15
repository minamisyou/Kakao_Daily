"""카카오 말풍선에 들어갈 텍스트 조립.

한국 트랙은 한 통, 해외 트랙은 두 통(원문 → 해석)을 만든다. 원문과 번역을
한 통에 우겨넣으면 200자 제한 때문에 양쪽 다 토막이 나서, 읽을 만한 분량을
지키려면 나누는 편이 낫다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import KAKAO_TEXT_LIMIT
from .corpus import Segment, Selection, Work

ORIGINAL_BUTTON = "원문 읽기"


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


def _korean_message(work: Work, segment: Segment) -> OutgoingMessage:
    header = f"📖 {work.title} — {work.author} {_progress(segment)}"
    return OutgoingMessage(
        text=f"{header}\n\n{segment.text}",
        link_url=work.source_url,
        button_title=ORIGINAL_BUTTON,
    )


def _foreign_messages(work: Work, segment: Segment) -> list[OutgoingMessage]:
    original_title = work.title_original or work.title
    original = OutgoingMessage(
        text=f"📖 {original_title} — {work.author} {_progress(segment)}"
        f"\n\n{segment.text}",
        link_url=work.source_url,
        button_title=ORIGINAL_BUTTON,
    )

    body = segment.text_ko
    if segment.note:
        body = f"{body}\n\n— {segment.note}"
    reading = OutgoingMessage(
        text=f"🔎 {work.title} {_progress(segment)}\n\n{body}",
        link_url=work.source_url,
        button_title=ORIGINAL_BUTTON,
    )
    return [original, reading]


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
    return [_korean_message(work, segment)]
