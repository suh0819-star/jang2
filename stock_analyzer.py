import yfinance as yf
import pandas as pd
import numpy as np
import math

# ──────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────
TOTAL_CAPITAL      = 100_000   # USD (≈ 100M KRW)
MAX_LOSS_PCT       = 0.02      # 2 % of capital per position
STOP_LOSS_PCT      = 0.10      # 10 % drop triggers stop-loss
ROE_THRESHOLD      = 0.10      # 10 %
DE_THRESHOLD       = 100       # Debt-to-Equity ratio
MA_TREND_WINDOW    = 120       # 120-day moving average for trend


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def _safe(info: dict, key: str, fallback=None):
    """Return info[key] if truthy, else fallback."""
    val = info.get(key)
    return val if val is not None else fallback


def _calc_mdd(series: pd.Series) -> float:
    """Maximum Drawdown (%) from a price series."""
    rolling_max = series.cummax()
    drawdown    = (series - rolling_max) / rolling_max
    return float(drawdown.min() * 100)


def _calc_position_size(current_price: float,
                        total_capital: float = TOTAL_CAPITAL,
                        max_loss_pct: float  = MAX_LOSS_PCT,
                        stop_loss_pct: float = STOP_LOSS_PCT) -> int:
    """
    Risk-based position sizing:
      max_loss   = total_capital × max_loss_pct     (e.g. $2,000)
      loss/share = current_price × stop_loss_pct    (e.g. $X × 10 %)
      qty        = floor(max_loss / loss_per_share)
    """
    if current_price <= 0:
        return 0
    loss_per_share = current_price * stop_loss_pct
    return math.floor((total_capital * max_loss_pct) / loss_per_share)


# ──────────────────────────────────────────────
#  CORE ANALYSIS
# ──────────────────────────────────────────────
def _analyze_ticker(ticker: str) -> dict | None:
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        # ── Fundamentals (safe extraction) ──────────────
        roe            = _safe(info, 'returnOnEquity',  0.0)
        debt_to_equity = _safe(info, 'debtToEquity',    999.0)
        trailing_pe    = _safe(info, 'trailingPE',      0.0)
        eps            = _safe(info, 'trailingEps',     0.0)

        # ── Price history (5 y for PER avg, 3 y for backtest / MAs) ──
        df_5y = stock.history(period="5y")
        if df_5y.empty or len(df_5y) < MA_TREND_WINDOW:
            print(f"[{ticker}] Insufficient price history – skipped.")
            return None

        # Keep last 3 y slice for backtest metrics
        df_3y         = df_5y.iloc[-756:]          # ≈ 3 trading years
        current_price = float(df_5y['Close'].iloc[-1])

        # Moving averages (computed on the full 5 y window)
        ma120 = df_5y['Close'].rolling(MA_TREND_WINDOW).mean().iloc[-1]
        ma200 = df_5y['Close'].rolling(200).mean().iloc[-1]

        # 5-Year average PER (approximation using current trailing EPS)
        avg_5y_pe = None
        current_pe = None
        if eps and eps > 0:
            hist_pe    = df_5y['Close'] / eps
            avg_5y_pe  = float(hist_pe.mean())
            current_pe = current_price / eps

        # ── Scoring (4 conditions) ───────────────────────
        score   = 0
        reasons = []

        # 1. Profitability: ROE > 10 %
        if roe > ROE_THRESHOLD:
            score += 1
            reasons.append(f"ROE {roe*100:.1f}% > 10%")

        # 2. Financial health: D/E < 100
        if 0 < debt_to_equity < DE_THRESHOLD:
            score += 1
            reasons.append(f"D/E {debt_to_equity:.1f} < 100")

        # 3. Valuation: current PER below 5-year average PER
        if current_pe and avg_5y_pe and current_pe > 0 and current_pe < avg_5y_pe:
            score += 1
            reasons.append(f"PER {current_pe:.1f} < 5Y Avg {avg_5y_pe:.1f}")

        # 4. Technical trend: price above MA120
        if pd.notna(ma120) and current_price > ma120:
            score += 1
            reasons.append(f"Price > MA120 ({ma120:.2f})")

        # ── Signal label ────────────────────────────────
        signal = {4: "★ Strong Buy",
                  3: "▲ Buy",
                  2: "◆ Hold"}.get(score, "▼ Watch")

        # ── Position sizing ──────────────────────────────
        rec_qty = _calc_position_size(current_price)

        # ── 3-Year backtest metrics ──────────────────────
        price_3y_ago       = float(df_3y['Close'].iloc[0])
        cumulative_return  = (current_price - price_3y_ago) / price_3y_ago * 100
        mdd                = _calc_mdd(df_3y['Close'])

        return {
            "Ticker":          ticker,
            "Signal":          signal,
            "Score":           f"{score}/4",
            "Current Price":   f"${current_price:,.2f}",
            "Rec. Qty":        rec_qty,
            "3Y Return (%)":   f"{cumulative_return:+.1f}%",
            "MDD (%)":         f"{mdd:.1f}%",
            # ── Detail columns ──
            "ROE":             f"{roe*100:.1f}%",
            "D/E Ratio":       f"{debt_to_equity:.1f}" if debt_to_equity < 999 else "N/A",
            "Trailing PE":     f"{trailing_pe:.1f}"    if trailing_pe else "N/A",
            "5Y Avg PE":       f"{avg_5y_pe:.1f}"      if avg_5y_pe   else "N/A",
            "MA120":           f"{ma120:.2f}"           if pd.notna(ma120) else "N/A",
            "MA200":           f"{ma200:.2f}"           if pd.notna(ma200) else "N/A",
            "Key Reasons":     " | ".join(reasons) if reasons else "—",
        }

    except Exception as exc:
        print(f"[{ticker}] Error: {exc}")
        return None


