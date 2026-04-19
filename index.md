---
layout: page
---

## 소개

2019년부터 백엔드 개발을 해온 개발자입니다.
Kubernetes 기반 멀티 테넌시 서비스를 개발하고 운영하며,
앱·GPU 클라우드 환경에서의 설계와 자동화에 관심을 두고 있습니다.

코드를 짜는 일만큼, 판단하고 설계하는 과정도 중요하다는 걸 느끼며
그 과정에서 얻은 기술적 탐구와 방법론의 진화를 기록하고 있습니다.

좋은 글은 결과보다 분석에서 갈린다고 봅니다.
얼마나 깊이 분석했는가에 따라 방향이 정해지고, 시작 방향이 틀어지면 결과도 크게 달라진다고 생각합니다.

- **개발 기록**: 프로젝트를 진행하며 겪은 경험과 도구 적응 과정
- **생각과 방법론**: 설계 원칙, 의사결정, 개발에 대한 생각
- **기술 노하우**: 운영 경험에서 얻은 실전 지식

## 최신 포스트

{% for post in site.posts limit:5 %}
1. [{{ post.title }}]({{ post.url | relative_url }}) <span class="text-muted small">({{ post.date | date: "%Y-%m-%d" }})</span>
{%- endfor %}

[전체 포스트 보기 →](/posts/)

## 주요 시리즈

### 미터링 시스템 구축

GPU 클라우드 서비스의 사용량 수집·집계 시스템을 설계하고 구현한 과정입니다.

{% assign series = site.posts | where: "categories", "미터링 시스템 구축" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

### AI 교차 검증

AI 협업에서 판단을 검증하는 방법과 도구 구현을 다루는 시리즈입니다.

{% assign series = site.posts | where: "categories", "AI 교차 검증" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

### 인증서 자동화 구축기

사용자 도메인 인증서 발급·갱신을 완전 자동화한 과정입니다.

{% assign series = site.posts | where: "categories", "인증서 자동화 구축기" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

### 트립 매니저

바이브코딩으로 만든 코드의 신뢰를 실험하는 시리즈입니다.

{% assign series = site.posts | where: "categories", "트립 매니저" | sort: "date" -%}
{% for post in series %}
1. [{{ post.title }}]({{ post.url | relative_url }})
{%- endfor %}

## 프로젝트

- [trip-planner](https://github.com/idean3885/trip-planner) - 우리의 여행 앱 만들기. React + GitHub Pages 모바일 웹
- [claude-devex](https://github.com/idean3885/claude-devex) - AI 기반 개발 사이클 자동화 도구
- [claude-cross-verify](https://github.com/idean3885/claude-cross-verify) - 의사결정·설계·문서·구현 4축 교차 검증 에이전트
- [claude-slack-to-notion](https://github.com/idean3885/claude-slack-to-notion) - Slack 스레드를 Notion으로 정리하는 MCP 플러그인

## 링크

- GitHub: [idean3885](https://github.com/idean3885)
