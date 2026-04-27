---
title: "MySQL 파티셔닝 도입기: JPA 복합 키 전환부터 시간 독립 DDL까지"
date: 2026-04-16 21:30:00 +0900
last_modified_at: 2026-04-20 23:20:00 +0900
categories: [개발 기록, 미터링 시스템 구축]
tags: [설계, 아키텍처, 테스트]
pin: true
description: >-
  미터링 테이블 5개에 월별 RANGE COLUMNS 파티셔닝을 도입했습니다.
  MySQL의 파티션 키 제약으로 복합 PK 전환, JPA @IdClass 도입,
  시간 독립 DDL 확보까지의 과정을 정리합니다.
---

> **TL;DR**<br>
> 미터링 테이블 5개에 월별 RANGE COLUMNS 파티셔닝을 도입했습니다.
> MySQL의 "파티션 키는 모든 유일성 키에 포함되어야 한다"는 제약으로
> 단일 PK를 복합 PK로 전환했고,
> JPA `@IdClass`와 Flyway DDL 분리로 두 세계의 충돌을 해소했습니다.<br>
> `findByKeyId` 컨벤션도 도입했습니다.
> DDL에는 `p_max`만 선언하고 Job이 동적으로 파티션을 생성하여
> 시간 독립적인 DDL을 확보했습니다.
{: .prompt-tip }

## 도입

### 시스템 배경

미터링 시스템은 클라우드 리소스 사용량을 시계열로 수집하고 집계합니다.

```text
모니터링 시스템 → [5분 수집] → raw_data
                              ↓
                        [10분 집계] → interval_aggregation / interval_detail
                              ↓
                        [일별 집계] → daily_aggregation / daily_detail
```

이 데이터는 과금 근거이므로 연 단위 보관이 필요합니다.
서비스 규모가 커지면서 테이블 크기와 아카이빙 전략을 고민해야 하는 시점이 왔습니다.

### 대상 테이블

| 스키마 | 테이블 | 파티션 키 | 특성 |
|--------|--------|-----------|------|
| metering_source | metering_raw_data | collected_at | 5분 주기 수집, 최대 볼륨 |
| metering | metering_interval_aggregation | started_at | 10분 주기 집계 |
| metering | metering_interval_detail | started_at | 10분 주기 집계 |
| metering | metering_daily_aggregation | metering_date | 일별 집계 |
| metering | metering_daily_detail | metering_date | 일별 집계 |

## 문제

### MySQL 파티셔닝의 필수 제약

MySQL RANGE COLUMNS 파티셔닝에는 하나의 절대적인 제약이 있습니다.

> 파티션 키는 테이블의 모든 유일성 키(PK, UK)에 포함되어야 합니다.<br>
> MySQL은 단일 파티션 내에서만 유일성을 검증하기 때문입니다.
> 파티션 키가 PK에 없으면 서로 다른 파티션에 같은 PK 값이 존재할 수 있어,
> 전역 유일성을 보장할 수 없습니다.
{: .prompt-warning }

기존 테이블은 서로게이트 키 `id`를 단일 PK로 사용하고 있었습니다.
파티셔닝을 도입하려면 `(id, 파티션키)` 복합 PK로 전환해야 합니다.

### JPA와 MySQL 파티셔닝의 충돌

Hibernate는 MySQL 파티셔닝을 지원하지 않습니다.
DDL 생성 시 파티셔닝 구문을 만들어주지 않고,
엔티티 매핑에도 파티셔닝 개념이 없습니다.

이로 인해 세 가지 충돌이 발생합니다.

| 충돌 | 원인 | 영향 |
|------|------|------|
| DDL 관리 | Hibernate DDL 자동 생성으로는 파티셔닝 불가 | DDL을 Flyway로 분리 관리 필요 |
| 엔티티 PK | 단일 `@Id`에서 복합 PK로 전환 필요 | `@IdClass` 도입 + Key 클래스 신규 |
| Repository 조회 | `CrudRepository.findById(CompositeKey)` vs 단일 id 조회 공존 | 새로운 조회 컨벤션 필요 |

### Daily 테이블도 파티셔닝해야 하는가

Daily 테이블은 하루 1건씩만 적재되므로 데이터 양이 적습니다.
연별 파티셔닝이나 파티셔닝 제외를 검토할 수 있습니다.

> 5인 팀이 유지보수하는 서비스에서 "Daily는 연별, Interval은 월별"이라는 예외 규칙은
> 운영 실수를 유발합니다.<br>
> 파티셔닝의 본질적 가치는 성능보다 아카이빙에 있습니다.
> 보관 주기가 만료된 데이터를 `PARTITION DROP`으로 즉시 제거하려면
> 모든 테이블이 동일한 파티셔닝 단위를 가져야 합니다.
{: .prompt-info }

연별 파티셔닝의 문제도 있습니다.
과금 데이터 보관 주기를 13개월로 설정하면,
연별 파티션에서는 24개월을 보관해야 합니다.
월 단위 제어가 불가능합니다.

**결론**: 전 테이블 5개를 월별 파티셔닝으로 통일했습니다.

