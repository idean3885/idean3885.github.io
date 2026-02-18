---
title: "자바 개발자가 처음 만난 uvx — 사용법부터 PyPI 배포 자동화까지"
date: 2026-02-19 00:00:00 +0900
categories: [기술 노하우, Python]
tags: [uvx, uv, Python, PyPI, MCP, 버전관리, GitHub Actions]
description: >-
  자바 개발자 관점에서 uvx의 핵심 개념, 사용법, 버전 관리,
  MCP 플러그인 배포, GitHub Actions 자동화까지 정리합니다.
---

## 왜 지금 uvx인가

MCP(Model Context Protocol) 생태계에서 Python이 주류 언어로 자리잡고 있습니다.
GitHub 스타 기준으로 Python SDK가 21,700개, TypeScript SDK가 11,600개입니다.
서버를 직접 만드는 쪽에서는 Python이 더 많이 선택받고 있습니다.

도구 자체도 빠르게 확산되고 있습니다.
uv/uvx는 GitHub 스타 79,400개 이상, 월간 다운로드 2,800만 건,
PyPI 트래픽 점유율 13.3%를 기록하고 있습니다.
JetBrains 개발자 설문에서는 1년 만에 0%에서 11%로 채택률이 올랐습니다.

MCP 공식 문서는 Python 서버 실행 방법으로 uvx를 "recommended"로 명시하고 있습니다.
Anthropic 공식 MCP 서버인 `mcp-server-git`도 uvx 기반으로 배포됩니다.
결론은 단순합니다.
MCP 플러그인을 Python으로 배포한다면 uvx가 사실상 표준 경로입니다.

