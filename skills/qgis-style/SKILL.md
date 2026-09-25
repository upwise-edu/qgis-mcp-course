---
name: qgis-style
description: 강의 표준 스타일을 레이어에 입힌다. "스타일 적용" · "심볼 통일" · "범례 정리" · "색 맞춰줘" · "범주별로 색칠" 일 때 쓴다. 동봉한 표준 QML 을 골라 apply_style_qml 로 적용한다. 새 심볼을 즉석에서 만들지 않는다.
license: CC-BY-4.0
compatibility: QGIS 3.44 LTR + QGIS MCP 플러그인 0.14.0 기준. MCP 도구만으로 성립한다. 추가 프로그램은 필요 없다.
---

## 출력 규칙

- 이 스킬로 답할 때 **첫 줄에 `[qgis-style 1.0.0]` 을 쓴다.** 예외 없다.
- 적용한 레이어 이름과 고른 QML 파일명을 반드시 함께 적는다.

## 이 스킬이 하는 일

강의 도면의 색과 심볼을 한 벌로 맞춘다.
이 `SKILL.md` 와 같은 폴더의 `assets/` 에 표준 스타일 24개가 들어 있다.
QML 21개와 치환 템플릿 3개다.

**즉석에서 새 심볼을 만들지 않는다.** 표준에서 고르는 것이 이 스킬의 일이다.
표준에 없는 표현이 필요하면 그 사실을 알리고 사람에게 묻는다.

## 자산 목록 — `assets/`

### 면 (폴리곤) · 6개

| 파일 | 쓰임 |
|---|---|
| `bg_sigungu_outline.qml` | 배경 시군구 경계. 면은 비우고 외곽선만 |
| `emphasis_outline_red.qml` | 강조 대상 외곽선. 빨강 |
| `fill_blue_soft.qml` | 연한 파랑 채움 |
| `fill_gray.qml` | 회색 채움. 중립 배경 |
| `fill_green.qml` | 초록 채움 |
| `fill_orange_soft.qml` | 연한 주황 채움 |

### 선 · 5개

| 파일 | 쓰임 |
|---|---|
| `line_contour_brown.qml` | 등고선 |
| `line_net_gray.qml` | 격자 · 망 |
| `line_road_navy.qml` | 도로 |
| `line_route_red.qml` | 경로 · 최단거리 결과 |
| `line_stream_blue.qml` | 하천 |

### 점 · 4개

| 파일 | 쓰임 |
|---|---|
| `point_apt_navy.qml` | 아파트 · 건물 점 |
| `point_center_red.qml` | 중심점 · 시설 |
| `point_node_teal.qml` | 네트워크 노드 |
| `point_store.qml` | 상가 점포 |

### 등급 · 범주 · 6개

`_raw` 는 경계선을 그린 판이고 `_noborder` 는 경계선을 없앤 판이다.
칸이 잘게 나뉜 레이어는 `_noborder` 가 읽기 좋다.

| 파일 | 대상 필드 | 렌더러 |
|---|---|---|
| `p5_elev_zones_raw.qml` · `p5_elev_zones_noborder.qml` | `elev_cls` | 등급 5구간 |
| `p5_zone_slope_raw.qml` · `p5_zone_slope_noborder.qml` | `slp_mean` | 등급 5구간 |
| `p9_urban_year_poly_raw.qml` · `p9_urban_year_poly_noborder.qml` | `DN` | 범주 5개 (`0` · `1980` · `1990` · `2000` · `2010`) |

**이 6개는 필드 이름에 묶여 있다.** 레이어에 그 필드가 없으면 심볼이 전부 회색으로 떨어지거나
범례가 비어서 나온다. 적용 전에 `get_layer_features` 로 필드 이름을 확인한다.
이름이 다르면 필드를 개명하거나, 아래 "표준에 없는 표현이 필요할 때" 로 간다.

### 치환 템플릿 · 3개 — QML 이 아니다

| 파일 | 자리표시자 |
|---|---|
| `fill_solid.qml.tmpl` | `__FILL__` · `__LINE__` · `__LINEW__` · `__LINESTYLE__` · `__ALPHA__` |
| `line_solid.qml.tmpl` | `__COLOR__` · `__WIDTH__` · `__ALPHA__` |
| `point_dot.qml.tmpl` | `__COLOR__` · `__SIZE__` · `__LINE__` · `__LINEW__` · `__ALPHA__` |

