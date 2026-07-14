---
title: "Chirpy 블로그 운영: SEO·GEO·댓글·커스텀 도메인까지"
date: 2026-05-17 22:40:00 +0900
last_modified_at: 2026-05-18 15:05:00 +0900
categories: [기술 노하우]
tags: [Jekyll, Chirpy, SEO, GEO, Giscus, GitHub Pages, GA4, 커스텀 도메인]
description: "Jekyll Chirpy 블로그의 SEO·GEO·댓글·커스텀 도메인·GA4 운영 과정을 정리합니다."
redirect_from:
  - /posts/chirpy-seo-and-search-console/
  - /posts/geo-for-dev-blog/
  - /posts/giscus-comments-on-static-blog/
  - /posts/custom-domain-gsc-ga4/
---

> **TL;DR**<br>
> Chirpy 테마는 SEO 기본기·OG 태그·sitemap·robots.txt·JSON-LD를 자동 생성하므로 추가 설정이 거의 없습니다.<br>
> GEO 대응도 새 기법보다 누락된 기본기(JSON-LD author, llms.txt, last_modified_at) 보완이 핵심이었습니다.<br>
> Giscus 댓글은 `_config.yml` 13줄, 커스텀 도메인은 `*.github.io` 의 GSC 사이트맵 인식 한계를 즉시 해소했습니다.
{: .prompt-tip }

## 1. SEO: Chirpy가 이미 다 하고 있었다

블로그를 시작하고 SEO를 점검했습니다. 메타태그·OG·sitemap·robots.txt·JSON-LD 를 직접 설정해야 한다고 생각했는데 결론은 **대부분 이미 되어 있었습니다**.

Chirpy 테마는 두 플러그인을 기본 의존성으로 포함합니다.

| 플러그인 | 역할 |
|---|---|
| `jekyll-seo-tag` | 메타태그·OG·JSON-LD 자동 생성 |
| `jekyll-sitemap` | sitemap.xml·robots.txt 자동 생성 |

별도 설치한 적 없지만 `Gemfile.lock` 에 이미 포함되어 있습니다. front matter 에 `title`·`date`·`description` 만 쓰면 나머지는 전부 자동입니다.

### 점검 결과

| 항목 | 상태 | 비고 |
|---|---|---|
| og:* / canonical / meta description | 자동 | jekyll-seo-tag |
| sitemap.xml / robots.txt | 자동 | jekyll-sitemap |
| JSON-LD (BlogPosting) | 자동 | jekyll-seo-tag |
| og:image | 미설정 | 포스트에 `image` 필드 없음 |
| Google Search Console | 미등록 | 인증 필요 |

### GSC 등록은 `_config.yml` 한 줄

GSC 에서 HTML 메타 태그 인증을 선택하면 받은 `content` 값을 `_config.yml` 한 줄에 명시하면 끝.

```yaml
webmaster_verifications:
  google: abc123xyz
```

배포하면 모든 페이지의 `<head>` 에 인증 태그가 자동 주입됩니다. 인증 후 좌측 메뉴 → Sitemaps → `sitemap.xml` 입력 → 제출. jekyll-sitemap 이 이미 파일을 생성하므로 URL 만 등록하는 절차입니다.

> 인증 태그는 영구 유지해야 합니다. 삭제하면 수개월 후 소유권이 취소될 수 있습니다.
{: .prompt-danger }

## 2. GEO: 새 기법보다 누락된 기본기

