---
title: "미터링 배치를 만들고 나서야 알게 된 것들 — 배치 전략과 패턴에 이름 붙이기"
date: 2026-03-25 00:00:00 +0900
categories: [개발 기록, 미터링 시스템 구축]
tags: [설계, 아키텍처, 개발사전]
last_modified_at: 2026-04-03 19:23:58 +0900
description: >-
  배치 시스템에서 자주 쓰이는 전략과 패턴을 분류하고,
  미터링 시스템의 실제 구현과 매핑합니다.
  이름을 아는 것만으로도 설계 논의의 정밀도가 올라갑니다.
---

> **TL;DR** — 배치 시스템에서 자주 쓰이는 전략과 패턴을 분류하고,
> 미터링 시스템의 실제 구현과 매핑합니다.
> 이름을 아는 것만으로도 설계 논의의 정밀도가 올라갑니다.
{: .prompt-tip }

미터링 배치를 설계하고 구현하면서,
AI와 소통하고 블로그를 찾아가며 하나씩 결정을 내렸습니다.
마지막 성공 시점을 기록하고 누락 구간을 따라잡는 것,
같은 구간을 다시 처리해도 결과가 같게 만드는 것,
구간이 완전히 끝난 뒤에만 집계하는 것.

내용은 이해하고 있었지만,
이 결정들이 각각 Catch-up, Idempotency라는 공식 이름을 가진 패턴이었다는 걸
나중에야 알았습니다.
수집-집계 경합 방지 버퍼는
팀 내에서 Safety Margin이라 부르기로 했습니다.

이 글은 미터링 배치를 만들면서 적용한 패턴과 전략을 정리한 것입니다.
각 패턴이 무엇인지, 우리 시스템에서 어떻게 적용되었는지,
그리고 이름을 알고 나서 무엇이 달라졌는지를 기록합니다.

## 데이터 적재 전략 — 어떤 범위를 처리할 것인가

배치 파이프라인의 가장 기본적인 질문은
"매번 전체를 처리할 것인가, 변경분만 처리할 것인가"입니다.

| 전략 | 동작 | 장점 | 단점 |
|------|------|------|------|
| **Full Refresh** | 전체 삭제 후 재생성 | 단순, 누적 오류 없음 | 규모 비례 비용 |
| **Incremental Load** | 변경분만 탐지하여 적재 | 비용 효율적, 빠름 | 변경 탐지 메커니즘 필요 |
| **Micro-batch** | 초~분 단위 소량 배치 | 준실시간 달성 | 진정한 실시간은 아님 |

Incremental Load에서
"변경분을 어떻게 탐지하는가"에 따라 세부 전략이 나뉩니다.

### High Water Mark (하이워터마크)

단조 증가 컬럼(`updated_at`, `id`)의 최댓값을 기록해두고,
다음 실행 시 이후 데이터만 조회합니다.

```sql
-- 마지막 처리 시점 조회
SELECT MAX(updated_at) AS hwm
  FROM job_history
 WHERE job_id = 'aggregate-usage';

-- 변경분만 조회
SELECT * FROM source_data WHERE updated_at > :hwm;
```

구현이 단순하고 DB 부하가 낮지만,
Hard Delete를 감지할 수 없습니다.

### Snapshot Diff (스냅샷 비교)

전체 스냅샷을 떠서 이전 스냅샷과 비교합니다.
Hard Delete를 감지할 수 있지만,
두 벌의 스냅샷 저장과 비교 비용이 필요합니다.

### Change Data Capture (CDC)

DB의 트랜잭션 로그(WAL/binlog)를 직접 읽어
변경 이벤트를 캡처합니다.
Debezium, AWS DMS 같은 도구를 사용합니다.
실시간에 가까운 지연과 낮은 DB 부하가 장점이지만,
인프라 복잡도가 높습니다.

