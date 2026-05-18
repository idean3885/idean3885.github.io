---
title: "미터링 배치 시스템 설계: 쓰기 경합·청사진·패턴 명명·저장 전략 통일까지"
date: 2026-05-17 23:20:00 +0900
last_modified_at: 2026-05-18 15:05:00 +0900
categories: [개발 기록, 미터링 시스템 구축]
tags: [설계, 아키텍처, 배치, JPA, JobRunr, 멱등성, Tumbling Window, YAGNI]
description: >-
  Prometheus → 5분 수집 → 10분 집계 → 일간 집계 파이프라인을 만들면서 내린 네 가지 의사결정을 한 글로 정리.
  쓰기 경합을 스키마 분리와 트랜잭션 라우팅으로 해결, 4단계 진화 청사진과 전환 시그널, 적용 패턴에 이름 붙이기, UPSERT를 DELETE+INSERT 로 통일한 YAGNI 사례.
redirect_from:
  - /posts/timeseries-write-contention/
  - /posts/timeseries-aggregation-batch-evolution/
  - /posts/batch-patterns-naming/
  - /posts/batch-storage-upsert-to-delete-insert/
---

> **TL;DR**<br>
> 5분 수집 / 10분 집계 / 일간 집계 미터링 파이프라인을 만들며 네 단계 의사결정을 거쳤습니다.<br>
> (1) 쓰기 경합은 스키마 분리 + `@Transactional(readOnly)` 라우팅으로 해결. (2) 배치 진화는 내장 스케줄러 → CronJob → 이벤트 → 분산 4단계 청사진 + 전환 시그널. (3) 적용 패턴에 이름 (HWM, Tumbling Window, Catch-up, Idempotency). (4) 합리적 UPSERT 를 DELETE+INSERT 로 통일 (YAGNI).<br>
> 면접 빈출 핀포인트 두 가지 (MySQL 파티셔닝, 용량 세 제약 의사결정) 는 별도 글로 분리.
{: .prompt-tip }

## 0. 배경: 미터링 파이프라인과 기술 스택

운영 중인 클라우드 GPU 서비스의 과금 근거가 되는 사용량 데이터를 빠짐없이 수집·집계해야 했습니다. 설계부터 구현까지 본인 담당.

```
Prometheus (GPU/CPU/Memory)
    ↓ 5분 수집
[원천] Pod 단위 저장
    ↓ 10분 집계
[구간] 서비스/Pod 단위
    ↓ 일간 누적
[일간] 서비스/Pod 단위
    ↓
사용자 조회 API
```

| 분류 | 기술 |
|---|---|
| Language / Framework | Java 17, Spring Boot |
| ORM | Spring Data JPA |
| Database | MySQL (마스터/슬레이브 복제, 월별 파티셔닝) |
| Architecture | 헥사고날 아키텍처 |
| Batch | JobRunr |
| Source | Prometheus |
| Infra | Kubernetes |

## 1. 쓰기 경합: 스키마 분리 + 트랜잭션 라우팅

### 단일 DataSource 의 세 가지 문제

| 문제 | 내용 |
|---|---|
| 쓰기 경합 | 5분 수집과 10분 집계가 같은 DB 에서 동시 실행, 락 경합 |
| 조회 성능 불안정 | 배치가 대량 INSERT/UPDATE 중일 때 사용자 조회 API 응답 시간 불안정 |
| 장애 전파 | 외부 소스 하나의 응답 지연이 수집→집계→조회까지 연쇄 영향 |

서비스 수가 늘면 배치 실행 시간이 길어지고 겹침 확률이 높아집니다. 2년 예측 (분기당 50 서비스 증가) 으로 누적 약 2억 건. 단일 데이터소스로는 한계.

### 세 방안 검토

