---
title: "Configuration Cascade — 로컬이 글로벌을 이기는 설정 전략"
date: 2026-03-08 00:00:00 +0900
categories: [기술 노하우, 개발 사전]
tags: [개발사전, 설계, 아키텍처]
description: >-
  여러 계층의 설정이 존재할 때,
  가장 가까운 설정이 먼 설정을 덮어쓰는
  Configuration Cascade 패턴을 정리합니다.
---

> **TL;DR** 여러 계층의 설정이 존재할 때,
> **가장 가까운(구체적인) 설정이 먼(일반적인) 설정을 덮어쓰는** 패턴입니다.
> CSS specificity, Git config, Spring property override 모두 같은 원리입니다.
{: .prompt-tip }

## 핵심 원리

- **계층 우선순위**: 로컬 > 프로젝트 > 글로벌 > 기본값 순으로 적용됩니다
- **부분 덮어쓰기**: 하위 계층은 상위 계층 전체를 대체하지 않고,
  지정된 키만 덮어씁니다
- **폴백(Fallback)**: 하위 계층에 값이 없으면
  상위 계층 값을 그대로 사용합니다

## 실무 적용

CLI 도구의 환경변수 설정에 적용했습니다.

| 계층 | 경로 | 용도 |
|------|------|------|
| 로컬 | `.env` (프로젝트 루트) | 프로젝트 전용 설정 |
| 글로벌 | `~/.config/.env` | 개인 기본 설정 |

로딩 로직은 로컬 파일이 있으면 로컬을 사용하고,
없으면 글로벌로 폴백합니다.

```bash
ENV_FILE=$( [ -f .env ] && echo ".env" || echo "$HOME/.config/.env" )
```

### Spring Boot 설정 캐스케이드

Spring Boot도 같은 원리로 동작합니다.
같은 키를 여러 소스에서 선언하면, 가까운 쪽이 이깁니다.

| 우선순위 | 소스 | 예시 |
|---------|------|------|
| 1 (최고) | 커맨드라인 인자 | `--server.port=9090` |
| 2 | 환경변수 | `SERVER_PORT=9090` |
| 3 | profile YAML | `application-dev.yml` |
| 4 (최저) | 기본 YAML | `application.yml` |

```yaml
# application.yml — 기본값
server:
  port: 8080
  servlet:
    context-path: /api

# application-dev.yml — port만 덮어씁니다
server:
  port: 8081
```

`dev` 프로필로 실행하면 port는 8081이 되고,
context-path는 기본값 `/api`를 그대로 씁니다.
port는 부분 덮어쓰기, context-path는 폴백 —
캐스케이드의 두 축이 동시에 작동합니다.

*이 글은 Claude의 도움을 받아 작성했습니다.*
