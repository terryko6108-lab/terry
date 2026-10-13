# Terry 웹 챗봇

Claude API(`claude-opus-5-5`)로 대화하는 간단한 웹 챗봇입니다.
Python 서버(`server.py`) 하나와 웹 화면(`index.html`) 하나로 이루어져 있습니다.

## 준비물

- Python 3.10 이상
- Anthropic API 키 ([console.anthropic.com](https://console.anthropic.com)에서 발급, 사용량만큼 요금이 부과됩니다)

## 1. 설치

`chatbot` 폴더에서 실행합니다.

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. API 키 설정

`.env.example`을 복사해 `.env` 파일을 만들고, 키를 붙여넣습니다.

```
ANTHROPIC_API_KEY=sk-ant-...
```

`.env`는 `.gitignore`에 들어 있어 GitHub에 올라가지 않습니다. **API 키를 코드나 커밋에 직접 넣지 마세요.**

## 3. 실행

```bash
python server.py
```

브라우저에서 <http://localhost:8000> 을 엽니다. 종료는 터미널에서 `Ctrl+C`.

## 구조

| 파일 | 역할 |
|---|---|
| `server.py` | 웹 화면을 보여주고, `/api/chat` 요청을 받아 Claude의 답변을 스트리밍으로 돌려줍니다 |
| `index.html` | 채팅 화면. 대화 기록은 브라우저 메모리에만 있고, 새로고침하면 사라집니다 |

## 바꿔보기

- **챗봇 성격:** `server.py`의 `SYSTEM_PROMPT`를 수정하세요. (예: "당신은 요리 도우미입니다")
- **답변 깊이:** `output_config={"effort": "low"}`를 `"medium"`이나 `"high"`로 올리면 더 신중하게 답하지만 느려지고 비용이 늘어납니다.
- **포트:** `PORT` 환경 변수로 바꿀 수 있습니다.
