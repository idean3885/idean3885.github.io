---
title: "uvx 사용법 — 설치부터 실행까지"
date: 2026-02-19 00:00:00 +0900
categories: [기술 노하우, Python]
tags: [uvx, uv, Python, MCP, pyproject.toml]
description: >-
  MCP 플러그인 배포를 위해 uvx를 처음 접한 자바 개발자의 학습 기록.
  핵심 개념, 자바 도구 대응표, 설치와 실행까지 정리합니다.
---

## 왜 uvx인가

AI 적응기 시리즈에서 MCP 플러그인을 배포하면서 uvx를 처음 접했습니다.
MCP 공식 문서가 Python 서버 실행 방법으로 uvx를 "recommended"로 명시하고 있고,
Anthropic 공식 MCP 서버인 `mcp-server-git`도 uvx 기반으로 배포됩니다.
사실상 Python MCP 플러그인의 표준 경로였습니다.

[검증 편](https://idean3885.github.io/posts/testing-changed-architecture/)에서
"왜 uvx를 선택했는가"와 전환 과정을 다뤘습니다.
이 글은 그 이후 — "어떻게 쓰는가" — 를 정리합니다.

## 자바 개발자를 위한 대응표

처음 uvx를 봤을 때 낯설었습니다.
자바 생태계에 대응시키니 금방 이해가 됐습니다.
하는 일은 거의 같고 명령어만 다릅니다.

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

"자바 개발자가 만난 Python 생태계"는
[검증 편](https://idean3885.github.io/posts/testing-changed-architecture/#자바-개발자가-만난-python-생태계)에서도 다뤘습니다.

## uvx란 무엇인가

uvx는 `uv tool run`의 별칭입니다.
PyPI 패키지를 격리된 가상환경에서 실행하는 명령어입니다.

처음 uvx를 봤을 때 npx가 떠올랐습니다.
Node.js에서 npx로 패키지를 설치 없이 실행하듯,
uvx도 같은 일을 합니다.
다만 Python에는 가상환경이라는 개념이 하나 더 끼어 있어서 처음엔 헷갈렸습니다.

실행 방식은 두 가지입니다.

| 모드 | 명령어 | 생명주기 |
|------|--------|---------|
| 임시 실행 | `uvx <tool>` | `uv cache clean` 시 삭제 |
| 영구 설치 | `uv tool install <tool>` | `uv tool uninstall` 시 삭제 |

임시 실행의 파일은 `~/.cache/uv/`{: .filepath}에, 영구 설치는 `~/.local/share/uv/tools/`{: .filepath}에 저장됩니다.
MCP 서버처럼 매 세션마다 실행되는 경우엔 캐시가 자동 재사용되어
임시 실행이어도 체감 성능 차이는 없습니다.

## 설치와 기본 사용

설치는 환경에 따라 세 가지 방법이 있습니다.

```bash
# macOS
brew install uv

# pip (범용)
pip install uv

# curl (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

기본 실행 명령어입니다.

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

`--from`은 패키지 이름과 실행 커맨드 이름이 다를 때,
또는 버전 범위 연산자(`>`, `<`, `~=`)를 쓸 때 필요합니다.

처음엔 매번 uvx로 실행하면 느리지 않을까 걱정했습니다.
실제로는 캐시가 재사용되어 두 번째 실행부터는 거의 즉시 뜹니다.

영구 설치 도구의 관리 명령어입니다.

```bash
uv tool install ruff
uv tool upgrade ruff
uv tool upgrade --all
uv tool list
uv tool uninstall ruff
```

## 마무리

uvx의 기본은 이 정도면 충분합니다.

PyPI에 패키지를 배포하고, MCP 플러그인으로 연결하고,
GitHub Actions로 자동화하는 과정은 다음 글에서 다룹니다.

왜 이 패턴을 선택했는지, 전환 과정에서 무엇이 달라졌는지는
[검증 편](https://idean3885.github.io/posts/testing-changed-architecture/)에 정리했습니다.

*이 글은 Claude의 도움을 받아 작성했습니다.*
