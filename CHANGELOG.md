# 변경 이력

버전 규칙은 semver 입니다. `README.md` 의 버전 표를 보십시오.

## 1.0.3 — 2026-09-26

문서 정정판입니다. 스킬 본문의 절차·동봉 자산·서버 태그는 그대로입니다.

- **설치 절을 앱 경로로 고쳤다.** Desktop 앱 Code 탭에서 `/plugin` → 플러그인 관리 팝업 →
  **마켓플레이스 추가 ▸ 저장소에서** → `upwise-edu/qgis-mcp-course` 순서다.
  1.0.2 까지 적혀 있던 "앱 안에는 마켓플레이스 추가 화면이 없다" 와 `+ ▸ Plugins ▸ Add plugin` 경로는
  실측과 달라 지웠다. 앱 경로를 CLI 절보다 앞에 둔다 — 수강생 기본 경로다
- `/plugin` 뒤에 인자를 붙이면 **인자가 무시되고 팝업만 열린다**는 주의를 넣었다
- **헤더 예시에서 버전 번호를 뺐다.** `[qgis-connect-check <버전>]` 처럼 적는다.
  `README.md` 에 버전 리터럴은 "버전" 절 한 줄만 남기고, 그 한 줄도 빌드가 `plugin.json` 에서 맞춘다
- **동봉 스크립트 요건 목록을 실제 import 로 통일했다** — Python 3 와
  fiona · geopandas · numpy · pandas · rasterio. `pandas` 가 빠져 있었다
- **공개 저장소에서 볼 수 없는 내부 문서·로그 경로 참조를 지웠다.** 스킬 본문과 동봉 스크립트
  두 개의 docstring 을 자기완결 문장으로 고쳤다 (로그 컬럼은 문서를 가리키지 않고 그 자리에 적는다)
- **업스트림 라이선스를 정정했다.** 저장소 `nkarasiak/qgis-mcp` 와 QGIS 플러그인은 GPL v2+,
  `uvx` 로 띄우는 서버 패키지 `src/qgis_mcp` 는 MIT 다. 이 플러그인은 그 코드를 포함하지 않고
  실행 명령만 참조한다
- **Codex 스킬 확인법을 실측으로 고쳤다.** `$qgis-connect-check` 로 지목해 첫 줄 헤더로 본다.
  `codex` CLI 0.145.0 에는 `/skills` 서브커맨드가 없다
- 이중 등록 제거 명령에 범위를 붙였다 — `claude mcp remove qgis -s user`
- 라이선스 표에 `*.qml.tmpl`(문서 자산)과 `.gitattributes`(설정, 라이선스 대상 아님) 를 적었다

## 1.0.2 — 2026-09-26

라이선스를 제한형으로 교체(MIT→PolyForm NC, CC BY→CC BY-NC-ND). 기능 변경 없음.

- 코드 — MIT 를 **PolyForm Noncommercial 1.0.0** 으로 교체했다. `LICENSE` 에 공식 원문 전문을 넣었다
- 문서·스킬 본문·스타일 자산 — CC BY 4.0 을 **CC BY-NC-ND 4.0** 으로 교체했다.
  `LICENSE-docs` 에 공식 legal code 전문과 한국어 요약을 넣었다
- 허용되는 것은 개인 학습·연구·사적 수정이고, 금지되는 것은 상업적 이용·재배포·개작본 공개다.
  출처 표시는 필수다. **강의 수강생에게도 같은 조건이 적용된다** (`README.md` 의 "라이선스" 절)
- 스킬 4종의 프론트매터 `license:` 를 `CC-BY-NC-ND-4.0` 으로 바꿨다
- **스킬 본문·동봉 자산·서버 태그는 그대로다.** 이 판은 라이선스 교체만 한다

## 1.0.1 — 2026-09-25

QGIS 3.44.14 로 실측한 결과를 반영한 문구 수정판입니다. 스킬 이름과 동봉 자산은 그대로입니다.

- `qgis-preprocess` — 로그 CSV 값 안에 쉼표가 있으면 그 칸을 큰따옴표로 감싸고 열 수를 센다는 규칙을 넣었다.
  값에 쉼표가 든 행 하나가 8열이 아니라 9열로 밀려 나온 일이 있었다 (정본 `PREPROCESS.md` 수정 후 재생성)
- `qgis-preprocess` · `qgis-verify` — 동봉 스크립트가 프로젝트 경로를 `C:\qgis_mcp_class\projNN_*` 로
  고정해 두었다는 경고를 넣었다. 실습 폴더가 다르면 스크립트를 쓰지 않고 MCP 도구만으로 수행한다
- `qgis-style` — `get_layer_style` 이라는 도구는 없다. 적용 결과 되읽기는 `save_style_qml` 또는
  `render_map` 으로 한다는 한 줄을 넣었다
- `README.md` — Codex · Cursor 스킬 폴더는 **여는 폴더 바로 아래** `.agents\skills\` 여야 한다.
  상위 폴더는 스캔되지 않는다. 스킬이 안 붙으면 조용히 자기 방식으로 처리하므로 첫 줄 헤더로 판별한다
- `README.md` — 이미 `qgis` MCP 서버를 직접 등록해 둔 경우 서버가 두 벌 뜬다. 플러그인을 쓰면
  직접 등록한 항목을 지우라는 안내를 넣었다
- MCP 서버 태그는 `v0.14.0` 을 유지한다. 실측에서 이 태그 하나로 전 항목이 성립했고,
  `0.15.0` 쪽은 QGIS 플러그인 0.14.0 과 불일치를 스스로 보고했다

## 1.0.0 — 2026-09-25

첫 배포판입니다.

- 스킬 4종 신설 — `qgis-connect-check` · `qgis-preprocess` · `qgis-verify` · `qgis-style`
- `qgis-preprocess/SKILL.md` 는 강의 저장소의 `handouts/PREPROCESS.md` 에서 자동 생성한다. 손편집하지 않는다
- 표준 스타일 24개 동봉 — QML 21 + 치환 템플릿 3. 수강생에게 처음 배포되는 자산이다
- 동봉 스크립트 2개 — `verify_preprocess.py` · `verify_outputs.py`. 둘 다 선택 실행이다
- `.mcp.json` 은 QGIS MCP 서버를 `v0.14.0` 태그로 고정한다. `main` 을 쓰지 않는다
- 라이선스 분리 — 코드 MIT, 문서와 스타일 자산 CC BY 4.0
- `qgis-project`(프로젝트 10선 플레이북)는 1.1 로 미뤘다
