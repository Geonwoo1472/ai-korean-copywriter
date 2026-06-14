![AI 카피라이터 구동 화면](static/demo.gif)

<h1 align="center">🖋️ AI 기반 한국어 카피라이터</h1>

<p align="center">
  <strong>Gemini · ChatGPT · Ollama 등 다양한 AI 엔진을 활용하여,<br/>
  매체·톤·키워드 조건에 맞춘 매끄러운 한국어 카피라이팅을 실시간 스트리밍으로 생성하는 웹 애플리케이션입니다.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Gemini_API-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/ChatGPT_API-412991?style=flat-square&logo=openai&logoColor=white" alt="ChatGPT" />
  <img src="https://img.shields.io/badge/Ollama_(Local_AI)-000000?style=flat-square&logo=ollama&logoColor=white" alt="Ollama" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
</p>

---

## 📋 목차

1. [프로그램 소개](#프로그램-소개)
2. [시스템 요구 사양](#시스템-요구-사양)
3. [주요 기능](#주요-기능)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [기술 스택](#기술-스택)
6. [디렉토리 구조](#디렉토리-구조)
7. [실행 방법](#실행-방법)
8. [AI 엔진 설정 가이드](#ai-엔진-설정-가이드)

---

## 💡 프로그램 소개

**AI 기반 한국어 카피라이터**는 사용자가 입력한 키워드와 설정한 조건(매체, 톤앤매너)을 바탕으로 최적의 한국어 카피를 생성하는 웹 도구입니다. 

복잡하고 번거로운 프롬프트 엔지니어링 없이, 웹 UI 상에서 몇 번의 클릭만으로 전문적인 비즈니스 이메일, 트렌디한 인스타그램 피드, 친근한 블로그 글 등을 즉시 작성할 수 있습니다. 클라우드 기반 API(Gemini, ChatGPT, Custom API)뿐만 아니라 완전 오프라인으로 작동하는 로컬 AI(Ollama)까지 모두 통합 지원합니다.

---

## 💻 시스템 요구 사양

프로그램 구동을 위한 최소 및 권장 사양입니다.

| 구분 | 최소 사양 (Minimum) | 권장 사양 (Recommended) |
| :--- | :--- | :--- |
| **OS** | Windows 10/11, macOS 11+, Linux | Windows 10/11 (64-bit), macOS 12+, 최신 Linux |
| **CPU** | Dual-Core 2.0GHz 이상 | Quad-Core 2.5GHz 이상 |
| **RAM** | 4GB 이상 | 8GB 이상 |
| **저장공간** | SSD 여유 공간 10GB 이상 | SSD 여유 공간 20GB 이상 |
| **Python** | 3.10 이상 | 3.10 또는 3.11 |

---

## 🚀 주요 기능

- **매체 맞춤형 프롬프트 엔진**: 인스타그램, 블로그, 당근마켓, 이메일 등 각 플랫폼의 문법과 노하우에 맞춘 가이드라인 자동 설계
- **정교한 톤앤매너(Tone & Manner) 제어**: '친근하게', '정중하게', '전문적으로' 등 원하는 말투를 설정하여 완성도 높은 텍스트 생성
- **멀티 AI 엔진 실시간 전환**: Gemini, ChatGPT, Ollama(로컬), Custom API(DeepSeek, Groq 등)를 UI에서 실시간으로 스위칭
- **실시간 스트리밍(SSE)**: 응답을 기다릴 필요 없이 실시간 생성 과정을 토큰 단위로 브라우저에 표시 (연결/생성/완료 상태 바 제공)
- **강력한 예외 처리 및 폴백**: API 키 에러, 한도 초과, 연결 유실 시 직관적인 한국어 에러 메시지 노출 및 자동 지수 백오프 재시도
- **다크/라이트 모드 지원**: 시스템 기본 테마 설정과 연동되며, 로드 시 깜빡임(FOUC) 방지 처리 적용

---

## 🏗️ 시스템 아키텍처

FastAPI 백엔드의 처리 흐름과 AI 엔진 연동 구조입니다.

```text
┌────────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (main.py)                                             │
│                                                                        │
│  ┌─ [라우터 / 서비스] ────────────────────────────────────────────────┐ │
│  │ Engine Router (_resolve_engine)                                    │ │
│  │  → UI 키 우선 → .env 폴백 → 엔진 자동 감지                         │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ Prompt Builder (_build_prompts)                                    │ │
│  │  → 매체별 가이드라인 매핑 + 톤 반영 + 키워드 지시                  │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ Error Handler (_format_api_error)                                  │ │
│  │  → 예외 타입별 한국어 메시지 + 대안 엔진 제안                      │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ Retry Engine (_is_retryable)                                       │ │
│  │  → 503/Timeout만 재시도, 지수 백오프                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  [엔드포인트]                                                          │
│  GET  /              → 정적 HTML 서빙                                  │
│  GET  /api/status    → 현재 활성 엔진 상태 반환                        │
│  POST /api/generate-stream → SSE 스트리밍 텍스트 생성                  │
│  POST /api/generate  → 비스트리밍 호환 엔드포인트                      │
│  GET  /api/ollama/status  → Ollama 실행 상태 + 모델 목록               │
│  POST /api/ollama/pull    → 모델 다운로드 (SSE 진행률)                 │
└──────────────────────┬─────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌────────────┐ ┌────────────┐ ┌────────────────┐
  │  ☁️ Gemini  │ │  ☁️ ChatGPT │ │  🖥️ Ollama     │
  │  (OpenAI   │ │  (Native   │ │  (OpenAI 호환  │
  │   호환 API)│ │   API)     │ │   로컬 서버)   │
  └────────────┘ └────────────┘ └────────────────┘
```

### 💡 핵심 설계 패턴

#### 🔌 어댑터 패턴 (ChatGPT SDK 통합)
Gemini, OpenAI, Ollama가 모두 OpenAI 규격의 API를 지원하므로, **OpenAI Python SDK 하나로 모든 AI 호출을 통합 처리**합니다. `base_url`과 `model`을 유연하게 교체하여 코드 유지보수성을 극대화했습니다.

```python
# Gemini → OpenAI 호환 엔드포인트 설정 예시
client = OpenAI(
    api_key=gemini_key, 
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Ollama → 로컬 OpenAI 호환 엔드포인트 설정 예시
client = OpenAI(
    api_key="ollama", 
    base_url="http://localhost:11434/v1"
)

# 동일한 인터페이스로 스트리밍 호출
stream = client.chat.completions.create(model=model, messages=messages, stream=True)
```


#### 🛡️ 지능형 에러 핸들링
API 에러 유형에 따라 명확한 한국어 가이드라인을 제공합니다.
```python
# 재시도 가능 여부 판단 (서버 일시적 오류 또는 시간 초과 시 지수 백오프 작동)
def _is_retryable(e):
    return (isinstance(e, APIStatusError) and e.status_code == 503) or isinstance(e, APITimeoutError)

# 에러 타입별 대응법 안내
def _format_api_error(e, provider, model_name):
    if isinstance(e, RateLimitError):
        return "무료 API 사용량 한도를 초과했습니다. 잠시 후 다시 시도하거나 다른 엔진을 선택하세요."
    if isinstance(e, AuthenticationError):
        return "입력한 API 키가 올바르지 않습니다. 키 설정을 확인해 주세요."
    if isinstance(e, APIConnectionError):
        return "AI API 서버에 연결할 수 없습니다. 네트워크 환경을 확인해 주세요."
    ...
```

---

## 🛠️ 기술 스택

| 레이어 | 기술 스택 |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI |
| **ASGI Server** | Uvicorn |
| **AI SDK** | OpenAI Python SDK (ChatGPT API 포함) |
| **Frontend** | HTML5 / CSS3 / Vanilla JS |
| **Markdown** | Marked.js (CDN) |
| **Font** | Pretendard WebFont |
| **Validation** | Pydantic v2 |
| **Env 관리** | python-dotenv |

---

## 📁 디렉토리 구조

```text
ai-korean-copywriter/
├── main.py                  # FastAPI 백엔드 (엔진 라우팅, 프롬프트 생성, SSE 스트리밍, 에러 핸들링)
├── requirements.txt         # Python 의존성 라이브러리 목록
├── .env                     # 로컬 API 키 설정 파일 (Git 추적 제외)
├── .env.example             # 환경 변수 템플릿 파일
├── .gitignore               # Git 관리 제외 파일 규칙 지정
├── LICENSE                  # MIT 라이선스 파일
├── README.md                # 프로젝트 소개 및 개발 가이드 (현재 파일)
└── static/                  # 프론트엔드 정적 리소스 디렉토리
    ├── index.html           # 시맨틱 마크업 기반 웹 UI 메인 화면
    ├── style.css            # 라이트/다크 테마 토큰 시스템 및 반응형 CSS 레이아웃
    ├── script.js            # SSE 파싱, 로컬 엔진 관리, 테마 연동 등의 클라이언트 로직
    └── screenshot.png       # README용 애플리케이션 스크린샷 이미지
```

---

## 📦 실행 방법

### 1. 저장소 클론 및 이동
```bash
git clone https://github.com/Geonwoo1472/ai-korean-copywriter.git
cd ai-korean-copywriter
```

### 2. 가상환경 구성 및 패키지 설치
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS / Linux)
source venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정
```bash
# 템플릿 복사
cp .env.example .env

# 에디터로 .env 파일을 열고 보유하고 계신 API 키를 기입합니다.
# (키가 없어도 웹 UI에서 실시간 직접 기입이나 데모 모드로 실행 가능합니다.)
```

### 4. 개발 서버 실행
```bash
python main.py
```
서버 실행 후 브라우저를 열고 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**으로 접속합니다.

---

## 🔧 AI 엔진 설정 가이드

본 프로젝트는 아래 3가지 방식으로 AI API 키를 연결할 수 있어, 상황에 맞춰 다양하게 사용이 가능합니다.

### 방법 1: 웹 UI에서 직접 입력 (권장)
웹 브라우저 상단 **"사용할 AI 엔진"** 선택 상자에서 원하는 엔진을 선택하면 API 키 입력 필드가 노출됩니다. 기입된 키는 **브라우저 로컬 스토리지(LocalStorage)에 안전하게 임시 저장**되므로, 매 실행마다 다시 입력할 번거로움이 없습니다.

### 방법 2: `.env` 환경 변수 파일 기입
백엔드 서버 설정에 고정하여 편리하게 사용하고자 할 경우 `.env` 파일에 기록합니다.
```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# ChatGPT (OpenAI) API Key
OPENAI_API_KEY=your_openai_api_key_here

# Custom OpenAI 호환 API
CUSTOM_API_KEY=your_custom_api_key_here
CUSTOM_BASE_URL=https://api.deepseek.com/v1/
CUSTOM_MODEL=deepseek-chat
```

### 방법 3: 로컬 오프라인 AI (Ollama 사용)
클라우드 비용 결제나 API 키 없이 완전 로컬 무료 AI 환경을 구성할 수 있습니다.
1. [Ollama 공식 홈페이지](https://ollama.com)에서 PC 사양에 맞는 클라이언트를 다운로드 및 설치합니다.
2. 터미널에서 경량 모델을 내려받습니다 (예: Gemma 2B):
   ```bash
   ollama run gemma2:2b
   ```
3. 백엔드 서버가 실행 중인 상태에서 웹 UI의 **"Ollama 사용"** 탭을 선택하고 실행할 모델을 연동합니다.

---

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE)에 따라 자유롭게 사용 및 수정, 배포할 수 있습니다.
