#!/usr/bin/env python3
"""[최초 1회] 카카오 인가를 받아 refresh token을 발급한다.

로컬에서 실행한다. 임시 웹서버를 띄우고 브라우저로 카카오 동의 화면을 연 뒤,
돌아온 인가 코드를 토큰으로 바꿔 화면에 출력한다.

  export KAKAO_REST_API_KEY=...
  python scripts/get_token.py

출력된 refresh token을 GitHub Secret KAKAO_REFRESH_TOKEN에 넣으면 끝이다.
이 값은 2개월 만료지만, 매일 발송이 돌면서 만료 전에 자동으로 새 값으로
교체되므로 다시 이 스크립트를 돌릴 일은 없다.

'나와의 채팅' 대신 친구(팀 멤버로 등록한 테스트 계정 등)에게 보내려면,
그 친구의 uuid가 필요하다. --scope로 friends 동의항목을 함께 받으면
로그인 직후 이 앱에 연결된 친구 목록과 uuid를 바로 보여준다:

  python scripts/get_token.py --scope talk_message,friends

이때는 로그인한 계정(발신자) 기준으로 친구 목록이 나온다 — 카카오톡에서
실제로 서로 친구여야 하고, 상대방도 이 앱의 팀 멤버로 등록돼 있어야 목록에
잡힌다. 나온 uuid를 KAKAO_RECEIVER_UUIDS에 넣으면 된다.
"""

from __future__ import annotations

import argparse
import http.server
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.kakao import (  # noqa: E402
    KakaoError,
    SCOPE_FRIENDS,
    SCOPE_TALK_MESSAGE,
    build_authorize_url,
    exchange_authorization_code,
    get_friends,
    troubleshooting_hint,
)

DEFAULT_PORT = 8080
CALLBACK_PATH = "/callback"

SUCCESS_HTML = """<!doctype html>
<meta charset="utf-8">
<title>인가 완료</title>
<body style="font-family:system-ui;padding:3rem;text-align:center">
<h1>인가가 끝났습니다</h1>
<p>터미널로 돌아가 출력된 refresh token을 확인하세요.</p>
</body>"""

