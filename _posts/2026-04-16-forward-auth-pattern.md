---
title: "Forward Auth 패턴: API Gateway의 인가 위임 방식"
date: 2026-04-16 19:14:00 +0900
categories: [기술 노하우, 개발 사전]
tags: [아키텍처, 개발사전]
description: >-
  Forward Auth는 API Gateway가 요청을 백엔드로 전달하기 전에,
  외부 인증/인가 서비스에 서브리퀘스트로 판정을 위임하는 패턴입니다.
---

> **TL;DR**<br>
> Forward Auth는 API Gateway가 요청을 백엔드로 전달하기 전에,
> 외부 인증/인가 서비스에 서브리퀘스트로 판정을 위임하는 패턴입니다.<br>
> 파일 스트리밍 등 데이터 전송 구간에 Auth 서비스가 끼지 않아
> 대역폭 병목이 발생하지 않습니다.
{: .prompt-tip }

## 패턴 정의

Forward Auth는 Gateway가 직접 인증/인가를 처리하지 않고,
별도 서비스에 "이 요청을 허용할까요?"라는 서브리퀘스트를 보내는 위임 패턴입니다.

핵심은 **데이터 경로와 인가 경로의 분리**입니다.

```text
[일반 프록시]
Client → GW → Auth → Backend     ← Auth가 데이터 경로에 있음

[Forward Auth]
Client → GW ─┬→ Auth (서브리퀘스트, 판정만)
              └→ Backend (원본 요청 전달)  ← Auth가 데이터 경로에 없음
```

## 동작 흐름

```text
1. Client → GW        : 원본 요청 도착
2. GW → Auth           : 서브리퀘스트 (헤더만 전달, 바디 미포함)
3. Auth → GW           : 200 OK (허용) 또는 401/403 (거부)
4. GW → Backend        : 허용 시 원본 요청 그대로 전달
```

- 2번에서 GW는 요청 바디를 Auth로 보내지 않습니다.
  헤더(Authorization, Cookie 등)만 전달합니다.
- Auth의 응답 헤더를 백엔드에 전파할 수 있습니다.
  (예: `X-User-Id`, `X-Permissions`)
- 거부 시 GW가 클라이언트에 직접 에러를 반환합니다.

## 스트리밍과 병목

Forward Auth에서 파일 업로드/다운로드 스트리밍 데이터는
Auth 서비스를 경유하지 않습니다.
GW가 Auth에 보내는 것은 헤더뿐이고,
인가 판정 후 원본 요청(바디 포함)은 백엔드로 직접 전달됩니다.

따라서 Auth 서비스의 처리량이 파일 전송 대역폭에 영향을 주지 않습니다.

## GW별 구현체

| Gateway | 구현체 | 타입 |
|---------|--------|------|
| APISIX | `forward-auth` | 플러그인 |
| Traefik | `forwardAuth` | 미들웨어 |
| NGINX | `auth_request` | 모듈 |
| Envoy | `ext_authz` | 필터 |
| Kong | `forward-auth` (커뮤니티) | 플러그인 |

이름은 다르지만 동작 원리는 동일합니다.
GW가 서브리퀘스트로 판정을 받고,
결과에 따라 원본 요청을 전달하거나 거부합니다.

## 적용 사례: 파일 서비스

파일 서비스에서는 APISIX `forward-auth` 플러그인으로
플랫폼 Auth에 인가를 위임합니다.

```text
Browser → LB → APISIX ─┬→ 플랫폼 Auth (인가 확인)
                        └→ 파일 서비스 BE (파일 전송)
```

- 인증: BE가 JWKS 기반으로 JWT를 로컬 검증 (GW 미관여)
- 인가: APISIX가 플랫폼 Auth에 forward-auth로 위임
- 파일 스트리밍: APISIX → BE 직접 전달, Auth 미경유

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
