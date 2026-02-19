---
title: "Chirpy 블로그의 SEO는 이미 되어 있었다 — Google Search Console까지"
date: 2026-02-19 03:00:00 +0900
categories: [기술 노하우, 블로그]
tags: [Jekyll, Chirpy, SEO, Google Search Console, jekyll-seo-tag]
description: >-
  Jekyll + Chirpy 테마 블로그의 SEO 현황을 점검했더니,
  대부분 자동으로 처리되고 있었습니다.
  실제로 뭐가 되어 있고 뭐가 남았는지,
  Google Search Console 등록까지 정리합니다.
---

블로그를 시작하고 글을 몇 편 올렸습니다.
그런데 검색에 노출이 되는 건지, 공유했을 때 제대로 보이는 건지 확인한 적이 없었습니다.
SEO를 챙겨야 한다는 건 알았지만, 어디서부터 시작해야 할지 몰랐습니다.

직접 점검해보니 Chirpy 테마가 생각보다 많은 걸 자동으로 처리하고 있었습니다.
이 글은 그 확인 과정과, 남은 작업인 Google Search Console 등록까지를 정리한 기록입니다.

---

## 1. 점검 전 예상 — 할 일이 많을 줄 알았다

SEO 최적화라고 하면 이런 것들이 떠오릅니다.

- Open Graph / Twitter Card 메타태그
- sitemap.xml
- robots.txt
- meta description
- JSON-LD 구조화 데이터

하나하나 직접 설정해야 한다고 생각했습니다.
그래서 이슈를 만들고 체크리스트를 작성했습니다.

결론부터 말하면, **대부분 이미 되어 있었습니다.**

---

## 2. Chirpy가 자동으로 해주는 것들

Jekyll + Chirpy 테마는 두 개의 플러그인을 기본 의존성으로 포함합니다.

| 플러그인 | 역할 |
|----------|------|
| `jekyll-seo-tag` | 메타태그, OG 태그, JSON-LD 자동 생성 |
| `jekyll-sitemap` | sitemap.xml, robots.txt 자동 생성 |

별도로 설치하거나 설정한 적 없지만,
Chirpy 테마(`jekyll-theme-chirpy`)가 이 둘을 의존성으로 가져옵니다.
`Gemfile.lock`을 확인하면 이미 포함되어 있습니다.

### jekyll-seo-tag가 자동 생성하는 것

Chirpy의 `head.html`에 `{% raw %}{% seo %}{% endraw %}` 태그가 삽입되어 있고,
빌드 시 이 태그가 다음 HTML로 변환됩니다.

**기본 메타태그:**

```html
<title>포스트 제목 | 사이트명</title>
<meta name="description" content="front matter의 description">
<link rel="canonical" href="https://...">
```

**Open Graph 태그 (카카오톡, LinkedIn 공유용):**

```html
<meta property="og:title" content="포스트 제목">
<meta property="og:description" content="description 값">
<meta property="og:url" content="https://...">
<meta property="og:type" content="article">
<meta property="og:locale" content="ko">
```

**JSON-LD 구조화 데이터:**

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "포스트 제목",
  "datePublished": "2026-02-19",
  "dateModified": "2026-02-19",
  "url": "https://..."
}
```

> 포스트 front matter에 `title`, `date`, `description`만 쓰면
> 나머지는 전부 자동입니다.
{: .prompt-info }

### jekyll-sitemap이 자동 생성하는 것

빌드 시 `_site/` 디렉토리에 두 파일을 생성합니다.

**sitemap.xml** — 모든 포스트와 페이지의 URL 목록:

```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://idean3885.github.io/posts/post-slug/</loc>
    <lastmod>2026-02-19T00:00:00+09:00</lastmod>
  </url>
