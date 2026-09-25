---
name: qgis-preprocess
description: 00.origins 의 원본을 01.preprocess 표준 입력으로 만든다. "전처리해줘" · "표준 입력 만들어줘" · "5186 으로 통일해줘" 일 때 쓴다. 검증 9항목을 순서대로 수행하고 _preprocess_log.csv 에 항목마다 기록한다. 분석과 도면화에는 쓰지 않는다.
license: CC-BY-4.0
compatibility: QGIS 3.44 LTR + QGIS MCP 플러그인 0.14.0 기준. MCP 도구만으로 성립한다. 동봉 감사 스크립트를 쓰려면 Python 3 와 geopandas · rasterio · fiona 가 필요하다.
---

<!-- 이 파일은 scripts/build_skills.py 가 생성한다. 손으로 고치지 않는다. -->

## 이 파일에 대하여

- **자동 생성물이다. 손편집 금지.** 고쳐도 다음 빌드에서 되돌아간다.
- 정본 파일: `handouts/PREPROCESS.md` (강의 저장소)
- 정본 커밋: `e5f12e26a69b1cf789e57b5eefd4c626131c39b8`
- 정본 sha256: `f3634f73b40f45cf76f8105699c5d995129a0e40e041b93c99755b77f1dca910`
- 생성 시각: 2026-09-25 19:11:52
- 생성 스크립트: `scripts/build_skills.py`

규칙을 고칠 일이 있으면 위 정본 파일을 고치고 빌드를 다시 돌린다.

## 출력 규칙

- 이 스킬로 답할 때 **첫 줄에 `[qgis-preprocess 1.0.0]` 을 쓴다.** 예외 없다.
- 항목마다 잰 값을 그대로 적는다. 값을 확인하지 않은 채로 "처리했다" 고 보고하지 않는다.

## 동봉 스크립트 — 선택이다

이 `SKILL.md` 와 같은 폴더의 `scripts/verify_preprocess.py` 는 9항목을 **QGIS 밖에서 한 번 더 재는**
감사 도구다. 판정만 하고 파일은 고치지 않는다.

```
python scripts/verify_preprocess.py --projects 3 --log C:\qgis_mcp_class\proj03_population\01.preprocess\_audit.csv
```

`--log` 는 **절대경로로 준다.** 안 주면 스크립트가 자기 위치를 기준으로 로그 폴더를 잡는데,
스킬 폴더에서 실행하면 그 경로가 실습 폴더 밖이 된다.

**Python 환경이 없으면 이 절을 건너뛴다.** 아래 9항목은 MCP 도구만으로 전부 성립한다.
`get_layer_crs` · `get_layer_features` · `get_layer_extent` · `get_raster_info` · `execute_processing` 로
같은 값을 잴 수 있다. 스크립트는 다른 경로로 한 번 더 재는 대조 수단이지 필수 조건이 아니다.

스크립트 값과 MCP 값이 다르면 **둘 다 적는다.** 한쪽을 골라 적지 않는다.

---

아래는 정본 `handouts/PREPROCESS.md` 의 본문 그대로다.

# PREPROCESS.md — QGIS 공통 전처리 규칙

> 이 파일을 실습 폴더 루트에 두고 `AGENTS.md` 에서 참조하면, "전처리해줘" 한 줄로 아래 절차가 그대로 실행된다.
> `AGENTS.md` 는 클라이언트 중립 규격이라 Codex·Cursor·Copilot 이 그대로 읽는다. Claude Code 는 같은 폴더의
> `CLAUDE.md`(`@AGENTS.md` 한 줄)를 통해 읽는다. 클라이언트별 로드 방식은 `docs/6` 의 표에 있다.

## 대상과 결과

