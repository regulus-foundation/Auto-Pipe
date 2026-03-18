"""파이프라인 실행 로그를 파일로 저장

로그 경로:
  projects/{name}/log/bootstrap-{YYYYMMDD_HHmmss}.log
  projects/{name}/log/pipeline-{YYYYMMDD_HHmmss}.log
"""

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent


class FileLogger:
    """파이프라인 실행 로그를 파일에 기록"""

    def __init__(self, project_name: str, pipeline_type: str):
        """
        Args:
            project_name: 프로젝트 이름 (projects/{name}/ 하위에 저장)
            pipeline_type: "bootstrap" 또는 "pipeline"
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = _ROOT / "projects" / project_name / "log"
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_path = log_dir / f"{pipeline_type}-{timestamp}.log"
        self._lock = threading.Lock()

        # 헤더 기록
        self._write(f"[{pipeline_type.upper()}] {project_name}")
        self._write(f"Started: {datetime.now().isoformat()}")
        self._write("=" * 60)

    def _write(self, message: str):
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")

    def log(self, message: str):
        """타임스탬프 포함 로그 한 줄 기록"""
        ts = datetime.now().strftime("%H:%M:%S")
        self._write(f"[{ts}] {message}")

    def close(self, success: bool = True):
        """로그 마무리"""
        self._write("=" * 60)
        status = "SUCCESS" if success else "FAILED"
        self._write(f"Finished: {datetime.now().isoformat()} [{status}]")

    def get_path(self) -> str:
        return str(self.log_path)


# ──────────────────────────────────────────
# 글로벌 인스턴스 관리 (콜백에서 접근용)
# ──────────────────────────────────────────

_current_logger: Optional[FileLogger] = None
_logger_lock = threading.Lock()


def start_file_logger(project_name: str, pipeline_type: str) -> FileLogger:
    """파일 로거 시작 — 파이프라인 실행 전에 호출"""
    global _current_logger
    with _logger_lock:
        _current_logger = FileLogger(project_name, pipeline_type)
    return _current_logger


def stop_file_logger(success: bool = True):
    """파일 로거 종료 — 파이프라인 완료 후 호출"""
    global _current_logger
    with _logger_lock:
        if _current_logger:
            _current_logger.close(success)
            _current_logger = None


def get_file_logger() -> Optional[FileLogger]:
    """현재 활성 파일 로거 반환"""
    return _current_logger
