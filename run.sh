#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# .env 파일 로드
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# 가상환경 확인/생성
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# API 키 확인
if [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "⚠️  OPENAI_API_KEY가 설정되지 않았습니다."
    echo "  export OPENAI_API_KEY=your-key-here"
    echo ""
    exit 1
fi

# Langfuse (Docker Compose) 시작
if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
    echo ""
    echo "🔍 Langfuse 시작 중..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --quiet-pull 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "   Langfuse UI: http://localhost:3000"

        # Langfuse 키가 없으면 안내
        if [ -z "$LANGFUSE_SECRET_KEY" ] || [ -z "$LANGFUSE_PUBLIC_KEY" ]; then
            echo ""
            echo "📋 Langfuse 연동 방법:"
            echo "   1. http://localhost:3000 에서 계정 생성"
            echo "   2. Settings → API Keys 에서 키 발급"
            echo "   3. 환경변수 설정:"
            echo "      export LANGFUSE_SECRET_KEY=sk-lf-..."
            echo "      export LANGFUSE_PUBLIC_KEY=pk-lf-..."
            echo "      export LANGFUSE_HOST=http://localhost:3000"
            echo ""
        fi
    else
        echo "   ⚠️  Langfuse 시작 실패 (Docker 문제). Streamlit만 실행합니다."
    fi
else
    echo ""
    echo "ℹ️  Docker가 없어 Langfuse를 건너뜁니다. Streamlit만 실행합니다."
fi

echo ""
echo "🚀 LangGraph 학습 UI 시작"
echo "   http://localhost:8502"
echo ""

streamlit run web/app.py --server.port 8502 --server.headless true
