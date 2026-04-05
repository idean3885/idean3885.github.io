---
title: "*.github.io에서 벗어나니 사이트맵이 바로 됐다 — 커스텀 도메인과 GA4"
date: 2026-04-05 15:00:00 +0900
categories: [기술 노하우, 블로그]
tags: [GitHub Pages, Google Search Console, GA4, 커스텀 도메인, Cloudflare, SEO]
description: >-
  GSC 사이트맵 인식 불가 2개월, 원인은 *.github.io 도메인이었습니다.
  커스텀 도메인 연결로 즉시 해소한 과정과
  GA4 도입까지 정리합니다.
---

> **TL;DR**
> GitHub Pages의 `*.github.io` 도메인에서 GSC(Google Search Console) 사이트맵이 2개월간 "읽을 수 없음" 상태였습니다.
> 기술적으로는 모두 정상이었고, 커스텀 도메인을 연결하자 즉시 해소되었습니다.
> 같은 시점에 GA4(Google Analytics 4)도 도입하여 검색 노출(GSC)과 방문자 행동(GA4) 양쪽을 볼 수 있게 되었습니다.
{: .prompt-tip }

## 배경 — 색인이 안 되고 있었다

[GEO 대응 포스트](https://blog.idean.me/posts/geo-for-dev-blog/)에서 블로그의 SEO/GEO 인프라를 점검했을 때,
기술적으로는 모두 정상이었습니다.
JSON-LD, sitemap.xml, robots.txt — 전부 갖춰져 있었습니다.

문제는 **Google이 사이트맵을 읽지 못한다**는 것이었습니다.

GSC에서 사이트맵을 제출하면 매번 같은 결과가 돌아왔습니다.

| 항목 | 상태 |
|------|------|
| 사이트맵 상태 | "사이트맵을 읽을 수 없음" |
| 발견된 페이지 | 0 |
| 마지막 읽은 날짜 | 2026-03-20에서 멈춤 |

2월 19일에 최초 제출한 뒤 2개월간 같은 상태가 지속되었습니다.

## 기술적으로는 모두 정상이었다

원인을 찾기 위해 가능한 것을 모두 확인했습니다.

| 점검 항목 | 결과 |
|----------|------|
| XML 유효성 (xmllint) | 통과 |
| HTTP 응답 | 200, `application/xml` |
| BOM / 빈 줄 | 없음 |
| Googlebot UA 접근 | 200 |
| IPv6 접근 | 200 |
| 리다이렉트 | 없음 |
| noindex / nofollow | 없음 |
| robots.txt | Sitemap 경로 명시 |
| 사이트맵 내 URL | 전부 200 |

모든 항목이 정상이었습니다.
XML namespace를 단순화하고, 사이트맵을 `jekyll-sitemap` 플러그인 자동 생성으로 교체하고,
수동 색인 요청도 해봤지만 결과는 같았습니다.

## 원인 — `*.github.io` 도메인 자체의 문제

Chirpy 테마의 이슈 트래커([#2658](https://github.com/cotes2020/jekyll-theme-chirpy/issues/2658))에서 같은 현상이 보고되어 있었습니다.
`*.github.io` 도메인에서 GSC 사이트맵 인식이 실패하는 알려진 문제였고,
**커스텀 도메인을 연결하면 즉시 해결된다**는 것이 확인된 해결책이었습니다.

2개월간 기술적 원인을 파고들었지만,
결국 도메인을 바꾸는 것 외에는 방법이 없었습니다.

## 도메인 선택 — `.dev` vs `.me`

커스텀 도메인을 결정할 때 두 가지를 고려했습니다.

**용도 확장성**: 블로그 외에 트래블 플래너 등 개인 서비스에도 서브도메인을 쓸 계획이 있었습니다.

| 후보 | 서브도메인 예시 | 판단 |
|------|--------------|------|
| `idean3885.dev` | `travel.idean3885.dev` | 비개발 서비스에 어색 |
| `idean.me` | `travel.idean.me` | 용도 무관하게 자연스러움 |

**장기 사용**: 도메인은 한번 사면 바꾸기 어렵습니다.
`.dev`는 개발자일 때만 의미가 있지만, `.me`는 방향이 바뀌어도 유효합니다.

`idean.me`를 선택했습니다.
연 $4 차이(`.dev` 대비)로, 10년이면 $40 — 유연성 대비 저렴한 투자입니다.

## 연결 과정

### 1. Cloudflare에서 도메인 구매

Cloudflare를 선택한 이유는 도메인 원가 판매(마크업 없음)와 DNS 관리가 한 곳에서 되기 때문입니다.

### 2. DNS 설정

Cloudflare DNS에 CNAME 레코드를 추가했습니다.

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | blog | idean3885.github.io | DNS only |

> Proxy status를 반드시 **DNS only**(회색 구름)로 설정해야 합니다.
> GitHub Pages의 SSL 인증서 발급에 필요합니다.
{: .prompt-warning }

### 3. GitHub Pages 설정

GitHub 레포 Settings > Pages에서 Custom domain에 `blog.idean.me`를 입력하고,
Enforce HTTPS를 활성화했습니다.

### 4. 블로그 레포 변경

```yaml
# _config.yml
url: "https://blog.idean.me"
```

루트에 `CNAME` 파일을 추가하고, `llms.txt`와 `CLAUDE.md`의 URL도 일괄 변경했습니다.

기존 `idean3885.github.io`로의 접근은 자동으로 `blog.idean.me`로 301 리다이렉트됩니다.
이미 공유된 링크나 이력서의 URL이 깨질 걱정은 없습니다.

## 결과 — 사이트맵 즉시 성공

배포 후 GSC에 사이트맵을 제출했습니다.

2개월간 "읽을 수 없음"이었던 사이트맵이 **즉시 성공**했습니다.

원인이 기술적 설정이 아니라 도메인 자체에 있었다는 것이 확인된 순간이었습니다.

## GA4 도입 — 검색 노출 너머의 데이터

사이트맵이 해소되면서 색인이 시작될 예정이고,
이 시점에 방문자 행동 분석도 함께 시작하기로 했습니다.

### GSC vs GA4

| 도구 | 보는 것 | 범위 |
|------|---------|------|
| GSC | 어떤 키워드로 노출/클릭됐는지 | 블로그 **밖** (검색 → 클릭) |
| GA4 | 누가, 얼마나 머물렀는지, 어떤 글이 인기인지 | 블로그 **안** (클릭 → 이탈) |

GSC만으로도 검색 노출은 파악할 수 있지만,
"글을 끝까지 읽었는지", "다른 글로 이어갔는지" 같은 행동 데이터는 GA4가 필요합니다.

### Chirpy에서의 GA4 적용

Chirpy 테마는 GA4를 내장 지원합니다.
`_config.yml`에 측정 ID 한 줄이면 gtag.js가 자동 삽입됩니다.

```yaml
analytics:
  google:
    id: G-HRWXK11B6L
```

별도 코드 삽입이나 태그 관리 없이,
페이지뷰·스크롤 90% 도달·이탈 클릭 같은 기본 이벤트가 자동 수집됩니다.

## 정리

| 항목 | Before | After |
|------|--------|-------|
| 도메인 | `idean3885.github.io` | `blog.idean.me` |
| GSC 사이트맵 | 2개월 "읽을 수 없음" | 즉시 성공 |
| 분석 도구 | GSC만 | GSC + GA4 |
| 비용 | 무료 | 연 ~$16 (도메인) |

2개월간 기술적 원인을 파고들었지만 답은 도메인에 있었습니다.
무료에 집착하기보다 연 $16으로 문제를 해소하고,
같은 시점에 GA4까지 도입하여 데이터 기반을 갖추게 되었습니다.

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
