"""Bootstrap 페이지 — LangGraph 기반 프로젝트 분석 파이프라인

흐름:
  input → scan_files(tool) → deep_analyze(console) → [Human Review] → generate_config(api) → done
"""

import streamlit as st
import yaml
import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from core.langfuse_callback import get_langfuse_handler


def render():
    st.header("Bootstrap")
    st.caption("프로젝트 경로를 입력하면 LangGraph 파이프라인이 자동으로 분석합니다")

    if "boot_phase" not in st.session_state:
        st.session_state.boot_phase = "input"
    if "boot_state" not in st.session_state:
        st.session_state.boot_state = None
    if "boot_thread" not in st.session_state:
        st.session_state.boot_thread = None
    if "boot_graph" not in st.session_state:
        st.session_state.boot_graph = None

    phase = st.session_state.boot_phase

    if phase == "input":
        _render_input()
    elif phase == "analyzing":
        _render_analyzing()
    elif phase == "review":
        _render_review()
    elif phase == "done":
        _render_done()


def _render_input():
    """프로젝트 경로 입력 화면"""
    projects_dir = _ROOT / "projects"
    existing = [d.name for d in projects_dir.iterdir()
                if d.is_dir() and d.name != ".gitkeep" and (d / "project_analysis.yaml").exists()]

    if existing:
        st.markdown("#### 기존 프로젝트")
        cols = st.columns(min(len(existing), 4))
        for i, name in enumerate(existing):
            with cols[i % 4]:
                if st.button(f"{name}", key=f"existing_{name}", use_container_width=True):
                    analysis_path = projects_dir / name / "project_analysis.yaml"
                    with open(analysis_path, "r") as f:
                        scan = yaml.safe_load(f)

                    # Deep Analysis 결과를 파일에서 로드
                    deep = {"steps": {}, "total_tokens": 0, "total_duration": 0, "files_analyzed": 0}
                    analysis_dir = projects_dir / name / "analysis"
                    if analysis_dir.is_dir():
                        step_filenames = {
                            "01_dependencies.md": "dependencies",
                            "02_architecture.md": "architecture",
                            "03_testing.md": "testing",
                            "04_summary.md": "summary",
                        }
                        for filename, step_key in step_filenames.items():
                            fpath = analysis_dir / filename
                            if fpath.exists():
                                deep["steps"][step_key] = fpath.read_text(encoding="utf-8")
                        # meta.json 로드
                        meta_path = analysis_dir / "meta.json"
                        if meta_path.exists():
                            import json
                            try:
                                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                                deep["files_analyzed"] = meta.get("files_analyzed", 0)
                                deep["total_duration"] = meta.get("total_duration", 0)
                                deep["total_tokens"] = meta.get("total_tokens", 0)
                            except (json.JSONDecodeError, OSError):
                                pass

                    st.session_state.boot_state = {
                        "scan_result": scan,
                        "deep_analysis": deep,
                    }
                    st.session_state.boot_phase = "review"
                    st.rerun()
        st.markdown("---")

    st.markdown("#### 새 프로젝트 분석")

    # LangGraph 그래프 다이어그램 표시
    with st.expander("Bootstrap 파이프라인 구조"):
        st.markdown("""
        ```
        scan_files (tool)          → 파일 구조/언어/프레임워크 스캔
              ↓
        analyze_deps (console)     → Step 1: 의존성 & 빌드 분석
              ↓
        analyze_arch (console)     → Step 2: 아키텍처 & 코드 패턴
              ↓
        analyze_tests (console)    → Step 3: 테스트 전략
              ↓
        analyze_summary (console)  → Step 4: 종합 평가
              ↓
        [Human Review]             → 웹에서 분석 결과 확인/승인
              ↓
        generate_config (api)      → pipeline.yaml + 프롬프트 생성
              ↓
        done                       → projects/<name>/ 에 저장
        ```
        """)

    project_path = st.text_input(
        "프로젝트 경로",
        placeholder="/Users/.../my-project",
        key="boot_path_input",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

    if analyze_btn and project_path:
        path = project_path.strip()
        if not os.path.isdir(path):
            st.error(f"경로가 존재하지 않습니다: {path}")
            return

        st.session_state.boot_phase = "analyzing"
        st.session_state.boot_path = path
        st.rerun()


def _render_analyzing():
    """LangGraph 파이프라인 실행 + 실시간 진행 표시"""
    from bootstrap.graph import build_bootstrap_graph, set_log_callback
    from core.file_logger import start_file_logger, stop_file_logger

    project_path = st.session_state.get("boot_path", "")
    if not project_path:
        st.session_state.boot_phase = "input"
        st.rerun()
        return

    st.info(f"분석 대상: `{project_path}`")

    # LangGraph 그래프 생성 & 실행
    graph = build_bootstrap_graph()
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    # Langfuse 콜백 연결 (설정되어 있으면 자동 트레이싱)
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    initial_state = {
        "project_path": project_path,
        "scan_result": {},
        "collected_files": {},
        "deep_analysis": {},
        "analysis_approved": False,
        "gen_result": {},
        "steps": [],
        "current_step": "시작",
        "progress": 0,
        "errors": [],
    }

    # 파일 로거 시작 (경로 마지막 폴더명을 프로젝트명으로 사용)
    _proj_name = os.path.basename(project_path.rstrip("/"))
    file_logger = start_file_logger(_proj_name, "bootstrap")

    # 실시간 로그 표시 영역
    step_log = []
    live_log_container = st.empty()
    live_lines = []

    def on_live_output(line: str):
        """Claude CLI stdout 실시간 콜백 → UI 업데이트"""
        live_lines.append(line)
        # 최근 30줄만 표시
        display = "\n".join(live_lines[-30:])
        live_log_container.code(display, language="markdown")

    # 콜백 등록
    set_log_callback(on_live_output)

    with st.status("Bootstrap 파이프라인 실행 중...", expanded=True) as status:
        st.write("파이프라인 시작...")

        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            # chunk가 tuple일 수도 있고 dict일 수도 있음
            if isinstance(chunk, tuple):
                node_name, update = chunk[0], chunk[1]
            elif isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    pass  # 마지막 항목 사용
            else:
                continue

            if not isinstance(update, dict):
                continue

            current_step = update.get("current_step", "")
            new_steps = update.get("steps", [])

            if current_step:
                status.update(label=f"{node_name} — {current_step}")
            for s in new_steps:
                step_log.append(f"`{node_name}` → {s}")
                st.write(s)

        status.update(label="Deep Analysis 완료! 리뷰 페이지로 이동합니다.", state="complete")

    # 콜백 해제 & 파일 로거 종료
    set_log_callback(None)
    stop_file_logger(success=True)

    # interrupt에 의해 멈춤 → 현재 상태 가져오기
    final_state = graph.get_state(config)

    # 상태 저장
    st.session_state.boot_state = dict(final_state.values)
    st.session_state.boot_graph = graph
    st.session_state.boot_thread = thread_id
    st.session_state.boot_phase = "review"

    st.rerun()


def _render_review():
    """분석 결과 리뷰 + Human Review 승인"""
    state = st.session_state.boot_state
    if not state:
        st.session_state.boot_phase = "input"
        st.rerun()
        return

    scan = state.get("scan_result", {})
    deep = state.get("deep_analysis", {})
    deep_steps = deep.get("steps", {}) if deep else {}

    project = scan.get("project", {})
    structure = scan.get("structure", {})
    languages = scan.get("languages", {})
    frameworks = scan.get("frameworks", [])
    build = scan.get("build", {})
    testing = scan.get("testing", {})
    infra = scan.get("infrastructure", {})
    conventions = scan.get("conventions", {})

    st.markdown(f"### {project.get('name', 'unknown')}")
    st.caption(project.get("path", ""))

    # 실행 로그
    steps_done = state.get("steps", [])
    if steps_done:
        with st.expander(f"실행 로그 ({len(steps_done)}단계)", expanded=False):
            for s in steps_done:
                st.caption(s)

    # 요약 카드
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("소스 파일", structure.get("source_files", 0))
    c2.metric("테스트 파일", structure.get("test_files", 0))
    c3.metric("코드 라인", f"{structure.get('lines_of_code', 0):,}")
    c4.metric("총 파일", structure.get("total_files", 0))
    files_analyzed = deep.get("files_analyzed", 0)
    c5.metric("분석 파일", files_analyzed)

    # 탭
    tab_names = [
        "종합 평가", "의존성 & 빌드", "아키텍처 & 코드 패턴", "테스트 전략",
        "언어/프레임워크", "구조", "빌드/인프라", "테스트 현황", "전체 YAML",
    ]
    tabs = st.tabs(tab_names)

    # Deep Analysis 4탭
    _deep_tabs = [
        (0, "summary", "종합 평가"),
        (1, "dependencies", "의존성 & 빌드"),
        (2, "architecture", "아키텍처 & 코드 패턴"),
        (3, "testing", "테스트 전략"),
    ]
    for tab_idx, step_key, label in _deep_tabs:
        with tabs[tab_idx]:
            if deep_steps.get(step_key):
                if tab_idx == 0 and deep:
                    meta_cols = st.columns(3)
                    meta_cols[0].caption(f"분석 파일: {deep.get('files_analyzed', 0)}개")
                    meta_cols[1].caption(f"소요 시간: {deep.get('total_duration', 0):.1f}초")
                    meta_cols[2].caption(f"토큰 사용: {deep.get('total_tokens', 0):,}")
                    st.markdown("---")
                st.markdown(deep_steps[step_key])
            else:
                st.info(f"{label} 결과가 아직 없습니다.")

    with tabs[4]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**언어 분포**")
            breakdown = languages.get("breakdown", {})
            if breakdown:
                for lang, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                    pct = int(count / max(sum(breakdown.values()), 1) * 100)
                    st.progress(pct / 100, text=f"{lang}: {count}개 ({pct}%)")
        with col2:
            st.markdown("**프레임워크**")
            if frameworks:
                for fw in frameworks:
                    st.success(f"**{fw['name']}** ({fw['language']})")
                    st.caption(f"감지 근거: {', '.join(fw.get('markers_found', []))}")

    with tabs[5]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**프로젝트 타입**")
            st.info(f"{structure.get('type', 'single')}")
            if structure.get("modules"):
                st.markdown("**모듈**")
                for m in structure["modules"]:
                    st.code(m)
            st.markdown("**아키텍처**")
            st.info(conventions.get("architecture", "unknown"))
            if conventions.get("layers"):
                st.markdown("**레이어**: " + " → ".join(conventions["layers"]))
        with col2:
            st.markdown("**디렉토리 구조** (상위 2 depth)")
            dirs = structure.get("directories", [])
            if dirs:
                st.code("\n".join(f"  {d}/" for d in dirs[:30]), language=None)

    with tabs[6]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**빌드**")
            st.info(f"도구: {build.get('tool', 'N/A')}")
            cmds = build.get("commands", {})
            if cmds:
                for name, cmd in cmds.items():
                    st.code(f"{name}: {cmd}", language=None)
        with col2:
            st.markdown("**인프라**")
            st.markdown(f"- Docker: {'O' if infra.get('docker') else 'X'}")
            st.markdown(f"- Docker Compose: {'O' if infra.get('docker_compose') else 'X'}")
            st.markdown(f"- CI/CD: {infra.get('ci_cd') or 'N/A'}")

    with tabs[7]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**테스트 현황**")
            st.markdown(f"- 테스트 존재: {'O' if testing.get('has_tests') else 'X'}")
            st.markdown(f"- 테스트 파일: {testing.get('test_files', 0)}개")
            st.markdown(f"- 추정 커버리지: {testing.get('estimated_coverage', 'N/A')}")
        with col2:
            st.markdown("**테스트 프레임워크**")
            if testing.get("frameworks"):
                for fw in testing["frameworks"]:
                    st.success(fw)
            else:
                st.warning("감지된 테스트 프레임워크 없음")

    with tabs[8]:
        yaml_data = {k: v for k, v in scan.items()}
        st.code(yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False, sort_keys=False),
                language="yaml")

    # ─── Human Review 액션 버튼 ───
    st.markdown("---")
    st.markdown("#### 분석 결과 확인")
    st.info("승인하면 `pipeline.yaml`과 프롬프트 템플릿이 생성됩니다.")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("승인 → 설정 생성", type="primary", use_container_width=True):
            _continue_pipeline()

    with col2:
        if st.button("다시 분석", use_container_width=True):
            st.session_state.boot_phase = "input"
            st.session_state.boot_state = None
            st.session_state.boot_graph = None
            st.session_state.boot_thread = None
            st.rerun()

    with col3:
        if st.button("취소", use_container_width=True):
            st.session_state.boot_phase = "input"
            st.session_state.boot_state = None
            st.rerun()