</urlset>
```

**robots.txt** — 크롤러 접근 규칙 + sitemap 위치:

```
User-agent: *
Sitemap: https://idean3885.github.io/sitemap.xml
```

저장소에 이 파일들을 직접 만들 필요가 없습니다.
배포할 때마다 자동으로 최신 상태가 반영됩니다.

---

## 3. 점검 결과 — 뭐가 되어 있고 뭐가 안 되어 있나

| 항목 | 상태 | 비고 |
|------|------|------|
| og:title, og:description, og:url | 자동 생성 | jekyll-seo-tag |
| meta description | 완료 | 모든 포스트에 description 작성됨 |
| sitemap.xml | 자동 생성 | jekyll-sitemap |
| robots.txt | 자동 생성 | jekyll-sitemap |
| JSON-LD (BlogPosting) | 자동 생성 | jekyll-seo-tag |
| **og:image** | **미설정** | 포스트에 image 필드 없음 |
| **Google Search Console** | **미등록** | 인증 필요 |

OG 이미지는 소셜 공유 시 썸네일로 표시됩니다.
없으면 카카오톡이나 LinkedIn에서 링크 공유 시 빈 박스가 나옵니다.
이건 별도 이슈로 분리했습니다(테마 커스텀 범위).

남은 작업은 **Google Search Console 등록** 하나였습니다.

---

## 4. Google Search Console이란

Google Search Console(이하 GSC)은 Google이 무료로 제공하는 웹마스터 도구입니다.
이전에는 "Google 웹마스터 도구"로 불렸습니다.

> 블로그를 만들었다고 Google이 자동으로 찾아오지 않습니다.
{: .prompt-warning }

GSC가 없으면 다음을 알 수 없습니다.

- 내 페이지가 Google 색인에 실제로 포함됐는지
- 어떤 키워드로 검색되어 노출되는지
- 크롤러가 특정 페이지에 접근하지 못하는지

### 주요 기능

| 기능 | 설명 |
|------|------|
| 실적(Performance) | 노출 수, 클릭 수, CTR, 평균 게재 순위 |
| URL 검사 | 특정 URL의 색인 상태 확인 및 크롤링 재요청 |
| Sitemaps | 사이트맵 제출 및 처리 결과 확인 |
| 색인 생성 보고서 | 색인된 페이지 수, 오류 목록 |

---

## 5. GSC 등록 절차 — Chirpy에서는 한 줄

### 5-1. 속성 추가

[Google Search Console](https://search.google.com/search-console/)에서 "속성 추가"를 클릭합니다.
속성 유형은 **URL 접두어**를 선택합니다.

| 유형 | 입력값 | 인증 방법 |
|------|--------|-----------|
| 도메인 | `example.com` | DNS만 가능 |
| **URL 접두어** | `https://idean3885.github.io` | **다양한 방법 선택 가능** |

GitHub Pages 블로그는 URL 접두어 방식이 간편합니다.

### 5-2. 소유권 인증

GSC는 여러 인증 방법을 제공합니다.

| 방법 | 방식 |
|------|------|
| **HTML 메타 태그** | `<head>`에 인증 태그 삽입 |
| HTML 파일 업로드 | 루트에 특정 파일 업로드 |
| DNS TXT 레코드 | 도메인 DNS에 TXT 추가 |
| Google Analytics | GA 연동 |

Chirpy에서는 **HTML 메타 태그** 방식이 가장 간단합니다.
`_config.yml`{: .filepath}에 한 줄만 추가하면 됩니다.

### 5-3. Chirpy에 인증 코드 적용

GSC에서 "HTML 태그" 인증을 선택하면 이런 태그를 줍니다.

```html
<meta name="google-site-verification" content="abc123xyz">
```

여기서 `content` 값만 복사해서 `_config.yml`{: .filepath}에 추가합니다.

```yaml
webmaster_verifications:
  google: abc123xyz
```
{: file="_config.yml" }

배포하면 모든 페이지의 `<head>`에 인증 태그가 자동 주입됩니다.
GSC에서 "확인"을 클릭하면 소유권 인증이 완료됩니다.

> 인증 태그는 영구적으로 유지해야 합니다.
> 삭제하면 수개월 후 소유권이 취소될 수 있습니다.
{: .prompt-danger }

---

## 6. 등록 후 해야 할 것들

