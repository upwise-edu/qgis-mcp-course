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

동봉 스크립트는 **선택 실행**입니다. Python 3 와 fiona · geopandas · numpy · pandas · rasterio 가 있어야 돌아갑니다.
없어도 스킬은 MCP 도구만으로 성립합니다.

## 설치 — Claude Desktop 앱 (Code 탭)

터미널을 쓰지 않고 앱 안에서 끝납니다. 아래가 수강생 기본 경로입니다.

1. 실습 폴더를 연 Code 탭 입력창에 `/plugin` 을 입력합니다. **플러그인 관리 팝업**이 열립니다.
2. 팝업에서 **"마켓플레이스 추가"** 를 고릅니다. 선택지가 두 개 나옵니다 — **"앤트로픽 소스 탐색"** 과 **"저장소에서"**.
3. **"저장소에서"** 를 고르고 `upwise-edu/qgis-mcp-course` 를 입력합니다.
4. 설치 직전에 경고 팝업이 뜹니다. **정상입니다.** 계속을 누르세요. 원문은 이렇습니다.

   > 이 플러그인에는 로컬 MCP 서버가 포함되어 있습니다
   > 설치하면 컴퓨터의 모든 항목에 대한 액세스 권한이 부여됩니다
   > QGIS + Claude MCP 완전 정복 플러그인에는 컴퓨터에서 로컬 프로세스를 실행하는 다음 MCP 서버가 포함되어 있습니다: qgis
   > 신뢰하는 개발자가 제공하는 플러그인만 사용하세요. …

   이 플러그인이 QGIS 에 붙는 MCP 서버를 이 PC 에서 직접 띄우기 때문에 나오는 경고입니다.
5. **새 세션을 엽니다.** 입력창에 `/qgis-mcp-course:qgis-connect-check` 를 넣습니다.
   첫 줄에 스킬 헤더가 나오고 `연결: pong` 이 보이면 끝입니다.

> **`/plugin` 뒤에 인자를 붙이지 마세요.** `/plugin marketplace add upwise-edu/qgis-mcp-course` 처럼
> 터미널 문법을 그대로 넣으면 **인자는 무시되고 팝업만 열립니다.** 팝업 안에서 위 순서대로 고르면 됩니다.

## 설치 — Claude Code CLI

```
claude plugin marketplace add upwise-edu/qgis-mcp-course
claude plugin install qgis-mcp-course@qgis-mcp-course
```

설치하면 스킬 4종과 QGIS MCP 서버 설정(`.mcp.json`)이 함께 들어옵니다.
호출은 `/qgis-mcp-course:qgis-connect-check` 처럼 하거나, 그냥 "연결 확인해줘" 라고 해도 됩니다.

> **이미 `qgis` 서버를 직접 등록해 두셨다면 그 항목을 지우십시오.**
> `~/.claude.json` 이나 실습 폴더의 `.mcp.json` 에 `qgis` 를 넣어 두셨다면 플러그인의 서버와 겹쳐
> 서버가 두 벌 뜨고 도구가 두 세트로 보입니다. 기능이 깨지지는 않지만 어느 쪽을 쓰는지 알 수 없게 됩니다.
> 플러그인을 쓸 때는 직접 등록한 항목을 지웁니다.
>
> ```
> claude mcp remove qgis -s user
> ```
>
> 사용자 범위에 등록한 경우입니다. 다른 범위에 넣어 두셨다면 그 범위를 `-s` 에 줍니다.

갱신은 한 줄입니다.

```
claude plugin update qgis-mcp-course@qgis-mcp-course
```

## 설치 — Codex · Cursor

Codex 와 Cursor 는 Claude 플러그인 형식을 설치하지 않습니다. **스킬 폴더를 복사**합니다.

