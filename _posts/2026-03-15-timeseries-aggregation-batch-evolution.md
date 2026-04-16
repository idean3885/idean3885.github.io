---
title: "시계열 집계 배치의 점진적 진화 - 내장 스케줄러에서 서버리스 배치까지"
date: 2026-03-15 00:00:00 +0900
last_modified_at: 2026-04-09 00:00:00 +0900
categories: [개발 기록, 미터링 시스템 구축]
tags: [설계, 아키텍처]
description: >-
  미터링 배치를 내장 스케줄러(JobRunr) + 상시 서버로 시작하고,
  규모에 따라 CronJob 분리 → 이벤트 기반 → 분산 처리로
  점진 확장하는 청사진을 설계했습니다.
---

> **TL;DR**<br>
> 미터링 배치를 내장 스케줄러(JobRunr) + 상시 서버로 시작하고, 규모에 따라 CronJob 분리 → 이벤트 기반 → 분산 처리로 점진 확장하는 청사진을 설계했습니다.<br>
> 각 단계의 전환 시그널을 정의하고, 단계를 관통하는 원칙(멱등성, 마지막 성공 시점 기반 복구, 데이터 완전성 우선)을 유지하는 것이 핵심입니다.
{: .prompt-tip }

---

<br>

## 도입 - 미터링 배치가 필요한 순간

클라우드 GPU 서비스를 운영하면 과금의 근거가 되는 사용량 데이터를 빠짐없이 수집해야 합니다.

GPU, CPU, 메모리 사용량은 Prometheus에 시계열로 쌓이지만, 이 원시 데이터를 그대로 과금에 쓸 수는 없습니다.
일정 주기로 수집하고, 구간별로 집계하고, 일간 단위로 누적하는 **파이프라인**이 필요합니다.

```
Prometheus (GPU/CPU/Memory 메트릭)
    ↓ (5분 주기 수집)
[원천 데이터] Pod 단위 저장
    ↓ (10분 주기 집계)
[구간 데이터] 서비스 단위 집계
    ↓ (일일 누적)
[일간 데이터] 일간 집계
```

"주기적으로 돌리면 되니까 배치지", 처음에는 이렇게 단순하게 시작했습니다.

<br>

---

<br>

## 문제 - 왜 내장 스케줄러 + 상시 서버인가

### 선택의 맥락

배치 시스템을 설계할 때 크게 두 가지를 결정해야 했습니다.

<br>

**1) 어떤 스케줄러를 쓸 것인가?**

Spring Batch는 강력하지만, 이 시스템에는 과했습니다.
집계 대상이 수천 건 수준이고, Reader → Processor → Writer의 정형화된 흐름보다는 Prometheus 쿼리 → 변환 → 저장의 단순한 흐름이 필요했습니다.

JobRunr를 선택한 이유는 명확했습니다.

| 요구사항 | JobRunr | Spring Batch |
|----------|---------|--------------|
| Job 이력 기반 실패 복구 | 내장 (`jobrunr_jobs` 테이블) | 별도 `JobRepository` 설정 |
| 메서드 단위 Job 등록 | `@Job` 어노테이션 하나 | Job, Step, Tasklet 정의 필요 |
| 마지막 성공 시점 조회 | Job 이력에서 바로 조회 | 별도 상태 테이블 필요 |
| 대시보드 | 내장 웹 UI | Spring Batch Admin 별도 |

특히 **별도 상태 테이블 없이** 마지막 성공 시점을 추적할 수 있다는 점이 결정적이었습니다.

```java
// 수집 범위 = (마지막 성공 시점, 현재]
var from = helper.getLastSuccessAt("collectSource");
var data = prometheus.queryRange(query, from, now, "1m");
```

배치가 실패하더라도, 다음 실행에서 마지막 성공 시점부터 다시 수집하면 누락 없이 복구됩니다.

<br>

**2) 어떻게 실행할 것인가?**

Kubernetes CronJob이 자연스러운 선택처럼 보이지만, 5분 주기 배치에서는 문제가 있습니다.

```
CronJob 실행 흐름:
  컨테이너 생성 → JVM 기동 → Spring Context 초기화 → Job 실행 → 종료
  [-------- ~30초 --------]   [--- 실제 작업 ~10초 ---]
```