> **경고. 이 세 파일을 `apply_style_qml` 에 그대로 넘기면 안 된다.**
> 확장자가 `.qml.tmpl` 인 이유가 그것이다. 안에 `__FILL__` 같은 자리표시자가 그대로 들어 있어
> QGIS 가 색을 읽지 못한다. 실패하거나 엉뚱한 색이 나온다.
>
> 쓰는 순서는 이렇다. 템플릿을 읽어 자리표시자를 값으로 바꾼다. 그 결과를 `.qml` 파일로 저장한다.
> 저장한 `.qml` 의 절대경로를 `apply_style_qml` 에 넘긴다.
> 색은 `255,0,0,255` 같은 RGBA 문자열, 굵기와 크기는 밀리미터 수치, `__ALPHA__` 는 0~1 실수다.

## 절차

### 1. 대상 확인

`get_layers` 로 레이어 목록을 받아 대상 레이어의 정확한 이름을 잡는다.
이름이 애매하면 `find_layer` 로 좁힌다. 추측한 이름으로 적용하지 않는다.

지오메트리 종류를 확인한다. 면 스타일을 선 레이어에 넣으면 아무 일도 일어나지 않는다.

### 2. 고르기

| 용도 | 고르는 것 |
|---|---|
| 배경 경계 | `bg_sigungu_outline.qml` |
| 결과 강조 | `emphasis_outline_red.qml` |
| 단색 면 | `fill_*` 4종 중 하나 |
| 선형 자료 | `line_*` 5종 중 용도에 맞는 것 |
| 점 자료 | `point_*` 4종 중 용도에 맞는 것 |
| 등급 · 범주 | `p5_*` · `p9_*` 중 필드가 맞는 것 |

여러 레이어를 한 화면에 얹을 때는 배경을 `fill_gray` 나 `bg_sigungu_outline` 으로 두고
강조 대상만 색을 준다. 모든 레이어에 색을 주면 무엇이 결과인지 안 보인다.

### 3. 적용

`apply_style_qml` 에 레이어 이름과 QML **절대경로**를 넘긴다.
경로는 이 스킬이 설치된 폴더 아래 `assets/<파일명>` 이다.
플러그인 설치 위치는 환경마다 다르므로, 먼저 `assets/` 의 실제 절대경로를 확인한 뒤 넘긴다.

적용 뒤 확인한다.

- `get_layers` 또는 `get_layer_tree` 로 레이어가 살아 있는지 본다.
- `render_map` 이나 `get_canvas_screenshot` 으로 실제 화면을 본다.
  등급 · 범주 스타일은 색 구간 수가 범례에 그대로 나와야 한다.

### 4. 보고

```
[qgis-style 1.0.0]
레이어: <이름>
적용 QML: <파일명>
확인: <범례 구간 수 또는 렌더 결과에서 관측한 것>
```

## 표준에 없는 표현이 필요할 때

1. **템플릿으로 되는가.** 단색 면 · 선 · 점이면 위 치환 템플릿으로 만든다.
2. **등급 · 범주인데 필드가 다른가.** `set_layer_style` 로 `categorized` 또는 `graduated` 를 직접 지정한다.
   색은 표준 스타일에서 쓰는 색을 그대로 가져와 맞춘다.
3. **둘 다 아닌가.** 만들지 말고 사람에게 묻는다. 무엇이 필요한지, 왜 표준으로 안 되는지 적어서 묻는다.

새로 만든 스타일이 강의에서 계속 쓸 만하면 `save_style_qml` 로 QML 을 내보내고,
그 파일을 표준 자산에 추가할지 사람에게 제안한다. 스킬이 자산을 임의로 늘리지 않는다.

## 하지 않는 것

- `.qml.tmpl` 을 그대로 적용하지 않는다.
- 표준 QML 파일을 고치지 않는다. 고치면 다른 도면과 색이 어긋난다.
- 필드 이름을 확인하지 않고 등급 · 범주 스타일을 적용하지 않는다.
- 적용 결과를 보지 않고 "스타일을 입혔다" 고 보고하지 않는다.
