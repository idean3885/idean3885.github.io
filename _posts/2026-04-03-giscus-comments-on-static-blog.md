---
title: "정적 블로그에 댓글을 달았다 - Giscus와 GitHub Discussions"
date: 2026-04-03 22:00:00 +0900
last_modified_at: 2026-04-06 00:00:00 +0900
categories: [기술 노하우, 블로그]
tags: [Jekyll, Chirpy, Giscus, GitHub Discussions, 댓글]
description: >-
  정적 블로그에 서버 없이 댓글 기능을 추가했습니다.
  GitHub Discussions 기반 Giscus의 동작 원리와
  Chirpy 테마에서의 설정 과정을 정리합니다.
---

> **TL;DR**<br>
> 정적 블로그에 댓글이 안 될 거라 생각했는데, Giscus를 쓰면 됩니다.<br>
> GitHub Discussions API를 활용하는 오픈소스 위젯이고,
> Chirpy 테마는 기본 지원하므로 `_config.yml` 13줄 추가로 끝납니다.<br>
> 비용은 0원입니다.
{: .prompt-tip }

## 계기

다른 기술 블로그를 읽다가 하단에 댓글창이 있는 걸 발견했습니다.
GitHub 로그인으로 댓글을 남기는 구조였습니다.

"정적 페이지인데 댓글이 어떻게 되지?"가 첫 반응이었습니다.
서버가 없으니 데이터를 저장할 곳이 없을 텐데, 실시간으로 읽고 쓰는 게 신기했습니다.

알아보니 **Giscus**(GitHub Discussions 기반 댓글 위젯)라는 오픈소스 프로젝트였습니다.

## Giscus의 동작 원리

핵심은 **댓글 데이터가 내 사이트가 아니라 GitHub에 저장**된다는 점입니다.

```text
사용자 브라우저
  ↓ iframe (Giscus 위젯)
  ↓ GitHub OAuth2 로그인
  ↓ GitHub GraphQL API
GitHub 저장소: Discussions 탭
```

GitHub 저장소에는 코드(Git) 외에 **Discussions**라는 별도 기능이 있습니다.
Issues 탭 옆에 있는 포럼 같은 것입니다.

```text
저장소
├── Code        ← Git 커밋/푸시 (파일)
├── Issues      ← 이슈 트래커
├── Pull Requests
└── Discussions ← 포럼/댓글 (Giscus가 여기 저장)
```

Giscus는 이 Discussions를 댓글 저장소로 사용합니다.
동작 흐름은 이렇습니다:

- **읽기**: 페이지 로드 → Giscus iframe이 GitHub GraphQL API로 해당 URL의 Discussion 스레드 조회 → 댓글 렌더링
- **쓰기**: GitHub OAuth2 로그인 → 댓글 입력 → Giscus가 Discussion에 댓글 생성

정적 HTML 자체는 변하지 않습니다.
댓글은 클라이언트(브라우저)에서 GitHub API로 직접 통신하므로 서버가 필요 없습니다.
댓글이 100개 달려도 Git 커밋 로그에는 아무것도 남지 않습니다.

> Git 커밋이 아니라 Discussions API입니다.<br>
> Issues에 댓글 다는 것과 동일한 방식으로, 코드에는 영향이 없습니다.
{: .prompt-info }

## 비용

적용 전에 비용부터 확인했습니다.

| 구성 요소 | 비용 |
|-----------|------|
| GitHub Discussions | 무료 (public repo) |
| Giscus 서비스 | 무료 (오픈소스) |
| GitHub OAuth2 | 무료 |
| GitHub GraphQL API | 무료 (rate limit 있지만 블로그 댓글 수준은 문제 없음) |

전부 무료입니다.
GitHub public 저장소의 Discussions는 용량 제한도 사실상 없습니다.

## Chirpy 설정 과정

Chirpy 테마는 Giscus를 **기본 지원**합니다.
테마 내부에 `_includes/comments/giscus.html` 템플릿이 이미 포함되어 있어서,
`_config.yml` 설정만 추가하면 됩니다.

### 1단계: Discussions 활성화 확인

저장소 Settings > General > Features에서 **Discussions**가 체크되어 있어야 합니다.
이미 활성화되어 있었습니다.

### 2단계: repo_id와 category_id 발급

Giscus 설정에는 저장소 고유 ID와 Discussion 카테고리 ID가 필요합니다.
[giscus.app](https://giscus.app/ko)에서 저장소를 입력하면 자동 발급받을 수 있습니다.

GitHub GraphQL API로도 조회할 수 있습니다:

```bash
gh api graphql -f query='{
  repository(owner: "idean3885", name: "idean3885.github.io") {
    id
    discussionCategories(first: 10) {
      nodes { id, name }
    }
  }
}'
```

카테고리는 **General**을 선택했습니다.
Announcements는 관리자만 글 작성이 가능하므로, 방문자 댓글에는 적합하지 않습니다.

### 3단계: _config.yml 설정

변경한 내용은 두 가지입니다.

**댓글 활성화**: defaults 섹션의 `comments: false`를 `true`로 변경:

```yaml
defaults:
  - scope:
      path: ""
      type: posts
    values:
      layout: post
      comments: true    # false → true
```

**Giscus provider 설정**: 최상위에 comments 블록 추가:

```yaml
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

`mapping: pathname`은 포스트 URL 경로별로 Discussion 스레드를 자동 생성합니다.
설정 파일 1개, 총 13줄 추가로 끝입니다.

## 놓치기 쉬운 함정

배포 후 포스트 하단에 댓글창이 나타났지만, 이런 에러가 떴습니다:

> **오류 발생: giscus is not installed on this repository**

`_config.yml` 설정만으로 되는 줄 알았는데, 한 가지가 더 필요했습니다.
**Giscus GitHub App**을 저장소에 설치해야 합니다.

[https://github.com/apps/giscus](https://github.com/apps/giscus) → Install → 저장소 선택 → Install

설치 후 새로고침하니 정상 동작했습니다.

> Giscus App 설치를 빠뜨리면 설정은 맞는데 동작하지 않습니다.<br>
> `_config.yml` 외에 App 설치가 필수라는 점을 기억해두면 좋습니다.
{: .prompt-warning }

## 마무리

정적 블로그라서 댓글은 안 된다고 생각했습니다.
Giscus를 알게 된 후 적용까지 걸린 시간은 10분 정도였습니다.

Chirpy 테마의 기본 지원 덕분에 코드 수정 없이 설정만으로 연동할 수 있었고,
GitHub Discussions를 댓글 저장소로 활용하는 구조가 깔끔했습니다.

| 항목 | 결과 |
|------|------|
| 변경 파일 | `_config.yml` 1개 |
| 추가 라인 | 13줄 |
| 비용 | 0원 |
| 추가 작업 | Giscus GitHub App 설치 |

이 시리즈의 이전 글에서 [SEO 점검](https://idean3885.github.io/posts/chirpy-seo-and-search-console/)과
[GEO 적용](https://idean3885.github.io/posts/geo-for-dev-blog/)을 다뤘습니다.
이번에 댓글까지 추가하면서, 블로그에 필요한 기본 기능이 갖춰진 것 같습니다.

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