기동 오버헤드가 실제 작업 시간의 3배입니다.
5분마다 이 비용을 지불하는 것보다 서버를 상시 띄워놓는 편이 합리적입니다.
JobRunr의 BackgroundJobServer가 주기적으로 Job을 폴링합니다.

<br>

### 그러나 대가가 있었습니다

```
리소스 사용 패턴:

[상시 점유] ████████████████████████████████████████  JVM 힙 512MB
[Job 실행]  ▌  ▌  ▌  ▌  ▌  ▌  ▌  ▌  ▌  ▌  ▌  ▌   5분마다 ~10초
            ↑                                        실제 작업
```

24시간 중 실제로 Job이 실행되는 시간은 **하루 약 48분** (5분 주기 × 10초 × 288회)입니다.
나머지 23시간 12분 동안 서버는 JobRunr 폴링과 Health Check만 수행하면서 리소스를 점유합니다.

소규모에서는 서버 1대의 비용이 크지 않습니다. 하지만 규모가 커지면 이야기가 달라집니다.

- 소스 종류가 늘어나면 Job이 많아지고 실행 시간이 길어집니다
- Pod 수가 늘어나면 Prometheus 쿼리가 무거워집니다
- 고가용성을 위해 2대 이상 운영하면 비용이 배가됩니다

이 시점에서 "계속 이 구조로 갈 것인가?"라는 질문이 생겼습니다.

<br>

---

<br>

## 해결 - 점진적 확장 청사진

핵심 원칙은 **전환 시그널이 나타날 때까지 현재 단계를 유지**하는 것입니다. 미리 과도하게 설계하면 복잡성만 늘어납니다.

<br>

### Stage 0: 내장 스케줄러 (현재)

```
[Spring Boot App (상시 가동)]
  └── JobRunr BackgroundJobServer
       ├── collectSource()        5분 주기
       ├── aggregateInterval()    10분 주기
       └── aggregateDaily()       일일
```

**작동 방식**

각 Job은 메서드 단위로 등록됩니다.
메서드명이 곧 Job 이름이며, 이름을 변경하면 새로운 Job으로 인식되어 이력이 단절됩니다.

이 제약은 의도적입니다. Job 이력의 일관성이 실패 복구의 기반이기 때문입니다.

```java
@Service
public class MeteringJobService {

    @Job  // name 생략 → 메서드명이 Job 이름
    public void collectSource() {
        var from = helper.getLastSuccessAt("collectSource");
        var rawData = prometheus.queryRange(query, from, now, "1m");
        sourceRepository.upsertAll(rawData);  // 멱등성 보장
    }

    @Job
    public void aggregateInterval() {
        // 완전한 10분 구간만 처리 (09:50~09:59)
        var interval = calculateCompleteInterval(now);
        var aggregated = aggregate(interval);
        intervalRepository.upsert(aggregated);
    }
}
```

멱등성은 UNIQUE 제약 + UPSERT 패턴으로 보장합니다. 같은 구간을 두 번 집계해도 결과가 동일합니다.

> **적합 규모**: 소스 1~2종, 인스턴스 수천 건, 단일 DB
>
> **한계 시그널**: 리소스 유휴율 80% 이상, Job 미실행 시간이 대부분

<br>

---

<br>

### Stage 1: 스케줄러 분리 (필요할 때만 실행)

```
[Kubernetes CronJob]
    ↓ (5분 주기 트리거)
[경량 컨테이너]
    ├── collectSource()
    └── (완료 후 즉시 종료)
```

**핵심 변화**: 상시 점유 → 실행 시에만 리소스 사용

Stage 0의 가장 큰 낭비는 "놀고 있는 서버"입니다.
CronJob으로 전환하면 실행 시에만 컨테이너가 생성되고, 완료 후 즉시 반환됩니다.

```
Before (상시 서버):  ████████████████████████  24시간 점유
After  (CronJob):    ▌  ▌  ▌  ▌  ▌  ▌  ▌  ▌   실행 시에만 점유
```

<br>

**기동 오버헤드 해결: GraalVM Native Image**

