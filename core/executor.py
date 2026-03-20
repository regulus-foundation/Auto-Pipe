"""Executor — LLM/도구 실행을 추상화하는 계층

3종류의 Executor:
  - api:     OpenAI/Claude API 직접 호출 (종량제, 경량 작업용)
  - console: Claude Code CLI 호출 (구독제, 대량 코드 생성용)
  - tool:    로컬 명령어 실행 (무료, 빌드/테스트용)

사용법:
    executor = create_executor("api", model="gpt-4o-mini")
    result = executor.run("이 코드를 리뷰해줘", context={"code": "..."})

    executor = create_executor("tool")
    result = executor.run("./gradlew build")

    executor = create_executor("console")
    result = executor.run("이 프로젝트를 분석해줘", project_path="/path/to/project")
"""

import os
import signal
import subprocess
import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutorResult:
    """Executor 실행 결과"""

    def __init__(self, success: bool, output: str, executor_type: str,
                 duration_sec: float = 0, tokens_used: int = 0, error: str = ""):
        self.success = success
        self.output = output
        self.executor_type = executor_type
        self.duration_sec = duration_sec
        self.tokens_used = tokens_used
        self.error = error
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "executor_type": self.executor_type,
            "duration_sec": self.duration_sec,
            "tokens_used": self.tokens_used,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class BaseExecutor(ABC):
    """Executor 기본 인터페이스"""

    def __init__(self, executor_type: str, **kwargs):
        self.executor_type = executor_type
        self.config = kwargs

    @abstractmethod
    def run(self, prompt_or_command: str, **kwargs) -> ExecutorResult:
        """프롬프트 또는 명령어를 실행하고 결과를 반환"""
        pass


class ApiExecutor(BaseExecutor):
    """API Executor — OpenAI/Claude API 직접 호출

    용도: 경량 분석/생성 (설계, 리뷰, 문서)
    비용: 토큰 종량제
    """

    def __init__(self, model: str = None, temperature: float = 0.7, **kwargs):
        super().__init__("api", **kwargs)
        self.model = model or os.getenv("AUTO_PIPE_MODEL", "gpt-4o-mini")
        self.temperature = temperature

    def run(self, prompt: str, **kwargs) -> ExecutorResult:
        from core.llm import get_llm

        start = datetime.now()
        try:
            llm = get_llm(model=self.model, temperature=self.temperature)

            # context가 있으면 프롬프트에 삽입
            context = kwargs.get("context", {})
            final_prompt = prompt
            for key, value in context.items():
                final_prompt = final_prompt.replace(f"{{{{{key}}}}}", str(value))

            response = llm.invoke(final_prompt)
            duration = (datetime.now() - start).total_seconds()

            # 토큰 사용량 추정 (response_metadata에서)
            tokens = 0
            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("token_usage", {})
                tokens = usage.get("total_tokens", 0)

            logger.info(f"[API] model={self.model} tokens={tokens} duration={duration:.1f}s")

            return ExecutorResult(
                success=True,
                output=response.content,
                executor_type="api",
                duration_sec=duration,
                tokens_used=tokens,
            )
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.error(f"[API] error: {e}")
            return ExecutorResult(
                success=False,
                output="",
                executor_type="api",
                duration_sec=duration,
                error=str(e),
            )


