# Architecture Decision Records

블로그 운영 의사결정의 영구 기록.

CLAUDE.md가 *현재 규칙*만 담는다면, ADR은 *왜 그 규칙으로 정했는가*를 담는다. 결정의 배경·대안·결과를 한 파일에 모아 휘발을 방지한다.

## 위치 및 빌드 제외

- 경로: `docs/adr/NNNN-title.md`
- `_config.yml`의 `exclude:` 목록에 `docs`가 명시되어 Jekyll 빌드에서 제외됨
- 외부에 노출되지 않고 레포 내부 참조용

## 파일명 규칙

`NNNN-kebab-case-title.md`

- `NNNN`: 4자리 일련번호 (0001부터, gap 허용)
- `title`: 결정을 짧게 요약하는 kebab-case 슬러그

예: `0002-kubernetes-as-strength-surface.md`

## 상태 모델

| 상태 | 의미 |
|------|------|
| Proposed | 초안, 합의 전 |
| Accepted | 채택, 적용 중 |
| Deprecated | 더 이상 적용 안 함, 대체 결정 존재 |
| Superseded by ADR-NNNN | 다른 ADR로 교체됨 |

## ADR 템플릿

```markdown
# ADR-NNNN: 제목

## Status

Accepted (YYYY-MM-DD)

## Context

왜 이 결정이 필요했는가. 어떤 문제·제약·기회가 있었는가.

## Decision

무엇을 결정했는가. 명시적·검증 가능한 문장으로.

## Consequences

이 결정으로 무엇이 따라오는가. 긍정·부정 모두.

## Alternatives Considered

검토했지만 채택하지 않은 안과 그 이유.

## References

관련 PR/Issue/외부 링크.
```

## 인덱스

| # | 제목 | 상태 | 날짜 |
|---|------|------|------|
| [0001](0001-adopt-adr-for-blog-decisions.md) | 블로그 의사결정을 ADR로 기록 | Accepted | 2026-05-15 |
| [0002](0002-kubernetes-as-strength-surface.md) | Kubernetes를 별도 시리즈로 노출하여 강점 가시화 | Accepted | 2026-05-15 |
