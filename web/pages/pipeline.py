"""Pipeline 페이지 — Auto-Pipe 메인 파이프라인 실행

흐름:
  input → running_design → design_review → running_main → code_review → done
"""

import streamlit as st
import uuid
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from core.langfuse_callback import get_langfuse_handler


def render():
    st.header("Pipeline")
    st.caption("요구사항을 입력하면 설계 → 개발 → 테스트 → 리뷰 → 문서 파이프라인을 자동 실행합니다")

    # 세션 상태 초기화
    for key, default in [
        ("pipe_phase", "input"),
        ("pipe_state", None),
        ("pipe_graph", None),
        ("pipe_thread", None),
        ("pipe_config_path", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    phase = st.session_state.pipe_phase

    if phase == "input":
        _render_input()
    elif phase == "running_design":
        _render_running_design()
    elif phase == "design_review":
        _render_design_review()
    elif phase == "running_main":
        _render_running_main()
    elif phase == "code_review":
        _render_code_review()
    elif phase == "done":
        _render_done()


def _get_configured_projects() -> list[dict]:
    """Bootstrap 완료된 프로젝트 목록"""
    projects_dir = _ROOT / "projects"
    results = []
    if projects_dir.exists():
        for d in sorted(projects_dir.iterdir()):
            pipeline_yaml = d / "pipeline.yaml"
            if d.is_dir() and pipeline_yaml.exists():
                results.append({
                    "name": d.name,
                    "path": str(d),
                    "config": str(pipeline_yaml),
                })
    return results


def _render_input():
    """프로젝트 선택 + 요구사항 입력"""
    projects = _get_configured_projects()

    if not projects:
        st.warning("Bootstrap이 완료된 프로젝트가 없습니다. 먼저 Bootstrap을 실행하세요.")
        return

    # 프로젝트 선택
    project_names = [p["name"] for p in projects]
    selected_idx = st.selectbox(
        "프로젝트 선택",
        range(len(project_names)),
        format_func=lambda i: project_names[i],
    )
    selected = projects[selected_idx]

    # 요구사항 입력
    requirements = st.text_area(
        "요구사항",
        height=200,
        placeholder="예: 사용자 로그인 API를 구현해주세요.\n- JWT 토큰 기반 인증\n- 로그인 실패 5회 시 계정 잠금",
    )

    # 파이프라인 다이어그램
    with st.expander("파이프라인 구조"):
        try:
            from pipeline.graph import get_mermaid
            st.code(get_mermaid(), language="mermaid")
        except Exception:
            st.caption("그래프 다이어그램을 로드할 수 없습니다")

    if st.button("파이프라인 실행", type="primary", disabled=not requirements.strip()):
        st.session_state.pipe_config_path = selected["config"]
        st.session_state.pipe_phase = "running_design"
        st.session_state.pipe_state = {
            "requirements": requirements.strip(),
            "project_name": selected["name"],
            "project_path": _get_project_path(selected["config"]),
            "config_path": selected["config"],
        }
        st.rerun()


def _get_project_path(config_path: str) -> str:
    """pipeline.yaml에서 프로젝트 경로 추출"""
    import yaml
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("project", {}).get("path", "")
    except Exception:
        return ""


def _render_running_design():
    """Phase 1 설계 스트리밍"""
    from pipeline.graph import build_pipeline_graph
    from pipeline.utils import set_log_callback
    from core.file_logger import start_file_logger, stop_file_logger

    state_data = st.session_state.pipe_state
    graph = build_pipeline_graph()
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    # Langfuse 연결 (실패해도 파이프라인은 계속 진행)
    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
    except Exception:
        pass

    initial_state = {
        "requirements": state_data["requirements"],
        "project_name": state_data["project_name"],
        "project_path": state_data["project_path"],
        "config_path": state_data["config_path"],
        "pre_build_result": "",
        "pre_build_errors": "",
        "pre_test_result": "",
        "pre_test_errors": "",
        "requirements_analysis": "",
        "design_spec": "",
        "api_spec": "",
        "db_schema": "",
        "ui_spec": "",
        "design_approved": False,
        "design_feedback": "",
        "source_code": {},
        "test_code": {},
        "code_files_created": [],
        "build_result": "",
        "build_log": "",
        "test_result": "",
        "test_log": "",
        "test_errors": [],
        "fix_iteration": 0,
        "max_fix_iterations": 5,
        "review_report": "",
        "security_report": "",
        "merged_review": "",
        "review_approved": False,
        "review_feedback": "",
        "review_iteration": 0,
        "max_review_iterations": 3,
        "api_doc": "",
        "ops_manual": "",
        "changelog": "",
        "deliverables": [],
        "current_phase": "design",
        "current_step": "시작",
        "progress": 0,
        "messages": [],
        "errors": [],
    }

    # 파일 로거 시작
    file_logger = start_file_logger(state_data["project_name"], "pipeline")

    # 실시간 로그 (병렬 노드가 worker thread에서 실행되므로 콜백에서 Streamlit 호출 불가)
    live_lines = []
    live_container = st.empty()

    def on_live_output(line: str):
        live_lines.append(line)  # list.append is thread-safe in CPython

    set_log_callback(on_live_output)

    with st.status("Phase 1: 설계 생성 중...", expanded=True) as status:
        st.write("설계 파이프라인 시작...")

        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            # 메인 스레드에서 로그 표시
            if live_lines:
                live_container.code("\n".join(live_lines[-30:]), language="markdown")

            if isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        step = update.get("current_step", "")
                        if step:
                            status.update(label=f"{node_name} — {step}")
                        for msg in update.get("messages", []):
                            st.write(msg)

        # 최종 로그 표시
        if live_lines:
            live_container.code("\n".join(live_lines[-30:]), language="markdown")
        status.update(label="설계 완료! 리뷰 페이지로 이동합니다.", state="complete")

    set_log_callback(None)

    # interrupt 상태 저장
    final_state = graph.get_state(config)
    st.session_state.pipe_state = dict(final_state.values)
    st.session_state.pipe_graph = graph
    st.session_state.pipe_thread = thread_id
    st.session_state.pipe_phase = "design_review"
    st.rerun()


def _render_design_review():
    """설계 결과 리뷰 + 승인/반려"""
    state = st.session_state.pipe_state

    st.subheader("설계 검토")
    st.info(f"프로젝트: **{state.get('project_name')}**")

    # 설계 결과 (요구사항 분석 + 설계가 한 번에 생성됨)
    st.markdown(state.get("design_spec", "(설계 없음)"))

    # 에러 표시
    errors = state.get("errors", [])
    if errors:
        with st.expander("에러 로그", expanded=True):
            for e in errors:
                st.error(e)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("승인 — 개발 진행", type="primary", use_container_width=True):
            st.session_state.pipe_state["design_approved"] = True
            st.session_state.pipe_phase = "running_main"
            st.rerun()

    with col2:
        feedback = st.text_input("수정 요청 (선택)")
        if st.button("수정 요청", use_container_width=True) and feedback:
            st.session_state.pipe_state["design_feedback"] = feedback
            st.session_state.pipe_phase = "running_design"
            st.session_state.pipe_graph = None
            st.session_state.pipe_thread = None
            st.rerun()

    with col3:
        if st.button("취소", use_container_width=True):
            _reset_state()
            st.rerun()


def _render_running_main():
    """Phase 2-5 실행 (설계 승인 후)"""
    from pipeline.utils import set_log_callback
    from core.file_logger import get_file_logger, start_file_logger, stop_file_logger

    graph = st.session_state.pipe_graph
    thread_id = st.session_state.pipe_thread
    config = {"configurable": {"thread_id": thread_id}}

    # Langfuse 연결 (실패해도 파이프라인은 계속 진행)
    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
    except Exception:
        pass

    # 설계 승인 상태 업데이트 (interrupt 지점 직전 노드 = generate_design)
    graph.update_state(config, {"design_approved": True}, as_node="generate_design")

    # 파일 로거가 없으면 새로 시작 (페이지 리로드 시)
    if not get_file_logger():
        project_name = st.session_state.pipe_state.get("project_name", "unknown")
        start_file_logger(project_name, "pipeline")

    # 실시간 로그 (병렬 노드가 worker thread에서 실행되므로 콜백에서 Streamlit 호출 불가)
    live_lines = []
    live_container = st.empty()

    def on_live_output(line: str):
        live_lines.append(line)  # list.append is thread-safe in CPython

    set_log_callback(on_live_output)

    with st.status("개발 → 테스트 → 리뷰 → 문서 실행 중...", expanded=True) as status:
        for chunk in graph.stream(None, config, stream_mode="updates"):
            # 메인 스레드에서 로그 표시
            if live_lines:
                live_container.code("\n".join(live_lines[-30:]), language="markdown")

            if isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        step = update.get("current_step", "")
                        progress = update.get("progress", 0)
                        if step:
                            status.update(label=f"{node_name} — {step} ({progress}%)")
                        for msg in update.get("messages", []):
                            st.write(msg)

        # 최종 로그 표시
        if live_lines:
            live_container.code("\n".join(live_lines[-30:]), language="markdown")

    set_log_callback(None)
    stop_file_logger(success=True)

    # interrupt 확인 (리뷰 승인 대기 또는 완료)
    final_state = graph.get_state(config)
    st.session_state.pipe_state = dict(final_state.values)

    if final_state.next:
        # review_decision에서 interrupt됨
        st.session_state.pipe_phase = "code_review"
    else:
        st.session_state.pipe_phase = "done"

    st.rerun()


def _render_code_review():
    """코드 리뷰 결과 + 승인/반려"""
    state = st.session_state.pipe_state

    st.subheader("코드 리뷰")

    iteration = state.get("review_iteration", 0)
    if iteration > 0:
        st.info(f"리뷰 반복 #{iteration}")

    # 리뷰 결과
    tabs = st.tabs(["통합 리뷰", "품질 리뷰", "보안 체크", "생성된 코드"])

    with tabs[0]:
        st.markdown(state.get("merged_review", "(리뷰 결과 없음)"))
    with tabs[1]:
        st.markdown(state.get("review_report", "(품질 리뷰 없음)"))
    with tabs[2]:
        st.markdown(state.get("security_report", "(보안 체크 없음)"))
    with tabs[3]:
        code = state.get("source_code", {})
        if code:
            for filepath, content in code.items():
                with st.expander(filepath):
                    lang = filepath.rsplit(".", 1)[-1] if "." in filepath else "text"
                    st.code(content, language=lang)
        else:
            st.caption("생성된 코드 없음")

    # 에러 표시
    errors = state.get("errors", [])
    if errors:
        with st.expander("에러 로그"):
            for e in errors:
                st.error(e)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("승인 — 문서 생성", type="primary", use_container_width=True):
            graph = st.session_state.pipe_graph
            thread_id = st.session_state.pipe_thread
            config = {"configurable": {"thread_id": thread_id}}

            graph.update_state(config, {"review_approved": True}, as_node="merge_reviews")
            st.session_state.pipe_phase = "running_main"
            # running_main이 이어서 실행
            st.rerun()

    with col2:
        feedback = st.text_input("수정 요청")
        if st.button("수정 요청 — 재리뷰", use_container_width=True) and feedback:
            graph = st.session_state.pipe_graph
            thread_id = st.session_state.pipe_thread
            config = {"configurable": {"thread_id": thread_id}}

            graph.update_state(config, as_node="merge_reviews", values={
                "review_approved": False,
                "review_feedback": feedback,
            })
            st.session_state.pipe_phase = "running_main"
            st.rerun()

    with col3:
        if st.button("강제 종료", use_container_width=True):
            _reset_state()
            st.rerun()


def _render_done():
    """완료 화면"""
    state = st.session_state.pipe_state
    project_name = state.get("project_name", "unknown")

    st.success(f"**{project_name}** 파이프라인 완료!")

    # 실행 로그
    messages = state.get("messages", [])
    if messages:
        with st.expander("전체 실행 로그"):
            for msg in messages:
                st.caption(msg)

    # 에러
    errors = state.get("errors", [])
    if errors:
        with st.expander("에러 로그", expanded=True):
            for e in errors:
                st.error(e)

    # 산출물
    deliverables = state.get("deliverables", [])
    if deliverables:
        st.markdown("#### 산출물")
        config_dir = Path(state.get("config_path", "")).parent
        st.code(str(config_dir / "output"), language=None)
        for d in deliverables:
            st.caption(f"  {d}")

    # 생성된 코드 미리보기
    source_code = state.get("source_code", {})
    if source_code:
        st.markdown("#### 생성된 코드")
        for filepath, content in source_code.items():
            with st.expander(filepath):
                lang = filepath.rsplit(".", 1)[-1] if "." in filepath else "text"
                st.code(content, language=lang)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("새 요구사항 실행", use_container_width=True):
            _reset_state()
            st.rerun()
    with col2:
        if st.button("리뷰 다시 보기", use_container_width=True):
            st.session_state.pipe_phase = "code_review"
            st.rerun()


def _reset_state():
    """세션 상태 초기화"""
    st.session_state.pipe_phase = "input"
    st.session_state.pipe_state = None
    st.session_state.pipe_graph = None
    st.session_state.pipe_thread = None
    st.session_state.pipe_config_path = None