| 방안 | 평가 |
|---|---|
| 시간대 분리 | 5분/10분으로 촘촘해서 시간대 확보 어려움. 한 배치 지연 시 연쇄 |
| **스키마 분리 + 트랜잭션 라우팅 (선택)** | 영역별 장애 격리, 읽기 부하 분산, DataSource 복잡도 증가 |
| 메시지 큐 기반 비동기 | 완전 디커플링이지만 현재 규모 대비 인프라 과함, 순서 제어 등 고려 부담 |

### 영역 분리 설계

| 영역 | 역할 | 스키마 |
|---|---|---|
| 원천 (Source) | Pod 데이터 수집만, 비즈니스 로직 없음 | 별도 스키마 (마스터/슬레이브) |
| 가공 (Processing) | 집계 + 조회, 비즈니스 로직 포함 | 기본 스키마 (마스터) |

가공은 집계 주기 (10분) 와 조회 패턴이 겹칠 가능성이 낮아 마스터 하나로 충분하다고 판단. 원천만 슬레이브 라우팅.

### `@Transactional(readOnly)` 기반 라우팅

`AbstractRoutingDataSource` 를 확장하여 트랜잭션의 readOnly 속성으로 라우팅.

```java
public class ReadWriteRoutingDataSource extends AbstractRoutingDataSource {
  @Override
  protected Object determineCurrentLookupKey() {
    return TransactionSynchronizationManager
        .isCurrentTransactionReadOnly() ? "slave" : "master";
  }
}
```

서비스 레이어는 어노테이션만 붙이면 라우팅이 결정됩니다.

```java
@Transactional(value = "sourceTransactionManager", readOnly = true)
public List<SourceMetric> findByRange(Instant from, Instant to) { ... }  // → 슬레이브

@Transactional(value = "sourceTransactionManager")
public void saveAll(List<SourceMetric> instances) { ... }  // → 마스터
```

원천 영역은 독립된 `EntityManagerFactory` 와 `TransactionManager`. 가공은 Spring Boot 기본 설정 그대로.

### 미리 대응한 엣지 케이스

- **슬레이브 복제 지연**: 집계 주기 (10분) 가 수집 주기 (5분) 보다 길어 자연스러운 버퍼 확보
- **배치 실패 시 빈 구간**: 마지막 성공 시점 추적 + 자동 재처리
- **멀티 소스 장애 격리**: 소스별 Job 분리
- **데이터 증가 대응**: 월별 파티셔닝 + 일정 기간 후 아카이빙

CQRS 라고 하면 이벤트 소싱이나 별도 읽기 저장소를 떠올리기 쉽지만, **스키마 분리 + 트랜잭션 라우팅만으로도 쓰기/읽기 독립 이점을 얻을 수 있었다**. 시스템 규모에 맞는 수준 선택이 더 중요합니다.

## 2. 배치 진화 청사진: Stage 0 → 3 + 전환 시그널

핵심 원칙은 **전환 시그널이 나타날 때까지 현재 단계 유지**. 미리 과도하게 설계하면 복잡성만 늘어납니다.

### Stage 0: 내장 스케줄러 + 상시 서버 (현재)

JobRunr `BackgroundJobServer` 가 주기적으로 Job 폴링. 메서드명이 곧 Job 이름이라 이름을 바꾸면 새 Job 으로 인식되어 이력이 단절됩니다. 이 제약은 **Job 이력 일관성이 실패 복구의 기반**이라 의도적.

```java
@Job  // name 생략 → 메서드명이 Job 이름
public void collectSource() {
    var from = helper.getLastSuccessAt("collectSource");
    var rawData = prometheus.queryRange(query, from, now, "1m");
    sourceRepository.upsertAll(rawData);  // 멱등성 (UPSERT)
}
```

**왜 CronJob 이 아니라 상시 서버?**

CronJob 은 매 실행마다 JVM 기동 (~30초) 이 실제 작업 시간 (~10초) 의 3배. 5분마다 이 비용을 내느니 서버 상시 띄우는 편이 합리적.

