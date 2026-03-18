"""LangGraph 학습 예제 페이지"""

import streamlit as st
import uuid
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

_EXAMPLES_DIR = _ROOT / "examples"


def render_mermaid(mermaid_code: str, height: int = 350):
    st.components.v1.html(f"""
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <div class="mermaid" style="background:white;padding:16px;border-radius:8px;">
    {mermaid_code}
    </div>
    <script>mermaid.initialize({{startOnLoad:true,theme:'default'}});</script>
    """, height=height)


def render():
    st.header("LangGraph 학습 예제")
    st.caption("Auto-Pipe에 사용된 LangGraph 핵심 패턴을 학습합니다")

    tabs = st.tabs([
        "조건부 분기", "메모리", "Human-in-Loop", "서브그래프",
        "병렬 실행", "스트리밍", "Tool Calling", "순환 루프", "에러 처리",
    ])

    with tabs[0]:
        _tab_basic()
    with tabs[1]:
        _tab_memory()
    with tabs[2]:
        _tab_human()
    with tabs[3]:
        _tab_subgraph()
    with tabs[4]:
        _tab_parallel()
    with tabs[5]:
        _tab_streaming()
    with tabs[6]:
        _tab_tool()
    with tabs[7]:
        _tab_cycle()
    with tabs[8]:
        _tab_error()


def _tab_basic():
    from examples.graph import build_graph, run as basic_run, get_mermaid_diagram

    st.markdown("### 조건부 분기 (Conditional Edge)")
    col_d, col_c = st.columns([1, 1])
    with col_d:
        render_mermaid(get_mermaid_diagram())
    with col_c:
        st.code("""graph.add_conditional_edges(
    "classify", route_by_category,
    {"question": "question", "calculation": "calculation", "translation": "translation"},
)""", language="python")

    user_input = st.text_input("입력", placeholder="질문, 계산, 번역 중 아무거나", key="basic_input")
    if st.button("실행", key="basic_run") and user_input:
        with st.spinner("실행 중..."):
            result = basic_run(user_input)
        st.success(f"분류: **{result['category']}** | 경로: {' → '.join(result['steps'])}")
        st.markdown(result.get("result", ""))

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph.py").read_text(), language="python")


def _tab_memory():
    from examples.graph_memory import chat, get_history, get_mermaid as mem_mermaid

    st.markdown("### Checkpointer (메모리)")
    render_mermaid(mem_mermaid(), height=200)

    if "mem_thread" not in st.session_state:
        st.session_state.mem_thread = str(uuid.uuid4())[:8]

    col1, col2 = st.columns([3, 1])
    with col1:
        mem_input = st.text_input("메시지", key="mem_input")
    with col2:
        st.markdown(""); st.markdown("")
        if st.button("새 대화", key="mem_new"):
            st.session_state.mem_thread = str(uuid.uuid4())[:8]
            st.rerun()

    if st.button("전송", key="mem_send") and mem_input:
        with st.spinner("응답 중..."):
            chat(mem_input, st.session_state.mem_thread)
        for msg in get_history(st.session_state.mem_thread):
            role = "User" if msg.type == "human" else "AI"
            st.markdown(f"**{role}**: {msg.content}")

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_memory.py").read_text(), language="python")


