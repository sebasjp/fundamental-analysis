import re
import logging
import pandas as pd
from finvizfinance.quote import finvizfinance
from constants import IncomeKpis
from utils.growth import score_growth
from utils.fetch_data import get_financial_data


def get_margins_ttm(inc_stmt: pd.DataFrame):
  """Esta función calcula los margenes de los estados de resultados.
  Se calcula a partir de los resultados de los ultimos doce meses (ttm)
  """
  per_compare = inc_stmt.iloc[0, :]
  margins = {
    "Gross M": per_compare["Gross Profit"] / per_compare["Revenue"],
    "Oper M": per_compare["Operating Income"] / per_compare["Revenue"],
    "Profit M": per_compare["Net Income"] / per_compare["Revenue"],
  }
  return margins


def get_competitors_tickers(ticker: str, n_competitors: int):
  """Obtiene los tickers de los competidores asociados a un ticker dado,
  desde la pagina de finviz.com"""

  logging.info("Identificando competidores usando finviz...")

  # Obtener tickers de la competencia
  # Ticker de interes
  stock = finvizfinance(ticker)

  # Obtencion de los competidores segun FinViz
  # basado en la estructura html de la pagina
  attrs = {
    "class": "tab-link",
    "href": re.compile("^screener")
  }
  peers = [
    x for x in stock.soup.findAll("a", attrs)
    if "Peers" in x
  ][0]
  peers = peers.get("href").split("=")[1].split(",")

  # primeros n competidores
  peers = peers[:n_competitors]

  logging.info(f"Competidores identificados: {peers}")
  
  return peers


def get_margins_peers(peers: list, data_type: str, kpis: list):
  """Esta funcion calcula los margenes de los estados de resultados para una lista de tickers,
    que son los competidores del ticker analizado"""

  logging.info("Calculando margenes de la competencia...")
  peers_margin = {}
  for tick_peer in peers:
    try:
      _, income_stmt_peer = get_financial_data(tick_peer, data_type, kpis)
      peers_margin[tick_peer] = get_margins_ttm(income_stmt_peer)
    except Exception as e:
      logging.warning(f"Error ticker: {tick_peer} - {e}")

  return peers_margin


def score_stmt_margins_competitors(
    ticker: str, 
    income_stmt: pd.DataFrame,
    peers_cfg: dict
  ):
  """Esta función calcula el score de los margenes del estado de resultados
  del ticker de interes vs los competidores.
  El score es la proporcion de indicadores (multiplicado por 10) en los que el ticker de interes
  supera en margenes a los competidores. Todos los indicadores-competidores tienen el mismo peso.

  Arguments:
  ----------
  ticker (str): Ticker de la empresa que se desea analizar.
  income_stmt (pd.DataFrame): Indicadores analizados en el estado de resultados de la empresa de interes.
  n_competitors (int): Cantidad máxima de competidores que se van a extraer para comparar

  Return:
  -------
  score_margins_peers (float): score de 0 a 10
  """
  logging.info(f"Calculando los margenes de la empresa: {ticker}")
  margin_interes = get_margins_ttm(income_stmt)

  weighted = False
  if peers_cfg["custom"] is None:
    # Definiendo los competidores
    n_competitors = peers_cfg["n_competitors"]
    peers = get_competitors_tickers(ticker, n_competitors)
  elif isinstance(peers_cfg["custom"], list):
    peers = peers_cfg["custom"]
  elif isinstance(peers_cfg["custom"], dict):
    peers_dict = peers_cfg["custom"]
    peers = list(peers_dict.keys())
    weighted = True

  logging.info(f"peers: {peers}")
  
  # Calculando los margenes de los competidores
  margin_peers = get_margins_peers(
    peers=peers,
    data_type="income",
    kpis=IncomeKpis.ANNUAL
  )
  # se calculara el score de comparacion de margenes
  result_peers = {}
  for peer_ticker, peer_margin in margin_peers.items():
    beat_peer = []
    for kpi in peer_margin:
      if margin_interes[kpi]>peer_margin[kpi]:
        beat_peer.append(1)
      else:
        beat_peer.append(0)
    
    if weighted:
      w = peers_dict[peer_ticker]["weight"]
    else:
      w = 1/len(margin_peers)
    
    logging.info(f"peer_ticker: {peer_ticker} - weight: {w}")
    result_peers[peer_ticker] = w * sum(beat_peer)/len(beat_peer)

  score_margins_peers = 10*sum(result_peers.values())
  logging.info("=="*20)
  logging.info(f"Aporte al score, ticker vs cada competidor - result_peer: {result_peers}")
  logging.info(f"Score comparación vs competencia - score_margins_peers: {score_margins_peers}")

  response = {
    "peers": peers, 
    "margin_ticker_interes": margin_interes,
    "margin_peers": margin_peers, 
    "score_margins_peers": score_margins_peers,
  }

  return response


def process_income(
    ticker: str, 
    weights: dict,
    peers_cfg
):

    # estado de resultados
    data_type = "income"
    logging.info(f"Tipo de resultados: {data_type}")
    logging.info(f"KPI's analizar: {IncomeKpis.ANNUAL}\n")

    income_stmt_complete, income_stmt = get_financial_data(ticker=ticker, data_type=data_type, kpis=IncomeKpis.ANNUAL)
    logging.info(f"earnings date: {income_stmt.index.values}")

    # evaluar crecimiento de la empresa
    logging.info(f"Vamos a revisar que la empresa {ticker} se encuentre creciendo")
    score_stmt_res_growth, stmt_res_growth = score_growth(income_stmt)

    # Comparar margenes: estado de resultados vs la competencia
    response_margins = score_stmt_margins_competitors(
        ticker, 
        income_stmt,
        peers_cfg
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


