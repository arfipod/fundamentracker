from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    yf_key: str | None
    unit: str
    multiplier: float
    category: str
    label: str
    description: str
    higher_is_better: bool | None
    supported_for_alerts: bool
    supported_for_history: bool
    source_kind: str = "info"
    period: str | None = None
    formula: str | None = None


def m(
    key: str,
    label: str,
    category: str,
    description: str,
    *,
    yf_key: str | None = None,
    unit: str = "ratio",
    multiplier: float = 1.0,
    higher_is_better: bool | None = None,
    history: bool = False,
    alerts: bool = True,
    source_kind: str = "info",
    period: str | None = None,
    formula: str | None = None,
) -> MetricDefinition:
    return MetricDefinition(
        key=key,
        yf_key=yf_key,
        unit=unit,
        multiplier=multiplier,
        category=category,
        label=label,
        description=description,
        higher_is_better=higher_is_better,
        supported_for_alerts=alerts,
        supported_for_history=history,
        source_kind=source_kind,
        period=period,
        formula=formula,
    )


METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    'price': m('price', 'Price', 'Price & Size', 'Latest regular-market price.', yf_key='currentPrice', unit='currency', history=True, source_kind='fast_info'),
    'market_cap': m('market_cap', 'Market Capitalization', 'Price & Size', 'Equity market value based on current price and shares outstanding.', yf_key='marketCap', unit='currency', history=True, source_kind='valuation'),
    'enterprise_value': m('enterprise_value', 'Enterprise Value', 'Price & Size', 'Market capitalization plus debt and lease-like financing, less cash when available.', yf_key='enterpriseValue', unit='currency', history=True, source_kind='valuation'),
    'pe': m('pe', 'Trailing P/E', 'Valuation', 'Price divided by trailing diluted earnings per share.', yf_key='trailingPE', higher_is_better=False, history=True, source_kind='valuation'),
    'fpe': m('fpe', 'Forward P/E', 'Valuation', 'Price divided by consensus forward earnings per share.', yf_key='forwardPE', higher_is_better=False, history=True, source_kind='valuation'),
    'normalized_pe': m('normalized_pe', 'Normalized P/E', 'Valuation', "Price divided by Yahoo's normalized diluted EPS. Review the GAAP-normalized gap before relying on it.", higher_is_better=False, source_kind='statement', period='TTM', formula='price / normalized diluted EPS'),
    'peg': m('peg', 'PEG Ratio (5Y Expected)', 'Valuation', "P/E relative to Yahoo's expected five-year earnings growth.", yf_key='trailingPegRatio', higher_is_better=False, history=True, source_kind='valuation'),
    'ps': m('ps', 'Price / Sales', 'Valuation', 'Market capitalization divided by trailing revenue.', yf_key='priceToSalesTrailing12Months', higher_is_better=False, history=True, source_kind='valuation'),
    'pb': m('pb', 'Price / Book', 'Valuation', 'Market price divided by book value per share.', yf_key='priceToBook', higher_is_better=False, history=True, source_kind='valuation'),
    'ev_revenue': m('ev_revenue', 'EV / Revenue', 'Valuation', 'Enterprise value divided by trailing revenue.', yf_key='enterpriseToRevenue', higher_is_better=False, history=True, source_kind='valuation'),
    'evebitda': m('evebitda', 'EV / EBITDA', 'Valuation', 'Enterprise value divided by trailing EBITDA.', yf_key='enterpriseToEbitda', higher_is_better=False, history=True, source_kind='valuation'),
    'ev_to_ebit_ttm': m('ev_to_ebit_ttm', 'EV / EBIT (TTM)', 'Valuation', 'Enterprise value divided by trailing EBIT; includes the economic effect of depreciation.', higher_is_better=False, source_kind='statement', period='TTM', formula='enterprise value / EBIT'),
    'price_to_fcf_ttm': m('price_to_fcf_ttm', 'Price / Free Cash Flow (TTM)', 'Valuation', 'Market capitalization divided by trailing free cash flow. Not reported for non-positive FCF.', higher_is_better=False, source_kind='statement', period='TTM', formula='market cap / free cash flow'),
    'fcf_yield_ttm': m('fcf_yield_ttm', 'Free Cash Flow Yield (TTM)', 'Valuation', 'Trailing free cash flow as a percentage of market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM', formula='free cash flow / market cap'),
    'earnings_yield_ttm': m('earnings_yield_ttm', 'Earnings Yield (TTM)', 'Valuation', 'Trailing net income attributable to common shareholders as a percentage of market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM', formula='net income / market cap'),
    'owner_earnings_yield_ttm': m('owner_earnings_yield_ttm', 'Owner Earnings Yield after SBC (TTM)', 'Valuation', 'Conservative owner-earnings proxy: trailing FCF less stock-based compensation, divided by market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM', formula='(free cash flow - stock based compensation) / market cap'),
    'pe_discount_to_median_5y': m('pe_discount_to_median_5y', 'P/E Discount to 5Y Median', 'Valuation', 'Current trailing P/E relative to the median of available quarterly observations over five years.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='valuation_context', period='5Y', formula='current P/E / 5Y median P/E - 1'),
    'pe_percentile_5y': m('pe_percentile_5y', 'P/E Percentile (5Y)', 'Valuation', 'Percentile rank of current trailing P/E within available five-year observations; lower is cheaper versus history.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='valuation_context', period='5Y'),
    'evebitda_discount_to_median_5y': m('evebitda_discount_to_median_5y', 'EV / EBITDA Discount to 5Y Median', 'Valuation', 'Current EV/EBITDA relative to the median of available quarterly observations over five years.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='valuation_context', period='5Y', formula='current EV/EBITDA / 5Y median EV/EBITDA - 1'),
    'evebitda_percentile_5y': m('evebitda_percentile_5y', 'EV / EBITDA Percentile (5Y)', 'Valuation', 'Percentile rank of current EV/EBITDA within available five-year observations.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='valuation_context', period='5Y'),
    'roe': m('roe', 'Return on Equity', 'Profitability', 'Trailing net income divided by average shareholder equity.', yf_key='returnOnEquity', unit='percent', multiplier=100.0, higher_is_better=True, history=True, source_kind='statement', period='TTM'),
    'roic': m('roic', 'Return on Invested Capital', 'Profitability', 'Trailing NOPAT divided by average invested capital, using reported invested capital when available.', unit='percent', multiplier=100.0, higher_is_better=True, history=True, source_kind='statement', period='TTM'),
    'profitmargins': m('profitmargins', 'Net Profit Margin', 'Profitability', 'Trailing net income divided by trailing revenue.', yf_key='profitMargins', unit='percent', multiplier=100.0, higher_is_better=True, history=True, source_kind='statement', period='TTM'),
    'operatingmargins': m('operatingmargins', 'Operating Margin', 'Profitability', 'Trailing operating income divided by trailing revenue.', yf_key='operatingMargins', unit='percent', multiplier=100.0, higher_is_better=True, history=True, source_kind='statement', period='TTM'),
    'gross_margin_ttm': m('gross_margin_ttm', 'Gross Margin (TTM)', 'Profitability', 'Trailing gross profit divided by trailing revenue.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM'),
    'fcf_margin_ttm': m('fcf_margin_ttm', 'Free Cash Flow Margin (TTM)', 'Profitability', 'Trailing free cash flow divided by trailing revenue.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM'),
    'cfo_to_net_income_ttm': m('cfo_to_net_income_ttm', 'CFO / Net Income (TTM)', 'Profitability', 'Trailing operating cash flow divided by trailing net income; a cash-conversion indicator.', higher_is_better=True, source_kind='statement', period='TTM'),
    'fcf_to_net_income_ttm': m('fcf_to_net_income_ttm', 'FCF / Net Income (TTM)', 'Profitability', 'Trailing free cash flow divided by trailing net income.', higher_is_better=True, source_kind='statement', period='TTM'),
    'interest_coverage_ttm': m('interest_coverage_ttm', 'Interest Coverage (TTM)', 'Profitability', 'Trailing EBIT divided by absolute interest expense.', higher_is_better=True, source_kind='statement', period='TTM'),
    'normalized_eps_gap': m('normalized_eps_gap', 'Normalized vs GAAP EPS Gap', 'Profitability', 'Yahoo normalized diluted EPS relative to GAAP diluted EPS. Large gaps require review of unusual items.', unit='percent', multiplier=100.0, source_kind='statement', period='TTM', formula='normalized diluted EPS / diluted EPS - 1'),
    'capex_to_revenue_ttm': m('capex_to_revenue_ttm', 'Capex / Revenue (TTM)', 'Reinvestment & Dilution', 'Absolute trailing capital expenditure divided by trailing revenue.', unit='percent', multiplier=100.0, source_kind='statement', period='TTM'),
    'sbc_to_revenue_ttm': m('sbc_to_revenue_ttm', 'SBC / Revenue (TTM)', 'Reinvestment & Dilution', 'Trailing stock-based compensation divided by trailing revenue.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='statement', period='TTM'),
    'sbc_to_fcf_ttm': m('sbc_to_fcf_ttm', 'SBC / Free Cash Flow (TTM)', 'Reinvestment & Dilution', 'Trailing stock-based compensation divided by positive trailing free cash flow.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='statement', period='TTM'),
    'rd_to_revenue_ttm': m('rd_to_revenue_ttm', 'R&D / Revenue (TTM)', 'Reinvestment & Dilution', 'Trailing research and development expense divided by trailing revenue.', unit='percent', multiplier=100.0, source_kind='statement', period='TTM'),
    'diluted_share_growth_yoy': m('diluted_share_growth_yoy', 'Diluted Share Growth (YoY)', 'Reinvestment & Dilution', 'Change in diluted average shares between the latest two reported annual periods; positive values indicate dilution.', unit='percent', multiplier=100.0, higher_is_better=False, source_kind='statement', period='FY YoY'),
    'debttoequity': m('debttoequity', 'Debt / Equity', 'Leverage', "Total debt as a percentage of shareholder equity, matching Yahoo's display convention.", yf_key='debtToEquity', unit='percent', higher_is_better=False, history=True),
    'net_debt_to_ebitda_ttm': m('net_debt_to_ebitda_ttm', 'Net Debt / EBITDA (TTM)', 'Leverage', 'Debt less cash divided by trailing EBITDA. Negative values indicate net cash.', higher_is_better=False, source_kind='statement', period='TTM'),
    'net_cash_to_market_cap': m('net_cash_to_market_cap', 'Net Cash / Market Cap', 'Leverage', 'Cash and short-term investments less debt, divided by market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement'),
    'current_ratio': m('current_ratio', 'Current Ratio', 'Leverage', 'Current assets divided by current liabilities.', yf_key='currentRatio', higher_is_better=True),
    'quick_ratio': m('quick_ratio', 'Quick Ratio', 'Leverage', 'Liquid current assets divided by current liabilities.', yf_key='quickRatio', higher_is_better=True),
    'revenue_growth_yoy': m('revenue_growth_yoy', 'Revenue Growth (YoY)', 'Growth & Revisions', 'Latest available year-over-year revenue growth; Yahoo current data is preferred with annual-statement fallback.', yf_key='revenueGrowth', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='growth'),
    'operating_income_growth_yoy': m('operating_income_growth_yoy', 'Operating Income Growth (YoY)', 'Growth & Revisions', 'Growth between the latest two reported annual operating-income periods.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='FY YoY'),
    'diluted_eps_growth_yoy': m('diluted_eps_growth_yoy', 'Diluted EPS Growth (YoY)', 'Growth & Revisions', 'Latest available year-over-year diluted EPS growth with annual-statement fallback.', yf_key='earningsGrowth', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='growth'),
    'cfo_growth_yoy': m('cfo_growth_yoy', 'Operating Cash Flow Growth (YoY)', 'Growth & Revisions', 'Growth between the latest two reported annual operating-cash-flow periods.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='FY YoY'),
    'fcf_growth_yoy': m('fcf_growth_yoy', 'Free Cash Flow Growth (YoY)', 'Growth & Revisions', 'Growth between the latest two reported annual free-cash-flow periods.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='FY YoY'),
    'gross_margin_change_yoy': m('gross_margin_change_yoy', 'Gross Margin Change (YoY)', 'Growth & Revisions', 'Percentage-point change in gross margin between the latest two annual periods.', unit='percentage_points', multiplier=100.0, higher_is_better=True, source_kind='statement', period='FY YoY'),
    'operating_margin_change_yoy': m('operating_margin_change_yoy', 'Operating Margin Change (YoY)', 'Growth & Revisions', 'Percentage-point change in operating margin between the latest two annual periods.', unit='percentage_points', multiplier=100.0, higher_is_better=True, source_kind='statement', period='FY YoY'),
    'eps_revision_90d': m('eps_revision_90d', 'Forward EPS Revision (90D)', 'Growth & Revisions', 'Change in the preferred forward EPS estimate versus 90 days ago, using +1Y then current-year estimates when available.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='analyst', period='90D'),
    'eps_revision_balance': m('eps_revision_balance', 'EPS Revision Balance (30D)', 'Growth & Revisions', 'Upward minus downward analyst EPS revisions over the latest available 30-day window.', unit='count', higher_is_better=True, source_kind='analyst', period='30D'),
    'dividendyield': m('dividendyield', 'Dividend Yield', 'Shareholder Return', 'Indicated annual dividend divided by current price.', yf_key='dividendYield', unit='percent', multiplier=100.0, higher_is_better=True),
    'payoutratio': m('payoutratio', 'Payout Ratio', 'Shareholder Return', 'Percentage of earnings distributed as dividends.', yf_key='payoutRatio', unit='percent', multiplier=100.0),
    'buyback_yield_ttm': m('buyback_yield_ttm', 'Gross Buyback Yield (TTM)', 'Shareholder Return', 'Gross trailing share repurchases divided by market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM'),
    'net_buyback_yield_ttm': m('net_buyback_yield_ttm', 'Net Buyback Yield (TTM)', 'Shareholder Return', 'Trailing share repurchases less cash issuance of shares, divided by market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM'),
    'shareholder_yield_ttm': m('shareholder_yield_ttm', 'Shareholder Yield (TTM)', 'Shareholder Return', 'Net buybacks plus cash dividends divided by market capitalization.', unit='percent', multiplier=100.0, higher_is_better=True, source_kind='statement', period='TTM'),
}


METRICS_MAP = {key: definition.yf_key for key, definition in METRIC_DEFINITIONS.items()}


def get_metric_catalog() -> list[dict[str, Any]]:
    catalog = [asdict(definition) for definition in METRIC_DEFINITIONS.values()]
    return sorted(catalog, key=lambda item: (item["category"], item["label"]))


def get_metric_definition(metric: str) -> MetricDefinition:
    return METRIC_DEFINITIONS[metric.lower()]


def is_supported_metric(metric: str) -> bool:
    return metric.lower() in METRIC_DEFINITIONS