## 해결

### 1. 복합 PK 전환: @IdClass

각 테이블의 파티션 키를 PK에 추가하고,
JPA `@IdClass`로 복합 PK를 선언했습니다.

| 엔티티 | Key 클래스 | PK 구성 |
|--------|-----------|---------|
| IntervalAggregationEntity | IntervalAggregationKey | (id, startedAt) |
| IntervalDetailEntity | IntervalDetailKey | (id, startedAt) |
| DailyDetailEntity | DailyDetailKey | (id, meteringDate) |

기존에 이미 복합 PK였던 두 테이블은 Key 클래스만 존재했습니다.

| 엔티티 | 기존 상태 |
|--------|----------|
| DailyAggregationEntity | 복합 PK 전환 완료 |
| RawDataEntity | 복합 PK 전환 완료 |

Key 클래스는 `Serializable`을 구현하고,
`id` + 파티션 키 두 필드만 갖는 단순한 구조입니다.

```java
@EqualsAndHashCode
@NoArgsConstructor
@AllArgsConstructor
public class IntervalAggregationKey implements Serializable {
  private Long id;
  private ZonedDateTime startedAt;
}
```

### 2. Repository 조회 컨벤션: findByKeyId

복합 PK 전환 후 `CrudRepository.findById()`의 파라미터가 Key 클래스로 바뀝니다.
그런데 서로게이트 `id`는 여전히 전역적으로 유일합니다.
비즈니스 로직에서는 `id` 하나로 조회할 수 있어야 합니다.

기존에는 `findFirstById(Long id)`라는 이름을 사용했습니다.

> `findFirstById`는 "여러 건 중 첫 번째"라는 의미를 내포합니다.<br>
> 실제로 `id`는 SEQUENCE로 생성되므로 항상 1건입니다.
> 복합 키를 모르는 개발자가 보면 "왜 First가 붙어 있지?"라는 의문이 생깁니다.
{: .prompt-info }

검토한 대안입니다.

| 대안 | 문제 |
|------|------|
| `findById(Long)` + `@Query` | `CrudRepository.findById(Key)`와 이름 충돌. 새 개발자가 두 `findById` 혼동 |
| `findByGeneratedId` | "generated"는 구현 상세 노출 |
| `findByIdEquals` | "Equals"는 노이즈 |

**최종**: `findByKeyId` ("복합 Key의 Id로 찾는다")

```java
@Query("SELECT e FROM IntervalAggregationEntity e WHERE e.id = :id")
Optional<IntervalAggregationEntity> findByKeyId(@Param("id") Long id);
```

`@Query` JPQL을 명시한 이유는 메서드 이름과 엔티티 프로퍼티 경로가 다르기 때문입니다.
`@IdClass` 환경에서 `id`는 엔티티의 직접 필드입니다.
Spring Data는 `findByKeyId`를 `key.id` 경로로 해석합니다.
엔티티에 `key` 프로퍼티가 없으므로 파생 쿼리 생성이 실패합니다.
읽기 좋은 메서드 이름을 유지하면서 JPQL로 실제 쿼리를 직접 지정했습니다.

### 3. Flyway DDL에 파티셔닝 직접 반영

v1.5는 마이그레이션이 아니라 새로운 시작입니다.
별도 ALTER TABLE 스크립트 대신 CREATE TABLE에 파티셔닝을 직접 포함했습니다.

```sql
CREATE TABLE metering_raw_data (
    id               BIGINT NOT NULL,
    collected_at     DATETIME(3) NOT NULL,
    -- ... 생략
    PRIMARY KEY (id, collected_at),
    INDEX idx_metering_raw_data_collected_at (collected_at)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
    PARTITION BY RANGE COLUMNS (collected_at) (
        PARTITION p_max VALUES LESS THAN MAXVALUE
    );
```

### 4. 시간 독립 DDL: p_max 전략

초기 구현에서는 DDL에 구체적인 날짜 파티션을 하드코딩했습니다.

```sql
-- 초기 버전 (시간 종속적)
PARTITION BY RANGE COLUMNS (collected_at) (
    PARTITION p202603 VALUES LESS THAN ('2026-04-01'),
    PARTITION p202604 VALUES LESS THAN ('2026-05-01'),
    PARTITION p202605 VALUES LESS THAN ('2026-06-01'),
    PARTITION p_max VALUES LESS THAN MAXVALUE
);
```

> 이 DDL을 내년 신규 설치에 그대로 사용하면
> `p202603`~`p202605`는 과거 날짜의 빈 파티션으로 남습니다.<br>
> 설치할 때마다 날짜를 수정해야 하는 DDL은 재사용할 수 없습니다.
{: .prompt-warning }

해결은 단순합니다.
DDL에는 `p_max`(MAXVALUE) 파티션만 선언합니다.
파티션 관리 Job이 첫 실행에서 `p_max`를 `REORGANIZE`하여
필요한 월별 파티션을 동적으로 생성합니다.

```text
DDL 실행 직후:    [p_max(MAXVALUE)]
Job 첫 실행 후:   [p202603] [p202604] [p202605] [p202606] [p_max]
```

