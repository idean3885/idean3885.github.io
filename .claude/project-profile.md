# Project Profile

프로젝트별 특수성을 정의하여 `/spec`과 `/implement` 스킬의 동작을 조정합니다.

## 산출물 유형

| 구분 | 내용 |
|------|------|
| 주요 산출물 | 마크다운 포스팅, Jekyll 설정 파일 |
| 빌드 도구 | Jekyll (GitHub Pages 자동 빌드) |
| 테스트 방법 | `bundle exec jekyll serve`로 로컬 미리보기 |

## /spec 컨텍스트

`/spec` 호출 시 아래 관점으로 명세를 작성합니다.

- **설계 대상**: 블로그 포스팅(`_posts/`), Jekyll 설정, CLAUDE.md
- **명세 항목**:
  - 포스팅 구조 설계 (제목, 카테고리, 태그, Front Matter)
  - 카테고리/태그 기존 체계와의 정합성 확인
  - 참조 프로젝트 변경 시 영향 분석 (CLAUDE.md 참조 프로젝트 테이블)
- **다이어그램**: 워크플로우 설명 시 Mermaid 사용

## /implement 컨텍스트

`/implement` 호출 시 아래 관점으로 구현합니다.

- **구현 대상**: 포스팅 작성, Front Matter 설정, CLAUDE.md 동기화
- **구현 순서**:
  1. 포스팅 파일 생성/수정 (`_posts/YYYY-MM-DD-slug.md`)
  2. Front Matter 필수 항목 검증
  3. 참조 프로젝트 변경 시 CLAUDE.md 동기화
- **검증 기준**:
  - Front Matter 필수 항목 존재 (title, date, categories, tags, description)
  - 카테고리 2단계 계층 준수
  - 본문 `##`부터 시작, 코드 블록 언어 명시
  - Semantic Line Breaks 규칙 준수
  - 마지막 줄 AI 도움 표기 포함

## 제약사항

- Chirpy 테마 Front Matter 규칙 준수
- 본문은 한국어로 작성
- Semantic Line Breaks 적용 (CLAUDE.md 마크다운 줄바꿈 규칙 참조)
- `/spec` 단계에서 포스팅 구조를 먼저 설계
