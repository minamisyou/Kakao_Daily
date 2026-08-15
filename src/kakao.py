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
FRIEND_SEND_URL = f"{KAPI_BASE}/v1/api/talk/friends/message/default/send"
FRIENDS_LIST_URL = f"{KAPI_BASE}/v1/api/talk/friends"

#: 나에게 보내기에 필요한 유일한 동의항목.
SCOPE_TALK_MESSAGE = "talk_message"
#: 친구 목록을 읽어와 UUID를 확인할 때만 필요하다. 친구에게 실제로
#: 보내는 API 자체는 talk_message 스코프만 있으면 된다.
SCOPE_FRIENDS = "friends"

#: 비즈니스 앱 전환(심사) 전에는 앱의 팀 멤버로 등록된 카카오 계정끼리만
#: 친구 메시지를 주고받을 수 있다. 개인 프로젝트에서 테스트 계정을 만들어
#: 팀 멤버로 등록하는 방식이 여기 해당한다.

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


def _with_client_secret(data: dict, client_secret: str | None) -> dict:
    """Client Secret을 '사용함'으로 켜 둔 앱은 토큰 요청마다 이 값을 요구한다.

    켜 놓고 빼먹으면 카카오가 invalid_client로 거절한다. 꺼져 있는 앱에
    굳이 보내면 그것도 거절당하므로, 값이 있을 때만 싣는다.
    """
    if client_secret:
        return {**data, "client_secret": client_secret}
    return data


def refresh_access_token(
    rest_api_key: str,
    refresh_token: str,
    client_secret: str | None = None,
    session: requests.Session | None = None,
) -> TokenBundle:
    """refresh token으로 access token을 재발급한다."""
    http = session or requests
    response = http.post(
        TOKEN_URL,
        data=_with_client_secret(
            {
                "grant_type": "refresh_token",
                "client_id": rest_api_key,
                "refresh_token": refresh_token,
            },
            client_secret,
        ),
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
    client_secret: str | None = None,
    session: requests.Session | None = None,
) -> TokenBundle:
    """최초 1회, 인가 코드를 토큰으로 교환한다 (scripts/get_token.py에서 사용)."""
    http = session or requests
    response = http.post(
        TOKEN_URL,
        data=_with_client_secret(
            {
                "grant_type": "authorization_code",
                "client_id": rest_api_key,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            client_secret,
        ),
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


def send_text(
    access_token: str,
    text: str,
    link_url: str,
    button_title: str | None = None,
    receiver_uuids: list[str] | None = None,
    session: requests.Session | None = None,
) -> dict:
    """카카오톡으로 텍스트 메시지를 보낸다.

    `receiver_uuids`가 없으면 '나와의 채팅'으로, 있으면 그 친구들에게 보낸다.
    """
    http = session or requests
    template = build_text_template(text, link_url, button_title)
    data = {"template_object": json.dumps(template, ensure_ascii=False)}

    if receiver_uuids:
        url = FRIEND_SEND_URL
        data["receiver_uuids"] = json.dumps(receiver_uuids, ensure_ascii=False)
    else:
        url = MEMO_SEND_URL

    response = http.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        data=data,
        timeout=TIMEOUT_SECONDS,
    )
    return _raise_for_kakao_error(response, "메시지 전송")


def get_friends(access_token: str, session: requests.Session | None = None) -> list[dict]:
    """이 앱에 연결된 카카오톡 친구 목록을 가져온다.

    `friends` 동의항목이 있는 토큰이어야 한다. 각 항목에 `uuid`, `profile_nickname`
    등이 들어 있다 — 그 uuid를 send_text의 receiver_uuids에 넣으면 된다.
    """
    http = session or requests
    response = http.get(
        FRIENDS_LIST_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT_SECONDS,
    )
    payload = _raise_for_kakao_error(response, "친구 목록 조회")
    return payload.get("elements", [])


#: 카카오 오류 코드는 원인을 거의 알려주지 않아서, 실제로 자주 걸리는
#: 설정 문제를 짚어 준다.
_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("invalid_client", "KOE010"),
        "확인할 것:\n"
        "  1. 카카오 콘솔 > 카카오 로그인 > 보안 > Client Secret이 '사용함'이면\n"
        "     KAKAO_CLIENT_SECRET 환경변수에 그 코드를 넣어야 합니다.\n"
        "     (반대로 '사용 안 함'인데 값을 넣어도 같은 오류가 납니다.)\n"
        "  2. 앱 키 화면의 여러 키 중 'REST API 키'가 맞는지\n"
        "     (네이티브/JavaScript/Admin 키를 넣으면 이 오류가 납니다.)\n"
        "  3. 키 앞뒤에 공백이나 줄바꿈이 섞이지 않았는지",
    ),
    (
        ("KOE006",),
        "등록되지 않은 Redirect URI입니다. 카카오 콘솔 > 카카오 로그인 >\n"
        "Redirect URI에 아래 주소를 글자 그대로 등록하세요 (끝 슬래시까지 동일해야 합니다).",
    ),
    (
        ("invalid_grant", "KOE320"),
        "인가 코드나 refresh token이 만료됐거나 이미 쓰였습니다.\n"
        "scripts/get_token.py를 처음부터 다시 실행하세요.",
    ),
    (
        ("insufficient scopes", "-402"),
        "카카오 콘솔 > 카카오 로그인 > 동의항목에서 '카카오톡 메시지 전송'을\n"
        "사용 설정한 뒤, 토큰을 다시 발급받아야 합니다. 동의항목을 바꿔도\n"
        "이미 발급된 토큰에는 반영되지 않습니다.",
    ),
    (
        ("-401", "KOE005"),
        "친구에게 보내기는 앱이 비즈니스 전환(심사)되기 전까지 앱의\n"
        "'팀 멤버'로 등록된 카카오 계정끼리만 됩니다. 콘솔 > 앱 설정 >\n"
        "팀 관리에서 발신 계정과 수신 계정이 모두 멤버로 등록돼 있는지,\n"
        "두 계정이 실제 카카오톡에서 서로 친구로 추가돼 있는지 확인하세요.",
    ),
)


def troubleshooting_hint(error: Exception) -> str:
    """오류 메시지에서 원인을 추측해 안내문을 돌려준다. 짚이는 게 없으면 빈 문자열."""
    text = str(error)
    for needles, hint in _HINTS:
        if any(needle in text for needle in needles):
            return hint
    return ""


def build_authorize_url(
    rest_api_key: str, redirect_uri: str, scope: str = SCOPE_TALK_MESSAGE
) -> str:
    """브라우저로 열 인가 URL (scripts/get_token.py에서 사용).

    여러 동의항목을 한 번에 받으려면 쉼표로 이어서 넘긴다
    (예: f"{SCOPE_TALK_MESSAGE},{SCOPE_FRIENDS}").
    """
    from urllib.parse import urlencode

    query = urlencode(
        {
            "client_id": rest_api_key,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"
