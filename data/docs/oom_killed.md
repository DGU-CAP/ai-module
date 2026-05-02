# OOMKilled 장애 대응

## 증상
- Pod가 반복적으로 재시작됨
- k8s 이벤트에 OOMKilled 발생
- 로그에 OutOfMemoryError 출력
- 메모리 사용률이 지속적으로 상승하다가 limit 도달

## 원인
- JVM heap size가 컨테이너 memory limit보다 크게 설정됨
- 메모리 누수로 인해 점진적으로 메모리 사용량 증가
- 갑작스러운 트래픽 증가로 인한 메모리 급증
- 대용량 파일 처리 또는 캐시 미제한 설정

## 조치
1. `kubectl describe pod <pod-name>`으로 memory limit 확인
2. `kubectl logs <pod-name> --previous`로 종료 직전 로그 확인
3. JVM 옵션에서 `-Xmx` 값이 memory limit의 75% 이하인지 확인
4. memory limit 상향 조정 (requests와 limits 모두)
5. 메모리 누수 의심 시 heap dump 분석

## 예방
- memory requests와 limits를 동일하게 설정 (Guaranteed QoS)
- JVM: -Xmx를 컨테이너 limit의 75% 이하로 설정
- 메모리 사용량 모니터링 알림 설정