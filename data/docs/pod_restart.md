# Pod 반복 재시작 장애 대응

## 증상
- Pod restart count가 3회 이상
- 서비스 간헐적 불가
- livenessProbe 실패 이벤트 발생

## 원인
- livenessProbe 응답 지연으로 인한 강제 재시작
- 애플리케이션 데드락
- 메모리 또는 CPU 부족으로 인한 응답 불가
- 외부 의존성 장애로 인한 헬스체크 실패

## 조치
1. `kubectl describe pod <pod-name>`으로 재시작 원인 확인
2. `kubectl logs <pod-name> --previous`로 이전 실행 로그 확인
3. livenessProbe 설정 검토 (timeoutSeconds, failureThreshold)
4. 재시작 직전 메모리/CPU 사용률 확인
5. 데드락 의심 시 스레드 덤프 분석

## 예방
- livenessProbe와 readinessProbe 분리
- livenessProbe는 단순 ping 수준으로 설계
- readinessProbe에서 의존성 체크 수행