> **Polling vs CDC**:
> 전략 선택의 핵심 기준은 시스템 규모가 아니라
> **Hard Delete 감지 필요 여부**와 **실시간 지연 요구**입니다.
> Polling(주기적 쿼리)은 구현이 간단하지만
> 원본 DB에 지속적 부하를 주고 Hard Delete를 감지할 수 없습니다.
> CDC는 인프라 구성이 복잡하지만 부하가 낮고
> INSERT/UPDATE/DELETE 모두 캡처 가능합니다.
> 소규모라도 Hard Delete가 비즈니스 핵심이면 CDC가 필요하고,
> 대규모라도 Soft Delete만 쓴다면 Polling으로 충분할 수 있습니다.
{: .prompt-info }

### 우리 시스템에서는

Incremental + High Water Mark를 사용합니다.
[2편](/posts/timeseries-aggregation-batch-evolution/)에서 다룬
`JobHistoryPort`의 마지막 성공 시점(`last_success_at`)이
이 시스템에서 HWM 역할을 합니다.
이 값을 기준으로 이후 구간만 처리합니다.

이 패턴에 "High Water Mark"라는 이름이 있다는 걸 나중에 알았습니다.
이름을 알고 나니 "HWM 기반 증분 적재"라고
한 문장으로 설명할 수 있게 되었습니다.

## 복구 전략 — 누락이 생기면 어떻게 하는가

배치는 실패합니다.
스케줄러가 다운될 수도 있고,
외부 시스템이 응답하지 않을 수도 있습니다.
중요한 것은 실패 자체가 아니라,
누락된 데이터를 어떻게 복구하느냐입니다.

| 전략 | 트리거 | 동작 |
|------|--------|------|
| **Catch-up** | 시스템이 자동 감지 | 마지막 성공 시점부터 누적분을 순차 따라잡기 |
| **Backfill** | 운영자가 수동 지정 | 과거 특정 구간을 소급 (재)처리 |
| **Replay** | 이벤트 로그 기반 | 특정 시점부터 이벤트를 재생하여 상태 재구성 |

```
정상:  [10:00] → [10:10] → [10:20] → [10:30]
장애:  [10:00] → [10:10] →  (다운)
복구:  [10:00] → [10:10] → [10:20][10:30][10:40] → [10:50] → ...
                             ~~~~~~~~~~~~~~~~~~~~~~
                             catch-up (자동 복구)
```

### Catch-up과 Backfill의 차이

Catch-up은 시스템이 스스로 감지하고 자동으로 복구합니다.
Backfill은 운영자가 "이 기간을 다시 처리해 달라"고 명시적으로 요청합니다.

두 전략이 필요한 이유가 다릅니다.
Catch-up은 "배치 실패"를 복구합니다.
단일 실패든 연속 실패(예: 2시간 다운)든,
마지막 성공 시점부터 누적분을 순차 따라잡습니다.
Backfill은 "로직이 바뀌었으니 과거 결과를 새 로직으로 다시 만들어야 한다"와 같은
상황에서 필요합니다.

### Backfill 베스트 프랙티스

| 항목 | 내용 |
|------|------|
| 테스트 먼저 | 전체 백필 전에 작은 구간(하루)으로 테스트 |
| 청크 분할 | 전체 기간을 작은 단위로 쪼개서 순차 처리 |
| 기간 상한 설정 | 무제한 백필 방지 (`max-aggregate-range-days`) |
| 오프피크 실행 | 운영 DB 부하를 피해 업무 외 시간 실행 |
| 감사 로그 | 언제, 어떤 구간을, 왜 백필했는지 기록 |

### Backfill의 흔한 함정

| 함정 | 설명 |
|------|------|
| DB 락 | 대규모 UPDATE를 단일 트랜잭션으로 실행하면 테이블 락. 소규모 배치로 분할 필요 |
| 중복 레코드 | UPSERT 키 없이 INSERT하면 중복 발생. 유니크 키 식별 필수 |
| 하류 영향 | FK, 트리거, 하류 배치에 연쇄 영향. 의존성 파악 후 순서 지정 |
| 감사 추적 누락 | 백필 이력 미기록 시 롤백 불가 |

### 우리 시스템에서는

Catch-up과 Backfill을 모두 사용합니다.

`aggregateUsage()` — 크론 기반 정기 집계 + 자동 Catch-up.
`JobHistoryPort`로 마지막 성공 시점 조회,
`max-recovery-days`(7일) 상한 내에서
누락 구간을 자동 복구합니다.

