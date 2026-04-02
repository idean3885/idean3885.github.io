---
title: "와일드카드 인증서 갱신 완전 자동화 — Docker IPC에서 Jenkins 배치까지"
date: 2026-04-01 12:00:00 +0900
categories: [개발 기록, 인증서 자동화 구축기]
tags: [Certbot, Jenkins, Let's Encrypt, DNS-01, Claude Code, 자동화, 인프라, Shell Script, Docker]
description: >-
  NHN Cloud DNS Plus에 certbot 플러그인이 없어 와일드카드 인증서를 수동 갱신해야 했습니다.
  Docker IPC로 DNS-01 Challenge를 자동화하고, 4개 클러스터 배포와 Jenkins 파이프라인까지
  완전 자동화한 과정을 정리합니다.
---

> **TL;DR**
> - NHN Cloud DNS Plus에 certbot 공식 플러그인이 없어
> 와일드카드 인증서를 수동 갱신해야 했습니다.
> - Docker certbot과 호스트 DNS Handler 간 **파일 기반 IPC**로
> DNS-01 Challenge를 자동화했습니다.
> - 4개 클러스터(Dev/Prod x IDC/K8s)에 인증서를 자동 배포하는 스크립트를 구축했습니다.
> - Jenkins 파이프라인으로 격월 자동 갱신 + 사내 메신저 알림까지
> 완전 자동화를 달성했습니다.
> - AI(Claude Code)를 활용하여 스크립트와 파이프라인 작성을 위임하고,
> 사용자는 플로우 설계에 집중했습니다.
{: .prompt-tip }

## 1. 배경

### 수동 갱신의 한계

클라우드 서비스는 2개의 와일드카드 인증서를 사용합니다.
Let's Encrypt 인증서의 유효기간은 90일이므로 주기적 갱신이 필요합니다.

문제는 갱신 과정이 전부 수동이었다는 점입니다.

1. certbot으로 DNS-01 Challenge 발급 (수동으로 TXT 레코드 설정)
2. 4개 클러스터에 인증서 적용 (kubectl patch, YAML 수정, git push)
3. 각 환경별 검증 (브라우저에서 하나씩 확인)

한 번의 갱신에 약 1~2시간이 소요되었고,
90일마다 반복해야 했습니다.
게다가 Let's Encrypt의 동일 도메인 세트 재발급 제한(주당 5회)으로
실수하면 최대 7일을 기다려야 합니다.

### 1편에서의 경험

1년 전(2024.11~2025.01)
사용자 도메인 인증서 발급 기능을 BE 코드로 구현하면서
certbot과 DNS-01 Challenge의 동작 원리를 학습했습니다.
이때의 경험이 이번 자동화 설계의 기반이 되었습니다.

### 자동화 목표

```
수동 갱신 (1~2시간)  →  Jenkins 버튼 하나 (또는 크론 자동)
```

최종 목표는 **사람이 개입하지 않는 완전 자동화**입니다.
격월 1일 정오에 Jenkins 크론이 자동 실행되고,
성공/실패 여부가 사내 메신저로 알림됩니다.

## 2. DNS-01 Challenge 자동화

### 와일드카드 인증서의 제약

와일드카드 인증서(`*.platform.com`)는
HTTP-01 Challenge를 사용할 수 없습니다.
반드시 DNS-01 Challenge,
즉 `_acme-challenge.platform.com` TXT 레코드를 설정하여
도메인 소유권을 증명해야 합니다.

certbot은 `--manual-auth-hook`으로 TXT 설정을 자동화할 수 있습니다.
하지만 NHN Cloud DNS Plus에는 공식 플러그인이 없습니다.
DNS API를 직접 호출해야 합니다.

### Docker와 호스트의 분리

certbot을 Docker로 실행하면 환경 격리와 재현성을 확보할 수 있지만,
DNS API 호출에 필요한 `curl`, `jq`, DNS 설정 등은 호스트에 존재합니다.
이 문제를 파일 기반 IPC로 해결하는 것이 적절하다고 생각했습니다.

```
[Docker certbot]                    [호스트 DNS Handler]
     │                                     │
     ├── auth-hook 실행                     │
     │   ├── request 파일 생성 ───────────→ │
     │   │   (DOMAIN, VALIDATION)          │
     │   │                                 ├── DNS Plus API 호출
     │   │                                 │   (TXT 레코드 설정)
     │   │                                 ├── DNS 전파 폴링
     │   │                                 │
     │   ← done 파일 감지 ←─────────────── ├── done 파일 생성
     │   └── certbot 검증 진행              │
     │                                     │
```

핵심 설계 포인트는 세 가지입니다.

**파일 기반 통신**:
Docker 볼륨 마운트로 `/certbot-comm` 디렉토리를 공유합니다.
certbot의 auth-hook이 request 파일을 생성하면,
호스트의 DNS Handler가 감지하여 처리하고 done 파일로 응답합니다.

**challenge 값 누적**:
`*.platform.com`과 `platform.com`은
같은 `_acme-challenge.platform.com` TXT 레코드를 사용합니다.
certbot은 이를 순차적으로 요청하므로,
이전 challenge 값을 유지한 채 새 값을 추가해야 합니다.
도메인별 challenge 파일에 값을 누적하여
한 번의 API 호출로 전체를 업데이트합니다.

**DNS 전파 폴링**:
DNS TXT 레코드를 설정한 후 바로 검증하면
전파 지연으로 실패할 수 있습니다.
고정 대기(30초) 대신
Google DNS(8.8.8.8)를 3초 간격으로 폴링하여
실제 전파를 확인합니다.
이를 통해 대기 시간을 최소화했습니다.

### auth-hook 설계 (Docker 내부)

```sh
# 요청 파일 생성
echo "DOMAIN=$CERTBOT_DOMAIN" > "$COMM_DIR/request_${REQUEST_ID}.txt"
echo "VALIDATION=$CERTBOT_VALIDATION" >> "$COMM_DIR/request_${REQUEST_ID}.txt"

# 호스트의 처리 완료 대기 (최대 120초)
while [ ! -f "$DONE_FILE" ]; do
    sleep 2
done
```

Docker 내부의 auth-hook은 `/bin/sh` 호환으로 작성했습니다.
certbot 공식 이미지에는 bash가 없기 때문입니다.
요청 파일을 생성하고 done 파일이 생길 때까지 대기하는 단순한 구조입니다.

## 3. 4개 클러스터 배포 자동화

### 클러스터 구조

클라우드 서비스는 Dev(개발)와 Prod(운영) 환경으로 나뉘며,
각 환경에 IDC와 K8s 두 개의 클러스터가 있습니다.
인증서 하나를 4개 클러스터에 각각 다른 방식으로 적용해야 합니다.

| 클러스터 | 적용 방식 | ArgoCD 관리 |
|---------|----------|-----------|
| IDC Dev/Prod | `kubectl patch secret` | 밖 |
| K8s Dev/Prod | YAML annotation 교체 + `kubectl apply` | 밖 |
| Helm Dev/Prod | git push → ArgoCD auto-sync | ArgoCD 관리 |

### IDC 클러스터: 시크릿 직접 교체

IDC 클러스터는 TLS 시크릿을 ArgoCD Application에 포함하지 않습니다.
포함하면 ArgoCD sync 시 인증서가 이전 버전으로 롤백되기 때문입니다.

```bash
TLS_CRT=$(base64 -w0 "$BASE_PATH/fullchain.pem" 2>/dev/null \
  || base64 -i "$BASE_PATH/fullchain.pem")
TLS_KEY=$(base64 -w0 "$BASE_PATH/privkey.pem" 2>/dev/null \
  || base64 -i "$BASE_PATH/privkey.pem")

kubectl patch secrets -n "$NS" "$NAME" \
  -p "{\"data\": {\"tls.key\": \"$TLS_KEY\", \"tls.crt\": \"$TLS_CRT\"}}"
```

`base64 -w0`(Linux)과 `base64 -i`(macOS)를 폴백으로 처리하여
로컬과 Jenkins 서버 모두에서 동작합니다.

### K8s 클러스터: YAML annotation 교체

NHN Cloud NKS의 로드밸런서는 Service annotation에
인증서를 직접 포함합니다.
`yq`로 annotation 값만 교체하고 `kubectl apply`로 적용합니다.

```bash
yq -i '(select(document_index == 0)
  | .metadata.annotations["loadbalancer.nhncloud/listener-terminated-https-cert"])
  = load_str("fullchain.pem")' "$file"
```

변경된 YAML은 git commit/push하여 k8s 저장소에도 반영합니다.
직접 `kubectl apply`하되, git 상태도 동기화하는 방식입니다.

### Helm: ArgoCD auto-sync

내부 웹 서비스는 Helm 차트로 관리되며 ArgoCD가 auto-sync합니다.
인증서가 포함된 `service.yaml` 템플릿을 perl로 교체하고
git push하면 ArgoCD가 자동 배포합니다.

### kubectl context 이식성

로컬(macOS)과 Jenkins 서버에서 kubectl context 이름이 다릅니다.
이를 `k8s-context.sh`로 추상화했습니다.

```bash
resolve_context() {
    case "$1" in
        dev-idc)
            local_name="service-dev-idc"    # 로컬
            jenkins_name="dev-idc"           # Jenkins
            ;;
    esac
    # 로컬 이름 먼저 시도, 없으면 Jenkins 이름
    if kubectl config get-contexts "$local_name" ...; then
        echo "$local_name"
    else
        echo "$jenkins_name"
    fi
}
```

스크립트가 실행 환경을 자동으로 감지하므로,
로컬 테스트와 Jenkins 실행 모두 동일한 스크립트를 사용합니다.

## 4. Jenkins 파이프라인으로 완전 자동화

### 파라미터 설계

인증서 갱신 파이프라인은 "발급"과 "배포"를 독립적으로 제어합니다.

| 파라미터 | 용도 |
|---------|------|
| `ISSUE` | NONE / STAGING / PRODUCTION |
| `DEPLOY` | NONE / DEV / PROD / ALL |

이 매트릭스 설계로 다양한 시나리오에 대응합니다.

- 발급 테스트만: `ISSUE=STAGING, DEPLOY=NONE`
- Dev만 먼저 검증: `ISSUE=PRODUCTION, DEPLOY=DEV`
- Dev 확인 후 Prod 적용: `ISSUE=NONE, DEPLOY=PROD`
- 정기 갱신: `ISSUE=PRODUCTION, DEPLOY=ALL`

### 크론 트리거

```groovy
triggers {
    cron('0 12 1 */2 *')  // 격월 1일 정오(KST)
}
```

크론 트리거 시에는 `getBuildCauses`로 배치 실행을 감지하고
`ISSUE=PRODUCTION`, `DEPLOY=ALL`을 자동 설정합니다.

```groovy
if (currentBuild.getBuildCauses(
        'hudson.triggers.TimerTrigger$TimerTriggerCause')) {
    env.ISSUE = 'PRODUCTION'
    env.DEPLOY = 'ALL'
}
```

### 사내 메신저 알림

배포(`DEPLOY != NONE`) 시
성공/실패 여부를 사내 메신저로 알립니다.
Dev 배포 시 Dev 방, Prod 배포 시 Prod 방에 각각 발송됩니다.
인증서 발급일과 만료일을 KST로 변환하여 포함합니다.

```groovy
def notBefore = sh(
    script: "TZ=Asia/Seoul date -d \"...\" '+%Y-%m-%d %H:%M:%S'",
    returnStdout: true)
```

### 엣지 케이스 해결

**Staging → Production 전환 시 충돌**:
certbot은 기존 renewal config에 ACME 서버 URL을 기록합니다.
Staging으로 테스트한 후 Production으로 발급하면
서버 불일치로 실패합니다.
발급 전에 기존 ACME 서버를 확인하고
다른 경우 인증서 디렉토리를 정리합니다.

**Docker root 파일 권한**:
certbot Docker가 root로 생성한 파일을
Jenkins(non-root)가 삭제할 수 없습니다.
`rm -rf`가 `set -e`로 실패하기 전에
Docker alpine 컨테이너로 먼저 정리합니다.

**인증서 검증 대기**:
인증서 적용 후 로드밸런서 리로드와 ArgoCD auto-sync에
시간이 필요합니다.
`cert-verify.sh`의 wait 모드로
최대 10분간 30초 간격으로 재시도하여
갱신 완료를 확인합니다.

## 5. AI 활용 소회

이번 자동화 구축에서 Claude Code를 적극 활용했습니다.
스크립트와 Jenkins 파이프라인 코드 작성을 AI에 위임하고,
사용자는 전체 플로우 설계와 의사결정에 집중했습니다.

1년 전에는 certbot과 DNS-01의 동작 원리를 이해하기 위해
8주를 투자했습니다.
그 경험이 있었기에
"무엇을 자동화해야 하는지",
"어디서 문제가 생길 수 있는지"를 판단할 수 있었고,
AI에게 올바른 방향을 제시할 수 있었습니다.

AI가 코드를 빠르게 생성해주는 것은 사실이지만,
엣지 케이스(Staging→Production 충돌, Docker root 권한 등)는
실제로 겪어야 발견됩니다.
결국 자동화의 품질은
"어떤 상황에서 실패할 수 있는가"를 아는 사람의 판단에 달려 있습니다.

## 마치며

수동으로 1~2시간 걸리던 인증서 갱신이
Jenkins 버튼 하나(또는 크론 자동)로 완전 자동화되었습니다.
더 이상 90일마다 인증서 만료를 걱정하지 않아도 됩니다.
사내 메신저 알림으로 갱신 결과를 확인할 수 있으며,
문제가 발생하면 Jenkins에서 수동 실행으로 대응합니다.

1년 전의 학습이 자동화의 기반이 되었고,
AI가 구현 속도를 높여주었습니다.
기술적 깊이와 AI 생산성,
둘 다 있어야 의미 있는 자동화를 만들 수 있다는 것을
체감한 프로젝트였습니다.

> 이 글은 Claude와 함께 작업했습니다.
{: .prompt-info }
