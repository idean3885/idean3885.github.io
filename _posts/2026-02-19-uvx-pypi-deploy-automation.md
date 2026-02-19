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
{: file="pyproject.toml" }

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

`uv build`는 두 가지 산출물을 생성합니다.

| 산출물 | 형식 | 역할 |
|--------|------|------|
| wheel (`.whl`) | 미리 빌드된 패키지 | 설치 시 빌드 불필요 — Java `.jar`과 동일 사상 |
| sdist (`.tar.gz`) | 소스 아카이브 | wheel 미지원 환경용 폴백 |

wheel의 핵심은 **사용자 환경에서 빌드를 제거**하는 것입니다.
PyPI에 둘 다 업로드되고, `uvx`로 실행하면 wheel이 우선 사용됩니다.

PyPI 자체는 빌드를 하지 않습니다.
GitHub Actions에서 빌드한 결과물을 저장하고 배포하는 저장소입니다.
Java의 Maven Central, Node의 npm registry와 같은 위치입니다.

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
{: file=".mcp.json" }

Anthropic 공식 `mcp-server-git`도 `"command": "uvx"`, `"args": ["mcp-server-git"]` 구조로 동일합니다.

uvx 기반 MCP 서버의 장점은 네 가지입니다.

1. **사용자 환경 설정 불필요** — uvx가 가상환경 생성과 의존성 설치를 모두 처리합니다.
2. **버전 고정 가능** — `args`에 `"slack-to-notion-mcp@0.2.0"`처럼 버전을 명시할 수 있습니다.
3. **의존성 격리** — 사용자 프로젝트의 Python 환경과 충돌하지 않습니다.
4. **업데이트 간편** — 설정 파일의 버전 번호만 바꾸면 됩니다.

git clone 기반에서 uvx로 전환하면서 6단계 설치가 2단계로 줄어든 과정은
[검증 편](https://idean3885.github.io/posts/testing-changed-architecture/)에 정리했습니다.

## 왜 PyPI인가 — 대안 검토

uvx는 PyPI 없이도 실행할 수 있습니다.

```bash
uvx --from git+https://github.com/user/repo slack-to-notion-mcp
```

GitHub 저장소에서 직접 소스를 받아 실행하는 방식입니다.
PyPI 배포 과정이 없어지니 처음에는 매력적으로 보였습니다.

검토 후 기각했습니다.
이유는 세 가지입니다.

1. **비표준** — Anthropic 공식 MCP 서버를 포함해
   Python 도구는 거의 모두 PyPI로 배포합니다.
   Git 직접 실행은 Python 진영의 일반적인 배포 방식이 아닙니다.
2. **매번 소스 빌드** — wheel이 아닌 소스를 받으므로
   사용자 환경에서 매번 빌드가 발생합니다.
   wheel의 존재 이유가 바로 이 빌드를 제거하기 위한 것입니다.
3. **보안 서명 불가** — PyPI Trusted Publishing(OIDC)은
   빌드 환경을 검증합니다.
   Git 직접 실행에는 이런 서명 체계가 없습니다.

대안을 검토해봐야 "왜 PyPI를 쓰는가"에 대한 답이 명확해집니다.

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
{: file=".github/workflows/pypi-publish.yml" }

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

> 신규 프로젝트라면 처음부터 Trusted Publisher를 쓰는 것을 권장합니다.
> PyPI 프로젝트 설정에서 GitHub 저장소와 워크플로우를 등록하면
> 시크릿 없이 OIDC로 인증됩니다.
{: .prompt-tip }

### 태그까지 자동화 — auto-tag.yml

그런데 하나 남았습니다.
태그 push가 여전히 수동입니다.

```
pyproject.toml 버전 수정 → 커밋 → [수동] git tag push → 자동 배포
```

이것도 자동화했습니다.
`pyproject.toml` 버전이 변경되어 main에 머지되면
태그를 자동 생성하는 워크플로우입니다.

```yaml
name: Auto Tag

on:
  push:
    branches: [main]
    paths: ["pyproject.toml"]

jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.AUTO_TAG_PAT }}

      - name: 버전 읽기 + 태그 생성
        run: |
          VERSION=$(grep -m1 '^version' pyproject.toml \
            | sed 's/.*= *"\(.*\)"/\1/')
          TAG="v$VERSION"
          if git ls-remote --tags origin "$TAG" | grep -q "$TAG"; then
            echo "태그 $TAG 이미 존재 — 스킵"
          else
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git tag "$TAG" && git push origin "$TAG"
          fi
```
{: file=".github/workflows/auto-tag.yml" }

주의할 점은 `GITHUB_TOKEN` 대신 `AUTO_TAG_PAT`을 써야 한다는 것입니다.
`GITHUB_TOKEN`으로 생성한 태그는 다른 워크플로우를 트리거하지 않습니다.
GitHub의 무한 루프 방지 정책 때문입니다.

이제 배포 파이프라인이 완전 자동화됩니다.

```
PR 머지 (pyproject.toml version 변경 포함)
  → auto-tag.yml: 태그 자동 생성
    → pypi-publish.yml: validate + PyPI 배포
```

손이 닿는 곳은 `pyproject.toml`의 버전 수정뿐입니다.

## 몰랐던 것 → 알게 된 것

| 몰랐던 것 | 알게 된 것 |
|-----------|-----------|
| `uv build`가 뭘 생성하는지 | wheel(미리 빌드된 패키지)과 sdist(소스 아카이브) 두 가지 |
| PyPI가 빌드도 해주는지 | 저장소일 뿐 빌드하지 않음 — Maven Central과 동일 |
| Git에서 직접 실행하면 되지 않나 | 비표준 + 매번 소스 빌드 + 보안 서명 불가로 기각 |
| 태그 push를 수동으로 해야 하나 | auto-tag.yml로 완전 자동화 가능 |

## 마무리

uvx를 처음 접한 지 얼마 되지 않았지만,
사용법부터 배포 자동화까지 한 사이클을 돌았습니다.
자바 생태계와 개념이 거의 대응되어서,
새로운 도구를 배운다기보다 번역하는 느낌이었습니다.

한 가지 교훈이 있습니다.
바이브 코딩으로 동작하게 만들 수는 있지만,
"왜 이렇게 하는가"를 모르면 아키텍처 의사결정에서 흔들립니다.
Git 직접 실행 대안을 검토하고 기각한 과정이 좋은 예입니다.
동작하는 코드에 만족하지 않고,
왜 그 방식인지 파고드는 시간이 필요합니다.

uvx의 기본 개념과 사용법은
[앞선 글](https://idean3885.github.io/posts/uvx-guide-for-java-developers/)에 정리했습니다.

*이 글은 Claude의 도움을 받아 작성했습니다.*