앞서 CronJob의 기동 오버헤드를 문제로 지적했습니다. Native Image로 컴파일하면 이 문제가 크게 완화됩니다.

| 방식 | 기동 시간 | 메모리 |
|------|----------|--------|
| JVM (기존) | ~30초 | 512MB |
| Native Image | ~0.5초 | 128MB |

> 다만 Spring Data JPA + Native Image 조합은 리플렉션 설정 등 호환성 작업이 필요하므로 전환 비용을 고려해야 합니다.

기동 시간이 0.5초로 줄어들면, 5분 주기 CronJob도 충분히 실용적입니다.

<br>

**과제: Job 이력 관리의 이전**

JobRunr의 BackgroundJobServer 없이 실행하므로, 마지막 성공 시점 관리를 직접 구현해야 합니다.

```java
// Stage 0: JobRunr가 알아서 관리
var from = helper.getLastSuccessAt("collectSource"); // JobRunr 테이블 조회

// Stage 1: 별도 테이블로 이전
var from = batchStatusRepository.getLastSuccessAt("collectSource");
// ... 작업 수행 ...
batchStatusRepository.updateLastSuccessAt("collectSource", now);
```

Stage 0에서 "별도 테이블 불필요"라는 장점이 사라지는 트레이드오프입니다.
하지만 테이블 하나 추가하는 비용보다 상시 서버 제거의 이점이 클 때 전환합니다.

> **전환 시그널**: 유휴 리소스 비용 > 구현 복잡성 비용

<br>

---

<br>

### Stage 2: 이벤트 기반 (수집과 집계의 디커플링)

```
[CronJob: 수집]
    ↓ (수집 완료 이벤트)
[Message Queue]
    ↓ (이벤트 수신)
[집계 Worker]
    ├── aggregateInterval()
    └── aggregateDaily()
```

**핵심 변화**: 시간 기반 스케줄링 → 이벤트 기반 트리거

Stage 1까지는 수집과 집계가 모두 시간 기반입니다.
"5분마다 수집, 10분마다 집계"라는 규칙은 단순하지만, 소스 종류가 늘어나면 문제가 생깁니다.

```
소스 A 수집 완료: 10:04
소스 B 수집 완료: 10:06
소스 C 수집 완료: 10:08
Interval 집계:    10:10  ← 소스 C의 데이터가 아직 없을 수 있음
```

이벤트 기반으로 전환하면, **모든 소스의 수집이 완료된 후에** 집계를 시작할 수 있습니다.

```java
// 수집 완료 이벤트 발행
eventPublisher.publish(new SourceCollected("sourceA", interval));

// 집계 트리거: 모든 소스 수집 완료 시
@EventListener
public void onAllSourcesCollected(AllSourcesCollectedEvent event) {
    aggregateInterval(event.getInterval());
}
```

<br>

**과제: Exactly-once 처리**

메시지 큐를 도입하면 "메시지가 두 번 전달되면?"이라는 문제가 생깁니다.

여기서 Stage 0부터 유지해온 **멱등성**이 빛을 발합니다.
UPSERT 패턴 덕분에 같은 이벤트를 두 번 처리해도 결과가 동일합니다.

> **전환 시그널**: 소스 종류 3개 이상, 수집-집계 간 타이밍 이슈 발생

<br>

---

<br>

### Stage 3: 분산 처리 (파티셔닝)

```
[Orchestrator]
  ├── Worker-1: 네임스페이스 A~M
  ├── Worker-2: 네임스페이스 N~Z
  └── Worker-N: (동적 확장)
```

**핵심 변화**: 단일 처리 → 데이터 분할 병렬 처리

Prometheus에는 쿼리당 총 샘플 수 제한(기본 5천만)이 있습니다.
인스턴스가 5,000개를 넘고 7일 복구가 필요하면, 단일 쿼리로는 한계에 도달합니다.

```
총 샘플 수 = 인스턴스 수 × (시간 범위(분) / step(분))

5,000 × (7일 × 1,440분 / 1분) = 50,400,000  ← 5천만 초과!
```

파티셔닝 전략은 데이터의 특성에 따라 선택합니다.

