import logging
from constants import Multiples
from utils.multiples import get_multiples


def process_multiples_price_historic(
    ticker: str,
    multiples_weights: dict
):
    """Esta funcion nos ayudara a realizar la valoración por multiplos de una compañia de interes.
    En especifico, se encarga de revisar los multiplos historicos de la acción.
    """
    # obtener los multiplos del ticker de interes
    hist_multiples_ticker = get_multiples(ticker=ticker)
    
    dict_score_precio_hist = {}
    dict_detail_multiples = {}
    for multiplo in Multiples.KPIS:
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