| 시그널 | 의미 |
|---|---|
| 적합 규모 | 소스 1~2종, 인스턴스 수천 건, 단일 DB |
| 한계 시그널 | 유휴 리소스 80%+, Job 미실행 시간 대부분 |

상시 서버의 대가는 하루 약 48분만 실행되고 나머지 23시간 12분은 JobRunr 폴링과 Health Check 만 하면서 리소스 점유.

### Stage 1: CronJob + Native Image

상시 점유 → 실행 시에만 리소스. GraalVM Native Image 로 기동 ~0.5초, 메모리 128MB 로 줄이면 CronJob 의 기동 오버헤드 문제가 크게 풀립니다.

대가: JobRunr 의 Job 이력 자동 관리가 없으니 별도 `BatchStatusRepository` 로 마지막 성공 시점을 직접 관리.

**전환 시그널**: 유휴 리소스 비용 > 구현 복잡성 비용

### Stage 2: 이벤트 기반 (수집과 집계 디커플링)

```
[CronJob: 수집] → [Message Queue] → [집계 Worker]
                  (수집 완료 이벤트)
```

소스 종류가 늘면 시간 기반 집계 (10:10) 시점에 일부 소스 데이터가 아직 없을 수 있습니다. 이벤트 기반이면 **모든 소스 수집 완료 후** 집계 시작.

대가: Exactly-once 처리. Stage 0 부터 유지한 멱등성 (UPSERT) 이 빛을 발합니다.

**전환 시그널**: 소스 종류 3개 이상, 수집-집계 타이밍 이슈 발생

### Stage 3: 분산 처리 (파티셔닝)

Prometheus 쿼리당 총 샘플 수 제한 (기본 5천만). 인스턴스 5,000개 + 7일 복구가 필요하면 단일 쿼리로 한계 도달.

```
총 샘플 수 = 인스턴스 수 × (시간 범위(분) / step(분))
5,000 × (7일 × 1,440 / 1) = 50,400,000  ← 5천만 초과
```

| 파티셔닝 전략 | 장단 |
|---|---|
| Range (네임스페이스 A~M / N~Z) | 단순, 데이터 편중 가능 |
| Hash (`hash(groupId) % N`) | 균등, 리밸런싱 복잡 |
| **논리 (프로젝트 단위)** | 비즈니스 의미 일치 (과금 단위), 프로젝트 크기 불균등 |

미터링은 **논리 분할 (프로젝트 단위)** 이 적합. 분할 경계가 과금 단위와 일치.

**전환 시그널**: 단일 Prometheus 쿼리 한계 도달, 처리 시간이 배치 주기 초과

### 단계를 관통하는 원칙

| 원칙 | 단계별 구현 |
|---|---|
| 멱등성 | 모든 단계에서 UPSERT 패턴 유지 |
| 마지막 성공 시점 기반 복구 | JobRunr 이력 → 별도 테이블 → 이벤트 오프셋 (구현은 달라도 추적 원칙은 동일) |
| 데이터 완전성 우선 | 성능보다 누락 방지가 먼저, 구간이 완전히 끝난 후에만 집계 |

## 3. 적용 패턴에 이름 붙이기

배치를 만들면서 "이게 안전하겠다" 는 직관으로 결정한 것들이 사실 공식 이름이 있는 패턴이었습니다.

| 우리가 한 것 | 패턴 이름 |
|---|---|
| 마지막 성공 시점 이후만 처리 | Incremental Load (**High Water Mark**) |
| 10분 고정 구간으로 집계 | **Tumbling Window** |
| 구간 종료 + 5분 후 처리 | **Safety Margin** (팀 내 명명) |
| 스케줄러 복구 시 누락 구간 자동 처리 | **Catch-up** |
| 운영자가 기간 지정하여 재처리 | **Backfill** |
| 같은 구간 재처리해도 결과 동일 | **Idempotency** (UPSERT) |
| JobRunr 이력으로 진행 상태 추적 | **Checkpoint** |
| 소스별 Job 분리 | **Fault Isolation** |
| 프로젝트 단위 병렬 처리 (계획) | **List Partitioning** |

