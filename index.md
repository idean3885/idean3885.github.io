---
layout: page
---

<style>
/* 대문 본문 모든 링크 밑줄 제거 (Chirpy는 border-bottom으로 밑줄을 그림) */
.content a { border-bottom: none !important; text-decoration: none !important; }

/* 카드 공통 */
.home-card {
  background: var(--card-bg);
  border: 1px solid rgba(128, 128, 128, 0.28);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  box-shadow: var(--card-shadow);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.home-card:hover {
  transform: translateY(-2px);
  background: var(--card-hover-bg);
  border-color: rgba(128, 128, 128, 0.45);
}

/* 카드 내 요약 리스트 */
.home-card ul { margin: 0; padding-left: 1.1rem; }
.home-card li { margin-bottom: 0.3rem; }
.home-card li:last-child { margin-bottom: 0; }

/* 섹션 간격 */
.home-card + .home-card { margin-top: 1rem; }

/* 소개 카드: 단락 사이 세로 간격 축소 */
.intro-card p { margin-bottom: 0.5rem; }
.intro-card ul { margin: 1rem 0 0.5rem; }
.intro-card > :first-child { margin-top: 0; }
.intro-card > :last-child { margin-bottom: 0; }

/* 시리즈/프로젝트 카드 제목 */
.home-card h3,
.home-card h4 { margin-top: 0; }
.home-card > :last-child { margin-bottom: 0; }

/* 개인 프로젝트: 반응형 그리드 (넓은 화면 2열, 모바일 1열) */
.card-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}
@media (max-width: 768px) {
  .card-grid { grid-template-columns: 1fr; }
}
.card-grid .home-card + .home-card { margin-top: 0; }
</style>

## 소개

<div class="home-card intro-card" markdown="1">

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

<a href="https://github.com/idean3885" target="_blank" rel="noopener">GitHub에서 전체 레포와 활동 보기 →</a>

</div>

## 주요 글

<div class="home-card" markdown="1">

운영 사례를 정리한 글입니다.

- [여러 쿠버네티스 클러스터를 백엔드 하나로 다루는 법: 설정 증설 대신 위임 서비스](/posts/multi-cluster-delegation-layer/)
- [미터링 배치 시스템 설계: 쓰기 경합·청사진·패턴 명명·저장 전략 통일까지](/posts/metering-batch-system-design/)
- [인증서 자동화: 사용자 도메인 ACME4j 구현부터 와일드카드 Jenkins 갱신까지](/posts/cert-automation-acme-and-wildcard/)

</div>

## 추천 글

<div class="home-card" markdown="1">

다른 글과 묶이지 않고 단독으로 공부한 글입니다.

- [Expand-and-Contract 패턴: 무중단 DB 스키마 변경을 3단계 PR로 분할하기](/posts/expand-and-contract-pattern/)

</div>

[전체 포스트 보기 →](/posts/)

## 개인 프로젝트

직접 만들고 운영하는 개인 프로젝트입니다.

<div class="card-grid">

<div class="home-card" markdown="1">

#### <a href="https://github.com/idean3885/claude-devex" target="_blank" rel="noopener">claude-devex</a>

* 이슈 플로우·콘텐츠 작성·교차 검증을 묶은 개인 개발 어시스턴트
* 작성 원칙·워크플로우 규칙을 하네스(SessionStart·hook·스킬)에 주입
* 매 세션 같은 출발선에서 시작

</div>

<div class="home-card" markdown="1">

#### <a href="https://github.com/idean3885/trip-planner" target="_blank" rel="noopener">trip-planner</a>

* spec-kit 풀사이클·하네스로 만든 1인 풀스택 프로젝트
* MCP 20종·RapidAPI(유료) 연동
* 자연어 숙소·항공·활동 검색을 일정에 자동 반영

</div>

<div class="home-card" markdown="1">

#### <a href="https://github.com/idean3885/claude-slack-to-notion" target="_blank" rel="noopener">claude-slack-to-notion</a>

* Slack 스레드를 Notion으로 정리하는 MCP 플러그인

</div>

</div>
