---
title: "GEO 시대, 개발 블로그는 뭘 해야 하나 — Chirpy 블로그에 적용한 기록"
date: 2026-03-15 23:30:00 +0900
last_modified_at: 2026-03-16 00:22:46 +0900
categories: [기술 노하우, 블로그]
tags: [SEO, GEO, Jekyll, Chirpy, JSON-LD, AI 검색]
description: >-
  GEO(생성형 검색 최적화)를 조사하고,
  Jekyll + Chirpy 블로그에 저비용으로 적용한 과정을 정리합니다.
---

> **TL;DR**
> AI 검색엔진(Claude, Gemini, ChatGPT 등)이 콘텐츠를 인용하는 시대가 왔습니다.
> GEO를 조사해보니 Chirpy는 이미 상당 부분 친화적이었고,
> JSON-LD author 누락 같은 기본기만 보완하면 충분했습니다.
{: .prompt-tip }

## 계기

[요즘IT의 콘텐츠 AX 실험기](https://yozm.wishket.com/magazine/detail/3647/)를 읽다가
GEO(Generative Engine Optimization)라는 개념을 처음 접했습니다.

GEO는 AI 검색엔진이 콘텐츠를 인용할 수 있도록 최적화하는 전략입니다.
기존 SEO가 Google 검색 순위를 겨냥했다면,
GEO는 ChatGPT, Claude, Gemini, Perplexity 같은 AI가 답변에 내 글을 출처로 포함하도록 만드는 것입니다.

이 블로그에서 [Chirpy SEO 포스트](https://idean3885.github.io/posts/chirpy-seo-and-search-console/)를 작성하면서
전통 SEO를 점검한 적은 있었지만, AI 검색은 의식한 적이 없었습니다.

"내 글이 AI에게 보이기는 하는 걸까?"라는 질문에서 출발했습니다.

## GEO, 근거가 있는 개념인가

바로 적용하기 전에 학술적 근거부터 확인했습니다.

### 핵심 논문

GEO라는 용어를 학술적으로 정의한 논문이 있습니다.
IIT Delhi, Princeton 연구진이 발표한
["GEO: Generative Engine Optimization"](https://arxiv.org/abs/2311.09735)으로,
ACM KDD 2024에서 동료심사를 통과했습니다.

10,000개 쿼리를 대상으로 9가지 최적화 전략을 테스트한 결과:

| 전략 | 가시성 향상 |
|------|-----------|
| 통계 추가 | ~41% |
| 인용구 삽입 | ~37% |
| 출처 명시 | ~31% |
| 키워드 스터핑 | 오히려 감소 |

### SEO와 GEO는 별개다

Yext의 6.8M 인용 분석(2025.10)에 따르면,
AI Overviews URL과 Google 1위 결과의 중복률은 **4.5%에 불과**합니다.
Google에서 1위를 해도 AI가 인용하지 않을 수 있고, 그 반대도 가능합니다.

### 비판도 유효하다

SandboxSEO는 GEO 논문의 방법론을 비판했습니다.
상위 3개 전략이 모두 새 정보를 추가하는 방식이라,
GEO 효과인지 단순 콘텐츠 양 증가 효과인지 구분할 수 없다는 지적입니다.

또한 AI 플랫폼의 인용 변동성이 월 40~60%에 달해,
"이렇게 하면 인용된다"는 보장은 없습니다.

**결론: 개념은 유효하나, 수치 효과는 회의적으로 봐야 합니다.**

## 내 블로그는 검색에 걸리고 있었나

GEO를 논하기 전에 현실을 직시했습니다.

### 기술 인프라는 갖춰져 있었다

| 항목 | 상태 |
|------|------|
| sitemap.xml | 정상 |
| robots.txt | 전체 허용, AI 크롤러 차단 없음 |
| Google Search Console | 등록됨 |
| OG 태그, Twitter Card | jekyll-seo-tag가 자동 생성 |

### JSON-LD에 author가 빠져 있었다

실제 출력을 확인해보니 이랬습니다.

```json
{
  "@type": "BlogPosting",
  "headline": "...",
  "datePublished": "...",
  "dateModified": "..."
}
```

`author`와 `publisher`가 없습니다.
`_config.yml`에 `author` 필드가 없었기 때문입니다.
이건 SEO와 GEO 양쪽 모두에서 기본적인 누락이었습니다.

### AI 검색에서 내 글은 보이지 않았다

"uvx requires-python 버전 문제", "Chirpy SEO 설정" 같은 쿼리로 확인해보니,
웹 검색에서도 상위에 없고, 당연히 AI 인용 가능성도 낮았습니다.

## Claude와 Gemini, 어떤 AI가 더 인용하나

주로 사용하는 AI인 Claude와 Gemini를 중심으로 비교했습니다.

| 항목 | Claude | Gemini |
|------|--------|--------|
| 검색 백엔드 | Brave Search | Google Search |
| 소스 선호 | 전문성·정확성 우선 | 도메인 권위 우선 |
| 개인 블로그 친화성 | 상대적으로 높음 | 상대적으로 낮음 |

**Claude**는 Brave Search 기반이라 Google 도메인 권위와 무관하게
전문성 있는 콘텐츠를 발견할 수 있습니다.
틈새 주제에서 개인 블로그도 인용 가능성이 있습니다.

**Gemini**는 Google 검색 인프라와 직결되어
기존 SEO 순위가 인용에 강하게 반영됩니다.
대형 플랫폼 중심의 인용 집중 현상이 있어 개인 블로그에는 불리합니다.

## Chirpy는 이미 GEO 친화적이었다

조사하면서 놀랐던 점은 Chirpy 테마와 기존 작성 규칙이
이미 GEO 권장 패턴과 상당히 겹친다는 것이었습니다.

| 기존 규칙 | GEO 관점 효과 |
|-----------|---------------|
| TL;DR 필수 (`.prompt-tip`) | AI가 추출할 "직접 답변" 패턴 |
| H2부터 시작, TOC 자동 생성 | 패시지 추출 단위가 명확 |
| 코드 블록 언어 명시 | 기술 콘텐츠 신뢰도 신호 |
| 카테고리 2단계 계층 | 콘텐츠 맥락 파악 용이 |

의식하지 않았지만, 이미 하고 있던 것들이 GEO에도 유효했습니다.

## 실제로 적용한 것들

대규모 구조 변경은 근거 대비 투자가 과합니다.
저비용으로 SEO/GEO 공통 기본기를 보완하는 방향으로 진행했습니다.

### 1. `_config.yml`에 author와 logo 추가

```yaml
author: idean3885
logo: /assets/img/favicons/favicon-96x96.png
```

이 두 줄로 JSON-LD 출력이 바뀝니다.

```json
{
  "@type": "BlogPosting",
  "author": {
    "@type": "Person",
    "name": "idean3885"
  },
  "publisher": {
    "@type": "Organization",
    "name": "idean3885",
    "logo": {
      "@type": "ImageObject",
      "url": "https://idean3885.github.io/assets/img/favicons/favicon-96x96.png"
    }
  }
}
```

jekyll-seo-tag가 `author`로 author를, `logo`로 publisher를 자동 생성합니다.

### 2. `llms.txt` 추가

AI 크롤러에게 블로그 구조를 안내하는 파일입니다.
[llmstxt.org](https://llmstxt.org/) 규격에 따라 루트에 배치했습니다.

```markdown
# idean3885.github.io

> 개발자의 기술적 탐구, 방법론의 진화,
> 운영 노하우와 의사결정의 기록을 담는 한국어 기술 블로그.

## 카테고리
- 개발 기록: 프로젝트 경험기, 도구 적응기
- 기술 노하우: 운영 경험 기반 실전 지식
...
```

### 3. `last_modified_at` 수정 규칙 추가

포스트 수정 시 front matter에 `last_modified_at`을 기록하도록 규칙을 추가했습니다.
jekyll-seo-tag는 이 값을 JSON-LD `dateModified`에 반영합니다.

웹에서는 수정 일시가 보이지 않지만,
검색엔진과 AI에는 freshness 신호로 작용합니다.

> jekyll-seo-tag의 `dateModified` 우선순위:
> `seo.date_modified` → `last_modified_at` → `date`
{: .prompt-info }

## 하지 않은 것들

조사 결과 효과가 불확실하거나 투자 대비 수익이 낮다고 판단한 항목입니다.

- **`TechArticle` 스키마 전환**: jekyll-seo-tag에서 타입 변경은 가능하나, 전용 필드 수동 추가 필요. 실질적 효과 불확실.
- **`FAQPage`, `HowTo` 스키마**: 포스트마다 수동으로 구조화 데이터를 삽입해야 함. 관리 부담 대비 효과 불분명.
- **GEO 전문 측정 도구**: 개인 블로그에 월 8~12시간 + 비용은 과다.
- **H2/H3 질문형 헤딩 전환**: 작성 습관 변경이 필요한 부분이라 점진적으로 검토.

## 마무리

GEO를 조사하면서 얻은 가장 큰 교훈은,
"새로운 최적화 기법"보다 **기본기를 먼저 챙기는 것**이 중요하다는 점이었습니다.

JSON-LD에 author가 빠져 있었다는 사실은 GEO를 조사하지 않았으면 몰랐을 것입니다.
결국 GEO라는 키워드가 계기가 되어, SEO 기본기를 점검하고 보완하는 결과로 이어졌습니다.

AI 검색 시대가 오고 있는 건 맞지만,
개인 블로그 수준에서 할 수 있는 일은 의외로 단순합니다.
좋은 구조로 좋은 글을 쓰는 것. 지금까지 해왔던 것과 크게 다르지 않았습니다.

*이 글의 작성에 AI(Claude Code)를 활용했습니다.*
