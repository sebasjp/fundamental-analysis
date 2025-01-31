from constants import CashFlowKpis
from utils.growth import score_growth
from utils.fetch_data import get_financial_data


def process_cash_flow(ticker: str):
    
    data_type = "cash_flow"
    _, cash_flow = get_financial_data(
        ticker=ticker, 
        data_type=data_type,
        kpis=CashFlowKpis.ANNUAL
    )
    score_cash_flow_growth, cash_flow_growth = score_growth(cash_flow)

    response = {
        "cash_flow": cash_flow,
        "detail_growth": cash_flow_growth,
        "score_final": score_cash_flow_growth
    }
    
    return response
