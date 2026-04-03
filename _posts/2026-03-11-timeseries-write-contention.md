---
title: "시계열 수집의 쓰기 경합 — 5분 주기 시스템에서 동시성을 해결한 방법"
date: 2026-03-11 00:00:00 +0900
last_modified_at: 2026-04-03 00:00:00 +0900
categories: [개발 기록, 미터링 시스템 구축]
tags: [설계, 아키텍처]
description: >-
  5분 수집과 10분 집계가 겹치는 환경에서,
  스키마 분리와 @Transactional(readOnly) 기반 라우팅으로
  쓰기 경합을 제거한 과정을 공유합니다.
---

> **TL;DR** — 5분 수집과 10분 집계가 겹치는 환경에서, 스키마 분리와 `@Transactional(readOnly)` 기반 라우팅으로 쓰기 경합을 제거했습니다.
{: .prompt-tip }

---

## 도입

### 시스템 배경

Prometheus에서 Kubernetes Pod 단위의 리소스 사용량을 수집하고, 단계별로 집계하는 미터링 파이프라인입니다.
하나의 서비스가 여러 Pod(레플리카)로 구성될 수 있으며, 각 Pod의 데이터를 개별 수집합니다.
이 미터링 파이프라인의 설계부터 구현까지 전 과정을 담당했습니다.

```
Prometheus → [5분 수집] → 원천 저장 (Pod 단위)
                                ↓
                      [10분 집계] → Interval 저장 (서비스/Pod)
                                          ↓
                                [일일 집계] → Daily 저장 (서비스/Pod)
                                                    ↓
                                          사용자 조회 API
```

### 기술 스택

| 분류 | 기술 |
|------|------|
| Language / Framework | Java 17, Spring Boot |
| ORM | Spring Data JPA |
| Database | MySQL (마스터/슬레이브 복제, 월별 파티셔닝) |
| Architecture | 헥사고날 아키텍처 (Port and Adapter) |
| Batch | JobRunr (배치 스케줄러) |
| Monitoring | Prometheus (시계열 데이터 소스) |
| Infra | Kubernetes |

---

## 문제

### 예측한 규모

| 항목 | 수치 |
|------|------|
| 원천 수집 주기 | 5분 (하루 288회/서비스) |
| Interval 집계 주기 | 10분 (하루 144개/서비스) |
| Daily 집계 | 일일 1건/서비스 |
| 저장 구조 | 서비스 1 : N Pod (레플리카) |
| 데이터 보관 | 월별 파티셔닝, 일정 기간 이후 아카이빙 |
| 자동 복구 기간 | 설정 가능 (기본 수일) |

서비스 수가 늘어날수록 수집/집계 데이터가 선형으로 증가합니다.
Pod 수(레플리카)에 비례해서 원천 데이터가 추가로 늘어납니다.

### 데이터 증가 예측

서비스당 평균 2개 Pod를 가정하고, 서비스 수 증가에 따른 데이터 축적량을 예측했습니다.

**서비스당 일일 생성 건수**

| 테이블 | 단위 | 일일 건수 (Pod 2개 기준) |
|--------|------|------------------------|
| 원천 (Source) | Pod 단위 | 576건 (288 x 2 Pod) |
| Interval 서비스 | 서비스 단위 | 144건 |
| Interval Pod | Pod 단위 | 288건 (144 x 2 Pod) |
| Daily 서비스 | 서비스 단위 | 1건 |
| Daily Pod | Pod 단위 | 2건 (1 x 2 Pod) |
| **합계** | | **1,011건/서비스/일** |

**분기별 누적 예측 (2년)**

서비스가 분기마다 50개씩 증가한다고 가정했습니다.