class ConsoleExecutor(BaseExecutor):
    """Console Executor — Claude Code CLI 호출

    용도: 대량 코드 생성/분석 (구독 범위 내 무제한)
    비용: 구독 고정비 (토큰 종량 아님)

    구현 방식:
      claude CLI를 subprocess로 호출하여 프롬프트를 전달하고 결과를 받음.
      Claude Code CLI가 설치되어 있어야 함 (claude --version).

    Fallback:
      CLI가 없으면 ApiExecutor로 대체 (경고 로그 출력).
    """

    def __init__(self, **kwargs):
        super().__init__("console", **kwargs)
        self._cli_available = self._check_cli()

    def _check_cli(self) -> bool:
        """Claude CLI 설치 여부 확인"""
        try:
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
                env=env,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run(self, prompt: str, **kwargs) -> ExecutorResult:
        """Claude CLI 실행

        Args:
            prompt: 프롬프트
            project_path: 실행 디렉토리
            on_output: 실시간 출력 콜백 (line: str) → None
        """
        project_path = kwargs.get("project_path", os.getcwd())
        on_output = kwargs.get("on_output", None)

        if not self._cli_available:
            logger.warning("[Console] Claude CLI 미설치 → API fallback")
            fallback = ApiExecutor(model="gpt-4o")
            result = fallback.run(prompt, **kwargs)
            result.executor_type = "console(fallback→api)"
            return result

        start = datetime.now()
        try:
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)

            # Popen으로 실시간 스트리밍 (stdin으로 프롬프트 전달 — ARG_MAX 초과 방지)
            # --dangerously-skip-permissions: 파일 수정/명령 실행 등 모든 권한 자동 승인
            process = subprocess.Popen(
                ["claude", "--print", "--dangerously-skip-permissions", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_path,
                env=env,
            )

            # 프롬프트를 stdin으로 전달 후 닫기
            process.stdin.write(prompt)
            process.stdin.close()

            output_lines = []
            for line in process.stdout:
                output_lines.append(line)
                if on_output:
                    on_output(line.rstrip("\n"))

            process.wait(timeout=600)
            duration = (datetime.now() - start).total_seconds()
            full_output = "".join(output_lines)
            stderr = process.stderr.read() if process.stderr else ""

            if process.returncode == 0:
                logger.info(f"[Console] duration={duration:.1f}s")
                return ExecutorResult(
                    success=True,
                    output=full_output,
                    executor_type="console",
                    duration_sec=duration,
                )
            else:
                logger.error(f"[Console] exit={process.returncode}: {stderr}")
                return ExecutorResult(
                    success=False,
                    output=full_output,
                    executor_type="console",
                    duration_sec=duration,
                    error=stderr,
                )
        except subprocess.TimeoutExpired:
            process.kill()
            duration = (datetime.now() - start).total_seconds()
            return ExecutorResult(
                success=False, output="", executor_type="console",
                duration_sec=duration, error="타임아웃 (10분 초과)",
            )
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            return ExecutorResult(
                success=False, output="", executor_type="console",
                duration_sec=duration, error=str(e),
            )


class ToolExecutor(BaseExecutor):
    """Tool Executor — 로컬 명령어 실행

    용도: 빌드, 테스트, 파일 조작
    비용: 무료 (로컬 실행)
    """

    def __init__(self, **kwargs):
        super().__init__("tool", **kwargs)

    def run(self, command: str, **kwargs) -> ExecutorResult:
        cwd = kwargs.get("cwd", os.getcwd())
        timeout = kwargs.get("timeout", 300)  # 5분 기본

        start = datetime.now()
        try:
            # 프로세스 그룹으로 실행 — 타임아웃 시 자식 프로세스까지 확실히 종료
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                preexec_fn=os.setsid,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # 프로세스 그룹 전체를 SIGKILL (Gradle 데몬 등 자식까지)
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
                duration = (datetime.now() - start).total_seconds()
                logger.warning(f"[Tool] cmd='{command[:50]}' 타임아웃 ({timeout}초)")
                return ExecutorResult(
                    success=False, output="", executor_type="tool",
                    duration_sec=duration, error=f"타임아웃 ({timeout}초 초과)",
                )

            duration = (datetime.now() - start).total_seconds()

            success = process.returncode == 0
            output = stdout
            if stderr:
                output += f"\n--- stderr ---\n{stderr}"

            logger.info(f"[Tool] cmd='{command[:50]}' exit={process.returncode} duration={duration:.1f}s")

            return ExecutorResult(
                success=success,
                output=output,
                executor_type="tool",
                duration_sec=duration,
                error="" if success else f"exit code {process.returncode}",
            )
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            return ExecutorResult(
                success=False, output="", executor_type="tool",
                duration_sec=duration, error=str(e),
            )


def create_executor(executor_type: str, **kwargs) -> BaseExecutor:
    """Executor 팩토리

    Args:
        executor_type: "api" | "console" | "tool"
        **kwargs: executor별 추가 설정

    Returns:
        해당 타입의 Executor 인스턴스
    """
    executors = {
        "api": ApiExecutor,
        "console": ConsoleExecutor,
        "tool": ToolExecutor,
    }

    cls = executors.get(executor_type)
    if not cls:
        raise ValueError(f"알 수 없는 executor 타입: {executor_type}. "
                         f"가능한 값: {list(executors.keys())}")

    return cls(**kwargs)
