# mcp-bridge

Docker で MCP サーバを起動し、内部で llama.cpp の OpenAI 互換 API を呼び出す構成です。

## 起動

```bash
docker compose up -d --build
```

## 停止

```bash
docker compose down
```

## 接続先

- MCP エンドポイント: `http://localhost:8000/mcp`
- トランスポート: `streamable-http`

## 接続確認

406 が返る場合でも、到達確認としては正常です。
MCP エンドポイントは Accept ヘッダー前提のためです。

```bash
curl -i http://localhost:8000/mcp
```

## Claude Code 設定

Claude Code の MCP は `~/.claude.json` で管理されます。

ローカルスコープ（特定プロジェクトのみ）で手動設定する場合は、
`client-config.example.json` の形式を `~/.claude.json` に反映してください。

### 推奨: CLI で追加

```bash
claude mcp add --transport http local-agent-helper http://localhost:8000/mcp
```

### 設定確認

```bash
claude mcp list
claude mcp get local-agent-helper
```

### 補足

- `--scope user` を付けると全プロジェクトで利用可能です。
- `--scope project` を使うと、プロジェクト直下の `.mcp.json` に保存されます。

## 環境変数

`.env.example` を `.env` にコピーして利用できます。

- `MCP_TRANSPORT` (既定: `streamable-http`)
- `FASTMCP_HOST` (既定: `0.0.0.0`)
- `FASTMCP_PORT` (既定: `8000`)
- `LLAMA_CPP_SERVER_URL`
- `LLAMA_CPP_SERVER_MODEL`
- `LLAMA_CPP_SERVER_TIMEOUT`
