"""Bootstrap LangGraph 파이프라인

흐름:
  scan_files (tool)              → 파일 기반 빠른 스캔
  analyze_deps (console)         → Step 1: 의존성 & 빌드
  analyze_arch (console)         → Step 2: 아키텍처 & 코드 패턴
  analyze_tests (console)        → Step 3: 테스트 전략
  analyze_summary (console)      → Step 4: 종합 평가
  [Human Review]                 → 분석 결과 확인 (interrupt_before)
  generate_config (api)          → 경량 설정 생성 + 파일 저장
  done                           → 완료

Executor 배분:
  - console: Deep Analysis (대량 소스 읽기, 구독 무제한)
  - api: 설정 생성 (가벼움, 종량)
  - tool: 파일 스캔/기록 (로컬, 무료)
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from core.checkpointer import get_checkpointer
import operator
import threading


# ──────────────────────────────────────────
# 실시간 로그 콜백
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
# State
# ──────────────────────────────────────────

class BootstrapState(TypedDict):
    project_path: str                           # 프로젝트 루트 경로

    # Phase 1: 파일 스캔 결과
    scan_result: dict                           # analyzer.py Phase 1 결과

    # Phase 2: Deep Analysis (console)
    collected_files: dict                       # 카테고리별 수집된 파일
    deep_analysis: dict                         # 4단계 LLM 분석 결과

    # Human Review
    analysis_approved: bool                     # 사람 승인 여부

    # Phase 3: 설정 생성
    gen_result: dict                            # 생성된 설정 파일 정보

    # 메타
    steps: Annotated[list[str], operator.add]   # 진행 로그
    current_step: str                           # 현재 단계 (UI 표시용)
    progress: int                               # 진행률 (0~100)
    errors: list[str]


# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────

def _get_project_summary(scan: dict) -> str:
    """scan_result에서 프로젝트 요약 텍스트 생성"""
    project = scan.get("project", {})
    languages = scan.get("languages", {})
    frameworks = scan.get("frameworks", [])
    structure = scan.get("structure", {})
    fw_names = ", ".join(fw["name"] for fw in frameworks) if frameworks else "unknown"

    return f"""프로젝트: {project.get("name", "unknown")}
언어: {languages.get("primary", "unknown")} (소스 {structure.get("source_files", 0)}개, 테스트 {structure.get("test_files", 0)}개, {structure.get("lines_of_code", 0):,}줄)
프레임워크: {fw_names}
빌드: {scan.get("build", {}).get("tool", "unknown")}"""


# ──────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────

def scan_files_node(state: BootstrapState) -> dict:
    """Phase 1: 파일 기반 빠른 스캔 (tool — 로컬 실행)"""
    from core.analyzer import (
        _scan_structure, _detect_frameworks, _detect_build,
        _analyze_tests, _detect_infra, _detect_conventions,
        _collect_all_files,
    )
    from pathlib import Path

    root = Path(state["project_path"]).resolve()

    structure = _scan_structure(root)
    lang_stats = structure.pop("_lang_stats", {})
    primary_lang_stats = structure.pop("_primary_lang_stats", {})
    languages = {}
    if lang_stats:
        sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)
        # primary는 프로그래밍 언어만으로 판별 (마크업/설정 제외)
        sorted_primary = sorted(primary_lang_stats.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_primary[0][0] if sorted_primary else sorted_langs[0][0]
        languages = {
            "primary": primary,
            "breakdown": {lang: count for lang, count in sorted_langs if count > 0},
        }

    frameworks = _detect_frameworks(root)
    build = _detect_build(root)

    # 프레임워크 감지 결과로 primary 언어 보정
    if frameworks:
        fw_lang = frameworks[0].get("language", "")
        if fw_lang and fw_lang != languages.get("primary", ""):
            languages["primary"] = fw_lang
            languages["primary_source"] = "framework_detection"

    primary_lang = languages.get("primary", "")
    testing = _analyze_tests(root, primary_lang, structure)
    infra = _detect_infra(root)
    conventions = _detect_conventions(root, primary_lang)

    scan_result = {
        "project": {"name": root.name, "path": str(root)},
        "structure": structure,
        "languages": languages,
        "build": build,
        "frameworks": frameworks,
        "testing": testing,
        "infrastructure": infra,
        "conventions": conventions,
    }

    collected = _collect_all_files(root, primary_lang)

    return {
        "scan_result": scan_result,
        "collected_files": collected,
        "deep_analysis": {
            "steps": {},
            "total_tokens": 0,
            "total_duration": 0,
            "files_analyzed": sum(len(v) for v in collected.values()),
        },
        "steps": [f"파일 스캔 완료: {structure.get('source_files', 0)}개 소스, {structure.get('test_files', 0)}개 테스트"],
        "current_step": "파일 스캔 완료",
        "progress": 10,
    }


def analyze_deps_node(state: BootstrapState) -> dict:
    """Step 1/4: 의존성 & 빌드 분석 (console)"""
    from core.executor import create_executor
    from core.analyzer import _format_files

    collected = state["collected_files"]
    if not collected.get("build_config"):
        return {
            "steps": ["Step 1/4: 빌드 설정 파일 없음 — 스킵"],
            "current_step": "Step 1/4 스킵",
            "progress": 25,
        }

    scan = state["scan_result"]
    executor = create_executor("console")
    project_summary = _get_project_summary(scan)

    prompt = f"""당신은 시니어 소프트웨어 아키텍트입니다. 아래 프로젝트의 빌드/의존성 파일을 분석하세요.