| 시점 | 서비스 수 | 분기 신규 건수 | 누적 건수 |
|------|-----------|--------------|----------|
| Q1 | 100 | 약 909만 건 | 약 909만 건 |
| Q2 | 150 | 약 1,364만 건 | 약 2,273만 건 |
| Q3 | 200 | 약 1,818만 건 | 약 4,091만 건 |
| Q4 | 250 | 약 2,273만 건 | 약 6,364만 건 |
| **1년차** | **250** | | **약 6,364만 건** |
| Q5 | 300 | 약 2,727만 건 | 약 9,091만 건 |
| Q6 | 350 | 약 3,182만 건 | 약 1억 2,273만 건 |
| Q7 | 400 | 약 3,636만 건 | 약 1억 5,909만 건 |
| Q8 | 450 | 약 4,091만 건 | 약 2억 건 |
| **2년차** | **450** | | **약 2억 건** |

이 예측이 단일 데이터소스에서의 쓰기 경합과 데이터 관리 문제를 사전에 대비해야 한다고 판단한 근거였습니다.

### 예상된 문제 세 가지

이 파이프라인을 하나의 데이터소스로 운영한다고 가정하면, 세 가지 문제가 보였습니다.

**1. 쓰기 경합**

5분 주기 수집과 10분 주기 집계가 같은 DB에서 동시에 실행됩니다.
수집이 진행 중일 때 집계가 시작되면 락 경합이 발생합니다.
서비스가 많아질수록 배치 실행 시간이 길어지면서 겹침 확률이 높아집니다.

**2. 조회 성능 불안정**

배치가 대량의 INSERT/UPDATE를 수행하는 동안, 사용자 조회 API의 응답 시간이 불안정해집니다.
사용자 입장에서는 갑자기 느려지는 현상으로 체감됩니다.

**3. 장애 전파**

외부 소스 하나가 응답하지 않으면, 수집 실패가 집계와 조회까지 연쇄적으로 영향을 줍니다.
소스 하나의 문제가 시스템 전체에 영향을 줄 수 있는 구조였습니다.

---

## 해결

### 선택지 검토

세 가지 방안을 검토했습니다.

**방안 1: 단일 DataSource + 시간대 분리**

수집과 집계가 겹치지 않도록 스케줄링하는 방법입니다.
구현은 단순하지만, 주기가 5분/10분으로 촘촘해서 시간대 확보가 어려웠습니다.
배치 하나가 지연되면 뒤따르는 배치까지 연쇄 지연이 발생하는 점도 부담이었습니다.

**방안 2: 스키마 분리 + 트랜잭션 라우팅**

원천(수집)과 가공(집계/조회)의 스키마를 물리적으로 나누고, 트랜잭션 속성으로 마스터/슬레이브를 라우팅하는 방법입니다.
영역별 장애 격리가 가능하고, 읽기 부하도 분산됩니다.
다만 DataSource를 여러 개 관리해야 하는 복잡도가 추가됩니다.

**방안 3: 메시지 큐 기반 비동기 처리**

수집 완료 이벤트를 큐에 발행하고, 집계 워커가 소비하는 구조입니다.
완전한 디커플링이 가능하지만, 현재 규모 대비 인프라가 과하다고 판단했습니다.
순서 보장 등 고려할 부분도 많아집니다.

**결정: 방안 2**

메시지 큐는 현재 규모에 비해 과했고, 시간대 분리는 주기가 짧아 현실적이지 않았습니다.
Spring Boot의 AbstractRoutingDataSource만으로 핵심 문제를 해결할 수 있어 방안 2를 선택했습니다.
시스템 규모가 더 커지면 방안 3으로 전환할 수 있도록 여지는 남겨두었습니다.

### 영역 분리 설계

데이터의 성격에 따라 두 영역으로 나누었습니다.

| 영역 | 역할 | 스키마 | 특성 |
|------|------|--------|------|
| 원천 (Source) | Pod 데이터 수집 | 별도 스키마 | 비즈니스 로직 없음 |
| 가공 (Processing) | 집계 + 조회 | 기본 스키마 | 비즈니스 로직 포함 |

원천은 Prometheus에서 받은 Pod 데이터를 저장만 합니다.
가공은 원천 데이터를 읽어서 서비스/Pod 단위로 집계하고, 그 결과를 사용자에게 제공합니다.
두 영역의 관심사가 다르기 때문에 스키마를 나누는 것이 자연스러웠습니다.

**읽기/쓰기 라우팅**

