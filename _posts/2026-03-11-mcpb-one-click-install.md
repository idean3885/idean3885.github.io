---
title: "남은 한 걸음 — .mcpb로 원클릭 설치까지"
date: 2026-03-11 00:00:00 +0900
last_modified_at: 2026-04-03 00:00:00 +0900
categories: [개발 기록, Slack to Notion 제작기]
tags: [AI, Claude Code, MCP, mcpb, Desktop Extension, 비개발자, UX]
description: >-
  6편에서 남겨둔 "한 걸음"을 채웠습니다.
  JSON 수동 설정을 없애고 .mcpb 원클릭 설치로 전환한 과정,
  그리고 MCP 효율 논란에 대한 팩트 체크를 정리합니다.
---

> **TL;DR** `.mcpb` 데스크톱 익스텐션(Desktop Extension)으로 JSON 수동 편집 없이 원클릭 설치를 만들었습니다.
> 비개발자가 혼자 설정까지 마칠 수 있는 수준에 도달했습니다.
{: .prompt-tip }

## 남은 한 걸음

[6편](https://idean3885.github.io/posts/real-feedback-from-non-developer/)을
이렇게 마무리했습니다.

> 비개발자가 혼자 설정까지 마치려면 아직 개발자의 도움이 필요합니다.
> 완전한 셀프서비스까지는 한 걸음이 남아 있습니다.

적응기는 거기서 끝났지만, 한 걸음은 남아 있었습니다.
6편의 피드백을 정리하면 결국 하나였습니다.

> JSON 파일을 열어서 경로와 토큰을 붙여넣는 행위 자체가 장벽이다.

가이드를 아무리 잘 써도 이 단계를 없앨 수는 없었습니다.
구조적으로 해결해야 할 문제였습니다.

## Desktop Extension이라는 해답

Anthropic이 Desktop Extension(`.mcpb`) 포맷을 공개했습니다.
MCP 서버를 ZIP으로 묶어 Claude Desktop에 드래그 앤 드롭으로 설치하는 방식입니다.

핵심은 **JSON 수동 편집이 사라진다**는 점입니다.
`.mcpb` 파일을 더블클릭하면 Claude Desktop이 열리고,
토큰 입력 UI가 나타납니다.

Before:

```
1. 터미널 열기
2. uv 설치
3. which uvx로 경로 확인
4. Claude Desktop 설정 파일 열기
5. JSON에 경로와 토큰 붙여넣기
6. 재시작
```

After:

```
1. .mcpb 파일 더블클릭
2. 토큰 3개 입력
3. 확장 활성화
```

6단계가 3단계로 줄었고, 터미널과 JSON이 모두 사라졌습니다.

## 만드는 과정

### manifest.json

`.mcpb`의 핵심은 `manifest.json`입니다.
서버 실행 방법, 사용자 입력 항목, 환경변수 매핑을 정의합니다.

```json
{
  "manifest_version": "0.4",
  "name": "slack-to-notion-mcp",
  "server": {
    "type": "uv",
    "mcp_config": {
      "command": "uv",
      "args": ["run", "slack-to-notion-mcp"]
    }
  },
  "user_config": {
    "slack_user_token": {
      "type": "string",
      "description": "Slack 앱 설정 → OAuth & Permissions → User OAuth Token (xoxp-로 시작)",
      "sensitive": true,
      "required": true
    }
  }
}
```

`user_config`에 정의한 항목이 설치 시 입력 UI로 나타납니다.
`sensitive: true`로 설정하면 토큰이 마스킹됩니다.
`description`에 발급 방법을 적어두면 입력 화면에서 바로 확인할 수 있습니다.

### 하나 걸렸다 — relative import

패킹 후 설치했는데 서버가 시작되지 않았습니다.

```
ImportError: attempted relative import with no known parent package
```

원인은 `mcp_config.args`였습니다.
처음에는 `["run", "src/slack_to_notion/mcp_server.py"]`로 설정했는데,
이렇게 하면 Python이 파일을 독립 스크립트로 실행합니다.
패키지 컨텍스트가 없으니 `from .analyzer import ...` 같은 상대 임포트가 실패합니다.

수정은 간단했습니다.
`pyproject.toml`에 이미 entry point가 정의되어 있었으니 그걸 쓰면 됩니다.

```json
"args": ["run", "slack-to-notion-mcp"]
```

`uv run slack-to-notion-mcp`은 패키지를 설치한 뒤 entry point를 실행하므로
패키지 구조가 정상적으로 인식됩니다.

### .mcpbignore

`.gitignore`와 같은 문법입니다.
번들에 포함할 필요 없는 파일을 제외합니다.

```
tests/
docs/
scripts/
.github/
```

결과: 66KB 소스가 22KB 번들로 패킹되었습니다.

### 설치 후 활성화

설치하면 바로 동작할 줄 알았는데, 비활성화가 기본이었습니다.
설정 → Extensions에서 토글을 켜야 합니다.
README에 이 단계를 명시하지 않으면 "설치했는데 안 된다"는 피드백이 반복될 것입니다.
직접 겪어봐야 아는 것이 또 하나 늘었습니다.

## MCP는 비효율적이라 대체되는 건가?

`.mcpb`를 만들면서 한 가지 의문이 있었습니다.
MCP가 토큰을 많이 소모해서 지양하는 추세라는 이야기를 들었기 때문입니다.
비효율적인 프로토콜 위에 패키징을 얹는 게 맞는 건지 확인이 필요했습니다.

조사 결과, **반은 맞고 반은 틀렸습니다.**

### 맞는 부분 — 토큰 오버헤드는 실재한다

MCP 서버를 연결하면 모든 도구 정의가 세션 시작 시 컨텍스트에 로드됩니다.
서버 하나당 4,000~8,000 토큰.
7개 서버를 연결하면 대화 시작 전에 67,000 토큰이 소모됩니다.

Anthropic은 이를 버그가 아닌 **의도된 동작**으로 분류했습니다.

### 틀린 부분 — MCP가 대체되는 것은 아니다

Anthropic이 발표한 것은 **대규모 에이전트에서의 호출 패턴 최적화**입니다.

- **Tool Search**: 도구를 미리 로드하지 않고 필요할 때만 로드 → 85% 절감
- **코드 실행 패턴**: LLM이 도구를 직접 호출하는 대신 코드를 작성해서 호출 → 98.7% 절감

이는 수십 개의 MCP 서버를 동시에 연결하는 Claude Code 같은 환경의 이야기입니다.
Claude Desktop에서 서버 1~2개를 연결하는 일반 사용자에게는 해당하지 않습니다.

오히려 MCP는 확대 중입니다.
2025년 12월 Linux Foundation에 기부되었고,
2026년 1월 MCP Apps 스펙이 추가되었습니다.

### .mcpb는 MCP의 대체가 아니라 포장이다

`.mcpb`는 내부적으로 동일한 MCP 프로토콜을 사용합니다.
토큰 효율이 개선되는 것이 아니라, **설치 UX가 개선되는 것**입니다.

> MCP가 비효율적이라 대체됨 ✗
>
> .mcpb가 MCP의 설치 장벽을 해소한 진화 ✓
{: .prompt-info }

## 돌아보며

6편에서 남긴 "한 걸음"이 채워졌습니다.

| 구분 | Before (6편) | After (이번) |
|------|-------------|-------------|
| 설치 방식 | JSON 수동 편집 | .mcpb 더블클릭 |
| 필요 지식 | 터미널, uvx 경로, JSON 문법 | 토큰 3개만 준비 |
| 셀프서비스 | 개발자 도움 필요 | 혼자 가능 |

비개발자가 혼자 설정까지 마칠 수 있는 수준.
1편에서 시작한 "비개발자도 쓸 수 있는 도구"라는 목표가
7편 만에 도달한 셈입니다.

물론 토큰 발급 자체의 복잡함은 여전합니다.
Slack 앱을 만들고, Notion Integration을 설정하는 과정은
`.mcpb`로 해결할 수 있는 영역이 아닙니다.
다음에 풀어야 할 문제는 이 인증 과정의 단순화입니다.

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
