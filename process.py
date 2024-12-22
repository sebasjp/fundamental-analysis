import logging
import pandas as pd
import numpy as np
from dependencies import (
    get_financial_data,
    score_growth,
    score_stmt_margins_competitors,
    calculate_kpis_balance_general,
    score_balance_general,
    get_multiples
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_income(
    ticker: str, 
    kpis_cfg: dict,
    weights: dict,
    peers_cfg
):

    # estado de resultados
    data_type = "income"
    kpis = kpis_cfg[data_type]
    logging.info(f"Tipo de resultados: {data_type}")
    logging.info(f"KPI's analizar: {kpis}\n")

    income_stmt_complete, income_stmt = get_financial_data(ticker=ticker, data_type=data_type, kpis=kpis)
    logging.info(f"earnings date: {income_stmt.index.values}")

    # evaluar crecimiento de la empresa
    logging.info(f"Vamos a revisar que la empresa {ticker} se encuentre creciendo")
    score_stmt_res_growth, stmt_res_growth = score_growth(income_stmt)

    # Comparar margenes: estado de resultados vs la competencia
    response_margins = score_stmt_margins_competitors(
        ticker, 
        income_stmt,
        peers_cfg,
        kpis_cfg
    )
    # score total de los estados de resultados (income)
    score_stmt_res = (
        score_stmt_res_growth*weights["income"]["growth"] + 
        response_margins["score_margins_peers"]*weights["income"]["peers"]
    )

    # parsing response    
    response = {"income": {}}
    response["income"]["income_complete"] = income_stmt_complete
    response["income"]["income"] = income_stmt

    # resultados del crecimiento
    response["income"]["score_stmt_growth"] = score_stmt_res_growth
    response["income"]["detail_growth"] = stmt_res_growth

    # resultados de comparacion de margenes vs la competencia
    response["peers"] = response_margins["peers"]
    response["income"]["score_margins_peers"] = response_margins["score_margins_peers"]
    response["income"]["margin_peers"] = response_margins["margin_peers"]
    response["income"]["margin_ticker_interes"] = response_margins["margin_ticker_interes"]

    # score final
    response["income"]["score_final"] = score_stmt_res

    return response


def process_balance_general(
    ticker: str, 
    kpis: list,
    income_stmt_complete: pd.DataFrame
):
    """Balance General

    De aqui obtenemos:

    1. Razon corriente
    2. Razón corriente "acida"
    3. Deuda sobre los activos totales
    4. Numero de meses de operación con el dinero en caja
    """
    kpis_balance = calculate_kpis_balance_general(
        ticker=ticker, 
        income_stmt_complete=income_stmt_complete, 
        kpis=kpis
    )
    score_balance = score_balance_general(kpis_balance)

    response = {"balance": {}}
    response["balance"]["balance"] = kpis_balance
    response["balance"]["score_final"] = score_balance

    return response


def process_cash_flow(
    ticker: str,
    kpis: list
):
    data_type = "cash_flow"
    _, cash_flow = get_financial_data(
        ticker=ticker, 
        data_type=data_type,
        kpis=kpis
    )
    score_cash_flow_growth, cash_flow_growth = score_growth(cash_flow)

    response = {"cash_flow": {}}
    response["cash_flow"]["cash_flow"] = cash_flow
    response["cash_flow"]["detail_growth"] = cash_flow_growth
    response["cash_flow"]["score_final"] = score_cash_flow_growth

    return response


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


def process_multiples_price_historic(
    ticker: str,
    kpis_cfg: dict,
    multiples_used: list,
    multiples_weights: dict
):
    """Esta funcion nos ayudara a realizar la valoración por multiplos de una compañia de interes.
    En especifico, se encarga de revisar los multiplos historicos de la acción.
    """
    # obtener los multiplos del ticker de interes
    hist_multiples_ticker = get_multiples(ticker=ticker, kpis_cfg=kpis_cfg)
    
    dict_score_precio_hist = {}
    dict_detail_multiples = {}
    for multiplo in multiples_used:
        logging.info("=="*20)
        logging.info(multiplo)
        last_val = hist_multiples_ticker[multiplo].iloc[-1]

        max_hist = hist_multiples_ticker[multiplo].max()
        min_hist = hist_multiples_ticker[multiplo].min()

        score_multiplo = (max_hist-last_val)/(max_hist-min_hist)
        dict_score_precio_hist[multiplo] = score_multiplo

        logging.info(f"valor actual - last_val: {last_val}")
        logging.info(f"min_hist: {min_hist}, max_hist: {max_hist}")
        logging.info(f"score_multiplo: {score_multiplo}")
        dict_detail_multiples[multiplo] = {
            "current_value": last_val,
            "min_historic": min_hist,
            "max_historic": max_hist,
            "score_multiplo": score_multiplo
        }

    if isinstance(multiples_weights, dict):
        score_precio_hist = 10*sum([value*multiples_weights[x] for x, value in dict_score_precio_hist.items()])
    else:
        score_precio_hist = round( 10*sum(dict_score_precio_hist.values())/len(dict_score_precio_hist), 2 )

    logging.info(f"\n\nScore precio historico-> score_precio_hist: {score_precio_hist}")

    # response price_historic
    response = {}
    response["price"] = hist_multiples_ticker
    response["detail_multiples"] = dict_detail_multiples
    response["score_final"] = score_precio_hist

    return response


def process_compare_multiples_peers(
    ticker: str,
    hist_multiples_ticker: pd.DataFrame,
    peers: list,
    kpis_cfg: dict,
    multiples_used: list,
    multiples_weights: dict
):
    """Esta funcion compara los multiplos del ticker de interes con los peers o competidores"""
    
    # multiplos del ticker de interes segun el precio del ultimo dia
    current_multiples_ticker = hist_multiples_ticker.iloc[-1, :].copy()

    # multiplos de la competencia segun el precio del ultimo dia
    multiples_peers = {}
    for peer_ticker in peers:
        try:
            logging.info("=="*20)
            hist_multiples_peer = get_multiples(ticker=peer_ticker, kpis_cfg=kpis_cfg)
            logging.info(f"hist_multiples_peer.shape: {hist_multiples_peer.shape}")

            current_multiples_peer = hist_multiples_peer.iloc[-1, :].copy()
            multiples_peers[peer_ticker] = current_multiples_peer
        except Exception as e:
            logging.info(f"ERROR No se pudo extraer informacion del ticker: {peer_ticker}")

    # multiplos ticker interes + competencia
    compare_multiples = pd.DataFrame({ticker: current_multiples_ticker, **multiples_peers}).T

    # correccion de negativos en multiplos
    logging.info("Revisando si se deben corregir multiplos negativos")
    for ratio in multiples_used:
        compare_multiples[ratio] = np.where(compare_multiples[ratio]<0, np.nan, compare_multiples[ratio])

    logging.info("Calculando el score para cada multiplo de acuerdo al rank de las empresas")
    for ratio in multiples_used:
        total_not_null = compare_multiples[ratio].notnull().sum()
        compare_multiples[f"score_{ratio}"] = (compare_multiples[ratio].rank(ascending=False)-1)/(total_not_null-1)

    # se revisa si se usa pesos para consolidar los multiplos
    if isinstance(multiples_weights, dict):
        logging.info("Usando los pesos de los multiplos: multiples_weights...")
        score_multiples_peers = 10*(
            compare_multiples
            .filter(like="score_")
            .apply(lambda x: sum([w*x["score_"+wname] for wname, w in multiples_weights.items()]), axis=1)
        )
    else:
        score_multiples_peers = 10*compare_multiples.filter(like="score_").mean(axis=1)

    score_multiples_peers = score_multiples_peers.sort_values(ascending=False)

    response = {}
    response["detail_multiples"] = compare_multiples
    response["score_final"] = score_multiples_peers

    return response