| 작업 | 대상 | DB 노드 |
|------|------|--------|
| 원천 수집 (5분) | Source 스키마 | 마스터 |
| 집계 시 원천 조회 (10분) | Source 스키마 | 슬레이브 |
| 집계 결과 저장 | 기본 스키마 | 마스터 |
| 사용자 조회 | 기본 스키마 | 마스터 |

원천 스키마에만 마스터/슬레이브 라우팅을 적용했습니다.
가공 스키마는 집계 주기(10분)와 조회 패턴이 겹칠 가능성이 낮아서, 마스터 하나로 충분하다고 판단했습니다.

### 구현

**패키지 구조**

```
adapter/
├── jpa/                    # 가공: 기본 DataSource
│   ├── configs/
│   ├── entities/           # Interval, Daily 엔티티
│   └── repositories/
│
└── source/jpa/             # 원천: 별도 DataSource
    ├── configs/
    │   ├── SourceDataSourceConfig.java   # 마스터/슬레이브 라우팅
    │   └── SourceJpaConfig.java          # 별도 EntityManager
    ├── entities/           # SourceInstance 엔티티
    └── repositories/
```

헥사고날 아키텍처의 Adapter 레이어 안에서, 가공과 원천을 패키지 수준으로 분리했습니다.
같은 모듈 안에 있지만 서로 다른 DataSource를 바라봅니다.

**트랜잭션 기반 라우팅**

Spring의 AbstractRoutingDataSource를 확장해서, `@Transactional`의 readOnly 속성으로 마스터/슬레이브를 결정하도록 구현했습니다.

```java
public class ReadWriteRoutingDataSource extends AbstractRoutingDataSource {

  @Override
  protected Object determineCurrentLookupKey() {
    return TransactionSynchronizationManager
        .isCurrentTransactionReadOnly() ? "slave" : "master";
  }
}
```

서비스 레이어에서는 어노테이션 하나로 라우팅이 결정됩니다.

```java
// 집계 시 원천 조회 → 슬레이브로 라우팅
@Transactional(value = "sourceTransactionManager", readOnly = true)
public List<SourceInstance> findByRange(Instant from, Instant to) { ... }

// 원천 수집 → 마스터로 라우팅
@Transactional(value = "sourceTransactionManager")
public void saveAll(List<SourceInstance> instances) { ... }
```

**별도 JPA 영역**

원천 영역은 독립된 EntityManagerFactory와 TransactionManager를 갖습니다.

```java
@Configuration
@EnableJpaRepositories(
    basePackages = "...source.jpa.repositories",
    entityManagerFactoryRef = "sourceEntityManagerFactory",
    transactionManagerRef = "sourceTransactionManager")
public class SourceJpaConfig {
  // 별도 EntityManagerFactory, TransactionManager 빈 등록
}
```

가공 영역은 Spring Boot 기본 설정을 그대로 사용합니다.

```java
@Configuration
@EntityScan(basePackages = "...jpa.entities")
@EnableJpaRepositories(basePackages = "...jpa.repositories")
public class ProcessingJpaConfig {}
```

### 미리 대응한 엣지 케이스

설계 단계에서 예측하고 대비한 부분들입니다.

**슬레이브 복제 지연**

마스터에 수집이 완료된 직후 슬레이브에서 조회하면, 복제가 아직 반영되지 않았을 수 있습니다.
집계 배치 주기(10분)가 수집 주기(5분)보다 길어서, 자연스럽게 지연 버퍼가 확보됩니다.
주기가 더 촘촘해진다면 이 부분은 별도 대응이 필요할 것 같습니다.

**배치 실패 시 빈 구간**

수집 배치가 실패하면 해당 구간의 Interval 집계가 비게 됩니다.
마지막 성공 시점을 추적해서 실패 구간을 자동 재처리하는 복구 로직을 설계했습니다.

**멀티 소스 장애 격리**

외부 소스가 여러 개일 때, 소스별로 개별 Job을 분리해서 실행합니다.
특정 소스의 장애가 다른 소스의 수집에 영향을 주지 않도록 하기 위해서입니다.

