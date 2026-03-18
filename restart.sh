#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔄 재시작 중..."
"$SCRIPT_DIR/stop.sh"
echo ""
"$SCRIPT_DIR/run.sh"
