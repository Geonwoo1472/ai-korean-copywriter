from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from openai import (
    OpenAI,
    RateLimitError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
)
import os
import json
import time
import logging
import uvicorn
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

# ─── 로깅 설정 ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("copywriter")

app = FastAPI(
    title="AI 한국어 카피라이터",
    description="매체·톤·키워드에 최적화된 한국어 텍스트 생성 API",
    version="1.0.0",
)

# ─── CORS 미들웨어 (로컬 개발 편의) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── 보안 헤더 미들웨어 ───
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── 상수 ───
MAX_RETRIES = 2
RETRY_DELAY_SEC = 2.0
REQUEST_TIMEOUT = 60

# ─── 입력값 최대 길이 ───
MAX_TOPIC_LEN = 500
MAX_KEYWORDS_LEN = 300

class GenerationRequest(BaseModel):
    topic: str
    purpose: str
    tone: str
    keywords: str
    engine: str = "auto"
    model: str = ""
    local_model: str = "gemma2:2b"
    local_url: str = "http://localhost:11434/v1"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    custom_api_key: str = ""
    custom_base_url: str = ""
    custom_model: str = ""

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("주제를 입력해주세요.")
        if len(v) > MAX_TOPIC_LEN:
            raise ValueError(f"주제는 {MAX_TOPIC_LEN}자 이내로 입력해주세요.")
        return v

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("키워드를 입력해주세요.")
        if len(v) > MAX_KEYWORDS_LEN:
            raise ValueError(f"키워드는 {MAX_KEYWORDS_LEN}자 이내로 입력해주세요.")
        return v

class OllamaPullRequest(BaseModel):
    model: str
    ollama_url: str = "http://localhost:11434"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지 서빙"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/api/health")
async def health_check():
    """서버 상태 확인 (헬스 체크)"""
    return {"status": "ok", "version": "1.0.0"}

