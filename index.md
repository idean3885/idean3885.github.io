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

팀 상황 안에서의 트레이드오프와 정량 의사결정에 관심이 많은
7년차 백엔드 개발자입니다.

SDD·ADR로 의사결정 흔적을 남기며,
GPU 기반 PaaS·시계열 파이프라인·자동화 시스템 사례를
정리하고 있습니다.

좋은 글은 결과보다 분석에서 갈린다고 봅니다.
얼마나 깊이 분석했는가에 따라 방향이 정해지고,
시작 방향이 틀어지면 결과도 크게 달라진다고 생각합니다.

- **개발 기록**: 프로젝트를 진행하며 내린 의사결정과 트레이드오프
- **생각과 방법론**: 설계 원칙, 판단 기준, 개발에 대한 생각
- **기술 노하우**: 운영 경험에서 얻은 실전 지식

</div>

## 추천 글

의사결정과 트레이드오프의 흔적이 가장 잘 드러난 글입니다.

### 데이터 정합성과 트레이드오프

- [미터링 용량을 3중 제약 교차로 역산한 이유 - 단일 제약만 보면 틀린다](/posts/metering-capacity-triple-constraint/)
- [미터링 배치 저장 전략 통일 - UPSERT → DELETE + INSERT 전환](/posts/batch-storage-upsert-to-delete-insert/)
- [시계열 수집의 쓰기 경합 - 5분 주기 시스템에서 동시성을 해결한 방법](/posts/timeseries-write-contention/)
- [MySQL 파티셔닝 도입기 - JPA 복합 키 전환부터 시간 독립 DDL까지](/posts/mysql-partitioning-jpa-composite-key/)

### 무중단 운영과 자동화

- [Expand-and-Contract 패턴 - 무중단 DB 스키마 변경을 3단계 PR로 분할하기](/posts/expand-and-contract-pattern/)
- [사용자 도메인 인증서 자동 발급 - certbot 학습에서 ACME4j 구현까지](/posts/domain-ssl-automation-certbot-to-acme4j/)

## 주요 시리즈

### 미터링 시스템 구축

GPU 클라우드 서비스의 사용량 수집·집계 시스템을 설계하고 구현한 과정입니다.

{% assign series = site.posts | where: "categories", "미터링 시스템 구축" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

### 인증서 자동화 구축기

사용자 도메인 인증서 발급·갱신을 완전 자동화한 과정입니다.

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

### 트립 매니저

바이브코딩으로 만든 코드의 신뢰를 실험하는 시리즈입니다.

{% assign series = site.posts | where: "categories", "트립 매니저" | sort: "date" -%}
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
