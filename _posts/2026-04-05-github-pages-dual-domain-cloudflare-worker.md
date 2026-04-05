---
title: "GitHub Pages 이중 도메인 구성기 — Cloudflare Worker로 QR코드와 커스텀 도메인 양립시키기"
date: 2026-04-05 20:00:00 +0900
categories: [기술 노하우, 실무 노하우]
tags: [GitHub Pages, Cloudflare, DNS, 도메인]
description: >-
  GitHub Pages에서 QR코드용 기존 도메인을 유지하면서
  깔끔한 커스텀 도메인을 추가한 과정을 정리합니다.
  Cloudflare DNS 프록시 모드와 Workers를 처음 써보며 겪은 삽질 기록입니다.
---

> **TL;DR**
> GitHub Pages는 리포지토리당 커스텀 도메인을 1개만 지원합니다.
> QR코드에 찍힌 기존 도메인을 살리면서 짧은 커스텀 도메인을 추가하기 위해
> Cloudflare Workers 무료 플랜으로 리버스 프록시를 구성했습니다.
{: .prompt-tip }

## 배경

모바일 청첩장을 SvelteKit + GitHub Pages로 운영하고 있었습니다.
커스텀 도메인은 AppPaaS에서 발급받은 긴 주소였습니다.

```
j4df09bd732eb302e05d225dd6ae40649.apppaas.app
```

실물 청첩장의 QR코드에 이 주소가 인쇄되어 있어서 변경이 불가능한 상태였습니다.
카카오톡으로 공유할 때 이 URL이 그대로 노출되는 게 마음에 걸렸고,
별도로 구매한 도메인(`wedding.idean.me`)을 사용하고 싶었습니다.

## 목표

- `wedding.idean.me`로 접속하면 청첩장이 보이고, URL 바에도 이 주소가 유지될 것
- `j4...apppaas.app` QR코드 링크는 그대로 동작할 것

## GitHub Pages의 제약

GitHub Pages는 **리포지토리당 커스텀 도메인을 1개만** 지원합니다.
`static/CNAME` 파일에 도메인을 지정하면 GitHub Pages가 해당 도메인으로 들어오는 요청만 서빙합니다.

```
// static/CNAME
j4df09bd732eb302e05d225dd6ae40649.apppaas.app
```

CNAME을 `wedding.idean.me`로 바꾸면 QR코드 도메인이 죽고,
그대로 두면 커스텀 도메인을 쓸 수 없습니다.
단순한 DNS 설정만으로는 해결할 수 없는 구조적 제약이었습니다.

## 시행착오

### 1차: CNAME 변경 → QR코드 도메인 사망

가장 먼저 시도한 것은 CNAME을 `wedding.idean.me`로 바꾸는 것이었습니다.
DNS 설정도 변경하고 배포까지 마쳤지만,
QR코드 도메인(`apppaas.app`)으로 접속하면 404가 나왔습니다.

GitHub Pages가 더 이상 해당 도메인을 인식하지 못했기 때문입니다.

### 2차: AppPaaS DNS 변경 → SSL 핸드셰이크 실패

AppPaaS 도메인의 CNAME을 `wedding.idean.me`로 변경해봤습니다.

```
apppaas.app → wedding.idean.me → Cloudflare → ???
```

Cloudflare 프록시를 거치게 되면서 SSL 인증서 불일치로 **525 에러**가 발생했습니다.
Cloudflare의 프록시 모드(주황색 구름)는 트래픽을 Cloudflare 엣지를 거쳐 보내는데,
origin 서버(GitHub Pages)의 SSL 인증서가 해당 도메인용이 아니면 핸드셰이크가 실패합니다.

### 3차: Worker로 GitHub Pages 직접 프록시 → 블로그가 나옴

Cloudflare Workers로 `idean3885.github.io`에 직접 프록시하는 방식을 시도했습니다.

```javascript
const response = await fetch(targetUrl, {
  headers: { Host: 'wedding.idean.me' },
});
```

결과는 청첩장 대신 **블로그**가 나왔습니다.
같은 `idean3885.github.io`에 블로그(`blog.idean.me`)와 청첩장(`wedding.idean.me`)이 모두 연결되어 있었고,
GitHub Pages가 Worker를 통한 Host 헤더 변경을 기대한 대로 라우팅하지 않았습니다.

## 최종 해결: Worker → AppPaaS → GitHub Pages

결국 가장 단순한 구조가 답이었습니다.