`aggregateUsage(AggregateUsageRequest)` — 운영자가 기간을 지정하는 Backfill.
`max-aggregate-range-days`(7일) 상한이 적용됩니다.

같은 UseCase 메서드의 오버로드로 표현합니다.
비즈니스 능력은 "집계"로 동일하고,
트리거 방식(자동/수동)만 다르기 때문입니다.

## 실행 패턴 — 데이터를 어떻게 분할하고 처리하는가

### Chunk Processing (청크 처리)

데이터를 고정 크기 단위로
읽기 → 가공 → 쓰기를 반복합니다.
Spring Batch의 기본 처리 모델입니다.

메모리 사용량을 예측할 수 있고,
실패 시 해당 청크만 재처리할 수 있습니다.
`chunk-size`가 너무 작으면 오버헤드,
너무 크면 메모리와 락 문제가 발생합니다.

### Partitioning (파티셔닝)

데이터를 독립된 파티션으로 나누어 병렬 처리합니다.

| 방식 | 분할 기준 | 예시 |
|------|----------|------|
| Range | 값의 범위 | 날짜별, ID 범위별 |
| Hash | 해시 함수 | `user_id % N` |
| List | 명시적 목록 | 테넌트별, 리전별 |

파티션 간 데이터 독립성이 핵심입니다.
의존성이 있으면 병렬 처리 시 정합성 문제가 발생합니다.

### Windowing (윈도잉)

시간 기반으로 데이터를 그룹화합니다.
스트리밍에서 주로 언급되지만,
배치 집계에서도 동일한 개념이 적용됩니다.

| 유형 | 특성 | 배치 사례 |
|------|------|----------|
| **Tumbling** | 고정 크기, 겹침 없음 | 10분 간격 집계, 일별 집계 |
| **Sliding** | 고정 크기, 겹침 있음 | 이동 평균, 최근 N분 추세 |
| **Session** | 가변 크기, 비활동 간격으로 구분 | 사용자 세션 분석 |

```
Tumbling:  |  0-10분  |  10-20분  |  20-30분  |   ← 겹침 없음
Sliding:   |  0------10분  |                      ← 겹침 있음
               |  2------12분  |
Session:   |--이벤트--이벤트--| gap |--이벤트--|   ← 비활동 구간으로 구분
```

### 우리 시스템에서는

Tumbling Window입니다.
Interval 집계가 정확히 `[10:00, 10:10)`, `[10:10, 10:20)` 같은
고정 10분 구간으로 나뉘고, 구간이 겹치지 않습니다.

이것이 "Tumbling Window"라는 이름의 패턴이라는 걸
배치 전략을 공부하면서 알게 되었습니다.

그리고 [2편](/posts/timeseries-aggregation-batch-evolution/)에서 다룬
Stage 3(분산 처리)의 프로젝트별 분할은
List Partitioning에 해당합니다.

## 안정성 패턴 — 실패해도 괜찮은 시스템

### Idempotency (멱등성)

동일한 입력으로 여러 번 실행해도 결과가 동일합니다.
재시도, 백필, Catch-up 모두
이 성질이 전제되어야 안전합니다.

| 구현 기법 | 동작 | 적합 상황 |
|----------|------|----------|
| DELETE → INSERT | 구간 삭제 후 재생성 | 하류 참조가 없을 때 |
| UPSERT (MERGE) | PK 기준 있으면 UPDATE, 없으면 INSERT | PK 안정성이 필요할 때 |
| ON DUPLICATE KEY UPDATE | MySQL 전용 UPSERT | 단순 덮어쓰기 |

**우리 시스템에서는** 계층별로 다른 멱등성 전략을 사용합니다.

| 계층 | 전략 | 근거 |
|------|------|------|
| SourceInstance | ON DUPLICATE KEY UPDATE | 재수집 시 최신 값 갱신 |
| IntervalWorkload | UPSERT (PK 유지) | Daily 배치 조회 중 행 소실 방지 |
| IntervalInstance | DELETE + INSERT (전체 교체) | 외부 참조 없음. 삭제-삽입 사이 짧은 공백이 생기지만, 이 계층은 외부에서 직접 조회하지 않으므로 허용 가능 |

