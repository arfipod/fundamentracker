import operator

METRICS_MAP = {
    "pe": "trailingPE",
    "fpe": "forwardPE",
    "pb": "priceToBook",
    "evebitda": "enterpriseToEbitda",
    "roe": "returnOnEquity",
    "price": "currentPrice",
    "roic": "roic",  # Handled specially
    "dividendyield": "dividendYield",
    "payoutratio": "payoutRatio",
    "debttoequity": "debtToEquity",
    "profitmargins": "profitMargins",
    "operatingmargins": "operatingMargins",
}

OPERATORS_MAP = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "=": operator.eq,
    "!=": operator.ne,
}
