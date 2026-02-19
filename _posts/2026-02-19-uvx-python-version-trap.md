---
title: "uvx가 Python 버전을 고르는 법 — requires-python의 함정"
date: 2026-02-19 02:00:00 +0900
categories: [기술 노하우, Python]
tags: [uvx, uv, Python, MCP, requires-python]
description: >-
  uvx는 requires-python을 무시한다.
  의도된 설계인 이 동작이 배포자에게 왜 함정이 되는지,
  어떻게 대응해야 하는지 정리합니다.
---

> 시리즈: 몰랐던 것을 알게 되다 #3

[앞선 글](https://idean3885.github.io/posts/uvx-pypi-deploy-automation/)에서
uvx 기반 MCP 플러그인의 PyPI 배포와 GitHub Actions 자동화를 정리했습니다.
이 글에서는 배포 후 만난 Python 버전 문제를 다룹니다.

자바 개발자입니다.
v0.2.0을 배포하고, setup.sh로 업데이트 메커니즘까지 만들었습니다.
그런데 "Python 3.9 쓰는 사람한테는 왜 안 되지?"라는 질문을 받았습니다.
이 글은 그 질문을 파고든 기록입니다.

---

## 1. 도입 — 배포했는데 안 되는 사람이 있다

v0.2.0 배포 직후, 이렇게 생각했습니다.
`pyproject.toml`에 `requires-python = ">=3.10"`을 써놨으니
3.9 사용자는 설치 단계에서 막힐 거라고.
그러면 안내 메시지가 나올 거라고.
그러니 "왜 안 되지"라는 상황 자체가 없을 거라고.

틀렸습니다.

설치는 됐습니다.
실행도 됐습니다.
그런데 동작이 이상했습니다.
`requires-python`이 제가 생각한 대로 작동하지 않고 있었습니다.

---

## 2. 충격 — uvx는 requires-python을 무시한다

uv 공식 문서를 찾아보니 이런 문장이 있었습니다.

> "will ignore non-global Python version requests like .python-version files and the requires-python value"

`requires-python`을 무시한다.
`.python-version` 파일도 무시한다.
버그가 아닙니다.
의도된 설계입니다.
GitHub 이슈 #8206, #14958에서 이미 논의된 내용입니다.

자바 관점에서 보면 이게 얼마나 낯선지 설명이 됩니다.
Maven에서 `<java.version>11</java.version>`을 `pom.xml`에 써놓으면,
JDK 8로 빌드하려는 순간 컴파일 에러가 납니다.
버전 불일치를 빌드 도구가 강제로 막아줍니다.

uvx는 그 체크 자체를 하지 않습니다.

그러면 `requires-python`은 뭘 위해 있는 건가.
이 의문이 다음 질문으로 이어졌습니다.

---

## 3. Python 버전 결정 순서

uvx가 실제로 Python을 고를 때 사용하는 우선순위는 이렇습니다.

1. `--python` 플래그 (명시적 지정)
2. `UV_PYTHON` 환경변수
3. uv가 관리하는 Python (`~/.local/share/uv/python/`)
4. 시스템 PATH의 Python

`requires-python`은 이 목록에 없습니다.
아무것도 지정하지 않으면 시스템에서 가장 적합한 Python,
보통은 최신 버전을 씁니다.

그러니 Python 3.9만 있는 사용자 환경에서는 3.9로 실행됩니다.
`requires-python`이 뭐라고 써있든 상관없이.

---

## 4. uv run과 uvx의 결정적 차이

혼란스러운 이유가 있습니다.
둘 다 uv 제품군인데, 동작이 다릅니다.

| | uvx (도구 실행) | uv run (프로젝트 실행) |
|---|---|---|
| requires-python | 무시 | 반영 |
| .python-version | 무시 | 반영 |
| 환경 | 격리 venv (캐시) | 프로젝트 venv |
| Python 자동 다운로드 | 조건부 | 필요 시 자동 |

`uv run`은 프로젝트 맥락을 가집니다.
`requires-python`을 보고, `.python-version`을 보고,
없으면 자동으로 맞는 Python을 설치합니다.
반면 `uvx`는 도구를 격리 실행하는 데 집중합니다.
프로젝트 맥락 없이, 그냥 "실행"만 합니다.

자바로 비유하면 `./gradlew run`과 `jbang script.java`의 차이와 비슷합니다.
하나는 프로젝트 빌드 시스템 안에서 돌고, 하나는 독립적으로 돌립니다.

---

## 5. 그러면 어떻게 해야 하나

선택지는 두 가지입니다.

하나는 사용자 안내에 `--python` 플래그를 명시하는 것입니다.

```bash
uvx --python 3.10 slack-to-notion-mcp
```

또 하나는 setup.sh에서 Python 버전을 체크한 뒤 자동으로 붙여주는 것입니다.

```bash
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f1,2)

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
  uvx slack-to-notion-mcp
else
  uvx --python 3.10 slack-to-notion-mcp
fi
```

시스템 Python이 3.10 이상이면 그대로 실행하고,
아니면 `--python 3.10`을 붙여 uv가 적합한 Python을 찾도록 합니다.

그리고 `requires-python`은 지우지 않습니다.
`pip install`로 설치하는 사용자에게는 여전히 작동합니다.
PyPI 메타데이터 표시에도 쓰입니다.
uvx에서만 무시될 뿐입니다.

---

## 6. 몰랐던 것 → 알게 된 것

| 몰랐던 것 | 알게 된 것 |
|-----------|-----------|
| requires-python이 모든 곳에서 작동한다 | uvx와 uv tool에서는 무시된다 (의도된 설계) |
| uvx와 uv run이 같은 방식으로 Python을 고른다 | 완전히 다른 탐색 로직을 쓴다 |
| pyproject.toml에 버전 명시하면 충분하다 | 사용자 안내에 --python 플래그를 명시해야 한다 |

---

생태계가 다르면 "당연한 안전장치"도 다릅니다.

Java에서는 Maven과 Gradle이 JDK 버전을 강제합니다.
버전 불일치는 빌드 도구가 막아줍니다.
그래서 `pom.xml`에 버전을 쓰면 그걸로 끝이라고 생각했습니다.

Python uvx에서는 그렇지 않습니다.
도구 실행 맥락에서는 설계 의도상 프로젝트 메타데이터를 보지 않습니다.
알고 나면 간단한 이유가 있습니다.
모르면 "왜 안 되지?"에서 한참 헤맵니다.

---

*이 글은 Claude의 도움을 받아 작성했습니다.*
