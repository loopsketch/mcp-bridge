# llama_mcp.py
import os

from mcp.server.fastmcp import FastMCP
import requests

FASTMCP_HOST = os.getenv("FASTMCP_HOST", "0.0.0.0")
FASTMCP_PORT = int(os.getenv("FASTMCP_PORT", "8000"))

mcp = FastMCP("LocalAgentHelper", host=FASTMCP_HOST, port=FASTMCP_PORT)

LLAMA_CPP_SERVER_URL = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:8080/v1/chat/completions")
LLAMA_CPP_SERVER_MODEL = os.getenv("LLAMA_CPP_SERVER_MODEL", "")
LLAMA_CPP_SERVER_TIMEOUT = int(os.getenv("LLAMA_CPP_SERVER_TIMEOUT", "90"))
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")


def _query_llama(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    payload = {
        "messages": messages,
        "temperature": temperature,
    }
    if LLAMA_CPP_SERVER_MODEL:
        payload["model"] = LLAMA_CPP_SERVER_MODEL

    try:
        response = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=LLAMA_CPP_SERVER_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.RequestException as exc:
        return f"Llama API request failed: {exc}"
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return f"Unexpected Llama API response format: {exc}"


@mcp.tool()
def local_coding_assist(question: str, code_context: str = "") -> str:
    """ローカルのLlamaモデルを使って、実装方針やコード改善を含むコーディング支援を行います。"""
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

if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)