---
title: "uvx로 MCP 플러그인 배포하기 — PyPI부터 GitHub Actions까지"
date: 2026-02-19 01:00:00 +0900
categories: [기술 노하우, Python]
tags: [uvx, uv, PyPI, MCP, GitHub Actions, CI/CD]
description: >-
  uvx 기반 MCP 플러그인을 PyPI에 배포하고,
  GitHub Actions로 자동화한 과정을 정리합니다.
---

## 이어서

[앞선 글](https://idean3885.github.io/posts/uvx-guide-for-java-developers/)에서
uvx의 개념과 기본 사용법을 정리했습니다.
이 글에서는 직접 만든 MCP 플러그인을 uvx로 배포하고 자동화한 과정을 다룹니다.

## 배포하기 — pyproject.toml

uvx로 실행 가능한 패키지를 만들려면 두 가지가 필요합니다.
PyPI에 배포된 패키지, 그리고 진입점이 정의된 `pyproject.toml`입니다.

`pyproject.toml`을 처음 열었을 때 `pom.xml`이 떠올랐습니다.
구조는 비슷한데 문법이 달라서 어디에 뭘 써야 하는지 헷갈렸습니다.
실제로 써보고 나니 생각보다 단순했습니다.

실제 [claude-slack-to-notion](https://github.com/dykim-base-project/claude-slack-to-notion)
프로젝트의 `pyproject.toml`입니다. 핵심만 발췌했습니다.

```toml
[project]
name = "slack-to-notion-mcp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "slack_sdk>=3.27.0",
    "notion-client>=2.2.0",
    "mcp[cli]>=1.0.0",
]

# uvx가 실행할 커맨드 정의 — 이것이 핵심
[project.scripts]
slack-to-notion-mcp = "slack_to_notion.mcp_server:main"
```

`[project.scripts]`가 핵심입니다.
`uvx slack-to-notion-mcp`를 실행했을 때 어떤 Python 함수가 호출될지를 여기서 정의합니다.
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
uv build    # dist/ 에 wheel + sdist 생성
uv publish  # PyPI에 배포
```

`uv publish`는 `UV_PUBLISH_TOKEN` 환경변수에 PyPI API 토큰을 설정하거나,
Trusted Publisher(OIDC) 방식으로 시크릿 없이 인증할 수 있습니다.

## MCP 플러그인에 적용하기

PyPI에 배포된 패키지는 `.mcp.json` 설정 한 줄로 연결됩니다.

실제 프로젝트의 `.mcp.json`입니다.

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

Anthropic 공식 `mcp-server-git`도 `"command": "uvx"`, `"args": ["mcp-server-git"]` 구조로 동일합니다.

uvx 기반 MCP 서버의 장점은 네 가지입니다.

1. **사용자 환경 설정 불필요** — uvx가 가상환경 생성과 의존성 설치를 모두 처리합니다.
2. **버전 고정 가능** — `args`에 `"slack-to-notion-mcp@0.2.0"`처럼 버전을 명시할 수 있습니다.
3. **의존성 격리** — 사용자 프로젝트의 Python 환경과 충돌하지 않습니다.
4. **업데이트 간편** — 설정 파일의 버전 번호만 바꾸면 됩니다.

git clone 기반에서 uvx로 전환하면서 6단계 설치가 2단계로 줄어든 과정은
[검증 편](https://idean3885.github.io/posts/testing-changed-architecture/)에 정리했습니다.

## 자동화 — GitHub Actions

처음에는 수동으로 `uv publish`를 실행했습니다.
태그를 push하면 자동 배포되도록 바꾼 건 버전 불일치를 한 번 겪고 나서입니다.
태그는 `v0.2.0`으로 달았는데 `pyproject.toml`은 `0.1.9`인 채로 올라갔습니다.
그 이후로 검증 단계를 먼저 넣었습니다.

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

핵심 설계는 `validate` → `publish` 2단계 분리입니다.
태그 버전과 `pyproject.toml` 버전이 다르면 배포 전에 실패합니다.
버전 불일치 상태로 PyPI에 올라가는 사고를 막습니다.

배포 흐름은 단순합니다.
`pyproject.toml` 버전 수정 → 커밋 → `v1.0.0` 태그 push → 자동 배포.
손으로 `uv publish`를 실행할 일이 없습니다.

인증 방식은 두 가지입니다.

| 방식 | 설정 | 보안 |
|------|------|------|
| API 토큰 | GitHub Secret에 PyPI 토큰 저장 | 양호 |
| Trusted Publisher (OIDC) | PyPI + GitHub 환경 1회 설정 | 최상 — 시크릿 불필요 |

신규 프로젝트라면 처음부터 Trusted Publisher를 쓰는 것을 권장합니다.
PyPI 프로젝트 설정에서 GitHub 저장소와 워크플로우를 등록하면
시크릿 없이 OIDC로 인증됩니다.

## 마무리

uvx를 처음 접한 지 얼마 되지 않았지만,
사용법부터 배포 자동화까지 한 사이클을 돌았습니다.
자바 생태계와 개념이 거의 대응되어서,
새로운 도구를 배운다기보다 번역하는 느낌이었습니다.

uvx의 기본 개념과 사용법은
[앞선 글](https://idean3885.github.io/posts/uvx-guide-for-java-developers/)에 정리했습니다.

*이 글은 Claude의 도움을 받아 작성했습니다.*
