---
title: "자바 개발자가 본 uvx: 개념·PyPI 배포·GitHub Actions·requires-python 함정까지"
date: 2026-05-17 22:50:00 +0900
last_modified_at: 2026-05-18 15:05:00 +0900
categories: [기술 노하우]
tags: [uvx, uv, Python, MCP, pyproject.toml, PyPI, GitHub Actions, requires-python]
description: >-
  MCP 플러그인 배포로 uvx를 처음 접한 자바 개발자의 입문·배포·함정 기록.
  pyproject.toml 의 진입점, GitHub Actions 자동화, requires-python 무시 문제까지 한 번에 다룹니다.
redirect_from:
  - /posts/uvx-guide-for-java-developers/
  - /posts/uvx-pypi-deploy-automation/
  - /posts/uvx-python-version-trap/
---

> **TL;DR**<br>
> uvx 는 PyPI 패키지를 격리 환경에서 실행하는 명령(=`uv tool run`). 자바의 jbang 자리에 가깝습니다.<br>
> 배포는 `pyproject.toml` 의 `[project.scripts]` 와 `uv build`/`uv publish`, GitHub Actions 의 validate→publish 2단계로 자동화합니다.<br>
> 함정 하나: uvx 는 `requires-python` 을 의도적으로 무시합니다. 사용자 환경 Python 이 낮으면 `setup.sh` 에서 `--python` 플래그를 자동 부여하는 것으로 막습니다.
{: .prompt-tip }

## 1. 왜 uvx 인가

