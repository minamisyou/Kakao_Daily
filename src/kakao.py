"""카카오 OAuth 토큰 갱신과 '나에게 보내기' 전송."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests

KAUTH_BASE = "https://kauth.kakao.com"
KAPI_BASE = "https://kapi.kakao.com"

TOKEN_URL = f"{KAUTH_BASE}/oauth/token"
AUTHORIZE_URL = f"{KAUTH_BASE}/oauth/authorize"
MEMO_SEND_URL = f"{KAPI_BASE}/v2/api/talk/memo/default/send"

#: 나에게 보내기에 필요한 유일한 동의항목.
SCOPE_TALK_MESSAGE = "talk_message"

TIMEOUT_SECONDS = 20


class KakaoError(Exception):
    """카카오 API가 실패 응답을 돌려줬을 때."""


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    #: 카카오는 refresh token 만료가 1개월 이내로 남았을 때만 새 값을 함께 준다.
    #: 그 외에는 None이고, 기존 refresh token을 계속 쓰면 된다.
    refresh_token: str | None
    expires_in: int | None


def _raise_for_kakao_error(response: requests.Response, action: str) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or "error" in payload:
        detail = payload.get("error_description") or payload.get("msg") or response.text
        code = payload.get("error") or payload.get("code") or response.status_code
        raise KakaoError(f"{action} 실패 (code={code}): {detail}")
    return payload


def refresh_access_token(
    rest_api_key: str,
    refresh_token: str,
    session: requests.Session | None = None,
) -> TokenBundle:
    """refresh token으로 access token을 재발급한다."""
    http = session or requests
    response = http.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": rest_api_key,
            "refresh_token": refresh_token,
        },
        timeout=TIMEOUT_SECONDS,
    )
    payload = _raise_for_kakao_error(response, "access token 갱신")

    access_token = payload.get("access_token")
    if not access_token:
        raise KakaoError(f"응답에 access_token이 없습니다: {payload}")

    return TokenBundle(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        expires_in=payload.get("expires_in"),
    )


def exchange_authorization_code(
    rest_api_key: str,
    code: str,
    redirect_uri: str,
    session: requests.Session | None = None,
) -> TokenBundle:
    """최초 1회, 인가 코드를 토큰으로 교환한다 (scripts/get_token.py에서 사용)."""
    http = session or requests
    response = http.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": rest_api_key,
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=TIMEOUT_SECONDS,
    )
    payload = _raise_for_kakao_error(response, "인가 코드 교환")
    return TokenBundle(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_in=payload.get("expires_in"),
    )


def build_text_template(
    text: str,
    link_url: str,
    button_title: str | None = None,
) -> dict:
    """카카오 text 템플릿 오브젝트를 만든다.

    link는 선택이 아니라 필수 필드다. 버튼을 붙이지 않아도 말풍선 자체가
    이 URL로 연결된다.
    """
    template: dict = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link_url, "mobile_web_url": link_url},
    }
    if button_title:
        template["button_title"] = button_title
    return template


def send_text_memo(
    access_token: str,
    text: str,
    link_url: str,
    button_title: str | None = None,
    session: requests.Session | None = None,
) -> dict:
    """카카오톡 '나와의 채팅'으로 텍스트 메시지를 보낸다."""
    http = session or requests
    template = build_text_template(text, link_url, button_title)
    response = http.post(
        MEMO_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=TIMEOUT_SECONDS,
    )
    return _raise_for_kakao_error(response, "메시지 전송")


def build_authorize_url(rest_api_key: str, redirect_uri: str) -> str:
    """브라우저로 열 인가 URL (scripts/get_token.py에서 사용)."""
    from urllib.parse import urlencode

    query = urlencode(
        {
            "client_id": rest_api_key,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE_TALK_MESSAGE,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"
