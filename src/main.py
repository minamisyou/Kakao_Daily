"""진입점: 오늘 분량을 골라 카카오톡 '나에게 보내기'로 발송한다."""

from __future__ import annotations

import logging
import sys
import time

from .config import Config, ConfigError, today_kst
from .corpus import CorpusError, load_corpus, select_for_day
from .kakao import (
    KakaoError,
    refresh_access_token,
    send_text_memo,
    troubleshooting_hint,
)
from .message import OutgoingMessage, build_messages

#: 연속 발송 사이 간격. 카카오는 순서를 보장하지 않아서 살짝 띄운다.
SEND_INTERVAL_SECONDS = 1.5

logger = logging.getLogger("kakao_daily")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _preview(messages: list[OutgoingMessage]) -> None:
    for i, message in enumerate(messages, start=1):
        print(f"\n{'─' * 46}")
        print(f"[{i}/{len(messages)}] {len(message.text)}자 · 버튼: {message.button_title}")
        print(f"{'─' * 46}")
        print(message.text)
        print(f"🔗 {message.link_url}")
    print(f"\n{'─' * 46}")


def _persist_rotated_token(config: Config, new_refresh_token: str) -> None:
    """카카오가 새 refresh token을 내려줬을 때 워크플로가 읽을 자리에 남긴다.

    refresh token은 2개월 만료인데, 만료 1개월 이내로 남으면 갱신 응답에
    새 값이 함께 온다. 이걸 Secret에 반영해야 연재가 끊기지 않는다.
    """
    if config.refresh_token_out is None:
        logger.warning(
            "새 refresh token이 발급됐지만 REFRESH_TOKEN_OUT이 설정되지 않아 "
            "저장하지 못했습니다. GitHub Secret KAKAO_REFRESH_TOKEN을 직접 갱신하세요."
        )
        return

    config.refresh_token_out.parent.mkdir(parents=True, exist_ok=True)
    config.refresh_token_out.write_text(new_refresh_token, encoding="utf-8")
    config.refresh_token_out.chmod(0o600)
    logger.info("새 refresh token을 %s에 기록했습니다.", config.refresh_token_out)


def run() -> int:
    config = Config.from_env()
    corpus = load_corpus(config.segments_path)

    today = today_kst()
    selection = select_for_day(corpus, today, config.start_date, config.track_pattern)
    messages = build_messages(selection)

    logger.info(
        "%s · %s일차 · %s 트랙 · %s %d/%d · 말풍선 %d통",
        today.isoformat(),
        selection.day_index,
        selection.track,
        selection.work.title,
        selection.segment.seq,
        selection.segment.total,
        len(messages),
    )

    if config.dry_run:
        logger.info("DRY_RUN=1 — 실제로 보내지 않고 미리보기만 출력합니다.")
        _preview(messages)
        return 0

    tokens = refresh_access_token(
        config.rest_api_key, config.refresh_token, config.client_secret
    )
    if tokens.refresh_token and tokens.refresh_token != config.refresh_token:
        _persist_rotated_token(config, tokens.refresh_token)

    for i, message in enumerate(messages, start=1):
        if i > 1:
            time.sleep(SEND_INTERVAL_SECONDS)
        send_text_memo(
            tokens.access_token,
            message.text,
            message.link_url,
            message.button_title,
        )
        logger.info("전송 완료 %d/%d (%d자)", i, len(messages), len(message.text))

    return 0


def main() -> int:
    _configure_logging()
    try:
        return run()
    except (ConfigError, CorpusError) as exc:
        logger.error("설정/코퍼스 오류: %s", exc)
        return 2
    except KakaoError as exc:
        logger.error("카카오 API 오류: %s", exc)
        hint = troubleshooting_hint(exc)
        if hint:
            logger.error("%s", hint)
        return 3
    except Exception:  # noqa: BLE001 - 워크플로 로그에 원인을 남기고 실패시킨다.
        logger.exception("예상치 못한 오류로 발송에 실패했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
