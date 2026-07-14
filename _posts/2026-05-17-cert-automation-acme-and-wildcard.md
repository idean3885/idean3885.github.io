---
title: "인증서 자동화: 사용자 도메인 ACME4j 구현부터 와일드카드 Jenkins 갱신까지"
date: 2026-05-17 23:00:00 +0900
last_modified_at: 2026-05-18 15:05:00 +0900
categories: [개발 기록]
tags: [Let's Encrypt, ACME, ACME4j, certbot, 헥사고날 아키텍처, Docker, Jenkins, 자동화, Spring Boot]
description: "사용자 도메인 ACME4j 자동 발급과 와일드카드 인증서 Jenkins 갱신 두 사이클을 한 흐름으로 정리합니다."
redirect_from:
  - /posts/user-domain-cert-automation/
  - /posts/domain-ssl-automation-certbot-to-acme4j/
  - /posts/wildcard-cert-automation-docker-ipc-jenkins/
---

> **TL;DR**<br>
> 1편: 사용자 도메인 인증서를 HTTP-01 + ACME4j 로 자동 발급. 헥사고날 + 상태 머신 + 4개 CronJob 으로 발급·갱신·재시도·타임아웃을 다 잡았습니다.<br>
> 2편: 1년 뒤 와일드카드 인증서 갱신을 Docker certbot 과 호스트 DNS Handler 의 파일 기반 IPC + Jenkins 격월 크론으로 끝까지 자동화했습니다.<br>
> 1편의 ACME 학습이 2편 자동화의 판단 기반이 됐습니다. 2편은 AI 에 코드 위임을 했지만, 엣지 케이스는 1편의 운영 경험에서만 나왔습니다.
{: .prompt-tip }

## 0. 배경: 두 가지 인증서 과제

운영 중인 앱 배포 플랫폼은 두 종류의 인증서를 다룹니다.

- **플랫폼 와일드카드**: `*.platform.com`. 모든 사용자 서비스가 공유. 90일 주기 갱신 필요
- **사용자 개별 도메인**: `my-service.example.com` 같은 사용자 자신의 도메인. 도메인 연결 시점에 자동 발급되어야 함

두 과제가 다른 시점에 나왔습니다. 사용자 도메인 자동 발급은 BE 구현 8주 (2024 말). 와일드카드 갱신 자동화는 1년 뒤 운영 자동화 (2026 초). 1편의 학습이 2편의 설계 기반이 됐고, 2편에서는 AI 협업으로 구현 속도를 크게 끌어올렸습니다.

## 1. Let's Encrypt 와 ACME 프로토콜

[Let's Encrypt](https://letsencrypt.org/) 는 무료 SSL 인증서를 자동 발급하는 CA. 핵심은 **도메인 소유권 검증**이고, ACME 프로토콜이 그 검증을 표준화한 메커니즘입니다.

### Challenge 유형

| Challenge | 검증 방식 | 용도 |
|---|---|---|
| HTTP-01 | `http://{도메인}/.well-known/acme-challenge/{token}` 에 응답 | 단일 도메인 |
| DNS-01 | `_acme-challenge.{도메인}` TXT 레코드 설정 | 와일드카드 도메인 |

와일드카드는 DNS-01 만 가능 (HTTP-01 은 호스트 단위라 와일드카드와 호환되지 않습니다).

### Rate Limits (이후 구현에 직접 영향)

| 제한 | 값 | 비고 |
|---|---|---|
| 동일 도메인 세트 인증서 | 주당 5회 | 초과 시 최대 7일 대기 |
| 계정당 인증서 | 시간당 10개 | 갱신은 10배 허용 |
| 계정당 신규 주문 | 3시간당 300개 | 주문 생성 제한 |

이 제한이 배치 스케줄과 재시도 전략을 결정한 핵심 입력이었습니다.

### certbot 으로 먼저 학습

본격적인 BE 구현 전에 certbot CLI 로 발급 과정을 직접 돌렸습니다.

```bash
certbot certonly --manual \
  --preferred-challenges dns \
  -d "*.platform.com"
```

certbot 이 TXT 레코드 값을 알려주면 DNS 에 수동으로 추가하고 확인. 이 학습에서 두 가지를 알게 됐습니다.

1. 와일드카드는 DNS-01 필수. 사용 중인 클라우드 DNS 서비스에는 certbot 공식 플러그인이 없어 수동 발급이 유일 방법이었음 (이게 2편의 자동화 동기가 됐습니다)
2. 사용자 도메인은 HTTP-01 이 적합. 사용자 DNS 를 플랫폼이 직접 제어할 수 없으니 HTTP 응답 기반이 자동화에 유리

## 2. 1편: 사용자 도메인 BE 구현 (HTTP-01 + ACME4j)

### 헥사고날 모듈 구조

```
cert/
├── api/        # 공유 인터페이스 (UseCase, Command, Event)
├── core/       # 비즈니스 로직 (도메인, 서비스, 포트, 어댑터)
├── server/     # REST API + 이벤트 구독
├── verifier/   # HTTP-01 토큰 응답 서비스 (사용자 도메인 트래픽 수신)
├── job/        # 배치 CronJob
└── client/     # 외부 서비스용 클라이언트
```

도메인 포트와 어댑터 매핑.

| 포트 | 어댑터 |
|---|---|
| `CertificateIssuerPort` | ACME4j 래핑 |
| `DomainVerifyPort` | Verifier 모듈 연동 |
| `CertificateRepository` | JPA |
| `CertificateValidator` | 상태 전이 검증 |

### 상태 머신 설계

발급은 즉시 완료되지 않습니다. 도메인 검증·ACME 통신·인증서 생성 여러 단계에서 실패할 수 있으니 상태 머신이 필요했습니다.

```
[서비스 등록] → APPLICATION → PROCESSING → SUCCESS → (갱신 시) APPLICATION
                  ▲              │
                  │              ▼
                  └── FAILURE_REAPPLICATION (재시도)
                       └→ PROCESSING → FAILURE_EXIT (최대 시도 초과)
```

### Rich Domain 패턴

`Certificate` 엔티티가 상태 전이 로직과 외부 호출을 내부에 캡슐화합니다. 서비스 레이어는 도메인에 메시지만 전달하면 됩니다.

```java
public class Certificate {
    // 발급 시작: APPLICATION → PROCESSING
    public void issueStart(Duration jobExpectDuration) {
        this.issuanceAttemptCount += 1;
        this.issuanceStatus = PROCESSING;
        this.jobRunExpectAt = ZonedDateTime.now().plus(jobExpectDuration);
    }

    // 발급 처리: 도메인이 직접 Output Port 호출
    public IssueProcessResponse issueProcess(IssueProcessRequest req) {
        var issuerPort = req.issuerPort();
        try {
            var data = issuerPort.issue(this);   // ACME4j 통신
            this.issuanceStatus = SUCCESS;
            this.issuedAt = data.issuedAt();
            this.expiredAt = data.expiredAt();
            this.publicKey = data.publicKey();
            this.privateKey = data.privateKey();
            this.jobRunExpectAt = this.expiredAt.minus(req.renewalExpectDuration());
            return new IssueProcessResponse(true);
        } catch (Exception e) {
            // 재시도 또는 최종 실패 처리
            return new IssueProcessResponse(false);
        }
    }
}
```

상태 전이 검증은 `CertificateValidator` 가 담당. APPLICATION 이 아닌 인증서에 `issueStart()` 를 호출하면 예외가 납니다.

### ACME4j 발급 흐름

```
CertificateIssuerPortImpl.issue()
  ├─ Acme4jService.createOrder(도메인)
  ├─ Acme4jService.createChallenge(주문)
  ├─ VerifierFeign.saveChallengeToken()    ─── Verifier 에 토큰 저장
  ├─ Acme4jService.triggerChallenge()       ─── Let's Encrypt 가 Verifier 로 검증 요청
  │     └─ GET /.well-known/acme-challenge/{token}
  ├─ Acme4jService.createCertificate()
  └─ VerifierFeign.deleteChallengeToken()  ─── 토큰 정리 (finally)
```

Verifier 의 토큰 저장은 인메모리 HashMap. 처음엔 임베디드 Redis 를 적용했지만 토큰의 일회성 특성을 보고 HashMap 으로 단순화. 어댑터로 격리되어 있어 교체가 짧았습니다.

### 4개 CronJob 으로 생명주기 관리

| Job | 주기 | 역할 |
|---|---|---|
| `certificateIssueAllJob` | 20분 | APPLICATION 인증서 발급 |
| `certificateRenewalApplyAllJob` | 10분 | 만료 임박 갱신 신청 |
| `certificateIssueFailureReapplyAllJob` | 30분 | 실패 인증서 재신청 |
| `certificatePendingIssueProcessFailureAllJob` | 10분 | PROCESSING 타임아웃 처리 |

발급 Job 은 Rate Limit 을 따릅니다.

```java
public void issueAll() {
    List<Certificate> targets = repository.findAllIssueTargetLimit(
        ACCOUNT_SPEC.getMaxCharge()  // 시간당 10건
    );
    for (Certificate cert : targets) {
        cert.issueStart(...);
        try {
            domainVerifyPort.verifyServiceLink(cert.getDomain());
        } catch (DomainVerifyServiceNotLinkedException e) {
            handleDomainLinkFailure(cert);
            continue;
        }
        certificateJobAsync.issueProcessAsync(cert);  // @Async
    }
}
```

### 실전 이슈 5가지

| 이슈 | 원인 | 해결 |
|---|---|---|
| Rate Limit 초과 | 배치가 한 번에 너무 많이 발급 시도 | `ACCOUNT_SPEC.maxCharge` (10건) 로 조회 제한 |
| ACME 계정 중복 생성 | 매 발급마다 계정 새로 등록 | Lazy 초기화로 한 번만 생성·재사용 |
| PROCESSING 상태 교착 | 비동기 발급 중 서버 재시작 | `pendingIssueProcessFailureAllJob` 으로 `jobRunExpectAt` 초과 PROCESSING 을 실패 처리 + 재시도 |
| 도메인 재연결 시 이벤트 미발행 | 기존 SUCCESS 가 있어 발급 절차 스킵 | 도메인 연결 시 발급 절차를 항상 진행, 이미 발급된 경우 기존 인증서의 성공 이벤트 즉시 발행 |
| 실패 이벤트 중복 발행 | 도메인 검증 실패 / 발급 실패가 각각 별도 이벤트 | 통합 + 최대 시도 초과한 최종 실패에만 발행 |

설계부터 QA 까지 약 8주. 일정 산정은 18.5MD (3.7주) 였지만 설계 시간과 엣지 케이스 대응이 두 배 이상 갔습니다. 설계에 시간을 더 쓰면 구현이 빨라진다는 걸 체감했습니다.

## 3. 2편: 와일드카드 갱신 운영 자동화 (1년 뒤)

### 수동 갱신의 한계

플랫폼 와일드카드 (`*.platform.com`) 의 갱신이 90일마다 수동이었습니다.

1. certbot 으로 DNS-01 발급 (수동 TXT 설정)
2. 4개 클러스터에 인증서 적용 (kubectl patch / YAML 수정 / git push)
3. 환경별 검증 (브라우저에서 하나씩)

회당 1~2시간. 게다가 동일 도메인 세트 재발급 제한 (주당 5회) 으로 실수하면 7일 대기. 자동화 목표는 "사람 개입 없는 격월 크론".

### DNS-01 자동화: Docker certbot + 호스트 DNS Handler IPC

DNS Plus 에 certbot 공식 플러그인이 없으니 `--manual-auth-hook` 으로 API 를 직접 호출해야 합니다. certbot 을 Docker 로 실행하면 환경 격리·재현성을 얻지만, DNS API 호출에 필요한 `curl`·`jq` 는 호스트에 있습니다. **파일 기반 IPC** 로 분리.

```
[Docker certbot]                    [호스트 DNS Handler]
     │                                     │
     ├── auth-hook 실행                     │
     │   ├── request 파일 생성 ────────→    │
     │   │   (DOMAIN, VALIDATION)          │
     │   │                                 ├── DNS API 호출 (TXT 레코드 설정)
     │   │                                 ├── DNS 전파 폴링 (8.8.8.8, 3초 간격)
     │   ← done 파일 감지 ←────────────    ├── done 파일 생성
     │   └── certbot 검증 진행              │
```

설계 포인트 3가지.

1. **파일 통신**: Docker 볼륨 마운트로 `/certbot-comm` 공유
2. **challenge 값 누적**: `*.platform.com` 과 `platform.com` 은 같은 TXT 레코드 사용. 도메인별 challenge 파일에 값을 누적하여 한 번의 API 호출로 전체 업데이트
3. **DNS 전파 폴링**: 고정 대기 대신 Google DNS 폴링으로 실제 전파 확인. 대기 시간 최소화

Docker 내부 auth-hook 은 `/bin/sh` 호환 (certbot 공식 이미지에 bash 없음).

### 4개 클러스터 배포

플랫폼은 Dev / Prod 환경에 각각 IDC (베어메탈) 와 매니지드 K8s 두 클러스터씩, 총 4개. 인증서 하나를 각각 다른 방식으로 적용합니다.

| 클러스터 | 적용 방식 | ArgoCD 관리 |
|---|---|---|
| IDC Dev/Prod | `kubectl patch secret` | 밖 (sync 시 롤백 방지) |
| 매니지드 Dev/Prod | YAML annotation 교체 + `kubectl apply` | 밖 |
| Helm | git push → ArgoCD auto-sync | 안 |

IDC 가 ArgoCD 관리 밖에 있는 이유는 sync 시 인증서가 이전 버전으로 롤백되기 때문. 매니지드 클러스터는 로드밸런서 annotation 에 인증서를 직접 포함하므로 `yq` 로 annotation 만 교체합니다.

### kubectl context 이식성

로컬 (macOS) 과 Jenkins 서버에서 context 이름이 달라 스크립트가 깨졌습니다. 추상화로 해결.

```bash
resolve_context() {
    case "$1" in
        alpha-idc)
            local_name="platform-alpha-idc"
            jenkins_name="dev-idc"
            ;;
    esac
    if kubectl config get-contexts "$local_name" &>/dev/null; then
        echo "$local_name"
    else
        echo "$jenkins_name"
    fi
}
```

스크립트가 실행 환경을 자동 감지. 로컬 테스트와 Jenkins 실행이 같은 스크립트를 씁니다.

### Jenkins 파이프라인: 파라미터 매트릭스

발급과 배포를 독립 제어.

| 파라미터 | 값 |
|---|---|
| `ISSUE` | NONE / STAGING / PRODUCTION |
| `DEPLOY` | NONE / ALPHA / REAL / ALL |

이 매트릭스로 다양한 시나리오 대응.
- 발급 테스트만: `ISSUE=STAGING, DEPLOY=NONE`
- Alpha 먼저 검증: `ISSUE=PRODUCTION, DEPLOY=ALPHA`
- Alpha 확인 후 Real: `ISSUE=NONE, DEPLOY=REAL`
- 정기 갱신: `ISSUE=PRODUCTION, DEPLOY=ALL`

크론 트리거 (격월 1일 정오 KST).

```groovy
triggers { cron('0 12 1 */2 *') }
```

크론 실행 감지 시 `ISSUE=PRODUCTION, DEPLOY=ALL` 자동 설정. 배포 결과는 메신저 webhook 으로 알림.

### 엣지 케이스 3가지

| 이슈 | 원인 | 해결 |
|---|---|---|
| Staging → Production 전환 시 충돌 | certbot 이 renewal config 에 ACME 서버 URL 기록. 서버 불일치로 실패 | 발급 전 기존 ACME 서버 확인, 다르면 인증서 디렉토리 정리 |
| Docker root 파일 권한 | certbot Docker 가 root 로 생성한 파일을 Jenkins (non-root) 가 삭제 못함 | `rm -rf` 가 `set -e` 로 실패하기 전, Docker alpine 컨테이너로 먼저 정리 |
| 인증서 검증 대기 | 적용 후 로드밸런서 리로드·ArgoCD sync 에 시간 필요 | `cert-verify.sh` wait 모드로 최대 10분, 30초 간격 재시도 |

## 4. 1년의 학습 차이와 AI 협업

1편에서는 certbot 과 DNS-01 의 동작 원리를 이해하기 위해 8주를 투자했습니다. 그 경험이 있었기에 2편에서 "무엇을 자동화해야 하는지", "어디서 문제가 생길 수 있는지" 를 판단할 수 있었고, AI 에게 올바른 방향을 제시할 수 있었습니다.

2편의 자동화에서는 스크립트와 Jenkins 파이프라인 코드 작성을 AI 에 위임했고, 본인은 전체 플로우 설계와 의사결정에 집중했습니다. 결과적으로 1편보다 훨씬 짧은 시간에 운영 수준의 자동화에 도달했습니다.

다만 엣지 케이스 (Staging → Production 충돌, Docker root 권한, DNS 전파 폴링 같은 디테일) 은 AI 가 처음부터 알려주지 않습니다. 실제로 한 번 겪어봐야 발견되는 종류입니다. 1편의 운영 경험이 그 발견의 토대였습니다.

## 회고: 깊이가 자동화 품질을 만든다

| 시기 | 작업 | 깊이 | AI 협업 |
|---|---|---|---|
| 2024 말 (8주) | 사용자 도메인 BE 자동 발급 | ACME 학습부터, 깊이 우선 | 부분 |
| 2026 초 (단기간) | 와일드카드 갱신 운영 자동화 | 1편의 깊이를 자동화 판단 기반으로 | 적극 |

도구 (certbot, ACME4j, Jenkins) 는 시간이 흐르며 바뀝니다. 바뀌지 않는 것은 **그 도구가 어떤 제약 위에서 동작하는지** 를 이해하는 깊입니다. Rate Limit, DNS 전파, 권한 모델, 환경별 적용 방식. 이 제약을 모르고 만든 자동화는 갱신 한 번에 무너집니다. 1편의 8주가 비싸 보였지만 2편에서 회수됐습니다.

AI 가 코드를 빠르게 생성해주는 시대에는, 어떤 사람의 자동화가 더 단단한가가 더 잘 드러납니다. 답은 단순합니다. "어떤 상황에서 실패할 수 있는가" 를 아는 사람의 자동화가 단단합니다.

---

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