| 전략 | 방식 | 장점 | 단점 |
|------|------|------|------|
| **범위 분할** | 네임스페이스 A~M / N~Z | 구현 단순 | 데이터 편중 가능 |
| **해시 분할** | hash(groupId) % N | 균등 분배 | 리밸런싱 복잡 |
| **논리 분할** | 프로젝트/테넌트 단위 | 비즈니스 의미 있음 | 프로젝트 크기 불균등 |

미터링에서는 **논리 분할(프로젝트 단위)**이 적합합니다.
프로젝트가 과금의 기본 단위이므로, 분할 경계가 비즈니스 의미와 일치합니다.

```java
// Orchestrator: 프로젝트별 워커 할당
var projects = projectRepository.findAll();
var partitions = partitioner.partition(projects, workerCount);

for (var partition : partitions) {
    workerQueue.send(new CollectCommand(partition));
}
```

<br>

**과제: 파티션 리밸런싱**

워커가 실패하면 해당 파티션을 다른 워커에 재할당해야 합니다. 여기서도 멱등성이 핵심입니다. 다른 워커가 동일 파티션을 처리해도 UPSERT 덕분에 안전합니다.

> **전환 시그널**: 단일 Prometheus 쿼리 한계 도달, 처리 시간이 배치 주기 초과

<br>

---

<br>

## 회고 - 확장 의사결정 프레임워크

### 단계별 전환 매트릭스

| 현재 단계 | 전환 시그널 | 다음 단계 | 핵심 질문 |
|----------|------------|----------|----------|
| Stage 0 (내장) | 유휴 리소스 80%+ | Stage 1 (CronJob) | "서버가 대부분 놀고 있는가?" |
| Stage 1 (CronJob) | 소스 3종+, 타이밍 이슈 | Stage 2 (이벤트) | "수집과 집계의 실행 순서가 중요한가?" |
| Stage 2 (이벤트) | 단일 쿼리 한계 도달 | Stage 3 (분산) | "한 번에 못 가져오는 규모인가?" |

<br>

### 단계를 관통하는 원칙

네 단계를 거치면서도 변하지 않는 원칙이 있습니다.

1. **멱등성**: 모든 단계에서 UPSERT 패턴을 유지합니다. 이것이 실패 복구, 재처리, 분산 환경에서의 안전성을 보장하는 기반입니다.

2. **마지막 성공 시점 기반 복구**: 구현 방식은 달라져도(JobRunr 이력 → 별도 테이블 → 이벤트 오프셋), "어디까지 처리했는가"를 추적하는 원칙은 동일합니다.

3. **데이터 완전성 우선**: 성능보다 데이터 누락 방지가 우선입니다. 구간이 완전히 끝난 후에만 집계하고, 실패 시 해당 구간을 다시 처리합니다.

<br>

### 오버엔지니어링 경고 신호

- "나중에 필요할 것 같아서" 분산 처리를 먼저 구현 → 운영 복잡성만 증가
- 인스턴스 500개인데 파티셔닝 고민 → 단일 쿼리로 7일 복구도 충분
- 소스 1종인데 이벤트 기반 설계 → 시간 기반 스케줄링으로 충분

<br>

### 면접에서 이 질문이 나온다면

> "배치 시스템을 설계한다면 어떻게 하시겠습니까?"

이 질문에 대한 답은 "규모에 따라 다릅니다"로 시작해야 합니다.

| 규모 | 권장 접근 | 핵심 근거 |
|------|----------|----------|
| 소규모 (수천 건) | 내장 스케줄러 + 상시 서버 | 구현 단순성, 운영 편의 |
| 중규모 (수만 건) | CronJob + Native Image | 리소스 효율, 기동 속도 |
| 대규모 (수십만 건) | 이벤트 기반 + 워커 | 처리 순서 보장, 확장성 |
| 초대규모 (수백만 건+) | 파티셔닝 + 분산 워커 | 쿼리 한계 극복, 병렬성 |

그리고 "현재 우리 시스템은 Stage 0이고, 이러한 시그널이 나타나면 Stage 1로 전환할 것입니다"라고 구체적으로 설명할 수 있어야 합니다.

배치 설계에서 가장 중요한 역량은 **적정 설계를 선택하는 것**입니다.
다음 단계로의 전환 시점을 판단하는 능력이 핵심입니다.

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
