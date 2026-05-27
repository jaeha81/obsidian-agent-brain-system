# KS C 3011 조도 계산기 & 등기구 배치 시각화

평면도 이미지를 업로드하면 KS C 3011 기준 조도(lux)를 계산하고
등기구 배치를 시각화해주는 Streamlit 웹앱.

## 빠른 시작

```bash
cd scripts/lighting_planner

# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속.

## 사용 방법

1. **평면도 업로드** — 사이드바에서 PNG/JPG 이미지 선택
2. **방 영역 그리기** — '방 영역 그리기' 탭에서 사각형 도구로 드래그
3. **방 정보 입력** — 오른쪽 폼에서 방 용도·크기·등기구 정보 입력
4. **방 추가 클릭** — 계산 결과가 즉시 반영됨
5. **결과 확인** — '결과 이미지' 탭 또는 하단 요약 테이블 확인
6. **다운로드** — PNG(배치도) 또는 CSV(결과표) 저장

## 파일 구조

```
lighting_planner/
├── app.py            # Streamlit 메인 앱
├── calculator.py     # 조도 계산 로직 (KS C 3011)
├── visualizer.py     # 이미지 오버레이 로직 (Pillow)
├── requirements.txt  # 패키지 의존성
└── README.md         # 이 파일
```

## 계산 공식

```
N = (E × A) / (F × UF × MF)

N  : 필요 등기구 수 (소수점 올림)
E  : 목표 조도 [lux] — KS C 3011
A  : 방 면적 [m²]
F  : 등기구 광속 [lm]
UF : 조명률 (기본 0.6)
MF : 보수율 (기본 0.8)
```

## KS C 3011 권장 조도

| 공간 | 조도 (lux) |
|------|-----------|
| 거실 | 200 |
| 침실 | 150 |
| 주방 | 300 |
| 욕실 | 200 |
| 복도 | 100 |
| 사무실 | 500 |
| 서재 | 400 |

## 참고

- `streamlit-drawable-canvas` 미설치 시 캔버스 없이 픽셀 좌표 직접 입력 모드로 동작
- PDF 평면도는 이미지로 변환 후 업로드 (권장: 150~300dpi PNG)
