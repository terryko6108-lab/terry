"""Claude API를 사용하는 간단한 웹 챗봇 서버.

실행: python server.py  →  브라우저에서 http://localhost:8000 접속
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8000"))
MODEL = "claude-opus-5-5"
SYSTEM_PROMPT = (
    "당신은 친절한 한국어 챗봇입니다. "
    "사용자의 질문에 명확하고 간결하게 답하세요."
)
MAX_HISTORY = 40  # 서버로 보낼 최대 메시지 수 (오래된 대화부터 잘라냄)


def load_env_file(path: Path) -> None:
    """.env 파일의 KEY=VALUE 줄을 환경 변수로 읽어온다 (이미 설정된 값은 유지)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(HERE / ".env")
client = anthropic.Anthropic()


def has_credentials() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def clean_history(raw) -> list[dict]:
    """브라우저에서 받은 대화 기록을 검증해 API 형식으로 바꾼다."""
    if not isinstance(raw, list):
        raise ValueError("messages는 배열이어야 합니다.")
    messages = []
    for item in raw[-MAX_HISTORY:]:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            continue
        messages.append({"role": role, "content": content})
    # API는 user 메시지로 시작해야 한다.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("마지막 메시지는 사용자 메시지여야 합니다.")
    return messages


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            messages = clean_history(payload.get("messages"))
        except (ValueError, json.JSONDecodeError) as e:
            self.send_plain(400, f"잘못된 요청: {e}")
            return

        # 답변을 생성되는 대로 조금씩 브라우저에 보낸다 (스트리밍).
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not has_credentials():
            self.write_chunk("⚠️ API 키가 설정되지 않았습니다. README의 '2. API 키 설정'을 참고하세요.")
            return
        try:
            with client.beta.messages.stream(
                model=MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_config={"effort": "low"},  # 일상 대화는 low로 충분하고 빠르다
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # 안전 필터가 거절하면 다른 모델로 자동 재시도
            ) as stream:
                for text in stream.text_stream:
                    self.write_chunk(text)
                final = stream.get_final_message()
            if final.stop_reason == "refusal":
                self.write_chunk("\n\n(이 요청에는 답변할 수 없어요. 다른 질문을 해주세요.)")
            elif final.stop_reason == "max_tokens":
                self.write_chunk("\n\n(답변이 너무 길어 중간에 잘렸어요.)")
        except anthropic.AuthenticationError:
            self.write_chunk("⚠️ API 키가 올바르지 않습니다. .env 파일의 ANTHROPIC_API_KEY를 확인하세요.")
        except anthropic.RateLimitError:
            self.write_chunk("⚠️ 요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
        except anthropic.APIStatusError as e:
            self.write_chunk(f"⚠️ API 오류 ({e.status_code}): {e.message}")
        except anthropic.APIConnectionError:
            self.write_chunk("⚠️ Claude API에 연결할 수 없습니다. 인터넷 연결을 확인하세요.")
        except (BrokenPipeError, ConnectionResetError):
            pass  # 사용자가 페이지를 닫은 경우
        except Exception as e:
            self.log_error("예상치 못한 오류: %r", e)
            self.write_chunk("⚠️ 서버에서 예상치 못한 오류가 발생했습니다. 터미널 로그를 확인하세요.")

    def send_plain(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_chunk(self, text: str) -> None:
        self.wfile.write(text.encode("utf-8"))
        self.wfile.flush()


if __name__ == "__main__":
    if not has_credentials():
        print("⚠️  ANTHROPIC_API_KEY가 설정되지 않았습니다. README의 '2. API 키 설정'을 참고하세요.")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ChatHandler)
    print(f"챗봇 실행 중: http://localhost:{PORT}  (종료: Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
