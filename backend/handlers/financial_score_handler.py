import logging


def get_financial_score_global(
    score_stmt_res: float,
    score_balance: float,
    score_cash_flow_growth: float,
    weights: dict
):
    """Esta funcion calcula el score financiero global, basado en el estado de resultados, balance general y flujo de caja"""

    logging.info(f"score_stmt_res: {score_stmt_res}")
    logging.info(f"score_balance: {score_balance}")
    logging.info(f"score_cash_flow_growth: {score_cash_flow_growth}")

    if "total" in weights["income"].keys():
        
        logging.info(f'income weight: {weights["income"]["total"]}')
        logging.info(f'balance weight: {weights["balance"]["total"]}')
        logging.info(f'cash_flow weight: {weights["cash_flow"]["total"]}')

        score_financial_final = (
            weights["income"]["total"]*score_stmt_res + 
            weights["balance"]["total"]*score_balance + 
            weights["cash_flow"]["total"]*score_cash_flow_growth
        )
    else:
        score_financial_final = (score_stmt_res + score_balance + score_cash_flow_growth)/3

    score_financial_final = round(score_financial_final, 2)
    logging.info(f"Score salud financiera final: {score_financial_final}")

    return score_financial_final
