---
title: "@Data vs 개별 어노테이션 — JPA 복합 키 클래스의 트레이드오프"
date: 2026-03-08 00:00:00 +0900
categories: [기술 노하우, 실무 노하우]
tags: [설계, 아키텍처, 개발사전]
description: >-
  JPA @IdClass 복합 키 클래스에서 @Data의 편의성과 @Setter 제거 사이의
  트레이드오프를 정리합니다.
  adapter 인프라 클래스에 한해 @Data 수용이 합리적인 이유를 설명합니다.
---

> **TL;DR** JPA @IdClass 복합 키 클래스에서 @Data의 편의성을 수용할 것인가,
> @Setter 제거를 위해 어노테이션을 개별 선언할 것인가의 트레이드오프입니다.
> adapter 인프라 클래스에 한해 @Data 수용은 합리적 판단입니다.
> **단, @Data는 @NoArgsConstructor를 포함하지 않으므로 반드시 명시해야 합니다.**
{: .prompt-tip }

## 핵심 원리

### Lombok @Data가 생성하는 것

@Getter + @Setter + @EqualsAndHashCode + @ToString + @RequiredArgsConstructor

**주의: @RequiredArgsConstructor ≠ @NoArgsConstructor**

- @RequiredArgsConstructor는 final/@NonNull 필드 대상 생성자를 생성합니다.
- final 필드가 없으면 매개변수 없는 생성자가 만들어지지만,
  이것은 **@NoArgsConstructor와 동일하지 않습니다.**
- Hibernate는 @IdClass/@Embeddable 클래스에 명시적 no-arg constructor를 요구합니다.
- **@Data + @AllArgsConstructor만으로는 Hibernate가 인스턴스를 생성하지 못해
  런타임 에러가 발생합니다.**

> 실제 장애 사례: `Unable to locate constructor for embeddable 'CompositeKey'`
> @Data + @AllArgsConstructor만 선언하고 @NoArgsConstructor를 누락하여 배치 잡이 실패.

### @IdClass vs @EmbeddedId 선택 기준

| 항목 | @IdClass | @EmbeddedId |
|------|-----------|---------------|
| @GeneratedValue | **지원** (필드가 엔티티에 직접 선언) | JPA 스펙 미보장 (@Embeddable 내 비표준) |
| 필드 접근 | entity.getId() (flat) | entity.getId().getId() (중첩) |
| Record 사용 | 불가 | Hibernate 6+ 지원 |

**결정적 기준**: PK에 @GeneratedValue가 있으면 @IdClass가 유일한 선택지입니다.

### @IdClass에서 Record를 쓸 수 없는 이유

JPA 스펙은 @IdClass에 no-arg constructor를 요구합니다.
Hibernate 구현체는 no-arg constructor로 인스턴스 생성 후
리플렉션으로 필드를 세팅하는 순서로 동작합니다.

Java 리플렉션 자체는 Record의 final 필드도 setAccessible(true)로 강제 세팅 가능하지만,
Hibernate가 @IdClass에 대해 이 방식을 지원하지 않습니다.
**기술적 제약이 아니라 구현체의 선택입니다.**

## 실무 적용

### 어노테이션 비교

| 방식 | 어노테이션 수 | Setter |
|------|-------------|--------|
| @Data + @NoArgsConstructor + @AllArgsConstructor | 3개 | 있음 |
| 개별 선언 (@Getter + @EqualsAndHashCode + @ToString + @NoArgsConstructor + @AllArgsConstructor) | 5개 | 없음 |

### 판단 기준

- no setter 원칙의 본래 목적은 **도메인 불변식 보호**입니다.
- @IdClass 키 클래스는 adapter 계층의 인프라 코드이며, 비즈니스 불변식이 없습니다.
- setter 호출처가 존재하지 않으므로 실질적 위험이 없습니다.
- 미끄러운 경사면(adapter에서 domain으로 확산) 위험은
  헥사고날 아키텍처 경계로 통제됩니다.

**결론**: adapter 인프라 클래스에 한해 @Data 편의성 수용은 합리적 트레이드오프입니다.

## 코드 예시

```java
// @IdClass 키 클래스 - @Data 사용
// ⚠️ @NoArgsConstructor 필수 — @Data는 이를 포함하지 않음
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderItemKey implements Serializable {
  private Long id;
  private LocalDate orderDate;
}

// 엔티티 - @GeneratedValue 때문에 @IdClass 필수
@IdClass(OrderItemKey.class)
@Entity
public class OrderItemEntity {
  @Id
  @GeneratedValue(strategy = GenerationType.SEQUENCE)
  private Long id;

  @Id
  private LocalDate orderDate;
}
```

*이 글은 Claude의 도움을 받아 작성했습니다.*
