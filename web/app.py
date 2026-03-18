"""Auto-Pipe — 메인 웹 UI"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Auto-Pipe",
    page_icon="",
    layout="wide",
)

# ─── 사이드바 네비게이션 ───
with st.sidebar:
    st.title("Auto-Pipe")
    st.caption("개발 자동화 파이프라인")
    st.markdown("---")

    page = st.radio(
        "메뉴",
        ["Bootstrap", "Pipeline", "LangGraph 예제"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # 프로젝트 상태 요약
    projects_dir = _ROOT / "projects"
    if projects_dir.exists():
        configured = [d.name for d in projects_dir.iterdir()
                      if d.is_dir() and d.name != ".gitkeep"
                      and (d / "pipeline.yaml").exists()]
        if configured:
            st.markdown("**설정된 프로젝트**")
            for name in configured:
                st.caption(f"  {name}")

# ─── 페이지 렌더링 ───
if page == "Bootstrap":
    from web.pages.bootstrap import render
    render()

elif page == "Pipeline":
    from web.pages.pipeline import render
    render()

elif page == "LangGraph 예제":
    from web.pages.examples import render
    render()
