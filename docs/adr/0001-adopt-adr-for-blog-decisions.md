# ADR-0001: 블로그 의사결정을 ADR로 기록

## Status

Accepted (2026-05-15)

## Context

블로그 운영 결정(카테고리 구조, 시리즈 운영 방식, 발행 규칙, Chirpy 스타일링 등)이 다음 위치에 흩어져 있어 일관성 유지가 어려웠다.

- `CLAUDE.md`: 현재 규칙만 담음. 결정 배경 없음
- 휘발성 메모리: 세션 단위로 휘발, 다음 세션·다른 에이전트에서 재현 불가
- 커밋 메시지: 검색은 가능하나 결정 단위로 묶이지 않음
- GitHub Issue: 클로즈되면 발견 동선 약함

결정의 *왜*가 기록되지 않으면 시간이 지난 뒤 같은 의사결정을 반복하거나 정반대로 회귀할 위험이 있다.

## Decision

블로그 레포 `docs/adr/` 디렉토리에 ADR(Architecture Decision Record) 파일로 결정을 영구 기록한다.

- 위치: `docs/adr/NNNN-title.md`
- 형식: `README.md` 템플릿 준수
- 인덱스: `README.md` 표 갱신
- 빌드 제외: `_config.yml`의 `exclude:`에 이미 `docs`가 명시되어 Jekyll 사이트로 노출되지 않음

## Consequences

긍정:

- 결정 배경(왜)이 결정 본문(무엇)과 함께 영구 보존됨
- 세션 휘발과 무관하게 다음 작업자(미래의 본인 + AI 에이전트)가 추적 가능
- ADR 번호로 의사결정 그래프 추적 가능 (`Superseded by` 링크)
- CLAUDE.md는 *현재 규칙*만 담아 가독성 유지

부정:

- 결정 시점에 ADR 작성 비용 추가 (5-10분)
- README.md 인덱스 동기화 필요

## Alternatives Considered

| 대안 | 기각 사유 |
|------|----------|
| CLAUDE.md에 결정 배경 추가 | CLAUDE.md는 *현재 규칙* 문서. 결정 이력이 섞이면 가독성 저하 |
| GitHub Issue 라벨 "decision" 운영 | 클로즈된 이슈는 발견 동선 약함, 본문 편집 이력 추적 불편 |
| 휘발성 메모리 기록 | 세션 단위 휘발, 원천이 아님, 다른 세션·도구에서 접근 불가 |

## References

- Issue: #271
- 첫 적용 ADR: [0002-kubernetes-as-strength-surface.md](0002-kubernetes-as-strength-surface.md)