# ──────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────
def analyze_long_term_stocks(tickers: list[str],
                             total_capital: float = TOTAL_CAPITAL) -> pd.DataFrame:
    """
    Run long-term investment analysis on a list of tickers.

    Parameters
    ----------
    tickers        : e.g. ['AAPL', 'MSFT', 'GOOGL', 'NVDA']
    total_capital  : total portfolio in USD (default $100,000)

    Returns
    -------
    pd.DataFrame with summary + detail columns, sorted by score (desc).
    """
    global TOTAL_CAPITAL
    TOTAL_CAPITAL = total_capital   # propagate override

    rows = [r for ticker in tickers if (r := _analyze_ticker(ticker)) is not None]
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Sort by numeric score descending
    df["_score_num"] = df["Score"].str[0].astype(int)
    df = df.sort_values("_score_num", ascending=False).drop(columns="_score_num")
    df = df.reset_index(drop=True)

    return df


# ──────────────────────────────────────────────
#  DISPLAY HELPER
# ──────────────────────────────────────────────
def print_report(df: pd.DataFrame) -> None:
    if df.empty:
        print("No results.")
        return

    sep = "=" * 90

    print(f"\n{sep}")
    print("  LONG-TERM INVESTMENT ANALYSIS  |  "
          f"Capital: ${TOTAL_CAPITAL:,}  |  "
          f"Risk: {MAX_LOSS_PCT*100:.0f}% max loss / {STOP_LOSS_PCT*100:.0f}% stop-loss")
    print(sep)

    summary_cols = ["Ticker", "Signal", "Score", "Current Price",
                    "Rec. Qty", "3Y Return (%)", "MDD (%)"]
    print("\n── SUMMARY ──")
    print(df[summary_cols].to_string(index=False))

    print("\n── FUNDAMENTALS ──")
    fund_cols = ["Ticker", "ROE", "D/E Ratio", "Trailing PE", "5Y Avg PE",
                 "MA120", "MA200", "Key Reasons"]
    print(df[fund_cols].to_string(index=False))
    print(sep)

    print("\nNotes:")
    print("  • Rec. Qty  : shares where a 10% drop = 2% portfolio loss")
    print("  • 5Y Avg PE : approximated from 5-year price history ÷ current trailing EPS")
    print("  • MDD       : Maximum Drawdown over the last 3 years")
    print("  • Scores    : ROE>10% | D/E<100 | PER<5YAvg | Price>MA120\n")


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    pd.set_option("display.max_columns",  None)
    pd.set_option("display.width",        220)
    pd.set_option("display.max_colwidth", 70)

    WATCHLIST = ["AAPL", "MSFT", "GOOGL", "NVDA"]
    # WATCHLIST = ["005930.KS", "000660.KS"]  # Korean tickers

    result_df = analyze_long_term_stocks(WATCHLIST, total_capital=100_000)
    print_report(result_df)

    # Optional: export to CSV
    # result_df.to_csv("stock_analysis.csv", index=False)