### Sitemap 제출

GSC 좌측 메뉴 → "Sitemaps" → `sitemap.xml` 입력 → "제출".

jekyll-sitemap이 이미 파일을 생성하고 있으니,
GSC에 위치만 알려주면 됩니다.
"제출"은 파일 업로드가 아니라 URL을 등록하는 것입니다.

### 새 포스트 색인 요청

새 글을 발행해도 Google이 바로 크롤링하지는 않습니다.
빠른 색인이 필요하면 URL 검사 도구로 직접 요청할 수 있습니다.

1. GSC 상단 검색창에 포스트 URL 입력
2. "색인 생성 요청" 클릭

하루 할당량이 약 10건이므로 대량 페이지는 sitemap 제출로 처리합니다.

### 실적 리포트

등록 후 3~4일이 지나면 데이터가 쌓이기 시작합니다.

| 지표 | 의미 |
|------|------|
| 노출 수 | 검색 결과에 표시된 횟수 |
| 클릭 수 | 실제로 클릭된 횟수 |
| CTR | 클릭 수 / 노출 수 |
| 평균 게재 순위 | 검색 결과에서의 평균 위치 |

---

## 7. 추가로 알게 된 것들

### robots.txt와 sitemap의 관계

| 파일 | 역할 | 비유 |
|------|------|------|
| robots.txt | 크롤러 접근 허용/차단 | 경비원 |
| sitemap.xml | 크롤링할 URL 목록 | 지도 |

robots.txt가 차단한 경로는 sitemap에 있어도 크롤링되지 않습니다.
Chirpy는 둘 다 자동 생성하고, robots.txt 안에 sitemap 위치를 명시합니다.

### OG 이미지의 간접적 SEO 효과

OG 이미지는 Google 랭킹 요소가 아닙니다.
하지만 간접적으로 영향을 줍니다.

1. 소셜 공유 시 썸네일이 매력적이면 클릭률이 올라감
2. 트래픽 증가는 도메인 권위도에 기여
3. 이미지 없는 링크는 신뢰도가 낮아 보임

Jekyll에서는 포스트 front matter에 `image` 필드를 추가하면
jekyll-seo-tag가 자동으로 `og:image`로 변환합니다.

```yaml
image:
  path: /assets/img/posts/og-image.png
  alt: "이미지 설명"
```

### JSON-LD와 Rich Results

jekyll-seo-tag가 생성하는 `BlogPosting` JSON-LD 덕분에
Google은 해당 페이지가 블로그 포스트임을 인식합니다.
검색 결과에 날짜, 작성자 등이 함께 표시되는
Rich Results로 이어질 수 있습니다.

[Google Rich Results Test](https://search.google.com/test/rich-results)에서
페이지 URL을 입력하면 구조화 데이터가 올바른지 확인할 수 있습니다.

---

## 8. 몰랐던 것 → 알게 된 것

| 몰랐던 것 | 알게 된 것 |
|-----------|-----------|
| SEO 설정을 직접 다 해야 한다 | Chirpy + jekyll-seo-tag + jekyll-sitemap이 대부분 자동 처리 |
| sitemap.xml을 직접 만들어야 한다 | jekyll-sitemap이 빌드마다 자동 생성 |
| JSON-LD를 직접 작성해야 한다 | jekyll-seo-tag가 BlogPosting 스키마를 자동 생성 |
| GSC 등록이 복잡하다 | Chirpy에서는 `_config.yml` 한 줄로 인증 완료 |
| OG 이미지가 SEO 랭킹에 직접 영향을 준다 | 직접 영향은 없지만, 소셜 공유 CTR을 통해 간접 영향 |

---

Chirpy 테마를 쓰고 있다면 SEO의 기술적 기반은 이미 갖춰져 있습니다.
남은 건 Google Search Console 등록과 OG 이미지 설정 정도입니다.

"해야 할 것이 많다"고 생각했는데,
점검해보니 "이미 된 것을 확인하는 과정"이었습니다.

---

*이 글은 Claude의 도움을 받아 작성했습니다.*
