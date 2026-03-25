# 장기 투자 주식 분석기 (Long-Term Stock Analyzer)

`yfinance`와 `pandas`를 활용한 **펀더멘털 + 기술적 분석 기반 장기 투자 스크리너**입니다.
복수 종목을 일괄 분석하고, 리스크 관리 기반 매수 수량까지 자동으로 산출합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **멀티 종목 분석** | 티커 리스트를 입력하면 일괄 분석 후 DataFrame으로 반환 |
| **4단계 스코어링** | ROE, 부채비율, PER 갭, 이동평균 기반 0~4점 채점 |
| **포지션 사이징** | 총자산 대비 최대 손실률로 권장 매수 수량 자동 계산 |
| **3년 백테스트** | 누적 수익률 및 최대 낙폭(MDD) 산출 |

---

## 설치

```bash
pip install yfinance pandas numpy
```

---

## 빠른 시작

```python
from stock_analyzer import analyze_long_term_stocks, print_report

tickers = ["AAPL", "MSFT", "GOOGL", "NVDA"]
df = analyze_long_term_stocks(tickers, total_capital=100_000)
print_report(df)

# CSV로 저장
df.to_csv("stock_analysis.csv", index=False)
```

---

## 스코어링 로직

총 **4개 조건**을 충족할수록 높은 점수를 받습니다.

```
Score 4/4 → ★ Strong Buy
Score 3/4 → ▲ Buy
Score 2/4 → ◆ Hold
Score 1/4 이하 → ▼ Watch
```

| # | 조건 | 기준 | 의미 |
|---|------|------|------|
| 1 | ROE | > 10% | 우수한 수익성 |
| 2 | 부채비율 (D/E) | < 100 | 재무 건전성 |
| 3 | PER 갭 | 현재 PER < 5년 평균 PER | 역사적 저평가 구간 |
| 4 | 이동평균 | 현재가 > MA120 | 장기 상승 추세 유지 |

> **5년 평균 PER 산출 방식**: yfinance는 과거 EPS를 직접 제공하지 않으므로,
> `과거 5년 주가 ÷ 현재 Trailing EPS`로 근사 계산합니다.

---

## 포지션 사이징 공식

```
최대 허용 손실 = 총자산 × 2%          (기본: $2,000)
주당 손실액   = 현재가 × 10%          (10% 손절 기준)
권장 수량     = floor(최대손실 / 주당손실액)
```

**예시**: 현재가 $200인 종목 → 주당 손실 $20 → 권장 수량 **100주** ($2,000 / $20)

---

## 출력 컬럼 설명

### Summary 테이블

| 컬럼 | 설명 |
|------|------|
| `Ticker` | 종목 코드 |
| `Signal` | 투자 신호 (Strong Buy / Buy / Hold / Watch) |
| `Score` | 4개 조건 중 충족 수 (예: `3/4`) |
| `Current Price` | 현재 주가 (USD) |
| `Rec. Qty` | 리스크 기반 권장 매수 수량 |
| `3Y Return (%)` | 최근 3년 누적 수익률 |
| `MDD (%)` | 최근 3년 최대 낙폭 (Maximum Drawdown) |

### Fundamentals 테이블

| 컬럼 | 설명 |
|------|------|
| `ROE` | 자기자본이익률 |
| `D/E Ratio` | 부채비율 |
| `Trailing PE` | 현재 주가수익비율 (과거 12개월 EPS 기준) |
| `5Y Avg PE` | 5년 평균 PER (근사값) |
| `MA120` | 120일 이동평균선 |
| `MA200` | 200일 이동평균선 |
| `Key Reasons` | 점수 획득 근거 |

---

## 설정값 변경

`stock_analyzer.py` 상단의 상수를 수정하여 기준을 조정할 수 있습니다.

```python
TOTAL_CAPITAL   = 100_000  # 총 투자 자산 (USD)
MAX_LOSS_PCT    = 0.02     # 포지션당 최대 손실 비율 (2%)
STOP_LOSS_PCT   = 0.10     # 손절 기준 (10%)
ROE_THRESHOLD   = 0.10     # ROE 기준선 (10%)
DE_THRESHOLD    = 100      # 부채비율 기준선
MA_TREND_WINDOW = 120      # 추세 판단 이동평균 기간 (일)
```

---

## 한국 주식 분석

야후 파이낸스의 KRX 티커를 사용합니다. 종목코드 뒤에 `.KS`를 붙입니다.

```python
# 예시: 삼성전자, SK하이닉스
WATCHLIST = ["005930.KS", "000660.KS"]
df = analyze_long_term_stocks(WATCHLIST, total_capital=100_000)
```

---

## 주의사항

- 본 도구는 **참고용 분석 도구**이며, 투자 권유가 아닙니다.
- yfinance 데이터는 실시간이 아니며 지연될 수 있습니다.
- 5년 평균 PER은 현재 EPS로 역산한 근사값으로, 실제 과거 EPS와 차이가 있을 수 있습니다.

---

## 의존성

| 패키지 | 용도 |
|--------|------|
| `yfinance` | 주가 및 재무 데이터 수집 |
| `pandas` | 데이터 처리 및 DataFrame 출력 |
| `numpy` | 수치 연산 |
| `math` | 수량 내림 계산 (`floor`) |
