# CLAUDE.md

Jekyll + Chirpy 테마 기반 블로그 프로젝트

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 사이트 | https://idean3885.github.io |
| 테마 | [jekyll-theme-chirpy](https://github.com/cotes2020/jekyll-theme-chirpy) |
| 언어 | 한국어 (ko) |
| 배포 | GitHub Pages (GitHub Actions) |

## 포스팅 규칙

### 파일 위치 및 네이밍

```
_posts/YYYY-MM-DD-slug.md
```

### Front Matter 필수 항목

```yaml
---
title: "제목"
date: YYYY-MM-DD HH:MM:SS +0900
categories: [카테고리]
tags: [태그1, 태그2]
description: >-
  요약 설명 (SEO, 미리보기용)
---
```

### 작성 규칙

- 본문은 `##`부터 시작 (h1은 title이 대체)
- 코드 블록에 언어 명시
- Mermaid 다이어그램 사용 가능
- 마지막 줄: `*이 글은 Claude의 도움을 받아 작성했습니다.*`

## 참조 프로젝트

이 블로그의 포스팅이 참조하는 프로젝트 목록. 참조 프로젝트가 변경되면 관련 포스팅 업데이트가 필요할 수 있다.

| 프로젝트 | 참조 포스팅 | 참조 요소 |
|----------|------------|-----------|
| [claude-devex](https://github.com/idean3885/claude-devex) | [AI에게 코드를 맡기고 나서 달라진 일하는 방식](https://idean3885.github.io/posts/ai-changed-my-workflow/) | 커맨드명, setup.sh URL, 이슈 사이클 플로우 |

## Git Flow

```
main ────────────────●─────
       \            /
        chore/2 ────
```

- PR 타겟: `main` 직접
- 브랜치명: `{타입}/{이슈번호}`

## 커밋 컨벤션

타입: `init`, `feat`, `fix`, `docs`, `refactor`, `chore`
