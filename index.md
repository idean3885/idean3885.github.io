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

Spring Boot·Kubernetes 기반 멀티테넌시 서비스를 개발·운영하는 7년차 백엔드 개발자입니다.
과금 미터링 데이터 파이프라인을 설계해 일 수십만 건을 수집·집계하고,
서비스 개발과 운영을 함께 맡아 리소스·노드 안정화 같은 운영 이슈를 인프라와 함께 풀어왔습니다.

결과만큼 분석을 중요하게 봅니다. 깊이 분석할수록 방향이 잡히고, 방향이 틀어지면 결과도 달라진다고 생각합니다.

<a href="https://github.com/idean3885" target="_blank" rel="noopener">GitHub 프로필에서 기술 스택·활동 보기 →</a>

</div>

## 주요 글

<div class="home-card" markdown="1">

직접 설계하고 운영한 대표 작업입니다.

- [여러 개발 플러그인을 하나로: 컨텍스트가 1M이 되자 분리가 손해였다](/posts/dev-plugins-into-one-assistant/)
- [미터링 배치 시스템 설계: 쓰기 경합·청사진·패턴 명명·저장 전략 통일까지](/posts/metering-batch-system-design/)
- [여러 쿠버네티스 클러스터를 백엔드 하나로 다루는 법: 설정 증설 대신 위임 서비스](/posts/multi-cluster-delegation-layer/)
- [인증서 자동화: 사용자 도메인 ACME4j 구현부터 와일드카드 Jenkins 갱신까지](/posts/cert-automation-acme-and-wildcard/)
- [교차 검증 도구 3개월: 사상·구현·운영과 스스로 찾은 맹점](/posts/cross-verify-tool-3month/)

</div>

[전체 포스트 보기 →](/posts/)

## 개인 프로젝트

직접 만들고 운영하는 개인 프로젝트는 GitHub 프로필에 정리합니다.

<div class="home-card" markdown="1">

<a href="https://github.com/idean3885" target="_blank" rel="noopener">GitHub 프로필에서 개인 프로젝트 보기 →</a>

</div>
