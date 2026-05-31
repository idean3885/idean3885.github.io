---
layout: page
---

<style>
/* 소개 섹션 한정: 단락 사이 세로 간격 축소 */
.intro p { margin-bottom: 0.5rem; }
.intro ul { margin-top: 1rem; }
</style>

## 소개

<div class="intro" markdown="1">

Spring Boot·Kubernetes 기반 클라우드 서비스를 설계·운영하는
7년차 백엔드 개발자입니다.

GPU 기반 PaaS·시계열 파이프라인·인증서 자동화 같은
백엔드 운영 사례를 다루고,
마주친 결정과 공부한 것을 꾸준히 기록합니다.

좋은 글은 결과도 중요하지만 분석에서 갈린다고 봅니다.
얼마나 깊이 분석했는가에 따라 방향이 정해지고,
시작 방향이 틀어지면 결과도 크게 달라진다고 생각합니다.

- **개발 기록**: 프로젝트 경험과 마주친 결정
- **생각과 방법론**: 설계 원칙, 판단 기준, 개발에 대한 생각
- **기술 노하우**: 운영·학습 기반 실전 지식

</div>

## 추천 글

시리즈에 묶이지 않은 단독 글입니다.

- [Expand-and-Contract 패턴: 무중단 DB 스키마 변경을 3단계 PR로 분할하기](/posts/expand-and-contract-pattern/)

## 주요 시리즈

### 미터링 시스템 구축

GPU 클라우드 서비스의 사용량 수집·집계 시스템을 설계하고 구현한 과정입니다.
쓰기 경합·용량 트레이드오프·저장 전략 통일 같은 데이터 정합성 결정을 다룹니다.

{% assign series = site.posts | where: "categories", "미터링 시스템 구축" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

### 인증서 자동화 구축기

사용자 도메인 인증서 발급·갱신을 무중단으로 자동화한 과정입니다.
ACME 프로토콜 학습·헥사고날 상태 머신·Jenkins 격월 크론으로 운영 부담을 끊었습니다.

{% assign series = site.posts | where: "categories", "인증서 자동화 구축기" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

### AI 교차 검증

AI 협업에서 판단을 검증하는 방법과 도구 구현을 다루는 시리즈입니다.

{% assign series = site.posts | where: "categories", "AI 교차 검증" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

## 도구·방법론

방법론과 도구를 직접 만들며 검증한 결과물입니다.

- [trip-planner](https://github.com/idean3885/trip-planner) - spec-kit 풀사이클과 하네스를 1인 개발에 적용한 테스트베드
- [claude-cross-verify](https://github.com/idean3885/claude-cross-verify) - 의사결정·설계·문서·구현 4축 교차 검증 에이전트
- [claude-devex](https://github.com/idean3885/claude-devex) - 개발 사이클 자동화 도구
- [claude-slack-to-notion](https://github.com/idean3885/claude-slack-to-notion) - Slack 스레드를 Notion으로 정리하는 MCP 플러그인

[전체 포스트 보기 →](/posts/)

## 링크

- GitHub: [idean3885](https://github.com/idean3885)