def _continue_pipeline():
    """Human Review 승인 → generate_config 실행"""
    graph = st.session_state.boot_graph
    thread_id = st.session_state.boot_thread

    if not graph or not thread_id:
        # 그래프가 없으면 (기존 프로젝트에서 왔을 때) 직접 생성
        from core.config_generator import generate_config

        scan = st.session_state.boot_state.get("scan_result", {})
        project_name = scan.get("project", {}).get("name", "unknown")
        output_dir = str(_ROOT / "projects" / project_name)

        with st.spinner("설정 파일 생성 중..."):
            gen_result = generate_config(scan, output_dir)

        st.session_state.boot_state["gen_result"] = gen_result
        st.session_state.boot_phase = "done"
        st.rerun()
        return

    # LangGraph: 승인 상태 업데이트 → 이어서 실행
    config = {"configurable": {"thread_id": thread_id}}

    # Langfuse 콜백 연결
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    graph.update_state(config, {"analysis_approved": True})

    with st.spinner("설정 생성 중... (generate_config → done)"):
        for chunk in graph.stream(None, config, stream_mode="updates"):
            for node_name, update in chunk.items():
                if "gen_result" in update:
                    st.session_state.boot_state["gen_result"] = update["gen_result"]

    # 최종 상태
    final = graph.get_state(config)
    st.session_state.boot_state = dict(final.values)
    st.session_state.boot_phase = "done"
    st.rerun()


