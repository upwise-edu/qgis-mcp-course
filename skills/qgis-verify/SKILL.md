---
name: qgis-verify
description: MCP 분석 결과를 QGIS GUI 재실행값과 대조한다. "검증해줘" · "수동 검증" · "대조표 채워줘" · "결과 맞는지 확인" 일 때 쓴다. 04.verify/verify_pN.csv 의 지표를 다시 재고 판정을 채운다. 전처리 감사는 qgis-preprocess 가 한다.
license: CC-BY-4.0
compatibility: QGIS 3.44 LTR + QGIS MCP 플러그인 0.14.0 기준. MCP 도구만으로 성립한다. 동봉 대조 스크립트를 쓰려면 Python 3 와 geopandas · rasterio · numpy · pandas 가 필요하다.
---

## 출력 규칙

- 이 스킬로 답할 때 **첫 줄에 `[qgis-verify 1.0.1]` 을 쓴다.** 예외 없다.
- 지표마다 잰 값을 그대로 적는다. "맞습니다" 같은 말로 값을 대신하지 않는다.

## 이 스킬이 하는 일

`02.analysis` · `03.outputs` 에 나온 수치가 맞는지 다시 잰다.
대상은 `04.verify/verify_pN.csv` 의 각 행이다. 이 표가 프로젝트의 대조표다.

**전처리 결과는 여기서 보지 않는다.** 그것은 `qgis-preprocess` 의 9항목이 본다.
대상 폴더가 다르다. 전처리는 `01.preprocess`, 검증은 `04.verify` 다.

## 대조표 구조 — `04.verify/verify_pN.csv`

```
metric,label,mcp_value,manual_value,diff,tolerance,verdict,note
```

| 컬럼 | 내용 |
|---|---|
| `metric` | 기계 식별자. 예 `p1_candidate_count` |
| `label` | 사람이 읽는 지표명 |
| `mcp_value` | **MCP 로 낸 값.** 이 스킬이 채운다 |
| `manual_value` | QGIS GUI 에서 사람이 직접 재서 넣는 값 |
| `diff` | `mcp_value` 와 `manual_value` 의 차 |
| `tolerance` | 허용 오차 |
| `verdict` | `PASS` / `FAIL` / `NA` |
| `note` | 근거. 어떤 도구로 어떻게 쟀는지 |

`manual_value` 는 **사람 몫이다.** 값이 비어 있으면 비워 두고 `verdict` 를 `NA` 로 남긴다.
비어 있는 칸을 추정값으로 채우지 않는다. 그 순간 대조가 대조가 아니게 된다.

## 절차

### 1. 연결과 대상 확인

qgis MCP 서버의 `ping` 으로 연결을 확인한다. 실패하면 멈추고 알린다.
프로젝트 번호를 받았으면 `C:\qgis_mcp_class\projNN_*\04.verify\verify_pN.csv` 를 읽는다.
파일이 없으면 만들지 말고, 없다는 사실과 만드는 방법(아래 "대조표가 없을 때")을 알린다.

### 2. 지표마다 다시 잰다

행을 위에서부터 하나씩 본다. `metric` 과 `label` 을 보고 무엇을 재는지 정한 뒤, 아래 도구로 재계산한다.

| 재는 것 | 쓰는 도구 |
|---|---|
| 피처 건수 | `get_layer_features` 또는 `get_field_statistics` |
| 합계 · 평균 · 최대 · 최소 | `get_field_statistics` |
| 면적 · 길이 | `evaluate_expression` 으로 `sum($area)` · `sum($length)` |
| 조건에 맞는 건수 | `select_features` 뒤 `get_selection` |
| 래스터 셀 통계 | `zonal_statistics` |
| 래스터 해상도 · nodata · 행열 수 | `get_raster_info` |
| 레이어 범위 | `get_layer_extent` |
| 고유값 분포 | `get_unique_values` |
| 좌표계 | `get_layer_crs` |

**단위를 확인한다.** 면적은 m2 인지 km2 인지, 길이는 m 인지 km 인지 `label` 과 `tolerance` 를 보고 맞춘다.
프로젝트 CRS 는 EPSG:5186 이고 단위는 미터다.