## 프로젝트 정보
{project_summary}

## 빌드/의존성 파일
{_format_files(collected["build_config"])}

{_format_files(collected["app_config"][:5]) if collected.get("app_config") else ""}

## 분석 요청 (한국어로 작성)

### 1. 의존성 분석
- 핵심 의존성 목록과 각각의 역할/용도
- 의존성 버전 상태 (최신 여부, 보안 이슈 가능성)
- 불필요하거나 중복되는 의존성

### 2. 빌드 구조
- 빌드 설정의 특이사항
- 멀티모듈이면 모듈 간 의존 관계
- 프로파일/환경 설정 구조

### 3. 외부 연동
- 설정 파일에서 확인되는 DB, 캐시, 메시지큐, 외부 API 등
- 환경별 설정 차이

구체적 파일명과 라인을 근거로 제시하세요."""

    _emit_log("── Step 1/4: 의존성 & 빌드 분석 시작 ──")
    r = executor.run(prompt, project_path=state["project_path"], on_output=_emit_log)

    deep = dict(state.get("deep_analysis", {}))
    steps = dict(deep.get("steps", {}))
    steps["dependencies"] = r.output if r.success else f"분석 실패: {r.error}"
    deep["steps"] = steps
    deep["total_tokens"] = deep.get("total_tokens", 0) + r.tokens_used
    deep["total_duration"] = deep.get("total_duration", 0) + r.duration_sec

    return {
        "deep_analysis": deep,
        "steps": [f"Step 1/4: 의존성 & 빌드 분석 완료 ({r.duration_sec:.0f}초)"],
        "current_step": "Step 1/4 완료: 의존성 & 빌드",
        "progress": 25,
    }


def analyze_arch_node(state: BootstrapState) -> dict:
    """Step 2/4: 아키텍처 & 코드 패턴 분석 (console)"""
    from core.executor import create_executor
    from core.analyzer import _format_files

    collected = state["collected_files"]
    if not collected.get("core_source"):
        return {
            "steps": ["Step 2/4: 핵심 소스 없음 — 스킵"],
            "current_step": "Step 2/4 스킵",
            "progress": 40,
        }

    scan = state["scan_result"]
    executor = create_executor("console")
    project_summary = _get_project_summary(scan)

    prompt = f"""당신은 시니어 소프트웨어 아키텍트입니다. 아래 프로젝트의 핵심 소스 코드를 분석하세요.

## 프로젝트 정보
{project_summary}

## 엔트리포인트
{_format_files(collected.get("entrypoints", []))}

## 핵심 소스 코드 (레이어별 대표)
{_format_files(collected["core_source"])}

## 분석 요청 (한국어로 작성)

### 1. 아키텍처 패턴
- 사용 중인 아키텍처 패턴 (layered, hexagonal, clean, MVC 등)
- 레이어 간 의존 방향과 데이터 흐름
- 관심사 분리 수준 평가

### 2. 코드 컨벤션 (매우 구체적으로)
- 네이밍 규칙: 클래스, 메서드, 변수, 패키지/모듈 (실제 예시 포함)
- DI(의존성 주입) 패턴 (constructor, field, setter 등)
- 응답 래퍼/공통 패턴 (ApiResponse, BaseEntity 등)
- 예외 처리 방식 (글로벌 핸들러, per-method 등)
- 검증/유효성 검사 방식

### 3. 코드 품질
- 잘 된 점 (강점 3개 이상)
- 개선 필요한 점 (약점 3개 이상)
- 보안 우려사항
- SOLID 원칙 준수 여부

### 4. 코드 생성 시 반드시 따라야 할 규칙
- 이 프로젝트에 새 코드를 추가할 때 꼭 지켜야 할 패턴/규칙을 구체적으로 나열
- 절대 하면 안 되는 것 (anti-pattern)