### Catch-up vs Backfill

같은 UseCase 메서드의 오버로드로 표현합니다. 비즈니스 능력은 "집계"로 동일하고 트리거 방식만 다르기 때문.

```java
aggregateUsage()                          // Catch-up (자동, 크론 기반 + 누락 구간 복구)
aggregateUsage(AggregateUsageRequest)     // Backfill (수동, 운영자가 기간 지정)
```

`max-recovery-days` (7일) 와 `max-aggregate-range-days` (7일) 상한이 무한 백필을 차단.

### 계층별 멱등성 전략

같은 멱등성 원칙이라도 계층마다 구현이 다릅니다.

| 계층 | 전략 | 근거 |
|---|---|---|
| 원천 수집 | `ON DUPLICATE KEY UPDATE` | 재수집 시 최신 값 갱신 |
| 구간 집계 (서비스) | UPSERT (PK 유지) | 일간 배치 조회 중 행 소실 방지 |
| 구간 집계 (Pod) | DELETE + INSERT (전체 교체) | 외부 참조 없음. 짧은 공백 허용 가능 |

이건 4장 전환의 출발점이 됐습니다.

### 이름을 아는 것의 가치

1. **의사소통이 정확해집니다**: "HWM 기반 Incremental Load" 한 문장으로 줄어듭니다
2. **선택지가 보입니다**: "Incremental Load" 안에 HWM 외에도 Snapshot Diff, CDC 가 있습니다
3. **검색이 됩니다**: "Catch-up pattern batch" 로 정확한 사례·베스트 프랙티스를 찾을 수 있습니다

## 4. 저장 전략 통일: UPSERT → DELETE + INSERT (YAGNI)

### UPSERT 선택의 합리성

미터링 배치 설계 초기 `INSERT ... ON DUPLICATE KEY UPDATE` 선택 근거는 명확했습니다.

- 멱등성: 동일 키 재수집해도 중복 없음
- 동시성 안전: 유니크 키 제약으로 충돌 감지
- 패턴 검증: 시계열 배치 모범 사례

AI 딥리서치도, 다른 시스템 사례도, UPSERT 가 맞다는 결론.

### 전환점: 팀원 자문

리뷰에서 팀원 자문 결과가 리서치와 달랐습니다.

| 항목 | 수치 | 의미 |
|---|---|---|
| 개발팀 규모 | 5인 | 유지보수 인력 한정 |
| 서비스 유형 | B2B2C GPU | 정적 엔터프라이즈, 버스트 트래픽 구조적으로 낮음 |
| 현재 Pod 규모 | ~500개 | 전체 합산 |
| 설계 최대치 | ~2,000개 | 물리 GPU 자원 상한 |
| 배치 아키텍처 | 단일 노드 JobRunR | 동시성 경합 구조적으로 불가능 |

**합리적인 설계였지만 우리 규모에서는 오버 엔지니어링이었습니다.**

> AI 에게 아무리 딥리서치를 시키고 다른 사례를 봐도 이런 결론은 나오지 않았습니다. "~2,000 Pod 상한의 B2B2C GPU 서비스에서 5인이 유지보수합니다" 라는 맥락은 어떤 리서치에도 다뤄지지 않습니다. 이 판단은 서비스 맥락을 이해하는 팀원에게서 나왔습니다.
{: .prompt-info }

### 쿼리 비용 비교

`ON DUPLICATE KEY UPDATE` 는 행마다 유니크 키 존재 여부를 확인. **내부 SELECT 가 반드시 1건 발생**. JDBC batch 로 1회 왕복에 전송해도 마찬가지.

```text
UPSERT (N건):      내부 SELECT × N + INSERT/UPDATE × N = 2N 연산
DELETE+INSERT:     range DELETE × 1 + batch INSERT × 1 = 2 연산
```