- 대상은 `00.origins` 폴더의 모든 원본 데이터다.
- 결과는 `01.preprocess` 폴더에 **새 파일**로 내보낸다.
- **`00.origins` 는 절대 수정하지 않는다.** 덮어쓰기·개명·삭제 금지. 원본이 남아 있어야 잘못된 전처리를 되돌릴 수 있다.
- 프로젝트 대상 좌표계는 **EPSG:5186** 이다. 입력이 4326·5179·3857 이면 먼저 재투영한다.
- **다른 프로젝트의 전처리본을 그대로 쓰는 경우**(예: 같은 대상지의 DEM)는 복제하지 않는다.
  `01.preprocess` 폴더는 만들고 **로그만 남기고**, `output` 열에 공유하는 파일의 절대경로를 적는다.
  같은 파일을 두 곳에 두면 나중에 어느 쪽이 정본인지 알 수 없다.

## 폴더 규약

| 폴더 | 무엇이 들어가나 |
|---|---|
| `00.origins` | 내려받은 원본 그대로 (읽기 전용) |
| `01.preprocess` | 검증 9항목을 통과한 표준 입력 + `_preprocess_log.csv` |
| `02.analysis` | 단계별 중간 산출물 |
| `03.outputs` | 지도·도면·집계표 |
| `04.verify` | GUI 재실행 대조표 (`verify_pN.csv`) |

## 파일 명명

- **`01.preprocess` 에만 좌표계 접미를 붙인다**: 벡터 `pN_내용_5186.gpkg`, 래스터 `pN_내용_5186.tif`.
  (`N` = 프로젝트 번호, 끝은 좌표계 EPSG 코드)
- **`02.analysis` · `03.outputs` 는 `pN_내용`** 으로 쓴다(예: `p1_candidate.gpkg`, `p9_change_class3.tif`).
  좌표계 접미를 붙이지 않는다 — 분석 산출물은 모두 프로젝트 CRS 이므로 표시할 이유가 없다.
- **파일명과 경로에 한글·공백을 쓰지 않는다.** 소문자·숫자·밑줄만.
- MCP 에 넘기는 경로는 언제나 절대경로로 쓴다.

## 한 파일에 여러 레이어를 담을 때

- 데이터셋 여러 개가 한 프로젝트의 입력이면 **GPKG 하나에 레이어 여러 개**로 담는다.
  도구는 **`native:package`** 다(`OVERWRITE=true`). QGIS **레이어 이름이 그대로 GPKG 레이어명**이 되므로,
  패키지 전에 `set_layer_property name=...` 으로 이름을 정리한다. 공간 인덱스도 같이 만들어 준다.
- **속성만 있는 CSV(인구표 등)는 따로 파일로 두지 않는다.** 같은 GPKG 의 **비공간 테이블 레이어**로 넣는다.
  `add_vector_layer` 에 `provider=delimitedtext` + URI `...?type=csv&geomType=none` 으로 읽고,
  경계 레이어와 함께 `native:package` 에 넘긴다. (예: `p3_sido_5186.gpkg` 안에 `boundary` · `population`)

## 검증 9항목 — 순서대로 수행한다

1. **파일 명명** — 이름이 규칙에 맞는지 확인한다. 맞지 않으면 `01.preprocess` 에 규칙대로 복사·개명한다.
2. **포맷 통일** — 벡터는 GPKG, 래스터는 GeoTIFF 로 통일한다.
   `native:package`(여러 레이어) / `export_layer`(한 레이어) / `gdal:translate`(래스터)를 쓴다.
3. **좌표계** — `get_layer_crs` 로 CRS 가 있는지, 값이 맞는지 확인한다. 세 경우를 구분한다.
   - **CRS 가 아예 없음** → 먼저 지정한다(벡터 `native:assignprojection`, 래스터 `gdal:assignprojection`).
   - **CRS 는 있는데 EPSG 코드가 없음** — `get_layer_crs` 의 `authid` 가 빈 문자열이고 이름만 나오는 경우다
     (예: 표준노드링크 `.prj` 의 `ITRF2000_Central_Belt_60`). `proj4` 파라미터가 5186 과 같으면
     **코드만 부여하고 재투영하지 않는다**(`set_layer_crs EPSG:5186`). 재투영하면 좌표가 두 번 변환된다.
   - **값이 맞는데 5186 이 아님** → 재투영한다(벡터 `native:reprojectlayer`, 래스터 `gdal:warpreproject`).
   - 래스터 계산기 출력에는 CRS 가 붙지 않으므로 반드시 지정한다.