구체적 파일명, 클래스명, 메서드명을 근거로 제시하세요."""

    _emit_log("── Step 2/4: 아키텍처 & 코드 패턴 분석 시작 ──")
    r = executor.run(prompt, project_path=state["project_path"], on_output=_emit_log)

    deep = dict(state.get("deep_analysis", {}))
    steps = dict(deep.get("steps", {}))
    steps["architecture"] = r.output if r.success else f"분석 실패: {r.error}"
    deep["steps"] = steps
    deep["total_tokens"] = deep.get("total_tokens", 0) + r.tokens_used
    deep["total_duration"] = deep.get("total_duration", 0) + r.duration_sec

    return {
        "deep_analysis": deep,
        "steps": [f"Step 2/4: 아키텍처 & 코드 패턴 분석 완료 ({r.duration_sec:.0f}초)"],
        "current_step": "Step 2/4 완료: 아키텍처 & 코드 패턴",
        "progress": 40,
    }


def analyze_tests_node(state: BootstrapState) -> dict:
    """Step 3/4: 테스트 전략 분석 (console)"""
    from core.executor import create_executor
    from core.analyzer import _format_files

    collected = state["collected_files"]
    scan = state["scan_result"]
    structure = scan.get("structure", {})
    executor = create_executor("console")
    project_summary = _get_project_summary(scan)

    test_section = _format_files(collected.get("tests", [])) if collected.get("tests") else "(테스트 파일 없음)"

    prompt = f"""당신은 시니어 QA 엔지니어입니다. 아래 프로젝트의 테스트 전략을 분석하고 개선안을 제시하세요.

## 프로젝트 정보
{project_summary}
테스트 파일: {structure.get("test_files", 0)}개 / 소스 파일: {structure.get("source_files", 0)}개

## 기존 테스트 코드
{test_section}

## 핵심 소스 코드 (테스트 대상)
{_format_files(collected.get("core_source", [])[:5])}

## 분석 요청 (한국어로 작성)

### 1. 현재 테스트 평가
- 테스트 커버리지 수준 평가 (어느 레이어가 부족한지)
- 테스트 코드 품질 (mocking, assertion, fixture 패턴)
- 테스트 네이밍/구조 규칙

### 2. 테스트 부족 영역
- 테스트가 없거나 부족한 구체적 영역/클래스
- 우선적으로 테스트를 추가해야 할 곳 (리스크 순)

### 3. 추천 테스트 전략
- 단위/통합/E2E 각각의 추천 프레임워크와 설정
- 이 프로젝트에 맞는 테스트 DB 전략 (H2, Testcontainers, mock 등)
- 테스트 작성 시 따라야 할 규칙/패턴"""

    _emit_log("── Step 3/4: 테스트 전략 분석 시작 ──")
    r = executor.run(prompt, project_path=state["project_path"], on_output=_emit_log)

    deep = dict(state.get("deep_analysis", {}))
    steps = dict(deep.get("steps", {}))
    steps["testing"] = r.output if r.success else f"분석 실패: {r.error}"
    deep["steps"] = steps
    deep["total_tokens"] = deep.get("total_tokens", 0) + r.tokens_used
    deep["total_duration"] = deep.get("total_duration", 0) + r.duration_sec

    return {
        "deep_analysis": deep,
        "steps": [f"Step 3/4: 테스트 전략 분석 완료 ({r.duration_sec:.0f}초)"],
        "current_step": "Step 3/4 완료: 테스트 전략",
        "progress": 55,
    }


def analyze_summary_node(state: BootstrapState) -> dict:
    """Step 4/4: 종합 평가 (console)"""
    from core.executor import create_executor
    from core.analyzer import _format_files

    collected = state["collected_files"]
    scan = state["scan_result"]
    deep = dict(state.get("deep_analysis", {}))
    deep_steps = deep.get("steps", {})
    executor = create_executor("console")
    project_summary = _get_project_summary(scan)

    infra_section = _format_files(collected.get("infra", [])) if collected.get("infra") else "(인프라 파일 없음)"

    prev_results = ""
    for step_name, step_result in deep_steps.items():
        if isinstance(step_result, str) and len(step_result) > 100:
            prev_results += f"\n### {step_name} 분석 결과 (요약)\n{step_result[:3000]}\n"

    prompt = f"""당신은 시니어 소프트웨어 아키텍트입니다. 지금까지의 분석 결과를 종합하여 최종 평가를 작성하세요.

## 프로젝트 정보
{project_summary}

## 인프라 파일
{infra_section}

## 이전 분석 결과
{prev_results}

## 종합 평가 요청 (한국어로 작성)

### 1. 프로젝트 성숙도 평가
- 전체 점수 (10점 만점)와 근거
- 강점 TOP 3
- 개선 필요 TOP 3

### 2. 인프라 & DevOps 평가
- CI/CD 파이프라인 상태
- 컨테이너화 수준
- 배포 전략