def get_llm_client_and_model():
    """
    환경 변수를 감지하여 어떤 LLM 공급자를 사용할지 판단하고
    맞춤형 OpenAI 호환 클라이언트와 모델명을 반환합니다.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    custom_key = os.environ.get("CUSTOM_API_KEY")
    custom_base_url = os.environ.get("CUSTOM_BASE_URL")
    custom_model = os.environ.get("CUSTOM_MODEL")

    if gemini_key:
        client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=REQUEST_TIMEOUT,
        )
        return "gemini", client, "gemini-2.0-flash"
    elif openai_key:
        client = OpenAI(api_key=openai_key, timeout=REQUEST_TIMEOUT)
        return "openai", client, "gpt-4o-mini"
    elif custom_key and custom_base_url:
        client = OpenAI(
            api_key=custom_key,
            base_url=custom_base_url,
            timeout=REQUEST_TIMEOUT,
        )
        return "custom", client, custom_model or "custom-model"
    else:
        return "mock", None, ""

# ─── 에러 메시지 생성 헬퍼 ───

def _format_api_error(e: Exception, provider: str, model_name: str) -> str:
    """예외 타입별 사용자 친화적 한국어 에러 메시지를 생성합니다."""
    provider_label = provider.upper()
    alt_engine = "💡 **대안**: 로컬 AI(Ollama)는 무료이며 인터넷 없이도 사용 가능합니다. 엔진을 '로컬 GPU/CPU (Ollama)'로 전환해보세요."

    if isinstance(e, RateLimitError):
        return (
            f"⚠️ **{provider_label} API 사용량 한도 초과 (429)**\n\n"
            f"현재 API 키의 무료 사용량 또는 요금제 한도를 초과했습니다.\n\n"
            f"**해결 방법:**\n"
            f"1. [Google AI Studio](https://aistudio.google.com/apikey) 또는 해당 API 대시보드에서 사용량을 확인하세요.\n"
            f"2. 무료 티어의 경우 일일/분당 요청 한도가 있습니다. 잠시 후 다시 시도해주세요.\n"
            f"3. 다른 모델을 선택해보세요. (예: `gemini-2.0-flash-lite`는 한도가 더 높습니다)\n\n"
            f"{alt_engine}"
        )
    elif isinstance(e, AuthenticationError):
        return (
            f"⚠️ **{provider_label} API 인증 실패 (401)**\n\n"
            f"API 키가 유효하지 않거나 만료되었습니다.\n\n"
            f"**해결 방법:**\n"
            f"1. `.env` 파일의 API 키 값이 정확한지 확인하세요.\n"
            f"2. API 키를 새로 발급받아 교체해보세요.\n"
            f"3. 키 앞뒤에 공백이나 따옴표가 없는지 확인하세요.\n\n"
            f"{alt_engine}"
        )
    elif isinstance(e, NotFoundError):
        return (
            f"⚠️ **모델을 찾을 수 없거나 접근 권한 없음 (404)**\n\n"
            f"요청한 모델 `{model_name}`을 찾을 수 없거나 API 키 권한에 맞지 않습니다.\n\n"
            f"**해결 방법:**\n"
            f"1. 입력하신 API 키가 유효하며 해당 모델에 대한 접근 권한(무료 한도 등)이 있는지 확인해주세요.\n"
            f"2. 구글 OpenAI 호환 API는 API 키가 잘못되거나 비활성화된 경우에도 404 에러를 반환할 수 있습니다. 키를 다시 확인해주세요.\n"
            f"3. 기본 추천 모델(`gemini-2.0-flash` 또는 `gemini-1.5-flash`)로 시도해보세요."
        )
    elif isinstance(e, BadRequestError):
        return (
            f"⚠️ **잘못된 요청 (400)**\n\n"
            f"API 서버가 요청을 처리할 수 없습니다.\n\n"
            f"에러 상세: `{str(e)[:150]}`\n\n"
            f"**해결 방법:**\n"
            f"1. 입력 내용에 특수문자나 너무 긴 텍스트가 없는지 확인하세요.\n"
            f"2. 다른 모델로 시도해보세요."
        )
    elif isinstance(e, APIConnectionError):
        if provider == "local":
            return (
                f"⚠️ **Ollama 서버 연결 실패**\n\n"
                f"로컬 Ollama 서버에 연결할 수 없습니다.\n\n"
                f"**해결 방법:**\n"
                f"1. Ollama가 PC에서 실행 중인지 확인하세요.\n"
                f"2. 터미널에서 `ollama serve`를 실행해보세요.\n"
                f"3. API 주소가 `http://localhost:11434/v1`인지 확인하세요.\n"
                f"4. 방화벽이 포트 11434를 차단하고 있지 않은지 확인하세요."
            )
        return (
            f"⚠️ **{provider_label} API 서버 연결 실패**\n\n"
            f"API 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.\n\n"
            f"**해결 방법:**\n"
            f"1. 인터넷 연결 상태를 확인하세요.\n"
            f"2. VPN 사용 시 일시적으로 해제해보세요.\n"
            f"3. 잠시 후 다시 시도해주세요.\n\n"
            f"{alt_engine}"
        )
    elif isinstance(e, APITimeoutError):
        return (
            f"⚠️ **요청 시간 초과**\n\n"
            f"AI 서버가 {REQUEST_TIMEOUT}초 내에 응답하지 않았습니다.\n\n"
            f"**해결 방법:**\n"
            f"1. 입력 주제나 키워드를 짧게 줄여보세요.\n"
            f"2. 잠시 후 다시 시도해주세요.\n"
            f"3. 서버가 혼잡할 수 있습니다."
        )
    elif isinstance(e, APIStatusError):
        status_code = getattr(e, 'status_code', 'N/A')
        if status_code == 503:
            return (
                f"⚠️ **{provider_label} 서버 일시 과부하 (503)**\n\n"
                f"API 서버가 일시적으로 과부하 상태입니다.\n\n"
                f"**해결 방법:**\n"
                f"1. 1~2분 후 다시 시도해주세요.\n"
                f"2. 다른 모델을 선택해보세요.\n\n"
                f"{alt_engine}"
            )
        return (
            f"⚠️ **{provider_label} API 에러 ({status_code})**\n\n"
            f"`{str(e)[:150]}`\n\n"
            f"{alt_engine}"
        )
    else:
        if provider == "local":
            return (
                f"⚠️ **로컬 LLM (Ollama) 에러**\n\n"
                f"`{str(e)[:150]}`\n\n"
                f"**해결 방법:**\n"
                f"1. Ollama가 실행 중인지 확인하세요.\n"
                f"2. 터미널에서 `ollama run {model_name}` 명령어로 모델을 먼저 다운로드하세요.\n"
                f"3. Ollama API 주소가 올바른지 확인하세요."
            )
        return (
            f"⚠️ **{provider_label} 에러**\n\n"
            f"`{str(e)[:150]}`\n\n"
            f"{alt_engine}"
        )

def _is_retryable(e: Exception) -> bool:
    """일시적 오류로 재시도 가능한지 판단합니다."""
    if isinstance(e, APIStatusError) and getattr(e, 'status_code', 0) == 503:
        return True
    if isinstance(e, APITimeoutError):
        return True
    return False

# ─── API 상태 ───

@app.get("/api/status")
async def get_status():
    """현재 서버에 설정된 LLM 엔진 상태를 반환"""
    provider, _, model_name = get_llm_client_and_model()
    logger.info(f"엔진 상태 조회: provider={provider}, model={model_name}")
    return {
        "provider": provider,
        "model": model_name
    }

# ─── Ollama 자동 설정 관련 엔드포인트 ───

@app.get("/api/ollama/status")
async def ollama_status():
    """Ollama 실행 상태 확인 및 설치된 모델 목록 반환"""
    ollama_url = "http://localhost:11434"
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                size_bytes = m.get("size", 0)
                size_gb = round(size_bytes / (1024 ** 3), 1)
                models.append({
                    "name": name,
                    "size": f"{size_gb}GB",
                    "modified": m.get("modified_at", "")
                })
            return {
                "running": True,
                "models": models,
                "url": ollama_url
            }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return {
            "running": False,
            "models": [],
            "url": ollama_url
        }

@app.post("/api/ollama/pull")
async def ollama_pull(req: OllamaPullRequest):
    """Ollama 모델 다운로드 (스트리밍 진행률 반환)"""
    def stream_pull():
        try:
            pull_data = json.dumps({"name": req.model, "stream": True}).encode("utf-8")
            http_req = urllib.request.Request(
                f"{req.ollama_url}/api/pull",
                data=pull_data,
                method="POST"
            )
            http_req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(http_req, timeout=600) as resp:
                buffer = b""
                while True:
                    chunk = resp.read(256)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if line.strip():
                            try:
                                progress_data = json.loads(line.decode("utf-8"))
                                status = progress_data.get("status", "")
                                total = progress_data.get("total", 0)
                                completed = progress_data.get("completed", 0)
                                pct = round((completed / total) * 100) if total > 0 else 0
                                yield f"data: {json.dumps({'status': status, 'percent': pct, 'total': total, 'completed': completed})}\n\n"
                            except json.JSONDecodeError:
                                pass

            yield f"data: {json.dumps({'status': 'success', 'percent': 100})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)[:200]})}\n\n"

    return StreamingResponse(stream_pull(), media_type="text/event-stream")

# ─── 프롬프트 빌더 ───

def _build_prompts(req: GenerationRequest):
    """시스템 프롬프트와 사용자 프롬프트를 생성합니다."""
    purpose_guidelines = {
        "instagram": "인스타그램/SNS 피드용 글입니다. 해시태그를 감각적으로 활용하고, 적절한 줄바꿈과 이모지를 사용하여 트렌디하고 가독성 높게 작성하세요.",
        "blog": "블로그 포스팅용 글입니다. 풍부한 정보 전달력과 논리적인 구성을 가지며, 상세하고 친절한 설명조로 긴 글을 작성하세요. 제목과 소제목 구조를 포함하세요.",
        "karrot": "당근마켓 및 지역 커뮤니티용 글입니다. 이웃에게 말하듯 따뜻하고 친근하며 둥글둥글한 말투(~해요, ~랍니다)를 사용하고, 지역 주민의 공감을 유도하세요.",
        "email": "이메일 및 서한용 글입니다. 격식을 갖춘 정중한 비즈니스 톤으로 인사말과 본문, 맺음말을 명확히 구분하여 작성하세요.",
        "sms": "안내 및 전달용 문자메시지(SMS/LMS)입니다. 중요한 정보가 한눈에 들어오도록 간결하고 명확하게 작성하되, 스팸으로 오인되지 않도록 깔끔한 어조를 유지하세요.",
        "general": "일반적인 글쓰기 및 에세이 양식입니다. 지정된 주제와 키워드를 매끄럽게 연결하여 조화롭고 완성도 높은 산문을 완성하세요."
    }

    system_prompt = f"""
