from handlers.income_handler import process_income
from handlers.balance_handler import process_balance_general
from handlers.cash_flow_handler import process_cash_flow
from handlers.financial_score_handler import get_financial_score_global
from handlers.multiples_historic_handlers import process_multiples_price_historic
from handlers.multiples_peers_handlers import process_compare_multiples_peers


def execute_process(
    ticker: str,
    financial_weights: dict,
    peers: dict,
    multiples_weights: dict
):

    # response structure
    response = {
        "financials": {},
        "price_historic": {},
        "price_competitors": {}
    }

    ### Analisis de los estados de resultados de la empresa
    results_process_income = process_income(
        ticker, 
        financial_weights,
        peers
    )
    response["financials"]["income"] = results_process_income["income"]
    response["peers"] = results_process_income["peers"]

    ### Balance General
    # De aqui obtenemos:
    # 1. Razon corriente
    # 2. Razón corriente "acida"
    # 3. Deuda sobre los activos totales
    # 4. Numero de meses de operación con el dinero en caja
    response["financials"]["balance"] = process_balance_general(
        ticker=ticker, 
        income_stmt_complete=response["financials"]["income"]["income_complete"]
    )

    ### Flujo de caja creciente
    response["financials"]["cash_flow"] = process_cash_flow(ticker=ticker)

    ### Score salud financiera global
    response["financials"]["score_final"] = get_financial_score_global(
        score_stmt_res=response["financials"]["income"]["score_final"],
        score_balance=response["financials"]["balance"]["score_final"],
        score_cash_flow_growth=response["financials"]["cash_flow"]["score_final"],
        weights=financial_weights
    )
    # ---
    ### Análisis del precio historico
    response["price_historic"] = process_multiples_price_historic(
        ticker=ticker,
        multiples_weights=multiples_weights
    )

    # Comparando el precio con la competencia
    response["price_competitors"] = process_compare_multiples_peers(
        ticker=ticker,
        hist_multiples_ticker=response["price_historic"]["price"],
        peers=response["peers"],
        multiples_weights=multiples_weights
    )

    # response["financials"]["income"]["income_complete"] = response["financials"]["income"]["income_complete"].to_dict()
    response["financials"]["income"]["income"] = response["financials"]["income"]["income"].to_dict()
    # response["financials"]["income"]["detail_growth"] = response["financials"]["income"]["detail_growth"].to_dict()

    # response["financials"]["balance"]["balance"] = response["financials"]["balance"]["balance"].to_dict()

    response["financials"]["cash_flow"]["cash_flow"] = response["financials"]["cash_flow"]["cash_flow"].to_dict()
    # response["financials"]["cash_flow"]["detail_growth"] = response["financials"]["cash_flow"]["detail_growth"].to_dict()

    # response["price_historic"]["price"] = response["price_historic"]["price"].to_dict()
    response["price_competitors"]["detail_multiples"] = response["price_competitors"]["detail_multiples"].to_dict()
    response["price_competitors"]["score_final"] = response["price_competitors"]["score_final"].to_dict()

    return response