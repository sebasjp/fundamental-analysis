class FetchData:
    url_income = "https://stockanalysis.com/stocks/{ticker}/financials/{suffix_url}"
    url_balance = "https://stockanalysis.com/stocks/{ticker}/financials/balance-sheet/{suffix_url}"
    url_cash_flow = "https://stockanalysis.com/stocks/{ticker}/financials/cash-flow-statement/{suffix_url}"
    

class IncomeKpis:
    ANNUAL: list = [
        'Revenue',
        'Gross Profit',
        'Operating Income',
        'Net Income'
    ]
    TTM: list = [
        "Revenue", 
        "Gross Profit", 
        "Net Income", 
        "Shares Outstanding (Basic)"
    ]


class BalanceKpis:
    ANNUAL: list = [
        'Cash & Equivalents',
        'Cash & Short-Term Investments',
        'Total Current Assets',
        'Total Current Liabilities',
        'Inventory',
        'Total Debt',
        'Total Assets'
    ]


class CashFlowKpis:
    ANNUAL: list = [
        'Operating Cash Flow', 
        'Free Cash Flow'
    ]
    TTM: list = [
        "Free Cash Flow"
    ]


class Multiples:
    KPIS: list = [
        "pe_ratio", 
        "ps_ratio", 
        "pgp_ratio", 
        "pfcf_ratio"
    ]