당신은 한국 시장에 대한 이해도가 매우 높고 트렌디한 전문 카피라이터이자 글쓰기 전문가입니다.
주어진 주제/분야, 타겟 매체(목적), 톤앤매너, 핵심 키워드를 바탕으로 완성도 높은 한국어 텍스트를 작성하세요.

[제약 조건 및 가이드라인]
1. 번역투가 느껴지는 표현이나 어색한 조사 사용(예: "당신은 ~를 해야 합니다" 등)을 절대 금지하고, 완벽하게 자연스러운 한국어 표현을 사용하세요.
2. 타겟 매체의 특징: {purpose_guidelines.get(req.purpose, '일반적인 양식에 맞춰 문맥에 어울리게 작성하세요.')}
3. 톤앤매너: '{req.tone}' 톤앤매너를 완벽하게 반영하여 일관된 어조로 작성하세요.
4. 필수 포함 키워드: '{req.keywords}'에 입력된 단어들을 자연스럽게 녹여내고, 억지로 끼워 맞춘 느낌이 없도록 흐름을 매끄럽게 만드세요.
5. 결과물은 마크다운(Markdown) 포맷으로 가독성 있게 작성해주세요.
    """

    user_prompt = f"""
- 주제 및 분야: {req.topic}
- 매체/목적: {req.purpose}
- 톤앤매너: {req.tone}
- 필수 포함 키워드: {req.keywords}

