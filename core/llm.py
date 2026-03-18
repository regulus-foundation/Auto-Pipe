"""LLM 인스턴스 중앙 관리

모든 모듈에서 get_llm()으로 LLM 인스턴스를 가져옴.
중복된 lazy init 패턴을 제거하고 설정을 한 곳에서 관리.

사용법:
    from core.llm import get_llm, get_llm_with_tools

    llm = get_llm()                        # 기본 모델
    llm = get_llm(model="gpt-4o")          # 모델 지정
    llm = get_llm_with_tools(tools)        # 도구 바인딩
"""

import os
from functools import lru_cache

_instances = {}


def get_llm(model: str = None, temperature: float = 0.7):
    """LLM 인스턴스를 반환. 같은 (model, temperature) 조합은 캐싱."""
    from langchain_openai import ChatOpenAI

    model = model or os.getenv("AUTO_PIPE_MODEL", "gpt-4o-mini")
    key = (model, temperature)

    if key not in _instances:
        _instances[key] = ChatOpenAI(model=model, temperature=temperature)

    return _instances[key]


def get_llm_with_tools(tools: list, model: str = None, temperature: float = 0.7):
    """도구가 바인딩된 LLM 인스턴스를 반환."""
    llm = get_llm(model=model, temperature=temperature)
    return llm.bind_tools(tools)


def reset():
    """테스트용: 캐시된 인스턴스 초기화."""
    _instances.clear()
