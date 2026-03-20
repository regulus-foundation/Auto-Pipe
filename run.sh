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

# Docker 필수
if ! command -v docker &> /dev/null || ! docker info &> /dev/null 2>&1; then
    echo ""
    echo "❌ Docker가 실행되고 있지 않습니다."
    echo "   Docker Desktop을 시작한 후 다시 실행하세요."
    echo ""
    exit 1
fi

echo ""
echo "🐳 Docker 서비스 시작 중 (PostgreSQL + Langfuse)..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --quiet-pull 2>/dev/null

if [ $? -ne 0 ]; then
    echo "   ❌ Docker Compose 시작 실패."
    exit 1
fi

echo "   ⏳ PostgreSQL 준비 대기 중..."
RETRIES=0
MAX_RETRIES=30
until docker compose -f "$SCRIPT_DIR/docker-compose.yml" exec -T langfuse-postgres pg_isready -U langfuse -q 2>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo "   ❌ PostgreSQL 시작 타임아웃."
        exit 1
    fi
    sleep 1
done

echo "   ✅ PostgreSQL 준비 완료"
export AUTOPIPE_DATABASE_URL="${AUTOPIPE_DATABASE_URL:-postgresql://langfuse:langfuse@localhost:5432/autopipe}"
echo "   Langfuse UI: http://localhost:3000"

if [ -z "$LANGFUSE_SECRET_KEY" ] || [ -z "$LANGFUSE_PUBLIC_KEY" ]; then
    echo ""
    echo "   📋 Langfuse 연동: http://localhost:3000 → API Keys 발급 → .env에 추가"
fi

# Frontend 의존성 확인
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo ""
    echo "📦 Frontend 의존성 설치 중..."
    (cd "$SCRIPT_DIR/frontend" && npm install)
fi

echo ""
echo "🚀 Auto-Pipe 시작"
echo "   Backend API: http://localhost:8502"
echo "   Frontend UI: http://localhost:3100"
echo ""

# 로그 디렉토리
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# 이전 로그 초기화
> "$BACKEND_LOG"
> "$FRONTEND_LOG"

# Backend + Frontend 동시 실행 (tee로 터미널 + 파일 동시 출력)
uvicorn web.app:app --host 0.0.0.0 --port 8502 --reload 2>&1 | tee -a "$BACKEND_LOG" &
BACKEND_PID=$!

(cd "$SCRIPT_DIR/frontend" && npx next dev --port 3100) 2>&1 | tee -a "$FRONTEND_LOG" &
FRONTEND_PID=$!

echo "   Logs: $LOG_DIR/"

# 종료 시 둘 다 종료
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