"왜 계층마다 전략이 다른가?"라는 질문의 답이
**PK 안정성**(하류 배치의 조회 안정성)이었습니다.
멱등성이라는 개념을 먼저 알았다면,
이 결정을 더 빨리 내릴 수 있었을 것입니다.

### Checkpoint (체크포인트)

처리 진행 상태를 주기적으로 저장하여,
실패 시 마지막 체크포인트부터 재개합니다.

```
[Chunk 1] ✓ → checkpoint → [Chunk 2] ✓ → checkpoint → [Chunk 3] ✗ 실패
재개 시: Chunk 3부터 (1, 2는 건너뜀)
```

**우리 시스템에서는** `JobHistoryPort`의 `last_success_at`이
Checkpoint 역할입니다.
별도 상태 테이블 없이 JobRunr의 Job 이력을 활용합니다.

### Dead Letter Queue (DLQ)

처리에 반복 실패하는 레코드를 별도 격리하여,
나머지 정상 레코드의 처리를 이어갑니다.
하나의 불량 레코드가 전체 배치를 중단시키지 않는 것이 핵심입니다.

DLQ를 도입하면 운영 프로세스도 함께 설계해야 합니다.
적재량 모니터링, 알림,
정기적 원인 분석 및 재처리가 필요합니다.

**우리 시스템에서는** 아직 DLQ를 도입하지 않았습니다.
현재는 소스별 Job 분리로 장애를 격리하고,
실패 시 다음 사이클에서 전체 재처리합니다.
소스 종류가 늘어나 레코드 단위 실패가 빈번해지면
DLQ 도입을 검토할 시점입니다.

### Retry + Exponential Backoff + Jitter

일시적 오류에 대해 점진적으로 간격을 늘리며 재시도합니다.

| 구성 요소 | 역할 |
|----------|------|
| Retry | 일시적 오류 자동 재시도 |
| Exponential Backoff | 재시도 간격을 지수적으로 증가 (서버 과부하 방지) |
| Jitter | 랜덤 지연 추가 (Thundering Herd 방지) |
| Circuit Breaker | 연속 실패 임계 초과 시 호출 차단 (장애 전파 방지) |

Retryable(네트워크 타임아웃, 5xx)과
Non-retryable(4xx, 데이터 오류)을 구분하는 것이 핵심입니다.
Non-retryable 오류를 재시도하면 리소스만 낭비됩니다.

### Reconciliation (대사)

두 데이터 소스를 주기적으로 대조하여
불일치를 탐지하고 보정합니다.
정산 시스템, 외부 API 연동 검증에서 흔히 사용됩니다.

## 데이터 정합성 — 지각한 데이터를 어떻게 다루는가

### Watermark와 Safety Margin

Watermark는 "이 시점 이전의 데이터는 모두 도착했다"고 선언하는
시간 기반 마커입니다.
Safety Margin은 예상 최대 지연에 추가하는 안전 버퍼입니다.

```
시간축:  10:00       10:10       10:15       10:20
          |-----------|-----------|-----------|
          [10:00, 10:10)          ↑           ↑
                      구간 종료   safety 만료  처리 시점
```

Safety Margin이 너무 크면 처리 지연이 증가하고,
너무 작으면 불완전한 데이터로 집계합니다.
실제 데이터의 지연 분포를 관찰하여 적정값을 결정해야 합니다.

**우리 시스템에서는** Safety Margin 5분을 적용합니다.
`endedAt + safetyMargin < now` 조건으로 구간 완료를 판단합니다.
safety margin(5분) < interval(10분)이므로
1 cron cycle(10분) 내에 흡수되어 기본 지연은 10분입니다.

이 값은 Prometheus의 수집 주기(5분)를 근거로 설정했습니다.
Safety Margin은 공식 패턴 이름이 아닙니다.
팀 내에서 수집-집계 경합 방지 버퍼를 이렇게 부르기로 했습니다.

## 회고 — 이름을 아는 것의 가치

미터링 배치를 만들면서 적용한 패턴들을 정리하면 이렇습니다.