DDL은 시간에 독립적이 되고, 파티션 생성은 Job에게 위임됩니다.

### 5. 파티션 관리 자동화

`PartitionJobService`가 5개 테이블의 파티션을 통합 관리합니다.

```text
PartitionJobService
  → PartitionPort.findExistingPartitions(schema, table)
    → INFORMATION_SCHEMA.PARTITIONS 조회
  → PartitionPort.addMonthlyPartition(schema, table, column, month)
    → ALTER TABLE REORGANIZE PARTITION p_max INTO (새 파티션, p_max)
```

2개 스키마를 다루므로 DataSource별 JdbcTemplate을 분리했습니다.
Operator Controller를 통해 수동 트리거도 가능합니다.

테스트는 Spock으로 7개 케이스를 작성했습니다.

| 테스트 케이스 | 검증 내용 |
|--------------|----------|
| 5개 테이블 관리 | 대상 테이블 누락 없이 호출 |
| 파티션 키 컬럼 정확성 | 테이블별 올바른 파티션 키 전달 |
| monthsAhead=3 생성 수 | 5 테이블 x 4개월 = 20회 호출 |
| 기존 파티션 건너뛰기 | 중복 생성 방지 |
| 전체 존재 시 미생성 | 불필요한 DDL 실행 방지 |
| 연속 월 범위 검증 | 현재월부터 연속된 월 생성 |
| monthsAhead=0 | 현재월만 생성 |

## 회고

### 설계 결과

| 항목 | Before | After |
|------|--------|-------|
| PK 구조 | 단일 서로게이트 키 | 복합 PK (서로게이트 + 파티션 키) |
| DDL 관리 | Flyway (파티셔닝 없음) | Flyway (파티셔닝 포함) |
| 파티셔닝 대상 | raw_data + daily_aggregation | 전 미터링 테이블 5개 |
| 아카이빙 | 불가 (DELETE 필요) | 파티션 DROP으로 즉시 제거 |
| DDL 재사용성 | 시간 종속적 | 시간 독립적 |

### Self-healing: 배치 장애 자동 복구

파티셔닝으로 데이터 수명주기를 관리하면,
배치 실패 시 복구도 파티션 단위로 가능합니다.
미터링 배치에는 Self-healing 패턴을 적용하여
외부 개입 없이 누락 데이터를 자동 보충합니다.

```text
[배치 실패] → [즉시 재시도 2회] → [포기]
                                      ↓
              [다음 cron 주기] → [복구 윈도우 내 누락 구간 탐지] → [백필로 보충]
```

이 설계가 성립하는 이유는 미터링 배치의 세 가지 속성 덕분입니다:

| 속성 | 미터링 시스템 적용 |
|------|-------------------|
| **멱등성** | DELETE + INSERT 패턴 (이전 편에서 전환 완료) |
| **복구 윈도우** | `max-recovery-days: 7`. 파티션 보관 주기(13개월) 내이므로 데이터 항상 존재 |
| **누락 탐지** | JobHistory 기반 gap 탐지. 마지막 성공 시점 이후 빈 구간 자동 식별 |

> 재시도는 '같은 시도를 반복'하는 것이고,
> Self-healing backfill은 '다음 기회에 빠진 부분을 채우는' 것입니다.<br>
> 재시도 횟수를 과도하게 늘리는 것은 Self-healing이 있다면 불필요합니다.
{: .prompt-info }

### 배운 것

이번 작업에서 가장 먼저 부딪힌 벽은 MySQL의 파티셔닝 제약이었습니다.
"파티션 키는 유일성 키의 부분집합이어야 한다". 이 한 줄의 제약 때문에
서로게이트 키 단독 PK라는 익숙한 구조를 포기해야 했습니다.

그 다음 벽은 JPA였습니다.
Hibernate는 파티셔닝이라는 개념 자체를 모릅니다.
DDL과 엔티티를 각각 따로 관리하는 수밖에 없다고 생각했습니다.
다행히 `@IdClass` 복합 PK는 파티션 유무와 무관하게 동작해서,
로컬과 운영 환경이 같은 엔티티 코드를 공유할 수 있었습니다.

`findByKeyId`라는 이름은 이 과정에서 자연스럽게 나왔습니다.
`CrudRepository.findById(CompositeKey)`와
비즈니스 로직의 단일 id 조회가 부딪히는 지점에서,
Key 클래스명과 자연스럽게 연결되는 이름을 찾았습니다.
컨벤션은 설계 초기에 정하는 것이 아니라,
충돌이 발생한 지점에서 필요에 의해 태어난다는 걸 느꼈습니다.

마지막으로, DDL에 날짜를 하드코딩하면 안 된다는 교훈을 얻었습니다.
`p_max`만 선언하고 Job이 동적으로 파티션을 생성하는 패턴으로 전환한 뒤에야
DDL이 시간에서 자유로워졌습니다.

### 남은 과제

- 파티션 보관 주기 만료 시 자동 DROP 기능
- 파티션 모니터링 알림 체계

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