def _tab_human():
    from examples.graph_human import start_request, approve_and_continue, get_mermaid as human_mermaid

    st.markdown("### Human-in-the-Loop")
    render_mermaid(human_mermaid())

    if "human_thread" not in st.session_state:
        st.session_state.human_thread = str(uuid.uuid4())[:8]
    if "human_phase" not in st.session_state:
        st.session_state.human_phase = "input"

    if st.session_state.human_phase == "input":
        request = st.text_input("요청사항", key="human_input")
        if st.button("요청 보내기", key="human_start") and request:
            st.session_state.human_thread = str(uuid.uuid4())[:8]
            with st.spinner("분석 중..."):
                result = start_request(request, st.session_state.human_thread)
            st.session_state.human_result = result
            st.session_state.human_phase = "review"
            st.rerun()

    elif st.session_state.human_phase == "review":
        result = st.session_state.human_result
        st.warning("실행 전 승인 대기 중")
        st.markdown(f"**분석:** {result.get('analysis', '')}")
        st.markdown(f"**제안:** {result.get('proposed_action', '')}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("승인", key="human_approve", use_container_width=True):
                with st.spinner("실행 중..."):
                    final = approve_and_continue(True, st.session_state.human_thread)
                st.session_state.human_final = final
                st.session_state.human_phase = "done"
                st.rerun()
        with c2:
            if st.button("거부", key="human_reject", use_container_width=True):
                final = approve_and_continue(False, st.session_state.human_thread)
                st.session_state.human_final = final
                st.session_state.human_phase = "done"
                st.rerun()

    elif st.session_state.human_phase == "done":
        final = st.session_state.human_final
        if final.get("approved"):
            st.success("승인 완료")
        else:
            st.error("거부됨")
        st.markdown(f"**결과:** {final.get('final_result', '')}")
        if st.button("다시 시작", key="human_reset"):
            st.session_state.human_phase = "input"
            st.rerun()

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_human.py").read_text(), language="python")


def _tab_subgraph():
    from examples.graph_subgraph import run as sub_run, get_mermaid as sub_mermaid, get_sub_mermaid

    st.markdown("### Subgraph")
    c1, c2 = st.columns(2)
    with c1:
        render_mermaid(sub_mermaid(), height=250)
    with c2:
        render_mermaid(get_sub_mermaid(), height=250)

    sub_input = st.text_area("요약할 텍스트", height=100, key="sub_input")
    if st.button("요약 + 평가", key="sub_run") and sub_input:
        with st.spinner("실행 중..."):
            result = sub_run(sub_input)
        st.markdown(f"**요약:** {result['summary']}")
        st.markdown(f"**평가:** {result['evaluation']}")

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_subgraph.py").read_text(), language="python")


def _tab_parallel():
    from examples.graph_parallel import run as par_run, get_mermaid as par_mermaid

    st.markdown("### 병렬 실행")
    render_mermaid(par_mermaid(), height=400)

    par_input = st.text_input("분석 주제", key="par_input")
    if st.button("3관점 분석", key="par_run") and par_input:
        with st.spinner("병렬 분석 중..."):
            result = par_run(par_input)
        for a in result.get("analyses", []):
            st.info(a)
        st.markdown(f"**종합:** {result.get('final_report', '')}")

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_parallel.py").read_text(), language="python")


def _tab_streaming():
    from examples.graph_streaming import run_stream as stream_run, get_mermaid as stream_mermaid

    st.markdown("### 스트리밍")
    render_mermaid(stream_mermaid())

    stream_input = st.text_input("글 작성 주제", key="stream_input")
    if st.button("스트리밍 실행", key="stream_run") and stream_input:
        progress = st.empty()
        results = {}
        for chunk in stream_run(stream_input):
            for node_name, update in chunk.items():
                results[node_name] = update
                with progress.container():
                    for n, u in results.items():
                        st.success(f"**{n}** 완료")

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_streaming.py").read_text(), language="python")


def _tab_tool():
    from examples.graph_tool import run_stream as tool_stream, get_mermaid as tool_mermaid

    st.markdown("### Tool Calling")
    render_mermaid(tool_mermaid())

    tool_input = st.text_input("질문", key="tool_input")
    if st.button("Agent 실행", key="tool_run") and tool_input:
        progress = st.empty()
        step_log = []
        final_result = None
        for chunk in tool_stream(tool_input):
            for node_name, update in chunk.items():
                for msg in update.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            step_log.append(f"도구 호출: `{tc['name']}({tc['args']})`")
                    elif msg.type == "tool":
                        step_log.append(f"도구 결과: {msg.content[:100]}")
                    elif msg.type == "ai" and msg.content:
                        final_result = msg.content
                with progress.container():
                    for log in step_log:
                        st.markdown(log)
        if final_result:
            st.markdown(f"**답변:** {final_result}")

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_tool.py").read_text(), language="python")


def _tab_cycle():
    from examples.graph_cycle import run_stream as cycle_stream, get_mermaid as cycle_mermaid

    st.markdown("### 순환 루프")
    render_mermaid(cycle_mermaid())

    cycle_input = st.text_input("글 주제", key="cycle_input")
    max_iter = st.slider("최대 반복", 1, 5, 3, key="cycle_max")
    if st.button("자기 개선 실행", key="cycle_run") and cycle_input:
        progress = st.empty()
        items = []
        for chunk in cycle_stream(cycle_input, max_iter):
            for node_name, update in chunk.items():
                if node_name == "write":
                    items.append(("write", f"작성 #{update.get('iteration', 0)}"))
                elif node_name == "review":
                    score = update.get("quality_score", 0)
                    items.append(("review", f"검증: {score}점"))
                with progress.container():
                    for t, s in items:
                        (st.success if "검증" in s and int(s.split(":")[-1].replace("점","").strip()) >= 8 else st.info)(s)

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_cycle.py").read_text(), language="python")


def _tab_error():
    from examples.graph_error import run_stream as error_stream, get_mermaid as error_mermaid

    st.markdown("### 에러 처리")
    render_mermaid(error_mermaid())

    error_input = st.text_input("분석할 텍스트", key="error_input")
    error_retries = st.slider("최대 재시도", 1, 5, 3, key="error_retries")
    if st.button("실행", key="error_run") and error_input:
        progress = st.empty()
        step_log = []
        for chunk in error_stream(error_input, error_retries):
            for node_name, update in chunk.items():
                steps = update.get("steps", [])
                if steps:
                    step_log.append((node_name, steps[-1]))
                with progress.container():
                    for n, s in step_log:
                        if "실패" in s:
                            st.error(f"`{n}` → {s}")
                        elif "Fallback" in s:
                            st.warning(f"`{n}` → {s}")
                        else:
                            st.success(f"`{n}` → {s}")

    with st.expander("전체 코드"):
        st.code((_EXAMPLES_DIR / "graph_error.py").read_text(), language="python")
