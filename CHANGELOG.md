# 변경 이력

버전 규칙은 semver 입니다. `README.md` 의 버전 표를 보십시오.

## 1.0.0 — 2026-09-25

첫 배포판입니다.

- 스킬 4종 신설 — `qgis-connect-check` · `qgis-preprocess` · `qgis-verify` · `qgis-style`
- `qgis-preprocess/SKILL.md` 는 강의 저장소의 `handouts/PREPROCESS.md` 에서 자동 생성한다. 손편집하지 않는다
- 표준 스타일 24개 동봉 — QML 21 + 치환 템플릿 3. 수강생에게 처음 배포되는 자산이다
- 동봉 스크립트 2개 — `verify_preprocess.py` · `verify_outputs.py`. 둘 다 선택 실행이다
- `.mcp.json` 은 QGIS MCP 서버를 `v0.14.0` 태그로 고정한다. `main` 을 쓰지 않는다
- 라이선스 분리 — 코드 MIT, 문서와 스타일 자산 CC BY 4.0
- `qgis-project`(프로젝트 10선 플레이북)는 1.1 로 미뤘다
