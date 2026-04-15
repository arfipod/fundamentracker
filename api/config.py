import operator

METRICS_MAP = {
    "pe": "trailingPE",
    "fpe": "forwardPE",
    "pb": "priceToBook",
    "evebitda": "enterpriseToEbitda",
    "roe": "returnOnEquity",
    "price": "currentPrice",
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
