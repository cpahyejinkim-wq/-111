# Financial Closing Analytics Dashboard

이 저장소는 여신전문금융회사 재무팀의 월별 결산 분석을 위한 Python + HTML 기반 로컬 대시보드 MVP를 포함합니다.

## NIM 분석 MVP

구현 위치: `nim_dashboard/`

주요 기능:

* 월별 PL / 평잔 BS 엑셀 자동 인식 및 정규화
* `product_map.csv` 기준 상품별 이자수익·자산평잔·수익률 계산
* `funding_map.csv` 기준 차입금별 이자비용·부채평잔·조달금리 계산
* 평균차입금리 방식 상품별 이자비용 배분
* 상품별 순이자수익 / 상품별 NIM / 총 NIM 산출
* Alert Center 및 Reconciliation JSON 생성
* 미래 Rate Sensitivity, Funding Forecast, Asset Forecast, NIM Forecast 확장 placeholder

실행 방법은 `nim_dashboard/README.md`를 참고하세요.
