"""pipeline.yaml 로더 — 설정 파일을 읽어서 Executor를 구성"""

import yaml
from pathlib import Path
from core.executor import create_executor, BaseExecutor


class PipelineConfig:
    """pipeline.yaml을 로드하고 노드별 Executor를 제공"""

    def __init__(self, config_path: str):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"설정 파일 없음: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            self._raw = yaml.safe_load(f)

        self.project = self._raw.get("project", {})
        self.nodes = self._raw.get("nodes", {})
        self.cycles = self._raw.get("cycles", {})
        self.human_checkpoints = self._raw.get("human_checkpoints", [])
        self.config_dir = str(path.parent)

    @property
    def project_name(self) -> str:
        return self.project.get("name", "unknown")

    @property
    def project_path(self) -> str:
        return self.project.get("path", "")

    @property
    def build_command(self) -> str:
        return self.project.get("build_command", "")

    @property
    def test_command(self) -> str:
        return self.project.get("test_command", "")

    def get_executor(self, node_name: str) -> BaseExecutor:
        """노드 이름에 해당하는 Executor 인스턴스를 반환"""
        node_config = self.nodes.get(node_name)
        if not node_config:
            raise ValueError(f"노드 설정 없음: {node_name}")

        executor_type = node_config.get("executor", "api")
        kwargs = {}

        if executor_type == "api":
            kwargs["model"] = node_config.get("model")

        return create_executor(executor_type, **kwargs)

    def get_prompt_template(self, node_name: str) -> str:
        """노드의 프롬프트 템플릿 내용을 반환"""
        node_config = self.nodes.get(node_name, {})
        template_path = node_config.get("prompt_template", "")

        if not template_path:
            return ""

        full_path = Path(self.config_dir) / template_path
        if not full_path.exists():
            return ""

        return full_path.read_text(encoding="utf-8")

    def get_max_retries(self, cycle_name: str) -> int:
        """순환의 최대 재시도 횟수"""
        return self.cycles.get(cycle_name, {}).get("max_retries", 3)

    def is_checkpoint(self, node_name: str) -> bool:
        """해당 노드 이후가 Human-in-the-Loop 체크포인트인지"""
        return any(cp.get("after") == node_name for cp in self.human_checkpoints)

    def get_node_command(self, node_name: str) -> str:
        """노드의 command 설정을 반환 (tool executor용)"""
        return self.nodes.get(node_name, {}).get("command", "")

    def to_dict(self) -> dict:
        return self._raw