Pod 별 원천 수집 (5분 주기, 하루 288회) 누적.

| 규모 | ODKU | DELETE+INSERT |
|---|---|---|
| 현재 (~500 Pod) | 1,440,000 | 576 |
| 최대 (~2,000 Pod) | 5,760,000 | 576 |

실측 성능 차이는 현재 규모에서 밀리초 단위. 소규모에서는 체감되지 않습니다.

**성능이 비슷하다면 더 단순한 쪽이 이깁니다.** 5인 팀에서 JDBC 하드코딩 SQL 관리 비용은 성능 이점을 상회합니다.

### 파이프라인 전체 통일

| 단계 | 삭제 단위 | 삽입 방식 | 쿼리 수 |
|---|---|---|---|
| Pod 별 원천 수집 | 수집 범위 (`from`~`to`) | JPA `saveAll()` | 2 |
| 구간 집계 (서비스) | 구간 (`started_at`, `ended_at`) | JPA `saveAll()` | 2 |
| 구간 집계 (Pod) | 서비스에 종속 | JPA `saveAll()` | 2 |
| 일간 집계 (서비스) | 날짜 | JPA `saveAll()` | 2 |
| 일간 집계 (Pod) | 서비스에 종속 | JPA `saveAll()` | 2 |

모든 단계가 같은 패턴.

```java
repository.deleteAllBy...(from, to);    // 1. 범위 삭제
repository.createAll(entities);          // 2. saveAll (DELETE + INSERT)
```

핵심 변경.

| 항목 | Before | After |
|---|---|---|
| 저장 방식 | JDBC batch UPSERT / Native SQL | JPA `saveAll` (DELETE + INSERT) |
| 유니크 키 | 복합 유니크 키 (충돌 감지) | 없음 (일반 인덱스만) |
| PK 전략 | IDENTITY | SEQUENCE (Hibernate 배치 INSERT 활성화) |
| 삭제 방식 | 없음 | 범위 기준 일괄 삭제 |

### 교훈: 합리적 설계 ≠ 올바른 설계

일반론으로 옳은 결정이 특정 맥락에서는 오버 엔지니어링이 됩니다. 돌이켜보면 YAGNI 위배였습니다. 현재 필요하지 않은 동시성 보호를 미리 설계한 것이 비용이 되었습니다. 그 경계를 판단하는 것은 코드가 아니라 사람입니다.

## 회고: 미터링 시스템의 의사결정 흐름

| 단계 | 의사결정 | 핵심 원칙 |
|---|---|---|
| 1. 쓰기 경합 | 스키마 분리 + 트랜잭션 라우팅 (CQRS 라이트) | 시스템 규모에 맞는 수준 |
| 2. 진화 청사진 | Stage 0~3 + 전환 시그널 정의 | 시그널이 올 때까지 현재 단계 유지 |
| 3. 패턴 명명 | HWM, Tumbling Window, Catch-up, Idempotency | 이름이 의사소통과 검색을 정확하게 만든다 |
| 4. 저장 통일 | UPSERT → DELETE + INSERT | 합리적 설계와 올바른 설계는 다르다 (YAGNI) |

배치 시스템 설계의 핵심 역량은 **적정 설계 선택**이라고 생각합니다. 다음 단계로의 전환 시점을 판단하는 능력이 정확한 청사진보다 중요합니다.

이 시스템의 면접 빈출 주제 두 가지는 별도 글로 분리했습니다.
- 데이터 증가 대응의 구체적 구현: [MySQL 파티셔닝 도입기 (JPA 복합 키 전환부터 시간 독립 DDL까지)](/posts/mysql-partitioning-jpa-composite-key/)
- 용량 설계의 근거: [어디까지 견뎌야 하는가: 미터링 용량을 세 가지 제약으로 역산한 의사결정](/posts/metering-capacity-triple-constraint/)

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