### 3. 값을 적는다

- `mcp_value` 에 잰 값을 넣는다. 반올림은 `tolerance` 자릿수까지만 한다.
- `manual_value` 가 이미 있으면 `diff` 를 계산하고 `tolerance` 와 비교해 `verdict` 를 정한다.
- `note` 에 **도구 이름과 인자**를 적는다. `get_field_statistics` 처럼 도구만 적지 말고
  어느 레이어의 어느 필드였는지까지 적는다. 값이 아니라 재현 방법이 근거다.
- 재지 못한 행은 `mcp_value` 를 비우고 `verdict` 를 `NA`, `note` 에 사유를 적는다.
  산출 파일이 없다거나 레이어가 안 열린다거나 하는 사실을 그대로 쓴다.

### 4. 보고

표를 그대로 보여 주고, 아래를 요약한다.

- 전체 행 수 · `PASS` · `FAIL` · `NA` 건수
- `FAIL` 이 있으면 그 행의 `metric` · `mcp_value` · `manual_value` · `diff`
- `manual_value` 가 비어 있어 판정하지 못한 행 수

`FAIL` 을 자동으로 고치지 않는다. 어느 쪽이 틀렸는지는 사람이 정한다.

## 대조표가 없을 때

`04.verify/verify_pN.csv` 는 동봉 스크립트가 만들 수 있다.
이 `SKILL.md` 와 같은 폴더의 `scripts/verify_outputs.py` 를 `--template` 옵션과 함께 실행하면
각 프로젝트의 `04.verify/verify_pN.csv` 를 생성한다.

> **먼저 확인할 것.** 이 스크립트는 프로젝트 폴더 경로를 `C:\qgis_mcp_class\projNN_*` 로 고정해 두었다.
> 실습 폴더가 그 경로가 아니면 `--template` 이 엉뚱한 폴더에 표를 만들거나, 원본 프로젝트 폴더를 덮어쓴다.
> 실습 폴더가 다르면 스크립트를 쓰지 말고 아래처럼 표를 직접 만든다.

스크립트가 없거나 Python 환경이 없으면, 위 컬럼 구조대로 표를 직접 만들고
지표는 그 프로젝트 산출물에서 정한다. 표가 없다고 검증을 건너뛰지 않는다.

## 동봉 스크립트 — 선택이다

이 `SKILL.md` 와 같은 폴더의 `scripts/verify_outputs.py` 는 같은 수치를 **QGIS 밖에서 한 번 더 재는**
대조 수단이다. geopandas · rasterio · numpy · pandas 로 산출 파일을 직접 읽어 재계산한다.

```
python scripts/verify_outputs.py --projects 3 --log C:\qgis_mcp_class\proj03_population\04.verify\verify_script_run.csv
```

| 옵션 | 뜻 |
|---|---|
| `--projects` | 프로젝트 번호. 쉼표로 여럿. 기본은 1~10 전부 |
| `--template` | 재계산에 더해 `04.verify/verify_pN.csv` 를 생성한다 |
| `--log` | 로그 파일 경로. **절대경로로 지정한다** |

**`--log` 를 반드시 준다.** 안 주면 스크립트가 자기 위치를 기준으로 로그 폴더를 잡는데,
스킬 폴더에서 실행하면 그 경로가 실습 폴더 밖이 된다.

**Python 환경이 없으면 이 절을 통째로 건너뛴다.** 위 2단계의 MCP 도구만으로 검증이 성립한다.
스크립트는 같은 값을 다른 경로로 한 번 더 재는 것이지, 검증의 필수 조건이 아니다.

스크립트 값과 MCP 값이 다르면 **둘 다 적는다.** 한쪽을 골라 적지 않는다.
차이 자체가 확인해야 할 사실이다.

## 하지 않는 것

- `manual_value` 를 만들어 넣지 않는다. GUI 재실행값은 사람이 넣는다.
- 산출 파일을 고치지 않는다. 검증은 읽기만 한다.
- `02.analysis` 를 다시 돌리지 않는다. 값이 틀렸다면 그 사실만 보고한다.
- 값을 확인하지 않은 채로 `PASS` 를 적지 않는다.
