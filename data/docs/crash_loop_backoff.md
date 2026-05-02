# CrashLoopBackOff 장애 대응

## 증상
- Pod 상태가 CrashLoopBackOff로 표시됨
- k8s 이벤트에 BackOff 발생
- Pod restart count가 반복적으로 증가
- 재시작 간격이 점점 길어짐 (10s → 20s → 40s → ...)

## 원인
- 애플리케이션 시작 시 필수 환경변수 또는 설정 파일 누락
- DB 연결 실패로 인한 앱 초기화 오류
- 잘못된 컨테이너 이미지 또는 엔트리포인트 설정
- livenessProbe 설정이 너무 엄격해서 정상 Pod도 재시작
- 애플리케이션 코드 버그로 인한 시작 직후 크래시

## 조치
1. `kubectl logs <pod-name> --previous`로 크래시 직전 로그 확인
2. `kubectl describe pod <pod-name>`으로 이벤트 및 환경변수 확인
3. 환경변수 및 ConfigMap/Secret 마운트 상태 확인
4. DB, Redis 등 의존 서비스 연결 상태 확인
5. livenessProbe initialDelaySeconds 값 증가 검토

## 예방
- 애플리케이션 시작 시 필수 설정 검증 로직 추가
- readinessProbe와 livenessProbe 분리 설정
- 의존 서비스 헬스체크 후 시작하는 init container 사용