[claude-slack-to-notion](https://github.com/idean3885/claude-slack-to-notion) MCP 플러그인을 배포하면서 uvx 를 처음 접했습니다. MCP 공식 문서가 Python 서버 실행 방법으로 uvx 를 "recommended" 로 명시하고, Anthropic 공식 MCP 서버인 `mcp-server-git` 도 uvx 기반으로 배포됩니다. 사실상 Python MCP 플러그인의 표준 경로였습니다.

자바 개발자라서 처음엔 낯설었습니다. 대응표를 만들어보니 이해가 빨라졌습니다.

| Java | Python (uv) |
|---|---|
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

명령어만 다르고 하는 일은 거의 같습니다.

### uvx 의 정의

uvx 는 `uv tool run` 의 별칭. PyPI 패키지를 격리된 가상환경에서 실행하는 명령입니다. Node 의 `npx` 와 같은 자리.

| 모드 | 명령어 | 생명주기 |
|---|---|---|
| 임시 실행 | `uvx <tool>` | `uv cache clean` 시 삭제 |
| 영구 설치 | `uv tool install <tool>` | `uv tool uninstall` 시 삭제 |

임시 실행 파일은 `~/.cache/uv/`, 영구 설치는 `~/.local/share/uv/tools/` 에 저장. MCP 서버처럼 매 세션마다 실행되는 경우에도 캐시 재사용으로 체감 성능 차이는 없습니다.

### 설치와 기본 사용

```bash
# macOS
brew install uv

# pip (범용)
pip install uv

# curl (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
uvx ruff check .                        # 임시 실행
uvx ruff@0.3.0 check .                  # 특정 버전
uvx --from 'ruff>0.2.0,<0.3.0' ruff .   # 버전 범위 (--from 필수)
uvx --from httpie http                  # 패키지명 ≠ 커맨드명
uvx --with mkdocs-material mkdocs build # 추가 의존성
```

`--from` 은 패키지 이름과 실행 커맨드 이름이 다를 때 또는 버전 범위 연산자를 쓸 때 필요.

## 2. PyPI 배포: pyproject.toml 의 진입점

uvx 로 실행 가능한 패키지를 만들려면 두 가지가 필요합니다. PyPI 에 배포된 패키지, 그리고 진입점이 정의된 `pyproject.toml`.

실제 프로젝트 핵심 발췌:

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

# uvx 가 실행할 커맨드 정의 (핵심)
[project.scripts]
slack-to-notion-mcp = "slack_to_notion.mcp_server:main"
```

`[project.scripts]` 가 핵심. `uvx slack-to-notion-mcp` 를 실행했을 때 어떤 Python 함수가 호출될지 여기서 정의합니다. 자바의 `MANIFEST.MF` `Main-Class` 자리. 형식은 `커맨드명 = "모듈.경로:함수명"`.

빌드와 배포:

```bash
uv version 1.0.0           # 버전 지정
uv version --bump minor    # 자동 bump
uv build                   # dist/ 에 wheel + sdist
uv publish                 # PyPI 배포
```

`uv build` 산출물:

| 산출물 | 형식 | 역할 |
|---|---|---|
| wheel (`.whl`) | 미리 빌드된 패키지 | 설치 시 빌드 불필요 (Java `.jar` 과 동일 사상) |
| sdist (`.tar.gz`) | 소스 아카이브 | wheel 미지원 환경 폴백 |

wheel 의 핵심은 **사용자 환경에서 빌드를 제거**하는 것. PyPI 자체는 빌드하지 않고 GitHub Actions 같은 곳에서 빌드한 결과물을 저장하는 저장소입니다 (Maven Central, npm registry 와 같은 자리).

### Git 직접 실행 대안 검토

uvx 는 PyPI 없이도 실행할 수 있습니다.

```bash
uvx --from git+https://github.com/user/repo slack-to-notion-mcp
```

PyPI 배포가 빠지니 매력적으로 보였습니다. 검토 후 기각:

1. **비표준**: Anthropic 공식 MCP 서버 포함 Python 도구는 거의 모두 PyPI 로 배포. Git 직접 실행은 Python 진영의 일반적 배포 방식이 아님
2. **매번 소스 빌드**: wheel 이 아닌 소스를 받으므로 사용자 환경에서 매번 빌드. wheel 의 존재 이유가 이 빌드를 제거하기 위함
3. **보안 서명 불가**: PyPI Trusted Publishing(OIDC) 은 빌드 환경을 검증. Git 직접 실행에는 이런 서명 체계가 없음

대안을 검토해봐야 "왜 PyPI 를 쓰는가" 에 답이 명확해집니다.

## 3. MCP 플러그인 연결: `.mcp.json`

PyPI 에 배포된 패키지는 `.mcp.json` 한 블록으로 연결됩니다.

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

`mcp-server-git` 도 `"command": "uvx"`, `"args": ["mcp-server-git"]` 동일 구조.

uvx 기반 MCP 서버의 장점:
1. **사용자 환경 설정 불필요**: uvx 가 가상환경·의존성을 모두 처리
2. **버전 고정 가능**: `args` 에 `"slack-to-notion-mcp@0.2.0"` 명시
3. **의존성 격리**: 사용자 프로젝트 Python 환경과 충돌 없음
4. **업데이트 간편**: 설정의 버전 번호만 변경

## 4. GitHub Actions 자동화: validate → publish → auto-tag

처음에는 수동 `uv publish`. 태그 `v0.2.0` 인데 `pyproject.toml` 이 `0.1.9` 로 올라간 버전 불일치 사고 한 번을 겪고 자동화로 갔습니다.

```yaml
name: PyPI 배포
on:
  push:
    tags: ["v*"]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: 태그-버전 일치 확인
        run: |
          TAG_VERSION="${GITHUB_REF_NAME#v}"
          PKG_VERSION=$(uv run python -c "
          import tomllib
          with open('pyproject.toml', 'rb') as f:
              print(tomllib.load(f)['project']['version'])
          ")
          if [ "$TAG_VERSION" != "$PKG_VERSION" ]; then
            echo "::error::태그($TAG_VERSION)와 pyproject.toml 버전($PKG_VERSION)이 불일치"
            exit 1
          fi
      - run: uv sync --extra dev && uv run pytest tests/ -v

  publish:
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - run: uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

핵심 설계는 `validate` → `publish` 2단계 분리. 태그 버전과 `pyproject.toml` 버전이 다르면 배포 전에 실패합니다.

인증 방식:

| 방식 | 설정 | 보안 |
|---|---|---|
| API 토큰 | GitHub Secret 에 PyPI 토큰 저장 | 양호 |
| Trusted Publisher (OIDC) | PyPI + GitHub 환경 1회 설정 | 최상 (시크릿 불필요) |

신규 프로젝트라면 처음부터 Trusted Publisher 권장.

### auto-tag.yml: 태그까지 자동화

`pyproject.toml` 버전이 변경되어 main 에 머지되면 태그를 자동 생성하는 워크플로우.

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
          VERSION=$(grep -m1 '^version' pyproject.toml | sed 's/.*= *"\(.*\)"/\1/')
          TAG="v$VERSION"
          if git ls-remote --tags origin "$TAG" | grep -q "$TAG"; then
            echo "태그 $TAG 이미 존재: 스킵"
          else
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git tag "$TAG" && git push origin "$TAG"
          fi
```

함정 하나: `GITHUB_TOKEN` 대신 `AUTO_TAG_PAT` 을 써야 합니다. `GITHUB_TOKEN` 으로 생성한 태그는 다른 워크플로우를 트리거하지 않습니다 (GitHub 의 무한 루프 방지 정책).

이제 손이 닿는 곳은 `pyproject.toml` 의 버전 수정뿐.

```
PR 머지 (pyproject.toml version 변경 포함)
  → auto-tag.yml: 태그 자동 생성
    → pypi-publish.yml: validate + PyPI 배포
```

## 5. 함정: uvx 는 `requires-python` 을 무시한다

v0.2.0 배포 후 "Python 3.9 쓰는 사람한테는 왜 안 되지?" 라는 질문을 받았습니다. `pyproject.toml` 에 `requires-python = ">=3.10"` 을 기재했으니 3.9 사용자는 설치 단계에서 막힐 거라고 생각했습니다. **틀렸습니다.**

설치는 됐고, 실행도 됐고, 동작이 이상했습니다.

### uv 공식 문서

> "will ignore non-global Python version requests like .python-version files and the requires-python value"

`requires-python` 무시. `.python-version` 무시. 버그가 아니라 의도된 설계. GitHub 이슈 #8206, #14958 에서 이미 논의된 내용입니다.

자바 관점에서 보면 이게 얼마나 낯선지 설명이 됩니다. Maven 에서 `<java.version>11</java.version>` 을 `pom.xml` 에 두면 JDK 8 로 빌드하려는 순간 컴파일 에러가 납니다. uvx 는 그 체크 자체를 안 합니다.

### uvx 의 Python 선택 우선순위

1. `--python` 플래그 (명시적 지정)
2. `UV_PYTHON` 환경변수
3. uv 가 관리하는 Python (`~/.local/share/uv/python/`)
4. 시스템 PATH 의 Python

> `requires-python` 은 이 목록에 없습니다.
{: .prompt-danger }

### `uvx` vs `uv run` 의 결정적 차이

| | uvx (도구 실행) | uv run (프로젝트 실행) |
|---|---|---|
| requires-python | 무시 | 반영 |
| .python-version | 무시 | 반영 |
| 환경 | 격리 venv (캐시) | 프로젝트 venv |
| Python 자동 다운로드 | 조건부 | 필요 시 자동 |

`uv run` 은 프로젝트 맥락이 있고, `uvx` 는 도구 격리 실행에 집중합니다. 자바로 비유하면 `./gradlew run` 과 `jbang script.java` 의 차이.

### 해결: setup.sh 에서 자동 처리

방법은 두 가지. 사용자에게 `uvx --python 3.10 slack-to-notion-mcp` 를 안내하거나, setup.sh 에서 자동 처리. 후자 선택.

```bash
# Python 버전 확인 (3.10 미만이면 --python 3.10 자동 부여)
PYTHON_TOO_OLD=false
if [[ -n "$PYTHON_CMD" ]]; then
  PYTHON_VERSION=$($PYTHON_CMD -c \
    "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
  PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
  if [[ "$PYTHON_MAJOR" -lt 3 ]] || \
     { [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -lt 10 ]]; }; then
    PYTHON_TOO_OLD=true
  fi
else
  PYTHON_TOO_OLD=true
fi

if [[ "$PYTHON_TOO_OLD" == "true" ]]; then
  claude mcp add slack-to-notion ... -- uvx --python 3.10 slack-to-notion-mcp
else
  claude mcp add slack-to-notion ... -- uvx slack-to-notion-mcp
fi
```

시스템 Python 이 3.10 이상이면 그대로, 미만이면 `--python 3.10` 을 자동으로 붙입니다. `--python 3.10` 지정 시 uv 가 자동으로 Python 3.10 을 찾거나 다운로드합니다.

`requires-python` 은 지우지 않습니다. `pip install` 사용자에게는 작동하고 PyPI 메타데이터 표시에도 쓰입니다. uvx 에서만 무시될 뿐.

## 회고: 생태계가 다르면 안전장치도 다르다

Java 에서는 Maven/Gradle 이 JDK 버전을 강제합니다. 버전 불일치는 빌드 도구가 막아줍니다. 그래서 `pom.xml` 에 버전을 쓰면 끝이라고 생각했습니다. Python uvx 에서는 그렇지 않습니다. 도구 실행 맥락에서는 설계 의도상 프로젝트 메타데이터를 보지 않습니다.

알고 나면 간단한 이유가 있고 모르면 "왜 안 되지?" 에서 한참 헤맵니다. 새 생태계로 옮길 때 가장 비싼 비용은 그 차이를 발견하는 시간입니다.

uvx 로 한 사이클을 돌면서 얻은 것:

| 영역 | 결론 |
|---|---|
| 입문 | jbang/npx 와 같은 자리, 자바 도구 대응만 잡으면 충분 |
| 배포 | `[project.scripts]` 진입점 + `uv build`/`uv publish`, PyPI 가 표준 경로 |
| 자동화 | validate → publish 2단계 + auto-tag 로 `pyproject.toml` 한 곳만 손대게 |
| 함정 | `requires-python` 은 uvx 에서 무시됨, setup.sh 에서 `--python` 자동 부여로 막기 |

동작하는 코드에 만족하지 않고 왜 그 방식인지 파고들면 새 생태계의 골격이 빠르게 보입니다.

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