실제 프로젝트에서 uvx 전환을 결정한 과정 —
왜 이 패턴을 골랐고, 무엇을 포기했는지 —
는 [검증 편](https://idean3885.github.io/posts/testing-changed-architecture/)에 정리했습니다.
이 글은 그 결정 이후의 이야기입니다.
uvx를 어떻게 쓰는지, 어떻게 배포하는지를 다룹니다.

## uvx란 무엇인가

uvx는 `uv tool run`의 별칭입니다.
Python CLI 도구를 격리된 가상환경에서 실행하는 명령어입니다.
Node.js의 npx에 정확히 대응합니다.
npx가 npm 패키지를 설치 없이 실행하듯, uvx는 PyPI 패키지를 설치 없이 실행합니다.

실행 방식은 두 가지입니다.

| 모드 | 명령어 | 저장 위치 | 생명주기 |
|------|--------|-----------|---------|
| 임시 실행 | `uvx <tool>` | uv 캐시 디렉토리 | `uv cache clean` 시 삭제 |
| 영구 설치 | `uv tool install <tool>` | `~/.local/share/uv/tools/` | `uv tool uninstall` 시 삭제 |

임시 실행은 한 번 쓰고 지우는 도구에, 영구 설치는 매일 쓰는 도구에 어울립니다.
MCP 서버처럼 매 세션마다 uvx로 실행되는 경우에는 캐시가 자동으로 재사용되어
체감 성능 차이는 거의 없습니다.

uvx가 파일을 저장하는 경로도 환경변수로 제어할 수 있습니다.

| 데이터 | 기본 경로 | 환경변수 |
|--------|-----------|---------|
| 도구 환경 (영구) | `~/.local/share/uv/tools/` | `UV_TOOL_DIR` |
| 도구 실행파일 | `~/.local/bin/` | `UV_TOOL_BIN_DIR` |
| 캐시 (임시 uvx) | `~/.cache/uv/` | `UV_CACHE_DIR` |

## 시작하기 — 설치와 기본 사용

설치는 환경에 따라 세 가지 방법이 있습니다.

```bash
# macOS
brew install uv

# pip (범용)
pip install uv

# curl (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 후 주요 명령어입니다.

```bash
# 임시 실행 — 설치 없이 바로 사용
uvx ruff check .
uvx black --check .

# 특정 버전 실행
uvx ruff@0.3.0 check .
uvx ruff@latest check .

# 버전 범위 지정 — --from 필수
uvx --from 'ruff>0.2.0,<0.3.0' ruff check .

# 패키지명과 커맨드명이 다를 때
uvx --from httpie http

# 추가 의존성과 함께 실행
uvx --with mkdocs-material mkdocs build
```

버전 지정 없이 `uvx <tool>`을 실행하면 최신 버전을 가져옵니다.
버전을 고정하고 싶다면 `@` 뒤에 명시합니다.
`--from`은 패키지 이름과 실행 커맨드 이름이 다를 때,
또는 버전 범위 연산자(`>`, `<`, `~=`)를 쓸 때 필요합니다.

영구 설치 도구의 관리 명령어입니다.

```bash
uv tool install ruff
uv tool upgrade ruff
uv tool upgrade --all
uv tool list
uv tool uninstall ruff
```

## 배포하기 — PyPI + pyproject.toml

uvx로 실행 가능한 패키지를 만들려면 두 가지가 필요합니다.
PyPI에 배포된 패키지, 그리고 진입점이 정의된 `pyproject.toml`입니다.

실제 [claude-slack-to-notion](https://github.com/dykim-base-project/claude-slack-to-notion)
프로젝트의 `pyproject.toml`을 예시로 살펴봅니다.

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "slack-to-notion-mcp"
version = "0.1.0"
description = "Slack 메시지/스레드를 분석하여 Notion 페이지로 정리하는 MCP 서버"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "slack_sdk>=3.27.0",
    "notion-client>=2.2.0",
    "mcp[cli]>=1.0.0",
]

# uvx가 실행할 커맨드 정의 — 이것이 핵심
[project.scripts]
slack-to-notion-mcp = "slack_to_notion.mcp_server:main"

[tool.setuptools.packages.find]
where = ["src"]
```

`[project.scripts]`가 핵심입니다.
`uvx slack-to-notion-mcp`를 실행했을 때
어떤 Python 함수가 호출될지를 여기서 정의합니다.
자바로 비유하면 `MANIFEST.MF`의 `Main-Class`와 같은 역할입니다.
형식은 `커맨드명 = "모듈.경로:함수명"`입니다.

버전 관리는 `uv version` 명령어로 합니다.

```bash
uv version 1.0.0           # 정확한 버전 지정
uv version --bump minor     # 0.1.0 → 0.2.0
uv version --bump patch     # 0.1.0 → 0.1.1
```

빌드와 배포는 두 단계입니다.

```bash
uv build    # dist/ 디렉토리에 wheel + sdist 생성
uv publish  # PyPI에 배포
```

`uv build`는 `dist/` 디렉토리에 `.whl`(wheel)과 `.tar.gz`(sdist) 두 파일을 생성합니다.
`uv publish`는 이 파일들을 PyPI에 업로드합니다.
`UV_PUBLISH_TOKEN` 환경변수에 PyPI API 토큰을 설정하거나,
Trusted Publisher(OIDC) 방식으로 시크릿 없이 인증할 수 있습니다.

## MCP 플러그인에 적용하기

PyPI에 배포된 패키지는 `.mcp.json` 설정 한 줄로 연결됩니다.

실제 프로젝트의 `.mcp.json` 예시입니다.

```json
{
  "mcpServers": {
    "slack-to-notion": {
      "command": "uvx",
      "args": ["slack-to-notion-mcp"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
        "SLACK_USER_TOKEN": "${SLACK_USER_TOKEN}",
        "NOTION_API_KEY": "${NOTION_API_KEY}",
        "NOTION_PARENT_PAGE_ID": "${NOTION_PARENT_PAGE_ID}"
      }
    }
  }
}
```

Anthropic 공식 `mcp-server-git`이 사용하는 패턴도 동일한 구조입니다.

```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/path/to/repo"]
    }
  }
}
```

uvx 기반 MCP 서버의 장점은 네 가지입니다.

1. **사용자 환경 설정 불필요** — uvx가 가상환경 생성과 의존성 설치를 모두 처리합니다.
2. **버전 고정 가능** — `args`에 `"slack-to-notion-mcp@0.2.0"`처럼 버전을 명시할 수 있습니다.
3. **의존성 격리** — 사용자 프로젝트의 Python 환경과 충돌하지 않습니다.
4. **업데이트 간편** — 설정 파일의 버전 번호만 바꾸면 됩니다.

실제 프로젝트에서 git clone 기반 배포를 uvx로 전환한 경험 —
6단계 설치 과정이 2단계로 줄어든 과정 —
은 [검증 편](https://idean3885.github.io/posts/testing-changed-architecture/)에 정리했습니다.

## 자동화 — GitHub Actions

태그를 push하면 자동으로 PyPI에 배포되는 워크플로우입니다.
실제 [claude-slack-to-notion](https://github.com/dykim-base-project/claude-slack-to-notion)에서
사용하는 `pypi-publish.yml`입니다.

```yaml
name: PyPI 배포

on:
  push:
    tags:
      - "v*"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: uv 설치
        uses: astral-sh/setup-uv@v4
      - name: 태그-버전 일치 확인
        run: |
          TAG_VERSION="${GITHUB_REF_NAME#v}"
          PKG_VERSION=$(uv run python -c "
          import tomllib
          with open('pyproject.toml', 'rb') as f:
              print(tomllib.load(f)['project']['version'])
          ")
          if [ "$TAG_VERSION" != "$PKG_VERSION" ]; then
            echo "::error::태그($TAG_VERSION)와 pyproject.toml 버전($PKG_VERSION)이 불일치합니다."
            exit 1
          fi
      - name: 테스트 실행
        run: uv sync --extra dev && uv run pytest tests/ -v

  publish:
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - name: PyPI 배포
        run: uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

설계에서 중요한 점 두 가지입니다.

첫째, `validate` → `publish` 2단계 분리입니다.
태그 버전과 `pyproject.toml` 버전이 다르면 배포 전에 실패합니다.
버전 불일치 상태로 PyPI에 올라가는 사고를 막습니다.

둘째, 배포 흐름이 명확합니다.
`pyproject.toml` 버전 수정 → 커밋 → `v1.0.0` 태그 push → 자동 배포.
손으로 `uv publish`를 실행할 일이 없습니다.

인증 방식은 두 가지입니다.

| 방식 | 설정 | 보안 |
|------|------|------|
| API 토큰 | GitHub Secret에 PyPI 토큰 저장 | 양호 |
| Trusted Publisher (OIDC) | PyPI + GitHub 환경 1회 설정 | 최상 — 시크릿 불필요 |

Trusted Publisher는 PyPI 프로젝트 설정에서 GitHub 저장소와 워크플로우를 등록하면
시크릿 없이 OIDC로 인증됩니다.
신규 프로젝트라면 처음부터 이 방식을 쓰는 것을 권장합니다.

## 자바 개발자를 위한 대응표

[검증 편](https://idean3885.github.io/posts/testing-changed-architecture/#자바-개발자가-만난-python-생태계)에서
"Maven Central이 PyPI고, jbang이 uvx"라고 한 줄로 정리했습니다.
여기서는 좀 더 체계적으로 비교합니다.

| Java | Python (uv) |
|------|-------------|
| SDKMAN (`sdk install java 21`) | `uv python install 3.12` |
| `pom.xml` / `build.gradle` | `pyproject.toml` |
| `mvn archetype:generate` | `uv init` |
| Maven/Gradle 의존성 관리 | `uv add`, `uv lock`, `uv sync` |
| `./gradlew run` | `uv run` |
| jbang (한 줄 실행) | `uvx <tool>` |
| Maven Central | PyPI |
| `MANIFEST.MF` Main-Class | `[project.scripts]` |
| `mvn package` / `./gradlew build` | `uv build` |
| `mvn deploy` / Nexus 업로드 | `uv publish` |

개념 자체는 낯설지 않습니다.
생태계와 명령어만 다를 뿐, 하는 일은 거의 같습니다.

## 알아두면 좋은 것들

**개발사 배경 — lock-in 리스크가 낮은 이유.**
uv는 Astral이라는 VC 후원 기업이 개발합니다.
MIT 라이선스이고, Python 표준인 PEP를 준수합니다.
특정 회사의 독점 포맷이 아니어서 나중에 다른 도구로 전환하기 어렵지 않습니다.

**conda를 대체하지는 않습니다.**
uv는 PyPI 기반 패키지를 다룹니다.
numpy나 scipy처럼 C 확장을 포함한 과학 계산용 패키지는 conda 영역입니다.
데이터 사이언스 환경에서 conda를 쓰고 있다면 uv로 대체하려 하지 않는 편이 낫습니다.

**속도가 실제로 빠릅니다.**
uv는 Rust로 작성되어 pip 대비 10~100배 빠릅니다.
CI에서 `pip install`이 느려서 답답했던 경험이 있다면
`uv sync`로 바꾸는 것만으로도 체감 차이가 납니다.

---

*이 글은 Claude의 도움을 받아 작성했습니다.*