### 3. Auto-Pipe 활용 가이드
- 이 프로젝트에서 Auto-Pipe가 코드를 생성할 때:
  a) 반드시 따라야 할 패턴 (구체적 규칙 5개 이상)
  b) 파일 생성 위치 규칙 (패키지/디렉토리 구조)
  c) 네이밍 규칙 요약
  d) import/의존성 주입 규칙
  e) 에러 처리 규칙
  f) 테스트 작성 규칙

### 4. 추천 개발 순서
- 이 프로젝트에 새 기능을 추가한다면 어떤 순서로 개발하는 것이 가장 효율적인지
- 각 단계에서 생성해야 할 파일 목록"""

    _emit_log("── Step 4/4: 종합 평가 시작 ──")
    r = executor.run(prompt, project_path=state["project_path"], on_output=_emit_log)

    steps = dict(deep_steps)
    steps["summary"] = r.output if r.success else f"분석 실패: {r.error}"
    deep["steps"] = steps
    deep["total_tokens"] = deep.get("total_tokens", 0) + r.tokens_used
    deep["total_duration"] = deep.get("total_duration", 0) + r.duration_sec

    return {
        "deep_analysis": deep,
        "steps": [f"Step 4/4: 종합 평가 완료 ({r.duration_sec:.0f}초)"],
        "current_step": "Deep Analysis 완료",
        "progress": 70,
    }


def generate_config_node(state: BootstrapState) -> dict:
    """Phase 3: 설정 생성 + deep analysis 파일 저장"""
    from core.config_generator import generate_config
    from pathlib import Path
    import json
    import sys

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    scan = state["scan_result"]
    deep = state.get("deep_analysis", {})
    project_name = scan.get("project", {}).get("name", "unknown")
    output_dir = str(root / "projects" / project_name)

    gen_result = generate_config(scan, output_dir, deep_analysis=deep)

    # Deep Analysis 결과도 파일로 저장
    out = Path(output_dir)
    deep_steps = deep.get("steps", {})
    if deep_steps:
        analysis_dir = out / "analysis"
        analysis_dir.mkdir(exist_ok=True)

        step_filenames = {
            "dependencies": "01_dependencies.md",
            "architecture": "02_architecture.md",
            "testing": "03_testing.md",
            "summary": "04_summary.md",
        }
        for step_key, filename in step_filenames.items():
            content = deep_steps.get(step_key, "")
            if content:
                with open(analysis_dir / filename, "w", encoding="utf-8") as f:
                    f.write(content)

        meta = {
            "files_analyzed": deep.get("files_analyzed", 0),
            "total_duration": deep.get("total_duration", 0),
            "total_tokens": deep.get("total_tokens", 0),
        }
        with open(analysis_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        gen_result["files"]["analysis"] = [
            f"analysis/{filename}" for key, filename in step_filenames.items()
            if deep_steps.get(key)
        ]

    return {
        "gen_result": gen_result,
        "steps": [f"설정 생성 완료: {output_dir}"],
        "current_step": "설정 생성 완료",
        "progress": 95,
    }


def write_done_node(state: BootstrapState) -> dict:
    """완료 마킹"""
    return {
        "steps": ["Bootstrap 완료"],
        "current_step": "완료",
        "progress": 100,
    }


# ──────────────────────────────────────────
# 그래프 빌드
# ──────────────────────────────────────────

def build_bootstrap_graph():
    """Bootstrap LangGraph 그래프 생성

    scan_files → analyze_deps → analyze_arch → analyze_tests → analyze_summary
      → [Human Review] → generate_config → done → END
    """
    graph = StateGraph(BootstrapState)

    # 노드 등록
    graph.add_node("scan_files", scan_files_node)
    graph.add_node("analyze_deps", analyze_deps_node)
    graph.add_node("analyze_arch", analyze_arch_node)
    graph.add_node("analyze_tests", analyze_tests_node)
    graph.add_node("analyze_summary", analyze_summary_node)
    graph.add_node("generate_config", generate_config_node)
    graph.add_node("done", write_done_node)

    # 흐름: 각 분석 단계가 별도 노드 → 단계마다 스트리밍
    graph.set_entry_point("scan_files")
    graph.add_edge("scan_files", "analyze_deps")
    graph.add_edge("analyze_deps", "analyze_arch")
    graph.add_edge("analyze_arch", "analyze_tests")
    graph.add_edge("analyze_tests", "analyze_summary")
    graph.add_edge("analyze_summary", "generate_config")
    graph.add_edge("generate_config", "done")
    graph.add_edge("done", END)

    return graph.compile(
        interrupt_before=["generate_config"],  # 분석 결과 확인 후 진행
        checkpointer=get_checkpointer(),
    )


def get_mermaid():
    """그래프 다이어그램"""
    return build_bootstrap_graph().get_graph().draw_mermaid()
