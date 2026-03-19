---
title: "사용자 도메인 인증서 자동 발급 — certbot 학습에서 ACME4j 구현까지"
date: 2026-03-18 23:45:00 +0900
last_modified_at: 2026-03-19 23:07:00 +0900
categories: [개발 기록, 시스템 구축기]
tags: [Let's Encrypt, ACME, 인증서, 자동화, 헥사고날 아키텍처, Java, Spring Boot]
description: >-
  사용자가 커스텀 도메인을 연결하면 SSL 인증서가 자동으로 발급되는 BE 시스템을 구현했습니다.
  certbot으로 ACME 프로토콜을 학습하고, ACME4j로 Java BE에 통합한 과정을 정리합니다.
---

> **TL;DR**
> - 사용자가 커스텀 도메인을 연결하면 **SSL 인증서가 자동으로 발급**되는 BE 시스템을 구현했습니다.
> - certbot으로 Let's Encrypt의 ACME 프로토콜(DNS-01, HTTP-01 Challenge)을 학습하고,
> **ACME4j 라이브러리로 Java BE에 통합**했습니다.
> - **헥사고날 아키텍처 + 상태 머신**으로 인증서 생명주기(신청→발급→갱신→실패 복구)를 관리합니다.
> - **4개 배치 Job**으로 발급/갱신/재시도/타임아웃을 처리하며,
> 비동기 + 이벤트 기반 아키텍처를 적용했습니다.
> - 약 8주, 14개 태스크로 진행했습니다. (2024.11 ~ 2025.01)
{: .prompt-tip }

## 1. 배경 — 왜 인증서 자동화가 필요했는가

앱 배포 플랫폼을 운영하고 있습니다.
사용자가 서비스를 배포하면 `{서비스명}.platform.app` 도메인이 자동으로 할당되며,
플랫폼이 관리하는 와일드카드 인증서(`*.platform.app`, `*.platform.net`)로 HTTPS가 제공됩니다.

여기까지는 문제가 없었습니다.
그런데 사용자가 **자신의 도메인**을 연결하는 기능이 추가되면서 상황이 달라졌습니다.

```
사용자 도메인: my-service.example.com
  → *.platform.app 와일드카드 인증서로는 커버 불가
  → 개별 도메인에 대한 SSL 인증서가 필요
```

수동 발급은 선택지가 아니었습니다.
사용자가 도메인을 연결할 때마다 관리자가 인증서를 발급하는 것은
운영 비용을 감당할 수 없기 때문입니다.
**사용자가 도메인을 연결하면 인증서가 자동으로 발급되는 시스템**이 필요했습니다.

### 일정 산정

상위 태스크에서 1차 일정 산정 결과,
cert 모듈은 **18.5MD**(약 3.7주)로 산정되었습니다.
실제로는 설계부터 QA까지 약 8주가 소요되었습니다.
설계 기간과 QA 과정에서 발견된 엣지 케이스 대응이 주된 차이였습니다.

## 2. Let's Encrypt와 ACME 프로토콜 이해

인증서 자동화의 핵심은 [Let's Encrypt](https://letsencrypt.org/)와
ACME(Automated Certificate Management Environment) 프로토콜입니다.

### Let's Encrypt의 동작 원리

Let's Encrypt는 무료 SSL 인증서를 자동으로 발급하는 CA(Certificate Authority)입니다.
핵심 개념은 **도메인 소유권 검증(Domain Validation)**입니다.
인증서를 발급받으려면, 해당 도메인을 실제로 제어하고 있음을 증명해야 합니다.

이 검증을 위해 ACME 프로토콜은 **Challenge**라는 메커니즘을 제공합니다.

### Challenge 유형

| Challenge | 검증 방식 | 용도 |
|-----------|----------|------|
| **HTTP-01** | `http://{도메인}/.well-known/acme-challenge/{token}`에 응답 | 단일 도메인 |
| **DNS-01** | `_acme-challenge.{도메인}` TXT 레코드에 값 설정 | 와일드카드 도메인 |

**HTTP-01**은 해당 도메인으로 HTTP 요청을 보내 토큰 값을 검증합니다.
단일 도메인 인증서에 적합합니다.

**DNS-01**은 DNS TXT 레코드로 검증합니다.
와일드카드 인증서(`*.example.com`)는 DNS-01만 사용할 수 있습니다.

### 발급 제한 (Rate Limits)

Let's Encrypt는 남용 방지를 위해 엄격한 발급 제한을 두고 있습니다.

| 제한 | 값 | 비고 |
|------|-----|------|
| 동일 도메인 세트 인증서 | 주당 5회 | 초과 시 최대 7일 대기 |
| 계정당 인증서 | 시간당 10개 | 갱신은 10배 허용 |
| 계정당 신규 주문 | 3시간당 300개 | 주문 생성 제한 |

이 제한은 이후 구현에서 배치 스케줄과 재시도 전략에 직접적인 영향을 미쳤습니다.

## 3. certbot으로 DNS-01 Challenge 학습

본격적인 BE 구현에 앞서, certbot CLI로 인증서 발급 과정을 직접 경험했습니다.

### certbot 수동 발급 과정

```bash
# certbot으로 인증서 발급 (DNS-01 수동 모드)
certbot certonly \
  --manual \
  --preferred-challenges dns \
  -d "*.platform.app" \
  -d "*.platform.net"
```

이 명령을 실행하면 certbot이 DNS TXT 레코드 값을 알려줍니다.

```
Please deploy a DNS TXT record under the name:
_acme-challenge.platform.app
with the following value:
AbCdEf123456...
```

관리자가 DNS에 TXT 레코드를 수동으로 추가하고,
certbot에서 확인을 누르면 인증서가 발급됩니다.

### 수동 발급의 한계

이 경험에서 두 가지를 확인했습니다.

1. **와일드카드 인증서는 DNS-01이 필수**이지만,
   사용 중인 클라우드 DNS 서비스에는 certbot 공식 플러그인이 없어
   수동 발급이 유일한 방법이었습니다.
   (이 문제는 2편에서 해결합니다.)

2. **사용자 도메인 인증서는 HTTP-01이 적합하다고 판단했습니다**.
   사용자의 DNS를 플랫폼이 직접 제어할 수 없기 때문에,
   HTTP 응답 기반의 HTTP-01 Challenge가 자동화에 유리합니다.

이 학습을 바탕으로, 사용자 도메인 인증서 발급 시스템을
**HTTP-01 Challenge 기반의 ACME4j 라이브러리**로 구현하기로 결정했습니다.

## 4. 시스템 설계 — 헥사고날 아키텍처

cert 모듈은 기존 아키텍처 컨벤션인
**헥사고날 아키텍처(Ports & Adapters)**를 따릅니다.

### 모듈 구조

```
cert/
├── api/        # 공유 인터페이스 (UseCase, Command, Event)
├── core/       # 비즈니스 로직 (도메인, 서비스, 포트, 어댑터)
├── server/     # REST API 서버 (이벤트 구독, HTTP 엔드포인트)
├── verifier/   # 도메인/인증서 검증 서비스 (IDC 배포)
├── job/        # 배치 Job (CronJob으로 실행)
└── client/     # 외부 서비스용 클라이언트 라이브러리
```

6개 모듈로 구성되며, 각 모듈의 역할이 명확히 분리되어 있습니다.

### 핵심 포트 설계

헥사고날 아키텍처에서 도메인 로직은 **포트(인터페이스)**를 통해 외부와 소통합니다.

```
[UseCase (Input Port)]                    [Output Port]
CertificateSystemUseCase ──┐      ┌── CertificateIssuerPort
CertificateJobUseCase ─────┤      ├── DomainVerifyPort
                           ▼      ├── CertificateRepository
                     [Domain]     └── CertificateValidator
                    Certificate
```

| 포트 | 역할 | 어댑터 구현 |
|------|------|-----------|
| `CertificateIssuerPort` | ACME 인증서 발급 | `CertificateIssuerPortImpl` (ACME4j 래핑) |
| `DomainVerifyPort` | 도메인 소유권 검증 | `DomainVerifyPortImpl` (Verifier 모듈 연동) |
| `CertificateRepository` | 인증서 영속화 | `CertificateRepositoryImpl` (JPA) |
| `CertificateValidator` | 상태 전이 검증 | `CertificateValidatorImpl` |

### 서비스 모듈과의 연동

cert 모듈은 독립적으로 동작하지 않습니다.
사용자가 도메인을 설정하면 서비스 모듈에서 이벤트가 발행되고,
cert 모듈이 이를 구독하여 인증서 발급을 시작합니다.

```
[사용자] → [서비스 모듈] → (Kafka 이벤트) → [cert 서버]
                                              │
                                              ▼
                                        인증서 발급 신청
                                        (APPLICATION 상태)
```

인증서 발급이 완료되면 cert 모듈이 성공/실패 이벤트를 발행하고,
서비스 모듈이 이를 수신하여 사용자 도메인에 인증서를 적용합니다.

## 5. 도메인 모델 — 상태 머신 설계

인증서 발급은 즉시 완료되지 않습니다.
도메인 검증, ACME 통신, 인증서 생성까지 여러 단계를 거치며,
각 단계에서 실패할 수 있습니다.
이를 관리하기 위해 **상태 머신**을 설계했습니다.

### 인증서 발급 상태

```
                      ┌──────────────────────────┐
                      │                          │
[서비스 등록] → APPLICATION → PROCESSING → SUCCESS
                  ▲              │            │
                  │              ▼            │
                  │    FAILURE_REAPPLICATION   │
                  │         (재시도)           │
                  └───────────┘               │
                                              ▼
                               PROCESSING → FAILURE_EXIT
                              (최대 시도 초과)
```

| 상태 | 설명 | 다음 상태 |
|------|------|----------|
| `APPLICATION` | 발급 신청 대기 | → `PROCESSING` |
| `PROCESSING` | 발급 진행 중 (ACME 통신) | → `SUCCESS` / `FAILURE_*` |
| `SUCCESS` | 발급 완료 | → `APPLICATION` (갱신 시) |
| `FAILURE_REAPPLICATION` | 실패, 재시도 대기 | → `APPLICATION` |
| `FAILURE_EXIT` | 최종 실패 (재시도 소진) | 종료 |

### 도메인 서비스 연결 상태

인증서 발급 전에 도메인이 실제로 사용자 서비스에 연결되어 있는지 검증합니다.

```
NOT_LINK → LINK_SUCCESS (연결 확인)
         → LINK_FAILURE (연결 실패)
```

이 검증은 인증서 발급 직전에 수행됩니다.
도메인이 다른 서비스를 가리키고 있다면, 인증서를 발급해도 의미가 없기 때문입니다.

### Certificate 도메인 엔티티

`Certificate` 엔티티는 상태 전이 로직을 내부에 캡슐화합니다.

```java
public class Certificate {
    private IssuanceStatus issuanceStatus;          // 발급 상태
    private ServiceRegistrationStatus serviceRegistrationStatus;  // 서비스 등록 상태
    private DomainServiceLinkStatus domainServiceLinkStatus;      // 도메인 연결 상태
    private int issuanceAttemptCount;                    // 시도 횟수
    private ZonedDateTime jobRunExpectAt;                // 다음 Job 실행 예정 시각

    // 발급 시작: APPLICATION → PROCESSING
    public void issueStart(Duration jobExpectDuration) {
        this.issuanceAttemptCount += 1;
        this.issuanceStatus = PROCESSING;
        this.jobRunExpectAt = ZonedDateTime.now().plus(jobExpectDuration);  // 타임아웃 감시용
    }

    // 발급 처리: PROCESSING → SUCCESS / FAILURE
    // 도메인 내부에서 issuerPort를 호출하는 Rich Domain 패턴
    public IssueProcessResponse issueProcess(IssueProcessRequest messageRequest) {
        var issuerPort = messageRequest.issuerPort();
        var renewalExpectDuration = messageRequest.renewalExpectDuration();
        try {
            var issuanceData = issuerPort.issue(this);  // ACME4j 통신
            this.issuanceStatus = SUCCESS;
            this.issuedAt = issuanceData.issuedAt();
            this.expiredAt = issuanceData.expiredAt();
            this.publicKey = issuanceData.publicKey();
            this.privateKey = issuanceData.privateKey();
            this.jobRunExpectAt = this.expiredAt.minus(renewalExpectDuration);  // 갱신 예정
            return new IssueProcessResponse(true);
        } catch (Exception e) {
            // 실패 시 재시도 또는 최종 실패 처리
            // ...
            return new IssueProcessResponse(false);
        }
    }

    // 갱신 신청: SUCCESS → APPLICATION
    public RenewalApplyResponse renewalApply() {
        this.issuanceStatus = APPLICATION;
        this.issuanceAttemptCount = 0;
        this.jobRunExpectAt = ZonedDateTime.now();
        return new RenewalApplyResponse(true);
    }
}
```

주목할 점은 `issueProcess()` 메서드입니다.
단순한 setter가 아니라,
**도메인 엔티티 내부에서 Output Port(`issuerPort`)를 호출**합니다.
발급 성공/실패에 따른 상태 전이, 갱신 예정 시각 계산, 키 저장까지
모두 도메인 엔티티가 책임집니다.

이런 Rich Domain 패턴 덕분에
서비스 레이어는 도메인에 메시지를 전달하고 결과만 확인하면 됩니다.

상태 전이 검증은 별도의 `CertificateValidator`가 담당합니다.
예를 들어, `APPLICATION` 상태가 아닌 인증서에 대해 `issueStart()`를 호출하면
예외가 발생합니다.

## 6. ACME4j를 활용한 HTTP-01 Challenge 구현

실제 Let's Encrypt와의 통신은
[acme4j](https://github.com/shred/acme4j) 라이브러리를 사용합니다.

### 발급 흐름

```
CertificateIssuerPortImpl.issue()
  │
  ├─ 1. Acme4jService.createOrder(도메인)     ─── ACME 주문 생성
  ├─ 2. Acme4jService.createChallenge(주문)    ─── HTTP-01 챌린지 생성
  ├─ 3. VerifierFeign.saveChallengeToken()     ─── 토큰을 Verifier에 저장
  ├─ 4. Acme4jService.triggerChallenge()       ─── Let's Encrypt에 검증 요청
  │      └─ Let's Encrypt → Verifier 서버:
  │         GET /.well-known/acme-challenge/{token}
  ├─ 5. Acme4jService.createCertificate()      ─── 인증서 생성
  └─ 6. VerifierFeign.deleteChallengeToken()   ─── 토큰 정리 (finally)
```

### Verifier 모듈의 역할

HTTP-01 Challenge에서 Let's Encrypt는
`http://{도메인}/.well-known/acme-challenge/{token}` 경로로
HTTP 요청을 보냅니다.
이 요청에 올바른 응답을 반환해야 도메인 소유권이 검증됩니다.

Verifier 모듈은 이 역할을 담당합니다.
쿠버네티스 클러스터에 배포되어 사용자 도메인의 트래픽을 수신합니다.

```java
// CertificateVerifyUserController — 외부(Let's Encrypt)에서 접근하는 엔드포인트
@GetMapping("/.well-known/acme-challenge/{tokenName}")
public String getToken(@PathVariable String tokenName) {
    return certificateVerifyUserUseCase.getValid(tokenName);
}
```

토큰 데이터는 인메모리(HashMap)로 관리합니다.
ACME 챌린지 토큰은 발급 과정에서만 필요한 일회성 데이터이므로,
DB에 저장할 필요가 없습니다.

```java
// CertificateVerifyRepositoryImpl — 인메모리 저장소
public class CertificateVerifyRepositoryImpl
        implements CertificateVerifyRepository {
    private final Map<String, CertificateVerify> store =
        new HashMap<>();
    // ...
}
```

처음에는 운영 환경에 Redis가 없어 임베디드 Redis를 적용했지만,
토큰의 일회성 특성을 고려하여
최종적으로 인메모리 HashMap이 적절하다고 판단하여 변경했습니다.

### 도메인 소유권 사전 검증

인증서 발급 전에 도메인이 실제로 플랫폼 서비스를 가리키고 있는지
먼저 확인합니다.

```java
// DomainVerifyPortImpl
public void verifyServiceLink(CertificateDomain domain) {
    String token = UUID.randomUUID().toString();

    // 1. Verifier에 검증 토큰 저장
    verifierFeign.createDomainVerifyData(token);

    // 2. 사용자 도메인으로 직접 요청하여 토큰 확인
    String response = verifierFeign.getDomainVerifyData(domain);

    // 3. 토큰 불일치 시 예외 발생
    if (!token.equals(response)) {
        throw new DomainVerifyServiceNotLinkedException();
    }
}
```

이 검증이 실패하면 인증서 발급을 시도하지 않습니다.
도메인이 다른 서버를 가리키고 있는 상태에서
인증서를 발급해도 사용할 수 없기 때문입니다.

## 7. 배치 Job 설계 — 4개 스케줄로 생명주기 관리

인증서 발급은 즉시 완료되지 않고,
외부 서비스(Let's Encrypt)와의 통신이 필요합니다.
이를 동기 API로 처리하면 타임아웃 위험이 있다고 판단하여,
**배치 Job + 비동기 처리** 구조를 채택했습니다.

### 4개 CronJob

| Job | 주기 | 역할 |
|-----|------|------|
| `certificateIssueAllJob` | 20분 | APPLICATION 상태 인증서 발급 처리 |
| `certificateRenewalApplyAllJob` | 10분 | 만료 임박 인증서 갱신 신청 |
| `certificateIssueFailureReapplyAllJob` | 30분 | 실패 인증서 재신청 |
| `certificatePendingIssueProcessFailureAllJob` | 10분 | PROCESSING 상태 타임아웃 처리 |

### 발급 Job 상세 흐름

`certificateIssueAllJob`은 가장 핵심적인 Job입니다.

```java
// CertificateJobService.issueAll()
public void issueAll() {
    List<Certificate> targets = repository.findAllIssueTargetLimit(
        ACCOUNT_SPEC.getMaxCharge()  // Let's Encrypt Rate Limit 준수
    );

    for (Certificate cert : targets) {
        cert.issueStart(...);
        // APPLICATION → PROCESSING

        // 1. 도메인 연결 검증
        try {
            domainVerifyPort
                .verifyServiceLink(cert.getDomain());
        } catch (
            DomainVerifyServiceNotLinkedException e) {
            handleDomainLinkFailure(cert);
            continue;
        }

        // 2. 비동기 인증서 발급
        certificateJobAsync
            .issueProcessAsync(cert);
    }
}
```

실제 ACME 통신은 `@Async`로 비동기 처리됩니다.
발급 완료 시 `IssueProcessSuccessEvent`가,
실패 시 `IssueProcessFailedEvent`가 발행됩니다.

### 갱신 전략

Let's Encrypt 인증서는 90일 만료입니다.
만료 전에 갱신해야 하므로,
갱신 Job이 주기적으로 만료 임박 인증서를 찾아 재발급을 신청합니다.

```java
// issueProcess() 내부에서 갱신 시점을 자동 계산
this.jobRunExpectAt = this.expiredAt.minus(renewalExpectDuration);  // 만료일 - N일 전
```

`issueProcess()` 내부에서 발급 성공 시
`expiredAt - renewalExpectDuration`을 다음 Job 실행 예정 시각으로 설정합니다.
갱신 Job은 이 `jobRunExpectAt`이 도래한 SUCCESS 상태 인증서를 찾아
APPLICATION 상태로 전환하고,
이후 발급 Job이 새 인증서를 발급합니다.

## 8. 실전 이슈와 해결

약 8주간의 개발 과정에서 여러 실전 이슈를 만났습니다.

### Let's Encrypt Rate Limit 대응

초기 구현에서 배치 Job이 한 번에 너무 많은 인증서를 발급하려 하여
Rate Limit에 걸리는 문제가 발생했습니다.

```java
// LetsEncryptSpec.java
ACCOUNT_SPEC(10, Duration.ofHours(1)),
    // 시간당 10개 제한
ACCOUNT_ORDER_SPEC(300, Duration.ofHours(3));
    // 3시간당 300개 주문 제한
```

배치 조회 시 `ACCOUNT_SPEC.maxCharge`(10개)로 제한하여
Rate Limit을 준수하도록 수정했습니다.

### ACME Account 생성 오류

ACME 계정이 매 발급마다 새로 생성되는 오류가 있었습니다.
Let's Encrypt는 계정 등록에도 제한이 있어,
계정을 **Lazy 초기화**하여 한 번만 생성하고 재사용하도록 수정했습니다.

### PROCESSING 상태 교착

비동기 발급 중 서버가 재시작되면,
인증서가 PROCESSING 상태에서 멈추는 문제가 있었습니다.

```
APPLICATION → PROCESSING → (서버 재시작) → ??? 영원히 PROCESSING
```

이를 위해 `pendingIssueProcessFailureAllJob`을 추가했습니다.
`jobRunExpectAt`이 지난 PROCESSING 상태 인증서를 찾아 실패 처리하고,
재시도 횟수가 남아있으면 재신청합니다.

### 도메인 재연결 시 이벤트 미발행

이미 인증서가 발급된 도메인을 해제 후 다시 연결하면,
발급 완료 이벤트가 발행되지 않는 문제가 있었습니다.
기존 인증서가 SUCCESS 상태이므로 발급 절차가 스킵되었기 때문입니다.

도메인 연결 시 항상 발급 절차를 진행하되,
이미 발급된 경우에는 기존 인증서의 성공 이벤트를 즉시 발행하도록 수정했습니다.

### 실패 이벤트 중복 발행

도메인 검증 실패와 인증서 발급 실패가 각각 별도 이벤트로 발행되어,
서비스 모듈에서 중복 처리하는 문제가 있었습니다.

최종적으로 실패 이벤트를 하나로 통합하고,
**최대 시도 횟수를 초과한 최종 실패 시에만** 이벤트를 발행하도록 수정했습니다.

## 9. 마치며

약 8주간 14개 태스크를 거쳐,
사용자 도메인 인증서 자동 발급 시스템을 완성했습니다.

### 개발 타임라인

| 기간 | 주요 작업 |
|------|----------|
| 2024.11 (2주) | certbot 학습, 설계, Verifier 모듈 구현 |
| 2024.12 초 (1주) | 핵심 배치 Job 4종 + ACME4j 어댑터 구현 |
| 2024.12 중~말 (2주) | 도메인 검증, 에러 핸들링, 엣지 케이스 대응 |
| 2025.01 (3주) | 알파 QA, Rate Limit 조정, 서비스 삭제 연동 |

### 배운 것들

**설계에 시간을 투자하면 구현이 빨라집니다.**
상태 머신을 먼저 설계한 덕분에,
배치 Job과 이벤트 처리의 구현이 자연스럽게 따라왔습니다.
반면, 설계에서 빠뜨린 엣지 케이스(도메인 재연결, PROCESSING 교착)는
QA 단계에서 추가 작업이 필요했습니다.

**헥사고날 아키텍처가 외부 서비스 연동에서 빛났습니다.**
ACME4j, Verifier, JPA 등 외부 의존성이 모두 어댑터로 격리되어 있어,
도메인 로직의 테스트와 수정이 독립적으로 가능했습니다.
임베디드 Redis에서 인메모리 HashMap으로 전환할 때도
어댑터만 교체하면 되었습니다.

이 시스템은 이후 약 1년간 운영되며
사용자 도메인 인증서를 자동으로 발급하고 갱신했습니다.
그리고 1년 후, 와일드카드 인증서의 수동 갱신 문제를 해결하기 위해
2편 — 와일드카드 인증서 갱신 완전 자동화로 이어집니다.

*이 글의 작성에 AI(Claude Code)를 활용했습니다.*
