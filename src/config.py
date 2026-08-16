"""환경변수에서 실행 설정을 읽어온다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEGMENTS_PATH = REPO_ROOT / "data" / "segments.json"

#: 카카오 text 템플릿의 text 필드 최대 길이.
KAKAO_TEXT_LIMIT = 200


class ConfigError(Exception):
    """필수 설정이 없거나 형식이 잘못됐을 때."""


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _required(name: str, dry_run: bool) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if dry_run:
        # DRY_RUN에서는 카카오를 호출하지 않으므로 자격증명 없이도 돌아가야 한다.
        return ""
    raise ConfigError(
        f"환경변수 {name}가 비어 있습니다. "
        f"README의 '카카오 앱 세팅'을 따라 값을 넣거나 DRY_RUN=1로 실행하세요."
    )


def parse_receiver_uuids(raw: str) -> tuple[str, ...]:
    """쉼표로 구분된 친구 UUID 목록. 비어 있으면 '나와의 채팅'으로 보낸다."""
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def parse_date(raw: str, field: str) -> date:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigError(f"{field}는 YYYY-MM-DD 형식이어야 합니다: {raw!r}") from exc


def today_kst(now: datetime | None = None) -> date:
    """KST 기준 오늘 날짜.

    GitHub Actions 러너는 UTC라서, 이 변환을 빼먹으면 한국 시간 오전 8시에
    보낸 메시지가 '어제 분량'이 된다.
    """
    return (now or datetime.now(timezone.utc)).astimezone(KST).date()


@dataclass(frozen=True)
class Config:
    rest_api_key: str
    refresh_token: str
    #: 카카오 콘솔에서 Client Secret을 '사용함'으로 켠 앱만 필요하다.
    #: 꺼져 있으면 빈 문자열이어야 하고, 넣으면 오히려 거절당한다.
    client_secret: str
    #: 비어 있으면 '나와의 채팅'으로, 값이 있으면 그 친구들에게 보낸다.
    #: 비즈니스 전환 전에는 앱의 팀 멤버로 등록된 계정끼리만 가능하다.
    receiver_uuids: tuple[str, ...]
    start_date: date
    segments_path: Path
    dry_run: bool
    #: 갱신된 refresh token을 적어둘 경로. 워크플로가 읽어 Secret을 교체한다.
    refresh_token_out: Path | None

    @classmethod
    def from_env(cls) -> "Config":
        dry_run = _env_flag("DRY_RUN")
        out = os.environ.get("REFRESH_TOKEN_OUT", "").strip()
        return cls(
            rest_api_key=_required("KAKAO_REST_API_KEY", dry_run),
            refresh_token=_required("KAKAO_REFRESH_TOKEN", dry_run),
            client_secret=os.environ.get("KAKAO_CLIENT_SECRET", "").strip(),
            receiver_uuids=parse_receiver_uuids(os.environ.get("KAKAO_RECEIVER_UUIDS", "")),
            start_date=parse_date(
                os.environ.get("START_DATE", "2026-08-17"), "START_DATE"
            ),
            segments_path=Path(
                os.environ.get("SEGMENTS_PATH", str(DEFAULT_SEGMENTS_PATH))
            ),
            dry_run=dry_run,
            refresh_token_out=Path(out) if out else None,
        )
