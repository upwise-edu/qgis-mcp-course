# QGIS + Claude MCP 완전 정복 — 강의 배포 플러그인

QGIS 를 MCP 로 제어하는 강의의 실습 자산입니다. 절차 스킬 4종과 표준 스타일 24개, 그리고 QGIS MCP 서버 설정이 들어 있습니다.

실습 데이터와 수집 스크립트는 여기 없습니다. 그쪽은 인프런 첨부 파일 `qgis_mcp_class_starter.zip` 입니다.
**이 플러그인이 없어도 실습은 됩니다.** 실습 규칙 본문은 데이터 패키지의 `AGENTS.md` 와 `PREPROCESS.md` 에 있습니다.
플러그인은 그 절차를 짧은 명령으로 바꿔 줄 뿐입니다.

## 스킬 4종

| 스킬 | 언제 쓰나 | 동봉 |
|---|---|---|
| `qgis-connect-check` | 연결 확인 · QGIS 버전 확인. 다른 작업을 시작하기 전에 | — |
| `qgis-preprocess` | `00.origins` → `01.preprocess` 검증 9항목 전처리 | 감사 스크립트 (선택) |
| `qgis-verify` | `04.verify/verify_pN.csv` 대조표 채우기 | 재계산 스크립트 (선택) |
| `qgis-style` | 표준 스타일 적용 | QML 21 + 치환 템플릿 3 |

동봉 스크립트는 **선택 실행**입니다. Python 3 와 geopandas · rasterio 가 있어야 돌아갑니다.
없어도 스킬은 MCP 도구만으로 성립합니다.

## 설치 — Claude Code CLI

```
claude plugin marketplace add upwise-edu/qgis-mcp-course
claude plugin install qgis-mcp-course@qgis-mcp-course
```

설치하면 스킬 4종과 QGIS MCP 서버 설정(`.mcp.json`)이 함께 들어옵니다.
호출은 `/qgis-mcp-course:qgis-connect-check` 처럼 하거나, 그냥 "연결 확인해줘" 라고 해도 됩니다.

갱신은 한 줄입니다.

```
claude plugin update qgis-mcp-course@qgis-mcp-course
```

## 설치 — Claude Desktop 앱 (Code 탭)

입력창 옆 **+** 버튼 ▸ **Plugins** ▸ **Add plugin** 을 고르면 플러그인 브라우저가 열립니다.
등록된 마켓플레이스 목록에서 `QGIS + Claude MCP 완전 정복` 을 고릅니다.

> 앱 안에는 마켓플레이스를 새로 추가하는 화면이 없습니다. 브라우저는 이미 등록된 마켓플레이스만 보여 줍니다.
> 목록에 안 보이면 위 CLI 두 줄 중 첫 줄(`marketplace add`)을 한 번 실행한 뒤 앱을 다시 엽니다.

## 설치 — Codex · Cursor

Codex 와 Cursor 는 Claude 플러그인 형식을 설치하지 않습니다. **스킬 폴더를 복사**합니다.

1. 이 저장소를 내려받습니다 (`Code ▸ Download ZIP` 또는 `git clone`).
2. `skills/` 아래 4개 폴더를 아래 위치로 복사합니다.

   | 범위 | 복사 위치 |
   |---|---|
   | 실습 폴더에서만 | `C:\qgis_mcp_class\.agents\skills\` |
   | 어느 폴더에서나 | `%USERPROFILE%\.agents\skills\` |

3. 호출은 Codex CLI · IDE 확장에서 `$qgis-connect-check`, 또는 `/skills` 로 목록에서 고릅니다.
   ChatGPT 에서는 `@` 입니다.

MCP 서버는 따로 등록합니다. `%USERPROFILE%\.codex\config.toml` 끝에 붙입니다.

```toml
[mcp_servers.qgis]
command = "uvx"
args = ["--from", "https://github.com/nkarasiak/qgis-mcp/archive/refs/tags/v0.14.0.zip", "qgis-mcp-server"]
```

Cursor 는 같은 `uvx` 명령을 Cursor 의 MCP 설정에 등록합니다.

규칙 파일은 할 일이 없습니다. 실습 폴더 루트의 `AGENTS.md` 를 그대로 읽습니다.

## 요건

| 항목 | 값 |
|---|---|
| QGIS | 3.44 LTR (기준 환경) |
| QGIS MCP 플러그인 | 0.14.0 — QGIS 플러그인 관리자에서 설치하고 **Start Server** 를 누릅니다 |
| MCP 서버 | `uvx` 로 실행. `uv` 가 설치돼 있어야 합니다 |
| 서버 버전 | `v0.14.0` 태그 고정 |
| 포트 | 127.0.0.1:9876 |
| 동봉 스크립트 (선택) | Python 3 · geopandas · rasterio · numpy · pandas · fiona |

연결이 안 되면 QGIS 가 떠 있는지, **Start Server** 를 눌렀는지부터 봅니다.
PowerShell 에서 `Test-NetConnection 127.0.0.1 -Port 9876` 이 `True` 여야 합니다.

## 버전

현재 `1.0.0` 입니다. 규칙은 semver 입니다.

| 자리 | 올리는 때 |
|---|---|
| MAJOR | 스킬 이름이 바뀌거나 없어질 때. QGIS 기준 버전이 바뀔 때 |
| MINOR | 스킬이 늘 때. 동봉 자산이 늘 때. `.mcp.json` 의 서버 태그를 올릴 때 |
| PATCH | 문구 수정. 오타. 트리거 문장 손질 |

## 라이선스

| 대상 | 라이선스 |
|---|---|
| 코드 (`*.py` · `*.json`) | MIT — `LICENSE` |
| 문서와 스타일 자산 (`SKILL.md` · `*.qml`) | CC BY 4.0 — `LICENSE-docs` |

QGIS MCP 서버(`nkarasiak/qgis-mcp`, GNU GPL v2 or later)의 코드나 문서는 이 저장소에 들어 있지 않습니다.

## 기여

이 저장소는 강의 배포용입니다. `skills/qgis-preprocess/SKILL.md` 는 **자동 생성물이라 손으로 고치지 않습니다.**
정본은 강의 저장소의 `handouts/PREPROCESS.md` 이고, 빌드 스크립트가 여기로 생성합니다.
