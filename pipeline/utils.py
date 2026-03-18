"""파이프라인 공통 유틸리티"""

import re
import threading

from core.config_loader import PipelineConfig


# ──────────────────────────────────────────
# 실시간 로그 콜백 (bootstrap/graph.py 패턴 동일)
# ──────────────────────────────────────────

_log_callback = None
_log_lock = threading.Lock()


def set_log_callback(callback):
    """실시간 로그 콜백 설정 (Streamlit UI 연동용)"""
    global _log_callback
    _log_callback = callback


def _emit_log(message: str):
    """로그 메시지 발행"""
    if _log_callback:
        with _log_lock:
            _log_callback(message)
    # 파일 로그 기록
    from core.file_logger import get_file_logger
    fl = get_file_logger()
    if fl:
        fl.log(message)


# ──────────────────────────────────────────
# 프롬프트 렌더링
# ──────────────────────────────────────────

def render_prompt(template: str, variables: dict) -> str:
    """프롬프트 템플릿에서 {variable_name} 치환"""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value or ""))
    return result


# ──────────────────────────────────────────
# 코드 파싱
# ──────────────────────────────────────────

def parse_code_output(output: str) -> dict:
    """LLM/Console 출력에서 파일 경로와 코드를 추출

    지원 형식:
    1) === FILE: path/to/file.java ===
       ...code...
    2) ```lang:path/to/file.java
       ...code...
       ```
    3) ```lang
       // path/to/file.java
       ...code...
       ```
    """
    files = {}

    # 형식 1: === FILE: path ===
    pattern1 = re.compile(r'^=== FILE:\s*(.+?)\s*===\s*$', re.MULTILINE)
    parts = pattern1.split(output)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            filepath = parts[i].strip()
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if filepath:
                files[filepath] = content
        return files

    # 형식 2: ```lang:path
    pattern2 = re.compile(
        r'```\w*:([^\n]+)\n(.*?)```',
        re.DOTALL,
    )
    for match in pattern2.finditer(output):
        filepath = match.group(1).strip()
        content = match.group(2).strip()
        if filepath:
            files[filepath] = content
    if files:
        return files

    # 형식 3: 마크다운 코드 블록에서 파일 경로 주석 추출
    pattern3 = re.compile(
        r'```\w*\n\s*(?://|#|--)\s*(\S+\.\w+)\n(.*?)```',
        re.DOTALL,
    )
    for match in pattern3.finditer(output):
        filepath = match.group(1).strip()
        content = match.group(2).strip()
        if filepath:
            files[filepath] = content

    return files


def format_source_code(code_dict: dict) -> str:
    """코드 딕셔너리를 프롬프트용 문자열로 변환"""
    if not code_dict:
        return "(코드 없음)"

    parts = []
    for filepath, content in code_dict.items():
        parts.append(f"=== FILE: {filepath} ===\n{content}")
    return "\n\n".join(parts)
