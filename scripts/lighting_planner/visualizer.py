"""
등기구 오버레이 시각화 모듈
Pillow + OpenCV-headless 기반
"""
from __future__ import annotations
import math
import io
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from calculator import LightingResult, RoomSpec

# 색상 팔레트 (방 인덱스별)
ROOM_COLORS = [
    (255, 99,  71),   # tomato
    (30,  144, 255),  # dodger blue
    (50,  205, 50),   # lime green
    (255, 165, 0),    # orange
    (138, 43,  226),  # blue violet
    (0,   206, 209),  # dark turquoise
    (220, 20,  60),   # crimson
    (0,   128, 128),  # teal
]

FIXTURE_RADIUS = 8      # 픽셀 단위 등기구 마커 반경
ROOM_ALPHA    = 40      # 방 배경 오버레이 알파 (0–255)


def _get_font(size: int = 14):
    """폰트 로드 (실패 시 기본 폰트)"""
    try:
        return ImageFont.truetype("malgun.ttf", size)   # Windows 맑은 고딕
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


def _room_to_pixel(
    mx: float, my: float,
    spec: RoomSpec,
) -> Tuple[int, int]:
    """
    방 내부 m 좌표 → 이미지 픽셀 좌표
    spec.px_x/y/w/h 는 이미지상 방 bbox (픽셀)
    """
    px = spec.px_x + int((mx / spec.width_m) * spec.px_w)
    py = spec.px_y + int((my / spec.height_m) * spec.px_h)
    return px, py


def draw_overlay(
    base_image: Image.Image,
    results: List[LightingResult],
    show_room_fill: bool = True,
    show_labels: bool = True,
) -> Image.Image:
    """
    평면도 이미지 위에 등기구 위치와 방 영역을 오버레이.

    Parameters
    ----------
    base_image   : PIL Image (RGB)
    results      : 방별 계산 결과 목록
    show_room_fill : 방 영역 반투명 색상 채우기 여부
    show_labels  : 등기구 번호 레이블 표시 여부

    Returns
    -------
    PIL Image (RGB) — 오버레이 완료 이미지
    """
    img = base_image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_label = _get_font(11)
    font_room  = _get_font(13)

    for idx, result in enumerate(results):
        spec  = result.spec
        color = ROOM_COLORS[idx % len(ROOM_COLORS)]
        r, g, b = color

        x0, y0 = spec.px_x, spec.px_y
        x1, y1 = spec.px_x + spec.px_w, spec.px_y + spec.px_h

        # --- 방 영역 반투명 채우기 ---
        if show_room_fill:
            draw.rectangle(
                [x0, y0, x1, y1],
                fill=(r, g, b, ROOM_ALPHA),
                outline=(r, g, b, 200),
                width=2,
            )

        # --- 방 이름 레이블 ---
        room_label = f"{spec.name} ({spec.room_type})"
        draw.text(
            (x0 + 4, y0 + 4),
            room_label,
            font=font_room,
            fill=(r, g, b, 230),
        )

        # --- 등기구 마커 ---
        for fix_idx, (mx, my) in enumerate(result.fixture_positions):
            px, py = _room_to_pixel(mx, my, spec)
            # 외곽 원 (흰색)
            draw.ellipse(
                [px - FIXTURE_RADIUS - 1, py - FIXTURE_RADIUS - 1,
                 px + FIXTURE_RADIUS + 1, py + FIXTURE_RADIUS + 1],
                fill=(255, 255, 255, 220),
            )
            # 내부 원 (방 색상)
            draw.ellipse(
                [px - FIXTURE_RADIUS, py - FIXTURE_RADIUS,
                 px + FIXTURE_RADIUS, py + FIXTURE_RADIUS],
                fill=(r, g, b, 220),
            )
            # 번호 레이블
            if show_labels:
                label = str(fix_idx + 1)
                # 텍스트 크기 측정
                try:
                    bbox = font_label.getbbox(label)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                except AttributeError:
                    tw, th = 8, 10
                draw.text(
                    (px - tw // 2, py - th // 2),
                    label,
                    font=font_label,
                    fill=(255, 255, 255, 255),
                )

    # 합성
    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    """PIL Image → bytes (다운로드용)"""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def pil_to_numpy(img: Image.Image) -> np.ndarray:
    """PIL → numpy array (OpenCV BGR)"""
    import cv2
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def draw_grid_lines(
    base_image: Image.Image,
    results: List[LightingResult],
) -> Image.Image:
    """
    등기구 배치 격자 선을 추가로 오버레이 (디버그/상세 보기용).
    """
    img = base_image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for idx, result in enumerate(results):
        spec  = result.spec
        color = ROOM_COLORS[idx % len(ROOM_COLORS)]
        r, g, b = color

        cols = result.grid_cols
        rows = result.grid_rows

        # 수직선
        for c in range(1, cols):
            x_m = result.spacing_x * c
            px, _ = _room_to_pixel(x_m, 0, spec)
            draw.line(
                [(px, spec.px_y), (px, spec.px_y + spec.px_h)],
                fill=(r, g, b, 80),
                width=1,
            )
        # 수평선
        for ro in range(1, rows):
            y_m = result.spacing_y * ro
            _, py = _room_to_pixel(0, y_m, spec)
            draw.line(
                [(spec.px_x, py), (spec.px_x + spec.px_w, py)],
                fill=(r, g, b, 80),
                width=1,
            )

    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")
