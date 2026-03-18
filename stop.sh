#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Streamlit 종료 (8502 포트)
PID=$(lsof -ti :8502 2>/dev/null)
if [ -n "$PID" ]; then
    echo "🛑 Streamlit 중지 중... (PID: $PID)"
    kill $PID 2>/dev/null
else
    echo "ℹ️  Streamlit이 실행 중이지 않습니다."
fi

# Langfuse 종료
echo "🛑 Langfuse 중지 중..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" down 2>/dev/null

echo "✅ 완료"