위 정보를 바탕으로 최적화된 글을 작성해주세요.
    """
    return system_prompt, user_prompt

# ─── 엔진 클라이언트 결정 ───

def _resolve_engine(req: GenerationRequest):
    """요청에 따라 provider, client, model_name을 결정합니다.
    Returns: (provider, client, model_name, error_msg_or_none)
    """
    if req.engine == "local":
        client = OpenAI(
            api_key="ollama",
            base_url=req.local_url,
            timeout=REQUEST_TIMEOUT,
        )
        return "local", client, req.local_model, None
    elif req.engine == "gemini":
        gemini_key = req.gemini_api_key.strip() if req.gemini_api_key else os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            return "gemini", None, "", "Gemini API Key가 설정되지 않았습니다.\n\n화면의 API 키 입력칸에 키를 입력하거나, 서버의 `.env` 파일에 `GEMINI_API_KEY=your_key` 형식으로 추가해주세요."
        client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=REQUEST_TIMEOUT,
        )
        model = req.model if req.model else "gemini-2.0-flash"
        if not model.startswith("models/"):
            model = f"models/{model}"
        return "gemini", client, model, None
    elif req.engine == "openai":
        openai_key = req.openai_api_key.strip() if req.openai_api_key else os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return "openai", None, "", "OpenAI API Key가 설정되지 않았습니다.\n\n화면의 API 키 입력칸에 키를 입력하거나, 서버의 `.env` 파일에 `OPENAI_API_KEY=your_key` 형식으로 추가해주세요."
        client = OpenAI(api_key=openai_key, timeout=REQUEST_TIMEOUT)
        model = req.model if req.model else "gpt-4o-mini"
        return "openai", client, model, None
    elif req.engine == "custom":
        custom_key = req.custom_api_key.strip() if req.custom_api_key else os.environ.get("CUSTOM_API_KEY")
        custom_url = req.custom_base_url.strip() if req.custom_base_url else os.environ.get("CUSTOM_BASE_URL")
        custom_model = req.custom_model.strip() if req.custom_model else os.environ.get("CUSTOM_MODEL")
        if not custom_key or not custom_url:
            return "custom", None, "", "Custom API Key 또는 Base URL이 설정되지 않았습니다.\n\n화면의 API 키 및 Base URL 입력칸에 입력하거나, 서버의 `.env` 파일에 `CUSTOM_API_KEY=your_key` 및 `CUSTOM_BASE_URL=your_url` 형식으로 추가해주세요."
        client = OpenAI(
            api_key=custom_key,
            base_url=custom_url,
            timeout=REQUEST_TIMEOUT,
        )
        model = custom_model if custom_model else "custom-model"
        return "custom", client, model, None
    else: # auto
        gemini_key = req.gemini_api_key.strip() if req.gemini_api_key else os.environ.get("GEMINI_API_KEY")
        openai_key = req.openai_api_key.strip() if req.openai_api_key else os.environ.get("OPENAI_API_KEY")
        
        if gemini_key:
            client = OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=REQUEST_TIMEOUT,
            )
            model = req.model if req.model else "gemini-2.0-flash"
            if not model.startswith("models/"):
                model = f"models/{model}"
            return "gemini", client, model, None
        elif openai_key:
            client = OpenAI(api_key=openai_key, timeout=REQUEST_TIMEOUT)
            model = req.model if req.model else "gpt-4o-mini"
            return "openai", client, model, None
        else:
            # 환경변수 감지 fallback
            provider, client, detected_model = get_llm_client_and_model()
            model = req.model if req.model else detected_model
            if provider == "gemini" and model and not model.startswith("models/"):
                model = f"models/{model}"
            return provider, client, model, None

# ─── SSE 스트리밍 생성 엔드포인트 ───

@app.post("/api/generate-stream")
async def generate_stream(req: GenerationRequest):
    """SSE 스트리밍으로 AI 텍스트 생성 결과를 실시간 전송"""
    logger.info(f"스트리밍 생성 요청: engine={req.engine}, topic={req.topic[:50]}...")
    provider, client, model_name, setup_error = _resolve_engine(req)

    if setup_error:
        return _sse_error(setup_error)

    if provider == "mock":
        mock_text = get_mock_result(req, "등록된 API 키 없음 (데모 모드)")
        def mock_stream():
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'connecting', 'percent': 10})}\n\n"
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating', 'percent': 50})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': mock_text})}\n\n"
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'formatting', 'percent': 95})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'percent': 100})}\n\n"
        return StreamingResponse(mock_stream(), media_type="text/event-stream")

    system_prompt, user_prompt = _build_prompts(req)

    def event_stream():
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'connecting', 'percent': 5})}\n\n"

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    yield f"data: {json.dumps({'type': 'stage', 'stage': 'retrying', 'percent': 8, 'attempt': attempt + 1})}\n\n"
                    time.sleep(RETRY_DELAY_SEC * attempt)

                stream = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    stream=True,
                )

                yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating', 'percent': 15})}\n\n"

                token_count = 0
                has_content = False
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        token_text = chunk.choices[0].delta.content
                        token_count += 1
                        has_content = True
                        progress = min(15 + int(token_count * 0.3), 90)
                        yield f"data: {json.dumps({'type': 'token', 'content': token_text, 'percent': progress})}\n\n"

                # 빈 응답 처리
                if not has_content:
                    yield f"data: {json.dumps({'type': 'token', 'content': '> ℹ️ AI가 빈 응답을 반환했습니다. 주제나 키워드를 변경하여 다시 시도해주세요.'})}\n\n"

                yield f"data: {json.dumps({'type': 'stage', 'stage': 'formatting', 'percent': 95})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'percent': 100})}\n\n"
                return  # 성공 시 함수 종료

            except Exception as e:
                last_error = e
                if _is_retryable(e) and attempt < MAX_RETRIES:
                    continue  # 재시도
                break  # 재시도 불가 → 에러 보고

        # 모든 시도 실패
        error_msg = _format_api_error(last_error, provider, model_name)
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

def _sse_error(message: str):
    """SSE 형식의 에러 응답을 반환"""
    def error_stream():
        yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"
    return StreamingResponse(error_stream(), media_type="text/event-stream")

# ─── 기존 비-스트리밍 엔드포인트 (호환성 유지) ───

@app.post("/api/generate")
async def generate_text(req: GenerationRequest):
    provider, client, model_name, setup_error = _resolve_engine(req)

    if setup_error:
        return {"success": True, "result": f"> ⚠️ {setup_error}"}

    if provider == "mock":
        return {"success": True, "result": get_mock_result(req, "등록된 API 키 없음 (데모 모드)")}

    system_prompt, user_prompt = _build_prompts(req)

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                time.sleep(RETRY_DELAY_SEC * attempt)

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            result_text = response.choices[0].message.content
            if not result_text or not result_text.strip():
                result_text = "> ℹ️ AI가 빈 응답을 반환했습니다. 주제나 키워드를 변경하여 다시 시도해주세요."
            return {"success": True, "result": result_text}

        except Exception as e:
            last_error = e
            if _is_retryable(e) and attempt < MAX_RETRIES:
                continue
            break

    error_msg = _format_api_error(last_error, provider, model_name)
    return {"success": True, "result": error_msg}

def get_mock_result(req: GenerationRequest, error_info: str):
    return f"""