def _render_done():
    """설정 생성 완료"""
    state = st.session_state.boot_state
    gen_result = state.get("gen_result", {})
    scan = state.get("scan_result", {})
    project_name = scan.get("project", {}).get("name", "unknown")

    st.success(f"**{project_name}** Bootstrap 완료!")

    # 실행 로그
    steps = state.get("steps", [])
    if steps:
        with st.expander("전체 실행 로그"):
            for s in steps:
                st.caption(s)

    st.markdown("#### 생성된 파일")
    output_dir = gen_result.get("output_dir", "")
    st.code(output_dir, language=None)

    files = gen_result.get("files", {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**설정 파일**")
        st.markdown("- `project_analysis.yaml`")
        st.markdown("- `pipeline.yaml`")
    with col2:
        st.markdown("**프롬프트 템플릿**")
        for p in files.get("prompts", []):
            st.markdown(f"- `prompts/{p}`")

    pipeline_path = files.get("pipeline", "")
    if pipeline_path and os.path.exists(pipeline_path):
        with st.expander("pipeline.yaml 미리보기"):
            with open(pipeline_path, "r") as f:
                st.code(f.read(), language="yaml")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("다른 프로젝트 분석", use_container_width=True):
            st.session_state.boot_phase = "input"
            st.session_state.boot_state = None
            st.session_state.boot_graph = None
            st.session_state.boot_thread = None
            st.rerun()
    with col2:
        if st.button("분석 결과 다시 보기", use_container_width=True):
            st.session_state.boot_phase = "review"
            st.rerun()