1. CNAME은 `apppaas.app` 도메인을 유지 (QR코드 호환)
2. AppPaaS DNS는 `idean3885.github.io`를 직접 가리킴 (원래 구조 복원)
3. Cloudflare Worker가 `wedding.idean.me` 요청을 `apppaas.app`으로 프록시

```javascript
// workers/wedding-proxy/src/index.js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = 'https://j4df09bd732eb302e05d225dd6ae40649.apppaas.app';
    const targetUrl = origin + url.pathname + url.search;

    const response = await fetch(targetUrl, {
      method: request.method,
      headers: {
        ...Object.fromEntries(request.headers),
        Host: 'j4df09bd732eb302e05d225dd6ae40649.apppaas.app',
      },
    });

    return new Response(response.body, response);
  },
};
```

```toml
# workers/wedding-proxy/wrangler.toml
name = "wedding-proxy"
main = "src/index.js"
compatibility_date = "2024-01-01"

routes = [
  { pattern = "wedding.idean.me/*", zone_name = "idean.me" }
]
```

### 최종 아키텍처

```
wedding.idean.me → Cloudflare Worker → apppaas.app → GitHub Pages (프록시, URL 유지)
apppaas.app      → DNS(CNAME)       → idean3885.github.io → GitHub Pages (직접)
```

### DNS 설정

| 도메인 | 형식 | 대상 | 프록시 |
|--------|------|------|--------|
| `wedding.idean.me` | CNAME | `idean3885.github.io` | 프록싱됨 (주황색 구름) |
| `blog.idean.me` | CNAME | `idean3885.github.io` | DNS 전용 (회색 구름) |
| `apppaas.app` | CNAME | `idean3885.github.io` | - (AppPaaS 관리) |

핵심은 **프록시 모드의 차이**입니다.
`wedding`은 주황색 구름(프록싱됨)이어야 Cloudflare Worker가 개입할 수 있고,
`blog`은 회색 구름(DNS 전용)이어야 GitHub Pages가 직접 서빙합니다.

## 배운 것

### Cloudflare DNS: 프록시 모드 vs DNS 전용

Cloudflare DNS에서 레코드를 추가할 때 주황색 구름과 회색 구름을 선택할 수 있습니다.

- **DNS 전용 (회색 구름)**: 순수 DNS 역할만 수행. 클라이언트가 origin 서버에 직접 연결
- **프록싱됨 (주황색 구름)**: 트래픽이 Cloudflare 엣지를 거침. Workers, Page Rules, 캐시 등 Cloudflare 기능 사용 가능

GitHub Pages처럼 자체 SSL 인증서를 발급하는 서비스는 DNS 전용이 안전합니다.
프록시 모드에서는 Cloudflare가 중간에서 SSL을 처리하기 때문에 인증서 충돌이 생길 수 있습니다.

### Cloudflare Workers 무료 플랜

Workers 무료 플랜은 일 10만 요청을 제공합니다.
청첩장처럼 트래픽이 적은 사이트에는 충분합니다.
`wrangler` CLI로 로컬에서 바로 배포할 수 있어 편리합니다.

```bash
npx wrangler login
npx wrangler deploy
```

### GitHub Pages의 Host 헤더 라우팅

GitHub Pages는 `username.github.io` 도메인으로 여러 리포지토리의 커스텀 도메인을 서빙합니다.
어떤 사이트를 보여줄지는 **요청의 Host 헤더**로 결정합니다.

하지만 외부 프록시에서 Host 헤더를 변조해서 보내는 경우,
GitHub Pages의 CDN 캐시 레이어에서 기대와 다른 사이트가 응답될 수 있습니다.
이번 경우에도 Worker에서 `Host: wedding.idean.me`를 보냈지만 블로그가 응답됐습니다.

이미 동작하는 도메인(`apppaas.app`)을 경유하는 것이 가장 확실한 방법이었습니다.

## 마무리

"도메인 하나 추가하는 건데 뭐가 어렵겠어"로 시작한 작업이
CNAME 변경 → SSL 에러 → 블로그 노출 → DNS 꼬임을 거쳐
결국 Cloudflare Worker까지 도입하는 여정이 됐습니다.

GitHub Pages의 단일 커스텀 도메인 제약은 문서에 명시되어 있지만,
실제로 부딪혀봐야 체감되는 제약이었습니다.
Cloudflare Workers는 이런 틈새 문제를 무료로 해결할 수 있는 좋은 도구였습니다.