[요즘IT 콘텐츠 AX 실험기](https://yozm.wishket.com/magazine/detail/3647/) 에서 GEO(Generative Engine Optimization) 를 접했습니다. AI 검색엔진(Claude·Gemini·ChatGPT 등) 이 콘텐츠를 인용하도록 최적화하는 전략.

### 근거 점검

바로 적용하기 전에 학술적 근거부터 확인했습니다. IIT Delhi·Princeton 의 ["GEO: Generative Engine Optimization"](https://arxiv.org/abs/2311.09735) (ACM KDD 2024) 가 10,000개 쿼리로 9가지 전략을 테스트했습니다.

| 전략 | 가시성 향상 |
|---|---|
| 통계 추가 | ~41% |
| 인용구 삽입 | ~37% |
| 출처 명시 | ~31% |
| 키워드 스터핑 | 오히려 감소 |

Yext 의 6.8M 인용 분석(2025.10) 에 따르면 AI Overviews URL 과 Google 1위 결과의 중복률은 **4.5%에 불과**. SEO 와 GEO 는 별개입니다.

다만 SandboxSEO 가 GEO 논문 방법론을 비판한 지점도 유효합니다. 상위 3개 전략이 모두 새 정보를 추가하는 방식이라 GEO 효과인지 단순 콘텐츠 양 증가 효과인지 구분할 수 없다는 지적, 그리고 AI 플랫폼의 인용 변동성이 월 40~60% 라는 점.

**개념은 유효하나 수치 효과는 회의적으로 봐야 합니다.**

### 발견한 누락: JSON-LD author

실제 출력을 확인하니 이랬습니다.

```json
{ "@type": "BlogPosting", "headline": "...", "datePublished": "...", "dateModified": "..." }
```

`author` 와 `publisher` 가 없었습니다. `_config.yml` 에 `author` 필드가 없었기 때문. SEO·GEO 양쪽 모두에서 기본 누락이었습니다.

### 저비용 적용 3가지

대규모 구조 변경은 근거 대비 투자가 과합니다. 저비용으로 SEO/GEO 공통 기본기만 보완했습니다.

**(1) `_config.yml` 에 author 와 logo 추가**

```yaml
author: idean3885
logo: /assets/img/favicons/favicon-96x96.png
```

jekyll-seo-tag 가 `author` → `Person`, `logo` → `publisher.Organization` 으로 JSON-LD 를 채웁니다.

**(2) `llms.txt` 추가** ([llmstxt.org](https://llmstxt.org/) 규격, 루트 배치)

```markdown
# idean3885.github.io
> 개발자의 기술적 탐구, 방법론의 진화, 운영 노하우와 의사결정의 기록.

## 카테고리
- 개발 기록: 프로젝트 경험기, 도구 적응기
- 기술 노하우: 운영 경험 기반 실전 지식
```

**(3) `last_modified_at` 수정 규칙**

포스트 수정 시 front matter 에 `last_modified_at` 을 기재. jekyll-seo-tag 가 이 값을 JSON-LD `dateModified` 에 반영합니다. 웹에는 안 보이지만 검색엔진·AI 에는 freshness 신호로 작용.

### Chirpy 자체가 이미 GEO 친화적

조사하면서 놀란 점. Chirpy 테마와 기존 작성 규칙이 이미 GEO 권장 패턴과 상당히 겹칩니다.

| 기존 규칙 | GEO 관점 효과 |
|---|---|
| TL;DR 필수 (`.prompt-tip`) | AI 가 추출할 "직접 답변" 패턴 |
| H2 부터 시작, TOC 자동 생성 | 패시지 추출 단위가 명확 |
| 코드 블록 언어 명시 | 기술 콘텐츠 신뢰도 신호 |
| 카테고리 2단계 계층 | 콘텐츠 맥락 파악 용이 |

"새로운 최적화 기법"보다 **기본기를 먼저 챙기는 것**이 답이었습니다.

## 3. Giscus 댓글: 13줄 설정 + App 설치 함정

"정적 페이지인데 댓글이 어떻게 되지?" 가 첫 반응이었습니다. 알아보니 [Giscus](https://giscus.app) (GitHub Discussions 기반 위젯) 가 답.

### 동작 원리

```text
브라우저 → Giscus iframe → GitHub OAuth2 → GraphQL API → Discussions
```

GitHub 저장소의 Discussions 탭을 댓글 저장소로 사용. 정적 HTML 자체는 변하지 않고 클라이언트가 GitHub API 로 직접 통신합니다. Git 커밋 로그에 댓글이 남지 않고 댓글 100개가 달려도 코드에 영향이 없습니다.

비용은 전부 0원 (GitHub Discussions·Giscus·OAuth2·GraphQL API).

### Chirpy 설정 (13줄)

Chirpy 는 Giscus 를 기본 지원합니다. `_config.yml` 에 두 가지만 추가.

```yaml
defaults:
  - scope: { path: "", type: posts }
    values:
      layout: post
      comments: true    # false → true

comments:
  provider: giscus
  giscus:
    repo: idean3885/idean3885.github.io
    repo_id: R_kgDORQ49gw
    category: General
    category_id: DIC_kwDORQ49g84C59HT
    mapping: pathname
    lang: ko
    input_position: bottom
    reactions_enabled: 1
```

`repo_id`·`category_id` 는 [giscus.app](https://giscus.app/ko) 에서 자동 발급. `mapping: pathname` 은 포스트 URL 경로별로 Discussion 스레드를 자동 생성.

### 빠뜨리기 쉬운 함정

배포 후 첫 시도에서 이 에러가 떴습니다.

> 오류 발생: giscus is not installed on this repository

`_config.yml` 외에 [Giscus GitHub App](https://github.com/apps/giscus) 설치가 추가로 필요. 설치 후 새로고침하면 정상 동작합니다.

## 4. 커스텀 도메인: `*.github.io` 의 GSC 사이트맵 함정

GEO 점검 시점에서 모든 기술 인프라가 정상이었는데 정작 GSC 사이트맵이 **2개월간 "읽을 수 없음"** 이었습니다.

### 모든 점검 통과

| 점검 항목 | 결과 |
|---|---|
| XML 유효성 (xmllint) | 통과 |
| HTTP 응답 | 200, `application/xml` |
| BOM / 빈 줄 | 없음 |
| Googlebot UA / IPv6 접근 | 200 |
| robots.txt | Sitemap 경로 명시 |
| 사이트맵 내 URL | 전부 200 |

모든 항목이 정상이었습니다. XML namespace 단순화, jekyll-sitemap 자동 생성 교체, 수동 색인 요청, 결과는 같았습니다.

### 원인: `*.github.io` 도메인 자체

Chirpy 이슈 트래커 [#2658](https://github.com/cotes2020/jekyll-theme-chirpy/issues/2658) 에서 같은 현상이 보고되어 있었습니다. `*.github.io` 에서 GSC 사이트맵 인식이 실패하는 알려진 문제. **커스텀 도메인을 연결하면 즉시 해결**된다는 것이 확인된 해결책.

### 도메인 선택: `.dev` vs `.me`

용도 확장성을 고려했습니다. 블로그 외에 개인 서비스용 서브도메인 계획이 있었습니다.

| 후보 | 서브도메인 예시 | 판단 |
|---|---|---|
| `idean3885.dev` | `travel.idean3885.dev` | 비개발 서비스에 어색 |
| `idean.me` | `travel.idean.me` | 용도 무관하게 자연스러움 |

`idean.me` 선택. 연 $4 차이(`.dev` 대비) 로 10년이면 $40, 유연성 대비 저렴한 투자.

### 연결 절차

Cloudflare 에서 도메인 구매 → DNS 에 CNAME 추가 (Proxy status 는 반드시 **DNS only** 회색 구름, GitHub Pages SSL 발급에 필요) → GitHub Pages Settings 에서 Custom domain 입력 + Enforce HTTPS → `_config.yml` 의 `url` 변경 → 루트에 `CNAME` 파일.

기존 `idean3885.github.io` 접근은 자동으로 `blog.idean.me` 로 301 리다이렉트. 이미 공유된 링크는 깨지지 않습니다.

### 결과

| 항목 | Before | After |
|---|---|---|
| 도메인 | `idean3885.github.io` | `blog.idean.me` |
| GSC 사이트맵 | 2개월 "읽을 수 없음" | 배포 즉시 성공 |

2개월간 기술적 원인을 파고들었지만 답은 도메인에 있었습니다.

## 5. GA4 추가: 검색 노출 너머의 행동 데이터

사이트맵이 해소되면서 색인이 시작될 시점에 방문자 행동 분석도 같이 추가했습니다.

| 도구 | 보는 것 | 범위 |
|---|---|---|
| GSC | 어떤 키워드로 노출/클릭됐는지 | 블로그 **밖** (검색 → 클릭) |
| GA4 | 누가, 얼마나 머물렀는지 | 블로그 **안** (클릭 → 이탈) |

Chirpy 는 GA4 를 내장 지원. `_config.yml` 에 측정 ID 한 줄이면 gtag.js 가 자동 삽입됩니다.

```yaml
analytics:
  google:
    id: G-HRWXK11B6L
```

페이지뷰·스크롤 90% 도달·이탈 클릭 같은 기본 이벤트가 자동 수집됩니다.

## 회고: Chirpy 운영의 핵심은 "이미 된 것을 확인하기"

| 단계 | 한 일 | 결정의 무게 |
|---|---|---|
| SEO 점검 | `_config.yml` GSC 인증 한 줄 + 사이트맵 제출 | 작음 (기본기 확인) |
| GEO 보강 | author·logo·llms.txt·last_modified_at | 중간 (누락 발견) |
| Giscus | 13줄 + GitHub App 설치 | 작음 (App 함정 1개) |
| 커스텀 도메인 | 도메인 선택 + DNS + GitHub Pages 설정 | 큼 (2개월 함정 해소 + 장기 의사결정) |
| GA4 | 측정 ID 한 줄 | 작음 (행동 데이터 확보) |

4편의 운영기를 한 글로 묶으면서 가장 일관된 발견은 "Chirpy 가 이미 하고 있는 것이 많다" 였습니다. SEO 도, GEO 의 절반도, 댓글 위젯도, GA4 도 테마가 들고 있습니다. 운영자가 하는 일은 누락된 한 두 가지를 채우는 것과 도메인 같은 장기 의사결정입니다.

다음 과제는 OG 이미지 자동화와 카테고리별 큐레이션 페이지입니다. 운영을 단순화할수록 글쓰기에 시간이 더 갑니다.

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