1. 이 저장소를 내려받습니다 (`Code ▸ Download ZIP` 또는 `git clone`).
2. `skills/` 아래 4개 폴더를 아래 위치로 복사합니다.

   | 범위 | 복사 위치 |
   |---|---|
   | 실습 폴더에서만 | Codex 로 **여는 폴더 바로 아래** `.agents\skills\` (예: `C:\qgis_mcp_class\.agents\skills\`) |
   | 어느 폴더에서나 | `%USERPROFILE%\.agents\skills\` |

   > **상위 폴더는 스캔되지 않습니다 (2026-09-25 실측).**
   > `C:\qgis_mcp_class\.agents\skills\` 에 두고 그 **하위 폴더**에서 Codex 를 열면 스킬이 붙지 않습니다.
   > 하위 폴더에서 작업하실 거라면 그 폴더 바로 아래에 `.agents\skills\` 를 두거나
   > `%USERPROFILE%\.agents\skills\` 를 쓰십시오.

3. 호출은 Codex CLI · IDE 확장에서 `$qgis-connect-check` 처럼 스킬을 지목합니다.
   ChatGPT 에서는 `@` 입니다.

   > **붙었는지는 답변 첫 줄로 확인합니다.** `$qgis-connect-check` 로 지목해 부르고
   > 첫 줄 헤더 `[qgis-connect-check <버전>]` 이 나오는지 봅니다.
   > 목록을 보여 주는 `/skills` 서브커맨드는 **`codex` CLI 0.145.0 에 없습니다** (2026-09-25 실측).
   >
   > **스킬이 안 붙어도 조용히 자기 방식으로 처리합니다.**
   > 실패했다고 알려 주지 않고 그냥 자기 판단으로 작업합니다. 로그 스키마가 통째로 달라집니다.
   > 첫 줄에 헤더가 없으면 스킬이 적용되지 않은 것입니다. 그때는 2번의 복사 위치를 다시 확인하십시오.

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
| 동봉 스크립트 (선택) | Python 3 · fiona · geopandas · numpy · pandas · rasterio |

연결이 안 되면 QGIS 가 떠 있는지, **Start Server** 를 눌렀는지부터 봅니다.
PowerShell 에서 `Test-NetConnection 127.0.0.1 -Port 9876` 이 `True` 여야 합니다.

## 버전

현재 버전: 1.0.3

규칙은 semver 입니다. 변경 내역은 `CHANGELOG.md` 에 있습니다.
이 문서에서 버전 번호를 적는 곳은 위 한 줄뿐입니다 — 빌드 스크립트가 `plugin.json` 에서 맞춥니다.

| 자리 | 올리는 때 |
|---|---|
| MAJOR | 스킬 이름이 바뀌거나 없어질 때. QGIS 기준 버전이 바뀔 때 |
| MINOR | 스킬이 늘 때. 동봉 자산이 늘 때. `.mcp.json` 의 서버 태그를 올릴 때 |
| PATCH | 문구 수정. 오타. 트리거 문장 손질 |

## 라이선스

저장소는 공개지만 **이용 조건은 비영리로 한정**합니다.

| 대상 | 라이선스 |
|---|---|
| 코드 (`*.py` · `*.json`) | PolyForm Noncommercial 1.0.0 — `LICENSE` |
| 문서와 스타일 자산 (`SKILL.md` · `README.md` · `CHANGELOG.md` · `*.qml` · `*.qml.tmpl`) | CC BY-NC-ND 4.0 — `LICENSE-docs` |
| 설정 (`.gitattributes`) | 라이선스 대상 아님 (줄끝 변환을 끄는 설정 파일) |

무엇이 되고 무엇이 안 되는지는 아래 표대로입니다.

| 행위 | 가능 |
|---|---|
| 개인 학습·연구에 쓰기 | ○ |
| 사적 수정 (내 환경에서 고쳐 쓰기) | ○ |
| 출처 표시 | **필수** |
| 남의 수업 자료로 재배포 | × |
| 상업 서비스·유료 강의에 편입 | × |
| 개작본을 공개·배포 | × |

**이 강의 수강생도 같은 조건입니다.** 수강료는 이용 허락 범위를 넓히지 않습니다.
상업적 이용이 필요하면 별도 협의 대상입니다.

Copyright (c) 2026 UPWISE. 출처 표시 형식은 `LICENSE-docs` 에 있습니다.
두 라이선스 파일의 머리말은 배포 의도를 밝힌 것이며 **법률 자문이 아닙니다.**

**업스트림 QGIS MCP 의 라이선스는 한 가지가 아닙니다.** 저장소 `nkarasiak/qgis-mcp` 와 그 QGIS 플러그인은
GPL v2 or later 이고(루트 `LICENSE` · `metadata.txt`), `uvx` 로 띄우는 서버 패키지 `src/qgis_mcp` 는
MIT 입니다(Copyright (c) 2025 Nicolas Karasiak).
이 플러그인은 **그 코드를 포함하지 않고 실행 명령만 참조**합니다 — `.mcp.json` 이 태그 zip 주소를 가리킬 뿐입니다.

## 기여

이 저장소는 강의 배포용입니다. `skills/qgis-preprocess/SKILL.md` 는 **자동 생성물이라 손으로 고치지 않습니다.**
정본은 강의 저장소의 `handouts/PREPROCESS.md` 이고, 빌드 스크립트가 여기로 생성합니다.
