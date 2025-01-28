import logging
import pandas as pd
import numpy as np
from constants import Multiples
from utils.multiples import get_multiples


def process_compare_multiples_peers(
    ticker: str,
    hist_multiples_ticker: pd.DataFrame,
    peers: list,
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
            hist_multiples_peer = get_multiples(ticker=peer_ticker)
            logging.info(f"hist_multiples_peer.shape: {hist_multiples_peer.shape}")

            current_multiples_peer = hist_multiples_peer.iloc[-1, :].copy()
            multiples_peers[peer_ticker] = current_multiples_peer
        except Exception as e:
            logging.info(f"ERROR No se pudo extraer informacion del ticker: {peer_ticker}")

    # multiplos ticker interes + competencia
    compare_multiples = pd.DataFrame({ticker: current_multiples_ticker, **multiples_peers}).T

    # correccion de negativos en multiplos
    logging.info("Revisando si se deben corregir multiplos negativos")
    for ratio in Multiples.KPIS:
        compare_multiples[ratio] = np.where(compare_multiples[ratio]<0, np.nan, compare_multiples[ratio])

    logging.info("Calculando el score para cada multiplo de acuerdo al rank de las empresas")
    for ratio in Multiples.KPIS:
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