4. **인코딩** — `get_layer_features` 로 샘플 피처를 꺼내 한글 속성이 깨졌는지 확인한다.
   깨졌으면 원본 인코딩(CP949/EUC-KR/UTF-8)을 지정해 다시 읽고 GPKG 로 재저장한다.
   SHP 는 `.cpg` 가 있으면 OGR 이 알아서 적용한다 — 먼저 `.cpg` 를 확인한다.
5. **무결성** — `native:checkvalidity` 로 불량 지오메트리를 센다.
   있으면 `native:fixgeometries`, `native:removenullgeometries`, `native:deleteduplicategeometries` 순으로 고친다.
   - 중복 지오메트리는 **선·면이면 제거**하고, **점이면 건수만 기록한다**(같은 건물 안 다점포는 정상).
   - 제거했으면 **제거 전후 건수를 둘 다** `measured` 에 적는다(`DUPLICATE_COUNT` / `RETAINED_COUNT`).
   - **중복을 제거한 입력으로 이미 분석을 돌려 둔 결과가 있으면, 그 분석은 재실행 대상이다.**
     건수뿐 아니라 **면적·길이 합계도 달라진다**(중복을 두 번 더하고 있었으므로). 로그 `action` 에
     "하류 재실행 필요: <파일>" 을 적고 끝낸다.
6. **필드 타입** — 숫자가 문자로 읽혔는지, 코드 열이 숫자로 자동 인식됐는지 확인한다.
   - **조인키뿐 아니라 코드·식별자 성격의 숫자열은 전부 문자열로 강제한다**(앞자리 0 보존).
     행정구역코드·업종코드·우편번호·지번·건물관리번호·연도 같은 것들이다. 자동 타입인식은 이들을
     정수나 실수로 바꿔 버리고, 자릿수가 길면(예: 25자리 건물관리번호) **실수로 읽혀 값이 손상된다.**
   - **CSV 는 `refactorfields` 보다 URI 선언이 먼저다.** `add_vector_layer` 의 delimitedtext URI 에
     `&field=<이름>:string` 을 필요한 만큼 붙여 **읽는 시점에** 타입을 고정한다. 이미 잘못 읽힌 레이어를
     고칠 때만 `native:refactorfields` 를 쓴다.
   - 조인은 이름이 아니라 코드로 한다. 이름은 행정구역 개편으로 달라진다.
7. **범위·해상도** — `get_layer_extent` 로 레이어 extent 가 **대상지 경계와 교차하는지** 확인한다.
   - **교차하면 통과**다. 전국·광역 자료를 표준 입력으로 그대로 쓰는 경우(표준노드링크 전국 링크 등)가
     정상이므로 허용한다. **대상지 안에 완전히 들어가는지는 `within` 값으로 `measured` 에 기록만** 한다.
   - **교차가 0이면 실패**다. 지역을 잘못 골랐거나 CRS 가 틀렸다는 신호다.
   - **대상지 클립은 선택**이다(용량·속도 목적).
   래스터는 `get_raster_info` 로 nodata·셀 크기·행열 수를 본다. API 로 받은 자료는 행 수도 확인한다
   (오류 없이 빈 결과가 오는 경우가 있다).
   - **여러 시점·여러 장의 래스터는 반드시 같은 격자에 맞춘다.** `gdal:warpreproject` 를 인자 없이 돌리면
     장마다 행열 수와 원점이 달라져 래스터 계산기에서 겹쳐지지 않는다. `TARGET_RESOLUTION` 과
     `TARGET_EXTENT`(+`TARGET_EXTENT_CRS`)를 **명시해 고정**하고, 범주형 자료는 `RESAMPLING=0`(최근접)을 쓴다.
   - 이미 그 격자로 만든 산출물이 있으면 **그 격자를 그대로** 쓴다. 격자를 바꾸면 기존 ② 산출물과 어긋난다.
