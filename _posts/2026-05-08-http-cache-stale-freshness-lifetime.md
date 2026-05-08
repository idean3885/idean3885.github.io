---
title: "HTTP 캐시 stale 차단: PUT 덮어쓰기와 freshness lifetime"
date: 2026-05-08 16:56:23 +0900
categories: [기술 노하우, 개발 사전]
tags: [HTTP, Cache-Control, RFC9111, 개발사전]
description: >-
  같은 키로 PUT 후 같은 URL을 브라우저로 재방문하니 v1이 응답되는 stale 회귀를 만났습니다.
  RFC 9111의 heuristic freshness가 진입되어 발생한 문제로,
  Cache-Control 디렉티브 설정으로 차단했습니다.
---

> **TL;DR**<br>
> 객체 스토리지(OpenStack Swift)에 파일을 같은 키로 덮어쓰기 PUT한 후, 사용자가 같은 TempURL(짧은 유효 시간의 서명 다운로드 URL)로 재방문하니 이전 컨텐츠가 응답되는 stale 회귀를 만났습니다.
> 원인은 Cache-Control 미설정 시 RFC 9111의 heuristic freshness가 진입되어 브라우저가 자체 freshness lifetime을 부여한 것이었습니다.<br>
> PUT 응답에 `Cache-Control: no-cache, no-store, must-revalidate`를 설정하면 차단됩니다.
{: .prompt-tip }

## 문제

객체 스토리지에 파일을 같은 키로 덮어쓰기 PUT한 후, 같은 TempURL을 브라우저에서 재방문하니 이전 컨텐츠가 응답됐습니다. 테스트 환경에서 e2e로 재현했습니다.

```text
[1] PUT  /v1/.../a.csv  (content: v1)         -> 201
[2] GET  /v1/.../a.csv?temp_url_sig=...       -> v1
[3] PUT  /v1/.../a.csv  (content: v2 덮어쓰기) -> 201
[4] GET  같은 TempURL                          -> v1 (stale)  ❌
```

기대했던 동작: [4]에서 v2가 응답되어야 합니다. 실제로 본 결과: v1이 그대로 응답됐습니다.

> `stale`: 갱신본이 있는데도 이전 응답이 반환되는 캐시 상태 (RFC 9111 freshness 모델).
{: .prompt-info }

## 어디서 stale이 발생하는가

가능한 위치 3개:

1. Swift 자체가 eventual consistency로 v1 보유
2. 저장소 앞단 CDN/Edge 캐시
3. 브라우저 HTTP 캐시

curl로 같은 TempURL을 직접 GET하니 v2가 응답됐습니다 (정상). Swift와 앞단 인프라는 최신 컨텐츠를 반환했습니다.

웹 브라우저(Chromium)에서 같은 TempURL을 주소창에 입력해 요청하니 v1이 응답됐습니다.

원인은 **브라우저 HTTP 캐시**였습니다. 다른 가설은 모두 검증 후 제외했습니다.

## 근본 원인: heuristic freshness

> `heuristic freshness`: 응답에 Cache-Control이 없을 때 캐시가 Last-Modified를 기준으로 freshness lifetime을 임의 부여하는 동작 (RFC 9111의 4.2.2절).
{: .prompt-info }

브라우저는 같은 URL 재방문 시 캐시 항목이 **fresh**라고 판정하면 원본 서버(origin) 도달 자체를 안 합니다. fresh 판정은 RFC 9111의 4.2절 freshness 모델을 따릅니다.

```text
fresh:  age < freshness_lifetime
stale:  age >= freshness_lifetime
```

`freshness_lifetime` 결정 우선순위:

1. `Cache-Control: s-maxage=N` (shared cache 한정)
2. `Cache-Control: max-age=N`
3. `Expires` 헤더
4. heuristic freshness (RFC 9111의 4.2.2절)

PUT 응답을 확인하니 Cache-Control과 Expires 둘 다 없었습니다. 1~3번이 빠진 상태라 4번 heuristic이 적용된 것이라고 예상하고 추적했습니다.

heuristic freshness 가이드 (RFC 권고):

```text
heuristic_lifetime = (response_time - Last-Modified) * 0.10
```

Swift는 PUT 시 `Last-Modified`를 자동 반환합니다. heuristic 기준점이 항상 존재하므로 항상 freshness lifetime이 부여되고, 짧은 PUT-GET 간격에서도 fresh로 판정될 수 있습니다.

> **흔한 오해**: "Cache-Control 없으면 캐시 안 됨"은 사실이 아닙니다. heuristic으로 캐시됩니다.
{: .prompt-warning }

## 재검증이 왜 안 됐는가

캐시가 stale로 판정되면 보통 conditional GET이 나갑니다.

```text
GET ... If-None-Match: "v1-etag"
 |
 v
origin: 304 Not Modified (응답 본문 동일)
        or
        200 OK + 새 응답 본문 (응답 본문 변경)
```

Swift는 PUT마다 ETag를 새로 발급합니다 (컨텐츠 해시 기반). v2 PUT 후 ETag가 변경되어 conditional GET이 발생했다면 200 OK + v2 컨텐츠를 받았어야 합니다.

그러나 브라우저가 fresh 판정을 내려서 conditional GET 자체를 보내지 않았습니다. 그래서 ETag 변경을 알아챌 기회 자체가 없었습니다.

## 수정: 디렉티브 설정으로 heuristic 진입 차단

PUT 요청에 `Cache-Control: no-cache, no-store, must-revalidate`를 설정하여 Swift 응답 메타에 반영시켰습니다 (Swift는 PUT 시 받은 Cache-Control을 응답 헤더로 보존).

각 디렉티브 의미 (RFC 9111의 5.2.2절):

| 디렉티브 | 의미 |
|---------|------|
| `no-cache` | 저장 허용. 단, 매 사용 전 원본 서버 재검증 필수 |
| `no-store` | 저장 금지 |
| `must-revalidate` | stale이면 재검증 강제. 오프라인이라도 stale 응답 금지 |

> **이름 함정**: `no-cache`는 "캐시 안 함"이 아닙니다. 저장은 허용하지만 매 사용 전 재검증을 강제합니다. 진짜 저장 금지는 `no-store`.
{: .prompt-warning }

세 디렉티브 동시 설정 이유:

- `no-cache`: 저장됐더라도 매 사용 전 재검증 강제
- `no-store`: 저장 자체 차단 (가장 직접적)
- `must-revalidate`: 캐시 구현체가 max-stale 등으로 stale 응답하는 케이스까지 차단

방어를 3중으로 둔 셈입니다.

## 결과와 재실측

테스트 환경에서 동일 시나리오 재실측:

```text
[1] PUT  /a.csv (v1, Cache-Control: no-cache, no-store, must-revalidate) -> 201
[2] HEAD /a.csv -> cache-control 응답 메타에 반영 확인
[3] GET  TempURL (브라우저) -> v1
[4] PUT  /a.csv (v2, 같은 헤더) -> 201
[5] GET  같은 TempURL (브라우저) -> v2 ✅
```

PUT 응답에 Cache-Control이 반영되어 브라우저가 heuristic freshness 진입을 안 했고 매 요청 원본 서버 재검증으로 v2를 받았습니다.

## 회고

캐시 디렉티브를 설정하지 않으면 캐시되지 않을 거라 짐작했지만, RFC 9111의 heuristic freshness가 이 가정을 깹니다. PUT 응답에 Cache-Control을 명시하는 습관이 stale 회귀의 근본 차단선입니다.

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
