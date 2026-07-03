"""
KS C 3011 조도 계산기 & 등기구 배치 시각화 — Streamlit 앱
실행: streamlit run app.py
"""
from __future__ import annotations
import io
import math
import json
from typing import List, Optional

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# streamlit-drawable-canvas
try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

from calculator import (
    KS_LUX, ROOM_TYPES, RoomSpec, LightingResult,
    calculate_fixtures, build_summary_row,
)
from visualizer import draw_overlay, draw_grid_lines, image_to_bytes

# ── 페이지 설정 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="조도 계산기 — KS C 3011",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    .stMetric label  { font-size: 0.78rem; color: #888; }
    .room-card       { background:#1e1e2e; border-radius:8px; padding:12px;
                       border-left:4px solid #7c5cbf; margin-bottom:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "rooms": [],          # List[dict] — 방 사양 (직렬화 가능)
        "results": [],        # List[LightingResult]
        "overlay_img": None,  # PIL Image
        "base_image": None,   # PIL Image (업로드 원본)
        "canvas_key": 0,      # 캔버스 강제 재렌더 트리거
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── 헬퍼 ───────────────────────────────────────────────────────────────────

def _rebuild_results():
    """세션에 저장된 방 목록으로 계산 결과 재생성"""
    results: List[LightingResult] = []
    for r in st.session_state["rooms"]:
        spec = RoomSpec(**r)
        results.append(calculate_fixtures(spec))
    st.session_state["results"] = results

    if st.session_state["base_image"] is not None:
        img = st.session_state["base_image"].copy()
        overlay = draw_overlay(img, results)
        st.session_state["overlay_img"] = overlay
    else:
        st.session_state["overlay_img"] = None


def _add_room(room_dict: dict):
    st.session_state["rooms"].append(room_dict)
    _rebuild_results()


def _delete_room(idx: int):
    st.session_state["rooms"].pop(idx)
    _rebuild_results()


def _parse_canvas_rects(canvas_data) -> list[dict]:
    """st_canvas 결과에서 사각형 객체 목록 추출"""
    if canvas_data is None or canvas_data.json_data is None:
        return []
    objects = canvas_data.json_data.get("objects", [])
    rects = []
    for obj in objects:
        if obj.get("type") == "rect":
            rects.append({
                "left":   int(obj.get("left",   0)),
                "top":    int(obj.get("top",    0)),
                "width":  int(obj.get("width",  0)),
                "height": int(obj.get("height", 0)),
            })
    return rects

# ── 사이드바 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💡 KS C 3011 조도 계산기")
    st.caption("평면도 업로드 → 방 영역 지정 → 계산")

    st.divider()

    # 파일 업로드
    uploaded = st.file_uploader(
        "평면도 이미지 업로드",
        type=["png", "jpg", "jpeg"],
        help="PNG / JPG 형식 지원. PDF는 이미지로 변환 후 업로드하세요.",
    )
    if uploaded:
        img_pil = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
        st.session_state["base_image"] = img_pil
        _rebuild_results()
        st.success(f"이미지 로드: {img_pil.width}×{img_pil.height} px")

    st.divider()
    st.subheader("전역 기본값")
    default_uf = st.slider("조명률 UF", 0.3, 1.0, 0.6, 0.05)
    default_mf = st.slider("보수율 MF", 0.5, 1.0, 0.8, 0.05)
    default_ceiling = st.number_input("천장고 기본값 (m)", 2.0, 5.0, 2.4, 0.1)

    st.divider()
    show_grid = st.checkbox("격자선 표시", value=False)
    show_labels = st.checkbox("등기구 번호 표시", value=True)

    st.divider()
    if st.button("전체 초기화", type="secondary"):
        st.session_state["rooms"] = []
        st.session_state["results"] = []
        st.session_state["overlay_img"] = None
        st.session_state["canvas_key"] += 1
        st.rerun()

# ── 메인 레이아웃 ────────────────────────────────────────────────────────────
col_canvas, col_form = st.columns([3, 2], gap="large")

# ─ 왼쪽: 평면도 + 캔버스 ─────────────────────────────────────────────────────
with col_canvas:
    st.subheader("평면도")

    base_img = st.session_state["base_image"]

    if base_img is None:
        st.info("사이드바에서 평면도 이미지를 업로드하세요.")
        # 샘플 placeholder 이미지 생성
        placeholder = Image.new("RGB", (800, 600), (240, 240, 240))
        base_img = placeholder

    # 캔버스 표시 크기 (화면 맞춤)
    MAX_DISPLAY_W = 780
    scale = min(MAX_DISPLAY_W / base_img.width, 1.0)
    disp_w = int(base_img.width * scale)
    disp_h = int(base_img.height * scale)

    # 결과 오버레이 이미지 (있으면 캔버스 배경으로)
    bg_image = (
        st.session_state["overlay_img"]
        if st.session_state["overlay_img"] is not None
        else base_img
    )
    if show_grid and st.session_state["results"]:
        bg_image = draw_grid_lines(bg_image, st.session_state["results"])

    tab_canvas, tab_result = st.tabs(["방 영역 그리기", "결과 이미지"])

    with tab_canvas:
        if CANVAS_AVAILABLE:
            st.caption("사각형 도구로 방 영역을 드래그하여 선택하세요.")
            canvas_result = st_canvas(
                fill_color="rgba(124, 92, 191, 0.15)",
                stroke_width=2,
                stroke_color="#7c5cbf",
                background_image=bg_image.resize((disp_w, disp_h)),
                update_streamlit=True,
                height=disp_h,
                width=disp_w,
                drawing_mode="rect",
                key=f"canvas_{st.session_state['canvas_key']}",
            )
            rects = _parse_canvas_rects(canvas_result)
            if rects:
                st.session_state["_pending_rects"] = rects
                st.caption(
                    f"선택된 사각형: {len(rects)}개 "
                    f"— 오른쪽에서 방 정보를 입력하고 '방 추가' 버튼을 누르세요."
                )
        else:
            st.info("평면도를 참고하여 오른쪽에서 방 위치(픽셀 좌표)를 직접 입력하세요.")
            st.image(bg_image.resize((disp_w, disp_h)), use_container_width=True)

    with tab_result:
        if st.session_state["overlay_img"] is not None:
            out_img = st.session_state["overlay_img"]
            if show_grid:
                out_img = draw_grid_lines(out_img, st.session_state["results"])
            st.image(out_img.resize((disp_w, disp_h)), use_container_width=True)

            dl_bytes = image_to_bytes(out_img)
            st.download_button(
                label="등기구 배치도 다운로드 (PNG)",
                data=dl_bytes,
                file_name="lighting_plan.png",
                mime="image/png",
            )
        else:
            st.info("방을 추가하면 배치 결과가 여기에 표시됩니다.")

# ─ 오른쪽: 방 추가 폼 ─────────────────────────────────────────────────────
with col_form:
    st.subheader("방 추가")

    pending_rects = st.session_state.get("_pending_rects", [])
    rect_idx = 0
    if pending_rects and len(pending_rects) > 0:
        rect_idx = st.selectbox(
            "캔버스에서 선택한 사각형",
            options=list(range(len(pending_rects))),
            format_func=lambda i: (
                f"사각형 {i+1}: "
                f"({pending_rects[i]['left']}, {pending_rects[i]['top']}) "
                f"{pending_rects[i]['width']}×{pending_rects[i]['height']} px"
            ),
        )

    with st.form("add_room_form", clear_on_submit=True):
        room_name  = st.text_input("방 이름", placeholder="예: 안방, 거실1")
        room_type  = st.selectbox("방 용도", ROOM_TYPES)
        lux_info   = KS_LUX[ROOM_TYPES[0]]
        st.caption(f"KS C 3011 권장 조도: **{KS_LUX[room_type]} lux**")

        c1, c2 = st.columns(2)
        with c1:
            width_m  = st.number_input("가로 (m)", 1.0, 50.0, 4.0, 0.1)
        with c2:
            height_m = st.number_input("세로 (m)", 1.0, 50.0, 3.0, 0.1)

        ceiling_h = st.number_input("천장고 (m)", 2.0, 5.0, default_ceiling, 0.1)

        fixture_name = st.text_input("등기구 종류", value="LED 다운라이트 18W")
        lumen = st.number_input(
            "광속 (lm)",
            min_value=100.0,
            max_value=50000.0,
            value=1600.0,
            step=100.0,
            help="예: LED 18W ≈ 1600lm, LED 24W ≈ 2400lm, 형광등 36W ≈ 3000lm",
        )

        with st.expander("고급 설정"):
            uf = st.slider("조명률 UF", 0.3, 1.0, default_uf, 0.05)
            mf = st.slider("보수율 MF", 0.5, 1.0, default_mf, 0.05)

        st.caption("이미지 위 방 위치 (픽셀 좌표)")
        px_col1, px_col2 = st.columns(2)
        with px_col1:
            # 캔버스 선택값 자동 채움
            pr = pending_rects[rect_idx] if pending_rects else {}
            # scale 역변환 (캔버스 표시 → 원본 픽셀)
            _scale = scale if "scale" in dir() else 1.0
            px_x = st.number_input(
                "X (px)", 0, 9999,
                int(pr.get("left",   0) / _scale) if pr else 0,
            )
            px_w = st.number_input(
                "폭 (px)", 1, 9999,
                int(pr.get("width",  100) / _scale) if pr else 100,
            )
        with px_col2:
            px_y = st.number_input(
                "Y (px)", 0, 9999,
                int(pr.get("top",    0) / _scale) if pr else 0,
            )
            px_h = st.number_input(
                "높이 (px)", 1, 9999,
                int(pr.get("height", 100) / _scale) if pr else 100,
            )

        submitted = st.form_submit_button("방 추가 ➕", type="primary")

        if submitted:
            if not room_name.strip():
                st.error("방 이름을 입력하세요.")
            elif width_m <= 0 or height_m <= 0:
                st.error("가로/세로 크기를 올바르게 입력하세요.")
            elif lumen <= 0:
                st.error("광속(lm) 값을 입력하세요.")
            else:
                room_dict = dict(
                    name=room_name.strip(),
                    room_type=room_type,
                    width_m=width_m,
                    height_m=height_m,
                    ceiling_h=ceiling_h,
                    lumen=lumen,
                    uf=uf,
                    mf=mf,
                    fixture_name=fixture_name,
                    px_x=px_x,
                    px_y=px_y,
                    px_w=px_w,
                    px_h=px_h,
                )
                _add_room(room_dict)
                st.success(f"'{room_name}' 방이 추가되었습니다.")
                st.rerun()

    # ── 등록된 방 목록 ────────────────────────────────────────────────────
    st.subheader("등록된 방")
    rooms = st.session_state["rooms"]
    results = st.session_state["results"]

    if not rooms:
        st.info("아직 추가된 방이 없습니다.")
    else:
        for i, (room, result) in enumerate(zip(rooms, results)):
            with st.container():
                st.markdown(
                    f"""<div class="room-card">
                    <b>{room['name']}</b> — {room['room_type']} &nbsp;|&nbsp;
                    {room['width_m']}m × {room['height_m']}m &nbsp;|&nbsp;
                    목표 {result.spec.target_lux} lux → 달성 {result.achieved_lux} lux &nbsp;|&nbsp;
                    등기구 {result.n_fixtures}개 ({result.grid_rows}×{result.grid_cols})
                    </div>""",
                    unsafe_allow_html=True,
                )
                if st.button(f"삭제", key=f"del_{i}"):
                    _delete_room(i)
                    st.rerun()

# ── 결과 요약 테이블 ─────────────────────────────────────────────────────────
st.divider()
st.subheader("결과 요약")

results = st.session_state["results"]
if not results:
    st.info("방을 추가하면 결과 테이블이 표시됩니다.")
else:
    rows = [build_summary_row(r) for r in results]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 집계
    total_fixtures = sum(r.n_fixtures for r in results)
    total_area     = sum(r.spec.area for r in results)
    avg_lux        = (
        sum(r.achieved_lux * r.spec.area for r in results) / total_area
        if total_area > 0 else 0
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("총 등기구 수", f"{total_fixtures} 개")
    m2.metric("총 방 면적", f"{total_area:.1f} m²")
    m3.metric("면적 가중 평균 조도", f"{avg_lux:.0f} lux")

    # CSV 다운로드
    csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "결과 CSV 다운로드",
        data=csv_bytes,
        file_name="lighting_result.csv",
        mime="text/csv",
    )

# ── 공식 참고 ────────────────────────────────────────────────────────────────
with st.expander("계산 공식 및 KS C 3011 기준"):
    st.markdown(
        """
        ### 조도 계산 공식 (광속법)

        $$N = \\frac{E \\times A}{F \\times UF \\times MF}$$

        | 기호 | 의미 | 비고 |
        |------|------|------|
        | N    | 필요 등기구 수 | 소수점 올림 |
        | E    | 목표 조도 (lux) | KS C 3011 |
        | A    | 방 면적 (m²) | 가로 × 세로 |
        | F    | 등기구 광속 (lm) | 카탈로그 참조 |
        | UF   | 조명률 | 기본 0.6 |
        | MF   | 보수율 | 기본 0.8 |

        ### KS C 3011 권장 조도 (주거/사무 공간)

        | 공간 | 권장 조도 (lux) |
        |------|----------------|
        | 거실 | 200 |
        | 침실 | 150 |
        | 주방 | 300 |
        | 욕실 | 200 |
        | 복도 | 100 |
        | 사무실 | 500 |
        | 서재 | 400 |

        ### 등기구 간격 기준

        - 최대 간격 = **1.5 × 작업면 높이 H**
        - 작업면 높이 H = 천장고 − 0.85 m (책상/바닥 기준)
        - 벽으로부터 첫 등기구: 간격의 0.5배 권장
        """
    )
