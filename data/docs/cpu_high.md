# CPU 사용률 급증 장애 대응

## 증상
- CPU 사용률이 85% 이상으로 지속
- 응답 지연(latency) 증가
- HTTP 요청 타임아웃 발생
- 동시 요청 처리 불가

## 원인
- 트래픽 급증으로 인한 CPU 부하
- 무한루프 또는 비효율적인 알고리즘
- GC(Garbage Collection) 과부하
- 외부 API 응답 지연으로 인한 스레드 블로킹
- CPU limit이 너무 낮게 설정됨

## 조치
1. `kubectl top pod <pod-name>`으로 실시간 CPU 확인
2. 스레드 덤프 분석으로 CPU 점유 스레드 식별
3. HPA(Horizontal Pod Autoscaler) 설정 확인 및 스케일아웃
4. CPU limit 상향 조정
5. 트래픽 급증이 원인이면 rate limiting 적용 검토

## 예방
- HPA 설정으로 CPU 70% 이상 시 자동 스케일아웃
- CPU requests와 limits 적절히 설정
- 프로파일링으로 CPU 집약적 코드 최적화