| 우리가 한 것 | 패턴 이름 |
|------------|----------|
| 마지막 성공 시점 이후만 처리 | Incremental Load (High Water Mark) |
| 10분 고정 구간으로 집계 | Tumbling Window |
| 구간 종료 + 5분 후 처리 | Safety Margin (팀 내 명명) |
| 스케줄러 복구 시 누락 구간 자동 처리 | Catch-up |
| 운영자가 기간 지정하여 재처리 | Backfill |
| 같은 구간 재처리해도 결과 동일 | Idempotency (UPSERT) |
| JobRunr 이력으로 진행 상태 추적 | Checkpoint |
| 소스별 Job 분리 | Fault Isolation (장애 격리) |
| 프로젝트 단위 병렬 처리 (계획) | List Partitioning |

이름을 모른다고 잘못 만드는 것은 아닙니다.
실제로 미터링 배치의 대부분의 결정은
"이게 안전하겠다"는 직관에서 출발했고,
그 직관은 대부분 맞았습니다.

하지만 이름을 아는 것은 세 가지 면에서 달랐습니다.

### 1. 의사소통이 정확해집니다

"마지막 성공 시점 기록해서 그 이후만 처리하는 거"라고 설명하던 것을
"HWM 기반 Incremental Load"로 줄일 수 있습니다.
설계 리뷰에서 팀원에게 설명하는 시간이 줄고,
오해의 여지도 줄었습니다.

### 2. 선택지가 보입니다

"Incremental Load"라는 범주를 알면,
그 안에 HWM 외에도 Snapshot Diff, CDC가 있다는 것을 알게 됩니다.
현재 HWM이면 충분하다는 판단도,
다음에 CDC가 필요한 시점도 더 명확하게 인식할 수 있습니다.

### 3. 검색이 됩니다

"배치 실패 복구 전략"이라고 검색하면 일반적인 결과가 나옵니다.
"Catch-up pattern batch"라고 검색하면
정확히 필요한 사례와 베스트 프랙티스를 찾을 수 있습니다.

## 아직 적용하지 않은 패턴들

공부하면서 알게 된,
현재 시스템에는 적용하지 않았지만
규모가 커지면 검토해야 할 패턴들도 있습니다.

| 패턴 | 현재 상태 | 검토 시점 |
|------|----------|----------|
| CDC | Polling (Prometheus 쿼리) | 실시간 요구 시, DB 부하 문제 시 |
| Dead Letter Queue | 소스별 Job 분리로 대체 | 레코드 단위 실패가 빈번해질 때 |
| Reconciliation | 미적용 | 외부 과금 시스템 연동 시 |
| Circuit Breaker | 미적용 | 외부 API 의존도 높아질 때 |
| Compaction | 미적용 | 이벤트 로그 기반 전환 시 |

이 패턴들은 "언젠가 필요하니 미리 넣자"가 아니라,
[2편](/posts/timeseries-aggregation-batch-evolution/)에서 다룬 것처럼
**전환 시그널이 나타날 때** 도입하는 것이 맞다고 생각합니다.

## 참고

- [Netflix - Incremental Processing using Maestro and Apache Iceberg](https://netflixtechblog.com/incremental-processing-using-netflix-maestro-and-apache-iceberg-b8ba072ddeeb)
- Martin Fowler - [Patterns of Distributed Systems: High-Water Mark](https://martinfowler.com/articles/patterns-of-distributed-systems/high-watermark.html)
- [Backfilling Data Pipelines: Concepts, Examples, and Best Practices](https://medium.com/@andymadson/backfilling-data-pipelines-concepts-examples-and-best-practices-19f7a6b20c82)
- [Building Idempotent Data Pipelines: A Practical Guide](https://medium.com/towards-data-engineering/building-idempotent-data-pipelines-a-practical-guide-to-reliability-at-scale-2afc1dcb7251)
- [Uber - Building Reliable Reprocessing and Dead Letter Queues with Kafka](https://www.uber.com/blog/reliable-reprocessing/)
- [AWS - Timeouts, Retries and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Spring Batch - Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/scalability.html)
- [Windowing Strategies in Stream Processing](https://dataengineerblog.com/windowing-in-stream-processing/)
- [Databricks - Watermarks in Structured Streaming](https://www.databricks.com/blog/feature-deep-dive-watermarking-apache-spark-structured-streaming)

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
