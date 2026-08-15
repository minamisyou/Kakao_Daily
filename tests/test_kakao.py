"""카카오 API 호출 — 실제 네트워크 없이 응답을 흉내 낸다."""

import json

import pytest

from src.kakao import (
    MEMO_SEND_URL,
    TOKEN_URL,
    KakaoError,
    build_authorize_url,
    build_text_template,
    refresh_access_token,
    send_text_memo,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    """마지막 요청을 기억해 두는 requests.Session 대역."""

    def __init__(self, response):
        self.response = response
        self.url = None
        self.data = None
        self.headers = None

    def post(self, url, data=None, headers=None, timeout=None):
        self.url = url
        self.data = data
        self.headers = headers
        return self.response


class TestRefreshAccessToken:
    def test_returns_access_token(self):
        session = FakeSession(FakeResponse({"access_token": "AT", "expires_in": 21599}))
        tokens = refresh_access_token("KEY", "RT", session=session)
        assert tokens.access_token == "AT"
        assert tokens.expires_in == 21599

    def test_sends_refresh_grant_to_the_token_endpoint(self):
        session = FakeSession(FakeResponse({"access_token": "AT"}))
        refresh_access_token("KEY", "RT", session=session)
        assert session.url == TOKEN_URL
        assert session.data == {
            "grant_type": "refresh_token",
            "client_id": "KEY",
            "refresh_token": "RT",
        }

    def test_refresh_token_is_absent_when_kakao_does_not_rotate_it(self):
        session = FakeSession(FakeResponse({"access_token": "AT"}))
        assert refresh_access_token("KEY", "RT", session=session).refresh_token is None

    def test_rotated_refresh_token_is_surfaced(self):
        session = FakeSession(
            FakeResponse({"access_token": "AT", "refresh_token": "NEW_RT"})
        )
        assert refresh_access_token("KEY", "RT", session=session).refresh_token == "NEW_RT"

    def test_expired_refresh_token_raises(self):
        session = FakeSession(
            FakeResponse(
                {"error": "invalid_grant", "error_description": "refresh token expired"},
                status_code=400,
            )
        )
        with pytest.raises(KakaoError, match="refresh token expired"):
            refresh_access_token("KEY", "RT", session=session)

    def test_missing_access_token_raises(self):
        session = FakeSession(FakeResponse({"token_type": "bearer"}))
        with pytest.raises(KakaoError, match="access_token이 없습니다"):
            refresh_access_token("KEY", "RT", session=session)


class TestTextTemplate:
    def test_link_is_set_on_both_web_and_mobile(self):
        template = build_text_template("본문", "https://example.test")
        assert template["link"] == {
            "web_url": "https://example.test",
            "mobile_web_url": "https://example.test",
        }

    def test_object_type_is_text(self):
        assert build_text_template("본문", "https://example.test")["object_type"] == "text"

    def test_button_title_is_omitted_when_not_given(self):
        assert "button_title" not in build_text_template("본문", "https://example.test")

    def test_button_title_is_included_when_given(self):
        template = build_text_template("본문", "https://example.test", "원문 읽기")
        assert template["button_title"] == "원문 읽기"


class TestSendTextMemo:
    def test_posts_to_the_memo_endpoint_with_bearer_token(self):
        session = FakeSession(FakeResponse({"result_code": 0}))
        send_text_memo("AT", "본문", "https://example.test", session=session)
        assert session.url == MEMO_SEND_URL
        assert session.headers == {"Authorization": "Bearer AT"}

    def test_template_is_sent_as_json_without_escaping_hangul(self):
        session = FakeSession(FakeResponse({"result_code": 0}))
        send_text_memo("AT", "봄·봄", "https://example.test", session=session)
        assert "봄·봄" in session.data["template_object"]
        assert json.loads(session.data["template_object"])["text"] == "봄·봄"

    def test_insufficient_scope_raises(self):
        session = FakeSession(
            FakeResponse(
                {"code": -402, "msg": "insufficient scopes."}, status_code=403
            )
        )
        with pytest.raises(KakaoError, match="insufficient scopes"):
            send_text_memo("AT", "본문", "https://example.test", session=session)


class TestAuthorizeUrl:
    def test_requests_only_the_talk_message_scope(self):
        url = build_authorize_url("KEY", "http://localhost:8080/callback")
        assert "scope=talk_message" in url
        assert "response_type=code" in url
