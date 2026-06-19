---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: knowledge-candidate
tags:
- '#area/ai_automation'
- '#status/active'
summary: LibreDWG 오픈소스 DWG 변환 API — 라이선스 제약, CAD 견적 파이프라인 통합, Autodesk APS 비교
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# LibreDWG Conversion API MVP

## 개요

LibreDWG는 DWG 파일 형식의 **무료 오픈소스 읽기/쓰기/변환 라이브러리**다. GNU GPLv3 라이선스 기반으로 상업적 사용에 제약이 있으나, 내부 도구나 서버 사이드 파이프라인에 활용 가능하다.

## 라이선스 제약 (중요)

| 항목 | 내용 |
|------|------|
| 라이선스 | GNU LGPLv3 (라이브러리 기준) |
| 상업 배포 | LGPL 조건 충족 시 가능 |
| SaaS 제공 | 소스 공개 의무 없음 (서버 사이드) |
| 클라이언트 배포 | 라이브러리 소스 링크 제공 필요 |

**결론**: JH 서버 사이드 파이프라인 (CAD → 견적)에 사용 가능. 클라이언트 앱 번들링 시 법무 검토 필요.

## 주요 기능

- DWG R2.6 ~ R2025 버전 지원
- DXF 변환 (DWG → DXF 가장 안정적)
- JSON 출력 (도면 객체 구조 추출)
- SVG 렌더링 (미리보기 생성)
- Python, Node.js 바인딩 지원

## 설치

```bash
# Ubuntu/Debian
sudo apt-get install libredwg-dev

# Python 바인딩
pip install libredwg

# macOS
brew install libredwg
```

## 기본 사용 (Python)

```python
import libredwg

def extract_dwg_data(dwg_path: str) -> dict:
    """DWG 파일에서 도면 정보 추출"""
    dwg = libredwg.DWG(dwg_path)
    
    layers = dwg.layers()
    entities = dwg.entities()
    
    return {
        "version": dwg.version,
        "layers": [l.name for l in layers],
        "entity_count": len(entities),
        "dimensions": extract_dimensions(entities)
    }

def dwg_to_dxf(input_path: str, output_path: str) -> bool:
    """DWG → DXF 변환"""
    dwg = libredwg.DWG(input_path)
    dwg.export_dxf(output_path)
    return True
```

## CAD → 견적 파이프라인 통합

```
DWG 파일 업로드
    ↓ LibreDWG 파싱
도면 요소 추출 (치수, 레이어, 면적)
    ↓ 견적 엔진
공종별 물량 산출
    ↓ JH 견적 시스템
최종 견적서 생성
```

### 면적 자동 추출 예시

```python
def extract_area_from_dwg(dwg_path: str) -> dict:
    """도면에서 공간별 면적 추출"""
    dwg = libredwg.DWG(dwg_path)
    areas = {}
    
    for entity in dwg.entities():
        if entity.type == "LWPOLYLINE" and entity.layer:
            area = entity.area()  # 제곱미터
            layer_name = entity.layer
            areas[layer_name] = areas.get(layer_name, 0) + area
    
    return areas
```

## Autodesk APS 비교

| 항목 | LibreDWG | Autodesk APS (Forge) |
|------|----------|---------------------|
| 비용 | 무료 | $0.01/변환 + 구독료 |
| 정확도 | 중간 | 최고 (공식) |
| 지원 버전 | R2.6~R2025 | 전 버전 |
| 설치 | 자체 서버 | 클라우드 API |
| SaaS 제약 | 없음 | 없음 |
| 3D 지원 | 제한적 | 완전 지원 |

**권장**: 
- 내부 견적 도구 → LibreDWG (비용 절감)
- 고객 대면 서비스 → Autodesk APS (정확도)

## 다음 단계

- [ ] `jh-estimate` 스킬과 LibreDWG 파이프라인 연동 검토
- [ ] DWG 샘플 파일로 면적 추출 정확도 테스트
- [ ] 견적 엔진 통합 POC 개발

## 참고

- GitHub: https://github.com/LibreDWG/libredwg
- 관련 스킬: `jh-estimate`