FAILURE_HTML = """<!doctype html>
<meta charset="utf-8">
<title>인가 실패</title>
<body style="font-family:system-ui;padding:3rem;text-align:center">
<h1>인가에 실패했습니다</h1>
<p>터미널의 오류 메시지를 확인하세요.</p>
</body>"""


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 규약
        parsed = urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_error(404)
            return

        params = parse_qs(parsed.query)
        _CallbackHandler.code = (params.get("code") or [None])[0]
        _CallbackHandler.error = (params.get("error_description") or params.get("error") or [None])[0]

        body = (SUCCESS_HTML if _CallbackHandler.code else FAILURE_HTML).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args) -> None:  # 서버 접근 로그는 지운다.
        pass


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def main() -> int:
    parser = argparse.ArgumentParser(description="카카오 refresh token 발급")
    parser.add_argument(
        "--scope",
        default=SCOPE_TALK_MESSAGE,
        help=(
            "쉼표로 구분된 동의항목 목록 (기본: talk_message). "
            f"친구 uuid를 조회하려면 '{SCOPE_TALK_MESSAGE},{SCOPE_FRIENDS}'."
        ),
    )
    args = parser.parse_args()
    requested_friends = SCOPE_FRIENDS in args.scope.split(",")

    rest_api_key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    if not rest_api_key:
        print(
            "환경변수 KAKAO_REST_API_KEY가 필요합니다.\n"
            "  export KAKAO_REST_API_KEY=<카카오 개발자 콘솔의 REST API 키>",
            file=sys.stderr,
        )
        return 2

    # Client Secret을 '사용함'으로 켜 둔 앱만 필요하다. 꺼져 있으면 비워 둔다.
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET", "").strip()

    port = int(os.environ.get("CALLBACK_PORT", DEFAULT_PORT))
    redirect_uri = f"http://localhost:{port}{CALLBACK_PATH}"

    if not _port_is_free(port):
        print(
            f"{port} 포트가 이미 쓰이고 있습니다. "
            f"CALLBACK_PORT=9000 처럼 다른 포트를 지정하세요.\n"
            f"(카카오 콘솔의 Redirect URI에도 같은 주소를 등록해야 합니다.)",
            file=sys.stderr,
        )
        return 2

    authorize_url = build_authorize_url(rest_api_key, redirect_uri, scope=args.scope)

    print("카카오 개발자 콘솔의 Redirect URI에 다음 주소가 등록돼 있어야 합니다:")
    print(f"  {redirect_uri}\n")
    print(f"요청할 동의항목: {args.scope}\n")
    print(
        "Client Secret: "
        + (
            "사용함 (KAKAO_CLIENT_SECRET 적용됨)"
            if client_secret
            else "미설정 — 콘솔에서 '사용함'으로 켜 두셨다면 KAKAO_CLIENT_SECRET을 넣어야 합니다"
        )
        + "\n"
    )
    print("브라우저에서 동의 화면을 엽니다. 열리지 않으면 아래 주소를 직접 여세요:")
    print(f"  {authorize_url}\n")

    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    webbrowser.open(authorize_url)
    print("동의를 기다리는 중… (Ctrl+C로 취소)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n취소했습니다.", file=sys.stderr)
        return 130
    finally:
        server.server_close()

    if _CallbackHandler.error or not _CallbackHandler.code:
        print(f"\n인가 실패: {_CallbackHandler.error or '인가 코드를 받지 못했습니다.'}", file=sys.stderr)
        return 1

    try:
        tokens = exchange_authorization_code(
            rest_api_key, _CallbackHandler.code, redirect_uri, client_secret
        )
    except KakaoError as exc:
        print(f"\n토큰 교환 실패: {exc}", file=sys.stderr)
        hint = troubleshooting_hint(exc)
        if hint:
            print(f"\n{hint}", file=sys.stderr)
            if "KOE006" in str(exc):
                print(f"  {redirect_uri}", file=sys.stderr)
        return 1

    if not tokens.refresh_token:
        print(
            "\naccess token은 받았지만 refresh token이 없습니다. "
            "카카오 앱 설정에서 '카카오 로그인'이 켜져 있는지 확인하세요.",
            file=sys.stderr,
        )
        return 1

    print("\n" + "=" * 60)
    print("발급 완료. 아래 두 값을 GitHub Secrets에 등록하세요.")
    print("  Settings → Secrets and variables → Actions → New repository secret")
    print("=" * 60)
    print(f"KAKAO_REST_API_KEY  = {rest_api_key}")
    print(f"KAKAO_REFRESH_TOKEN = {tokens.refresh_token}")
    if client_secret:
        print(f"KAKAO_CLIENT_SECRET = {client_secret}")
    print("=" * 60)
    print("\n이 값은 비밀번호와 같습니다. 저장소나 채팅에 붙여넣지 마세요.")

    if requested_friends:
        print("\n" + "=" * 60)
        print("이 앱에 연결된 카카오톡 친구 목록")
        print("=" * 60)
        try:
            friends = get_friends(tokens.access_token)
        except KakaoError as exc:
            print(f"친구 목록 조회 실패: {exc}", file=sys.stderr)
            hint = troubleshooting_hint(exc)
            if hint:
                print(f"\n{hint}", file=sys.stderr)
            return 1

        if not friends:
            print(
                "친구가 없습니다. 다음을 확인하세요:\n"
                "  - 상대방이 카카오 개발자 콘솔 > 앱 설정 > 팀 관리에 멤버로 등록돼 있는지\n"
                "  - 방금 로그인한 계정과 실제 카카오톡에서 서로 친구인지"
            )
        else:
            for friend in friends:
                nickname = friend.get("profile_nickname", "(닉네임 비공개)")
                print(f"  {friend['uuid']}  —  {nickname}")
            print(
                "\n보낼 대상의 uuid를 KAKAO_RECEIVER_UUIDS Secret에 넣으세요 "
                "(여러 명이면 쉼표로 구분)."
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