8. **공간 인덱스** — 대용량 벡터에는 인덱스가 있어야 한다. GPKG 로 기록하는 알고리즘
   (`native:package` · `reprojectlayer` · `clip` 등)은 **rtree 를 자동으로 만든다.** 없을 때만
   `native:createspatialindex` 를 건다. 확인·생략 여부도 로그에 남긴다.
9. **기록** — 항목마다 결과를 `01.preprocess/_preprocess_log.csv` 에 **그 항목의 조치가 끝나는 즉시 append**
   한다(버퍼링·마지막 몰아쓰기 금지). `verdict` 는 **잰 시점의 판정**, `action` 은 그에 대해 한 조치다.
   전부 끝나면 PASS·FAIL·조치 건수를 요약해 보고한다.

## 로그 스키마 — `_preprocess_log.csv`

```
date,project,file,item,measured,verdict,action,output
```

| 컬럼 | 내용 | 예시 |
|---|---|---|
| `date` | 점검 실행일 | `2026-09-12` |
| `project` | 프로젝트 번호 | `p03` |
| `file` | 점검 대상 원본 파일 | `sgis_sido.geojson` |
| `item` | 항목 키 `0.folder` `1.naming` `2.format` `3.crs` `4.encoding` `5.integrity` `6.field_type` `7a.extent` `7b.raster` `8.rtree` `9.record` | `3.crs` |
| `measured` | 실제로 잰 값 | `EPSG:5179` |
| `verdict` | 잰 시점의 판정 `PASS` / `FAIL` / `NA` | `FAIL` |
| `action` | 취한 조치(도구·인자). 없으면 `없음`, 미루면 `보류: 사유` | `reprojectlayer 5186` |
| `output` | 결과 파일 경로 | `01.preprocess/p03_sido_5186.gpkg` |

- 인코딩은 `utf-8-sig`, 항목마다 한 행씩 즉시 기록한다.
- `9.record` 는 ⑨ 기록 자체의 판정 행이다 — 로그 파일이 있고 행 수가 **대상 파일 수 × 항목 수(9)**
  이상인지. 감사 스크립트(`action`=`audit`)가 프로젝트마다 한 행 남긴다.
- **로그 본문에 `|` 를 쓰지 않는다.** GPKG 레이어 지정(`파일.gpkg|layername=x`)을 그대로 적으면
  파이프를 구분자로 쓰는 도구에서 열이 밀린다. `<파일.gpkg> 의 <레이어> 레이어` 로 풀어 쓴다.
- `action` 에는 **도구 이름만 쓰지 말고 인자 값까지** 적는다. 기본값에 맡긴 인자도 값을 적어 둔다
  (예: `native:buffer DISTANCE=100 SEGMENTS=8 DISSOLVE=true`). 값이 없으면 나중에 같은 결과를 재현할 수 없다.

## 작업 방식

- **MCP 호출은 한 번에 하나만 한다.** 단일 소켓이라 동시 요청을 보내면 연결이 멈춘다.
- **중간 산출물은 반드시 파일로 저장한 뒤 다시 로드해서** 다음 단계에 넘긴다.
  `TEMPORARY_OUTPUT` / `memory:` 출력은 **`load_results=true` 를 줘도 프로젝트에 등록되지 않고 버려진다.**
  선택이 아니라 필수다. (건수·면적 같은 **반환값만** 필요할 때는 `TEMPORARY_OUTPUT` 으로 받아도 된다.)
- 표준 작업은 `execute_processing` 으로 한다. `execute_code` 는 꼭 필요할 때만 쓰고, 쓰기 전에 무엇을 왜 실행하는지 먼저 알린다.
- 알고리즘 ID 는 `list_processing_algorithms` 로 확인한 뒤 호출한다. 버전·도구에 따라 `native:` / `qgis:` / `gdal:` 접두가 다르다.
- 값을 확인하지 않은 채로 "처리했다"고 보고하지 않는다. 항목마다 잰 값을 로그와 보고에 함께 남긴다.
