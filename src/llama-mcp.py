# llama_mcp.py
import logging
import os
import secrets
import sys

import requests
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("llama-mcp")


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int | None = None) -> int:
    """環境変数を整数として読み出し、不正値はプロセスを止める"""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.error("Environment variable %s must be an integer (got %r)", name, raw)
        sys.exit(2)
    if value < min_value or (max_value is not None and value > max_value):
        logger.error("Environment variable %s out of range: %d", name, value)
        sys.exit(2)
    return value


FASTMCP_HOST = os.getenv("FASTMCP_HOST", "0.0.0.0")
FASTMCP_PORT = _env_int("FASTMCP_PORT", 8000, min_value=1, max_value=65535)

LLAMA_CPP_SERVER_URL = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:8080/v1/chat/completions")
LLAMA_CPP_SERVER_MODEL = os.getenv("LLAMA_CPP_SERVER_MODEL", "")
LLAMA_CPP_SERVER_TIMEOUT = _env_int("LLAMA_CPP_SERVER_TIMEOUT", 90, min_value=1, max_value=86400)
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")

# 厳しめ既定: 入力(question + code_context)の合計文字数上限
MAX_INPUT_CHARS = _env_int("MAX_INPUT_CHARS", 200_000, min_value=100)

MCP_API_TOKEN = os.getenv("MCP_API_TOKEN", "").strip()
if not MCP_API_TOKEN:
    logger.error("MCP_API_TOKEN is required. Set a strong random token in the environment.")
    sys.exit(2)
if len(MCP_API_TOKEN) < 32:
    logger.error("MCP_API_TOKEN is too short (need >= 32 chars).")
    sys.exit(2)


mcp = FastMCP("LocalAgentHelper", host=FASTMCP_HOST, port=FASTMCP_PORT)


def _query_llama(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    """llama.cpp の chat/completions を呼び出す"""
    payload: dict = {"messages": messages, "temperature": temperature}
    if LLAMA_CPP_SERVER_MODEL:
        payload["model"] = LLAMA_CPP_SERVER_MODEL

    try:
        response = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=LLAMA_CPP_SERVER_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.RequestException:
        logger.exception("Llama API request failed")
        return "Llama API request failed (see server logs)."
    except (KeyError, IndexError, TypeError, ValueError):
        logger.exception("Unexpected Llama API response format")
        return "Llama API returned an unexpected response (see server logs)."


@mcp.tool()
def local_coding_assist(question: str, code_context: str = "") -> str:
    """ローカルのLlamaモデルを使って、実装方針やコード改善を含むコーディング支援を行います。"""
    total = len(question) + len(code_context)
    if total > MAX_INPUT_CHARS:
        return f"Input too large: {total} chars exceeds limit ({MAX_INPUT_CHARS})."

    user_content = (
        f"質問:\n{question}\n\n"
        f"関連コード:\n{code_context}\n\n"
        "必要なら改善コードを提示し、理由も簡潔に説明してください。"
    )
    messages = [
        {
            "role": "system",
            "content": (
                "あなたは実務経験豊富なソフトウェアエンジニアです。"
                "ユーザーの開発タスクを支援し、実装しやすい具体的な提案を返してください。"
            ),
        },
        {"role": "user", "content": user_content},
    ]
    return _query_llama(messages, temperature=0.2)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Authorization: Bearer <token> を要求する簡易認証"""

    async def dispatch(self, request, call_next):
        auth = request.headers.get("authorization", "")
        prefix = "Bearer "
        if not auth.startswith(prefix) or not secrets.compare_digest(auth[len(prefix):], MCP_API_TOKEN):
            client = request.client.host if request.client else "?"
            logger.warning("Unauthorized request from %s %s %s", client, request.method, request.url.path)
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def main() -> None:
    if MCP_TRANSPORT != "streamable-http":
        logger.error("Only streamable-http transport is supported in this build (got %s).", MCP_TRANSPORT)
        sys.exit(2)

    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware)
    logger.info("Starting MCP server on %s:%d", FASTMCP_HOST, FASTMCP_PORT)
    uvicorn.run(app, host=FASTMCP_HOST, port=FASTMCP_PORT, log_level="info", access_log=True)


if __name__ == "__main__":
    main()