> ⚠️ **API 연결 및 데모 안내**: 현재 실제 API 통신 중 에러가 발생했거나 API 키가 설정되지 않아 **샘플(Mock) 데이터**를 출력합니다.
> (진단 정보: `{error_info}`)

---

### ✨ {req.topic} 맞춤형 카피 (샘플)

요청해주신 **\"{req.keywords}\"** 키워드를 바탕으로 작성된 샘플 글입니다.

* **매체/목적**: {req.purpose}
* **원하는 톤**: {req.tone}

**[본문 예시]**
이것은 API 연결에 실패했거나 키가 없을 때 동작하는 로컬 대체 샘플입니다. 실제 환경 변수에 유효한 API 키(`GEMINI_API_KEY`, `OPENAI_API_KEY` 또는 `CUSTOM_API_KEY` + `CUSTOM_BASE_URL`)를 등록하면 실시간 AI 작성이 이루어집니다.
항상 {req.tone} 느낌으로, '{req.keywords}'의 가치와 장점을 직관적으로 전달해 드립니다.

앞으로도 많은 관심 부탁드립니다! 😊
"""

if __name__ == "__main__":
    logger.info("🚀 AI 카피라이터 서버를 시작합니다...")
    logger.info("📌 http://127.0.0.1:8000 에서 접속 가능합니다.")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