**데이터 증가 대응**

Daily 테이블은 월별 파티셔닝을 적용하고, 일정 기간 이후 아카이빙하도록 설계했습니다.
서비스 수 증가에 따른 선형 데이터 증가에 대비한 구조입니다.

---

## 회고

### 설계 시점의 기대 효과

| 항목 | Before (단일 DataSource) | After (스키마 분리) |
|------|------------------------|-------------------|
| 쓰기 경합 | 5분 수집 + 10분 집계 동시 실행 | 스키마 분리로 경합 제거 |
| 조회 안정성 | 배치 중 응답 시간 불안정 | 원천 조회는 슬레이브 분산 |
| 장애 범위 | 전체 소스 영향 | 소스별 격리 (1/N) |
| DataSource | 1개 | 3개 (원천 M/S + 가공 M) |
| 복구 | 수동 | 자동 재처리 |
| 데이터 관리 | 단일 스키마 | 월별 파티셔닝 + 아카이빙 |

운영 복잡도가 올라간 것은 사실입니다.
DataSource가 늘어난 만큼 모니터링 포인트도 함께 늘었습니다.
하지만 쓰기 경합과 장애 전파를 설계 단계에서 예방할 수 있다는 점에서, 충분히 감수할 만한 트레이드오프라고 판단했습니다.

### 배운 것

**분리에는 근거가 필요합니다**

모든 배치 시스템에 데이터소스 분리가 필요한 것은 아닙니다.
이 시스템에서는 짧은 수집 주기(5분), 레플리카 수에 비례하는 데이터 증가, 그리고 사용자 조회 API의 안정성 요구라는 구체적인 이유가 있었습니다.
근거 없이 분리하면 운영 복잡도만 올라가게 됩니다.

**CQRS는 스펙트럼입니다**

CQRS라고 하면 이벤트 소싱이나 별도 읽기 저장소를 떠올리기 쉽습니다.
하지만 반드시 그 수준까지 갈 필요는 없다고 느꼈습니다.
스키마 분리 + 트랜잭션 라우팅만으로도 쓰기/읽기 독립이라는 핵심 이점을 얻을 수 있었습니다.
시스템 규모에 맞는 수준을 선택하는 것이 더 중요하다고 생각합니다.

**결정 근거는 남겨야 합니다**

"왜 분리했는가"를 기록해두지 않으면, 나중에 코드를 보는 사람은 불필요한 복잡도로 오해할 수 있습니다.
데이터 볼륨, 경합 시나리오, 장애 격리 요구사항 등 결정 근거를 설계 문서에 남겨두는 것이 미래의 동료를 위한 일이었습니다.

### 남은 과제

이 글은 설계 단계의 의사결정을 기록한 것입니다.
실제 운영 이후 다음 항목을 측정하여 보완할 예정입니다.

- 원천 수집 배치 평균 소요 시간
- Interval 집계 배치 평균 소요 시간
- 슬레이브 복제 지연 실측치
- 사용자 조회 API P95 응답 시간
- 서비스 N개 기준 일일 데이터 증가량
- 장애 격리 실제 사례 (소스별 독립 동작 여부)
- 월별 파티셔닝 + 아카이빙 운영 결과

설계 단계에서 내린 결정이 실제 운영에서 어떤 결과를 만드는지, 운영 데이터가 쌓이면 후속 글로 공유하겠습니다.

---

## 참고

- [AbstractRoutingDataSource - Spring Framework](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/jdbc/datasource/lookup/AbstractRoutingDataSource.html) — 트랜잭션 기반 DataSource 라우팅의 기반 클래스
- [CQRS - Martin Fowler](https://martinfowler.com/bliki/CQRS.html) — Command Query Responsibility Segregation 패턴 개요
- [Configuring Multiple Data Sources - Baeldung](https://www.baeldung.com/spring-boot-configure-multiple-datasources) — Spring Boot 멀티 DataSource 설정 가이드
- [MySQL Replication](https://dev.mysql.com/doc/refman/8.0/en/replication.html) — 마스터/슬레이브 복제 공식 문서

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
