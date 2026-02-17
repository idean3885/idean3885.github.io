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

### 마크다운 줄바꿈 규칙 (Semantic Line Breaks)

**원칙:** [Semantic Line Breaks(sembr.org)](https://sembr.org/) 기반.
문장 단위로 줄바꿈하여 소스 가독성과 git diff 품질을 확보한다.

**단문/소개/README류 (스캔형 텍스트):**
- 문장마다 빈 줄(`\n\n`)로 분리하여 별도 단락으로 렌더링
- 한 문장이 길면 절(clause) 단위로 줄바꿈 (쉼표, 세미콜론 뒤)
- 한 줄 목표: 한글 기준 25-35자 (A4 12pt 기준 한 줄 이내)

**장문/블로그 포스팅 (산문형 텍스트):**
- 2-4문장을 한 단락으로 묶어 자연스러운 흐름 유지
- 단락 사이에 빈 줄로 구분
- 소스에서는 문장마다 줄바꿈 (렌더링에는 영향 없음, diff 품질 향상)

**공통:**
- 소스 한 줄 80자 이내 권장 (링크, 테이블, 뱃지 등은 예외)
- 단일 개행은 마크다운에서 무시됨 — 시각적 분리가 필요하면 반드시 빈 줄 사용

## 참조 프로젝트

이 블로그의 포스팅이 참조하는 프로젝트 목록. 참조 프로젝트가 변경되면 관련 포스팅 업데이트가 필요할 수 있다.

| 프로젝트 | 참조 포스팅 | 참조 요소 |
|----------|------------|-----------|
| [claude-devex](https://github.com/idean3885/claude-devex) | [AI에게 코드를 맡기고 나서 달라진 일하는 방식](https://idean3885.github.io/posts/ai-changed-my-workflow/) | 커맨드명, setup.sh URL, 이슈 사이클 플로우 |

## 이슈 사이클

```
이슈 생성 → 브랜치 → 작업 → 커밋 → PR → 리뷰 → 머지
```

### 체크박스 역할 분리

| 영역 | 체크 주체 | 역할 |
|------|-----------|------|
| 이슈 체크박스 | 사용자 | 요구사항 충족 확인 (리뷰 체크리스트) |
| PR Test plan | AI | 자가 검증 결과 |
| PR 머지 | 사용자 | 최종 승인 |

- 이슈 체크박스는 사용자가 PR 리뷰 시 확인하며 체크한다.
- AI는 이슈 체크박스를 체크하지 않는다.
- PR Test plan은 AI가 자가 검증 후 체크한다.

## Git Flow

- **main 브랜치 보호됨**: 직접 푸시 불가, PR 머지만 허용
- PR 타겟: `main`
- 브랜치명: `{타입}/{이슈번호}`
- 모든 변경은 이슈 사이클을 통해 PR로 처리 (핫픽스 포함)

## 커밋 컨벤션

타입: `init`, `feat`, `fix`, `docs`, `refactor`, `chore`
