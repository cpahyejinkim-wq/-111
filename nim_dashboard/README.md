# 여신전문금융회사 월별 NIM 분석 대시보드 MVP

월별 PL / 평잔 BS 엑셀과 상품·차입 맵핑 CSV를 기준으로 실제 월별 이자수익, 이자비용, 상품별 배분 이자비용, 상품별/총 NIM, Alert, Reconciliation 결과를 산출하는 로컬 대시보드입니다.

## 실행

```bash
cd nim_dashboard
python -m pip install -r requirements.txt
python src/export/build_dashboard_data.py
python app.py
```

브라우저: <http://localhost:8601>


## 의존성 설치 문제 해결

`python -m pip install -r requirements.txt`에서 `Tunnel connection failed: 403 Forbidden`이 발생하면 코드 문제가 아니라 현재 실행 환경의 프록시 또는 패키지 인덱스 정책이 PyPI 접근을 차단한 상태입니다. 먼저 아래 진단 명령을 실행하세요.

> 이미 `pandas`를 설치했는데도 `ModuleNotFoundError: No module named 'pandas'`가 나오면, 설치한 Python과 실행 중인 Python이 다른 경우가 많습니다. 아래 명령으로 같은 인터프리터에 설치되어 있는지 확인하세요.
>
> ```bash
> python -c "import sys; print(sys.executable)"
> python -m pip show pandas
> ```


```bash
python scripts/check_environment.py
```

해결 방법은 실행 환경에 따라 다릅니다.

1. 인터넷 / PyPI 접근이 허용된 환경에서는 그대로 설치합니다.

   ```bash
   python -m pip install -r requirements.txt
   ```

2. 회사 내부 PyPI 미러가 있는 경우 승인된 미러 URL을 지정합니다.

   ```bash
   python -m pip install -r requirements.txt --index-url https://<company-pypi-mirror>/simple
   ```

3. 내부망에서 외부 접속이 불가능한 경우 인터넷 가능한 PC에서 wheelhouse를 만든 뒤 내부망으로 복사해 설치합니다.

   ```bash
   python -m pip download -r requirements.txt -d wheelhouse
   python -m pip install --no-index --find-links ./wheelhouse -r requirements.txt
   ```

이 저장소의 현재 필수 패키지는 `requirements.txt`에 고정되어 있으며, `pandas`, `openpyxl`, `fastapi`, `uvicorn`, `python-multipart`입니다.

## 입력 파일

* `data/raw/`: 월별 PL / 평잔 BS 엑셀 파일을 넣습니다.
* `mapping/product_map.csv`: 상품별 자산계정과 이자수익 계정 맵핑입니다.
* `mapping/funding_map.csv`: 차입유형별 부채계정과 이자비용 계정 맵핑입니다.
* `config/settings.json`: Alert 임계값과 계정 키워드를 설정합니다.

raw 엑셀이 없으면 MVP 확인을 위해 샘플 데이터로 `output/dashboard_data.json`을 생성합니다. 실제 파일만 검증하려면 `python src/export/build_dashboard_data.py --no-sample`을 사용하세요.

## 산출물

`output/` 아래에 다음 JSON이 생성됩니다.

* `dashboard_data.json`
* `product_monthly.json`
* `funding_monthly.json`
* `total_monthly.json`
* `anomalies.json`
* `reconciliation.json`

## 설계 원칙

* PL / BS 원천 데이터와 맵핑 파일 기준으로 계산합니다.
* 월간 손익은 1월 잔액, 2월 이후 증감액 헤더를 자동 인식합니다.
* 연환산 금리는 `monthly_rate / days_in_month * days_in_year` 방식입니다.
* 평균차입금리 배분 로직은 `src/analytics/funding_allocation.py`에 분리되어 있습니다.
* Forecast / Scenario 기능은 현재 실적과 섞지 않도록 placeholder 모듈과 JSON 구조만 열어두었습니다.
