"""Langfuse 콜백 핸들러 중앙 관리

Langfuse가 설정되어 있으면 콜백 핸들러를 반환하고,
설정되지 않았으면 None을 반환하여 기존 코드에 영향 없음.

사용법:
    from core.langfuse_callback import get_langfuse_handler

    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}
    graph.stream(state, config)
"""

import os
import logging

# Langfuse/OpenTelemetry context 전파 시 발생하는 무해한 에러 억제
logging.getLogger("langfuse").setLevel(logging.ERROR)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)

_handler = None
_initialized = False


def get_langfuse_handler():
    """Langfuse CallbackHandler를 반환. 미설정 시 None."""
    global _handler, _initialized

    if _initialized:
        return _handler

    _initialized = True

    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not secret_key or not public_key:
        return None

    try:
        from langfuse.langchain import CallbackHandler
        # v4: 환경변수(LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST)에서 자동 읽음
        _handler = CallbackHandler()
        return _handler
    except ImportError:
        print("[langfuse] langfuse 패키지가 설치되지 않았습니다. pip install langfuse")
        return None
    except Exception as e:
        print(f"[langfuse] 초기화 실패: {e}")
        return None


def reset():
    """테스트용: 초기화 상태 리셋."""
    global _handler, _initialized
    _handler = None
    _initialized = False
