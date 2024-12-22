import re
import requests
import yaml
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from finvizfinance.quote import finvizfinance
import yfinance as yf


def load_yaml_from_local(file_path: str):
  """
  Load a rule from a YAML file.
  """
  with open(file_path) as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

  logging.info(f"Se cargó la configuración en: {file_path}")
  return data


def request_historic_financial_data(data_type: str, ticker: str, is_ttm: bool=False):
  """Funcion para traerse la informacion financiera de la accion.
  Información traida desde stockanalysis."""
  # Se intento traer la información desde yahoofinance 
  # pero trae menos historia que stockanalysis
  # ademas yahoofinance no coincide con finchat, stockanalysis si

  if is_ttm:
    suffix_url = "?p=trailing"
  else:
    suffix_url = ""

  # Nos traemos los estados de resultados
  if data_type=="income":
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/{suffix_url}"
  elif data_type=="cash_flow":
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/cash-flow-statement/{suffix_url}"
  elif data_type=="balance_sheet":
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/balance-sheet/{suffix_url}"

  response = requests.get(url)
  if response.status_code==200:
    logging.info(f"Request successful to url: {url}")

  return response.content


def parse_historic_financial_data(html_data, kpis: list):
  """Funcion para parsear o formatear la info financiera TTM"""

  hist_fin_complete = pd.read_html(html_data)[0]
  hist_fin_complete.columns = [x[1][8:].strip() for x in hist_fin_complete.columns]
  
  # si la rentabilidad bruta no está, ponemos las mismas ventas
  if ("Gross Profit" in kpis)&("Gross Profit" not in hist_fin_complete.iloc[:,0].values):
    # print(hist_fin_complete.iloc[:,0].values)
    row_rev = hist_fin_complete[hist_fin_complete.iloc[:,0]=="Revenue"].copy()
    row_rev.iloc[:,0] = "Gross Profit"
    hist_fin_complete = pd.concat([hist_fin_complete, row_rev])
    logging.info("No se encontro el kpi Gross Profit... ajustado al Revenue")

  if "Inventory" in kpis:
    # si no encontramos Inventory en la tabla (Ej: empresas de IT)
    if hist_fin_complete.iloc[:,0].isin(["Inventory"]).sum()==0:
      kpis = [x for x in kpis if "Inventory"!=x]
      logging.info("'Inventory' no se encuentra en la tabla extraida, removido de kpis")

  # a partir de la tabla completa, nos quedamos con los indicadores
  # que nos interesan, por ejemplo: ventas total, utilidad bruta, etc..
  hist_fin = hist_fin_complete[hist_fin_complete.iloc[:,0].isin(kpis)].copy().T
  hist_fin.columns = hist_fin.iloc[0, :]
  hist_fin = hist_fin.iloc[1:,:]
  hist_fin = hist_fin.reset_index()
  hist_fin = hist_fin.rename(columns={"index": "period"})
  hist_fin = hist_fin[hist_fin[kpis[0]]!="Upgrade"]
  hist_fin["earning_date"] = pd.to_datetime(
    hist_fin["period"], format="%b %d, %Y"
  ).dt.strftime("%Y-%m-%d")
  hist_fin = hist_fin.set_index(["earning_date"])
  hist_fin = hist_fin.drop(columns=["period"])

  # casteo de los indicadores porque vienen tipo object
  for x in kpis:
    try:
      if (hist_fin[x]=="-").any():
        logging.warning(f"Caracteres especiales encontrados en kpi: {x}. Cantidad de registros con '-': {(hist_fin[x]=='-').sum()}")
        hist_fin = hist_fin[hist_fin[x]!="-"]
        logging.warning(f"'-> Cantidad de registros despues de remover '-': {hist_fin.shape}")
      hist_fin[x] = hist_fin[x].astype(float)
    except Exception as e:
      logging.warning(f"No se proceso el kpi: {x}. Exception error: {e}")

  hist_fin.columns.name=None

  return hist_fin_complete, hist_fin


def get_financial_data(ticker: str, data_type: str, kpis: list, is_ttm: bool=False):
  """Esta funcion extrae los datos financeros de estado de resultados
  y flujo de caja para un ticker dado.
  
  Arguments
  ---------
  ticker (str): ticker de la empresa que se desea analizar
  data_type (str): tipo de datos que se desea extraer, puede ser income o cash_flow
  """
  # extraer de la pagina stockanalysis la tabla ttm historico
  response_data = request_historic_financial_data(data_type=data_type, ticker=ticker, is_ttm=is_ttm)
  data_complete, data = parse_historic_financial_data(html_data=response_data, kpis=kpis)
  
  return data_complete, data


def score_growth(hist_kpis: pd.DataFrame) -> float:
  """
  Esta funcion construye la proporcion de periodos que ha crecido un kpi para una empresa.
  Esta proporcion la multiplica por 10 para obtener un score de 0 a 10.
  Ejemplo: compara las ventas totales de cada año vs el año anterior correspondiente, calculando
  la proporcion de años que se ha presentado crecimiento

  Arguments
  ---------
  hist_kpis (pd.DataFrame): dataframe periodos x kpi

  Return
  ------
  score (float): score de 0 a 10
  """
  logging.info("=="*20)
  logging.info("Analizando crecimiento de la compañía...")
  # validamos que tengamos al menos tres años de analisis
  if hist_kpis.shape[0]>3:
    # indicador a comparar la empresa con su historia
    crece_df = []
    results = []
    for kpi in hist_kpis.columns:
      # Numero de periodos que el kpi ha crecido
      crece_df.append(hist_kpis[kpi] > hist_kpis[kpi].shift(-1))
      num_per_growth = sum(hist_kpis[kpi] > hist_kpis[kpi].shift(-1))

      # proporcion de periodos que el kpi ha crecido
      # restamos 1 al denominador porque el primer periodo
      # no lo podemos comparar con un periodo anterior
      prop_per_growth = num_per_growth / (hist_kpis.shape[0]-1)

      # concatenamos para cada kpi, la proporcion de periodos que crecio
      results.append(prop_per_growth)

      logging.info(f"kpi: {kpi} analizado. Proporcion de periodos de crecimiento: {prop_per_growth}")

    # sacamos score del 0 al 10, dandole el mismo peso a cada kpi
    score = 10*sum(results)/len(results)
    crece_df = pd.concat(crece_df, axis=1)
    crece_df.columns = crece_df.columns + "_crece"
    crece_df.iloc[-1, :] = None
  else:
    score = None
    crece_df = None
    logging.warning("Sin información suficiente para analizar la empresa")

  logging.info("=="*20)
  logging.info(f"Score de crecimiento: {score}")

  return score, crece_df


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
    peers_cfg: dict,
    kpis_cfg: dict
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
    kpis=kpis_cfg["income"]
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


def calculate_kpis_balance_general(
    ticker: str,
    income_stmt_complete: pd.DataFrame,
    kpis: list
):
  """Esta función calcula los indicadores del balance general, como:
  1. Razon corriente
  2. Razón corriente "acida"
  3. Deuda sobre los activos totales
  4. Numero de meses de operación con el dinero en caja
  """
  balance_complete, balance = get_financial_data(ticker=ticker, data_type="balance_sheet", kpis=kpis)

  # Dinero en caja que cubra mas de tres meses de operación
  # Total cash and short term investments > selling general & admin expenses (gastos totales de operacion)
  income_stmt_complete = income_stmt_complete.set_index(["nding"])
  try:
    operation_expenses_12month = income_stmt_complete.iloc[:,0]["Selling, General & Admin"]
  except Exception as e:
    logging.warning(f"'Selling, General & Admin' no existe en el dataframe 'income_stmt_complete' - {e}")
    operation_expenses_12month = income_stmt_complete.iloc[:,0]["Total Operating Expenses"]
    logging.warning(f" '-> Usando 'Total Operating Expenses': {operation_expenses_12month} para identificar los gastos de operacion a 12 meses")

  operation_expenses_month = float(operation_expenses_12month) / 12
  logging.info(f"Gastos operativos mensuales - operation_expenses_month: {round(operation_expenses_month)}")

  # dinero en caja
  try:
    cash = balance["Cash & Short-Term Investments"].iloc[0]    
  except Exception as e:
    logging.warning(f"'Cash & Short-Term Investments' no existe en el dataframe 'balance' - {e}")
    cash = balance["Cash & Equivalents"].iloc[0]
    logging.warning(f" '-> Usando 'Cash & Equivalents' para identificar el dinero en caja")
    
  logging.info(f"Dinero en caja - cash: {cash}")

  # meses de operacion que se cubren con la caja
  months_operation = round(cash / operation_expenses_month, 2)
  logging.info(f"Meses de operación con el dinero en caja - months_operation: {months_operation}")

  # activos corrientes
  try:
    current_assets = balance["Total Current Assets"].iloc[0]
  except Exception as e:
    logging.warning(f"'Total Current Assets' no existe en el dataframe 'balance' - {e}")
    logging.warning(f" '-> Realizando calculo manual de current_assets")
    ixtotalassets = np.where(balance_complete["nding"]=="Total Assets")[0][0]
    total_assets = float(balance_complete.iloc[ixtotalassets, 1])
    data_assets = balance_complete.iloc[:ixtotalassets, :]

    # quitarle el long term al total para calcular el current
    non_current_item_names = data_assets[data_assets["nding"].str.contains("Long")]["nding"].to_list()
    non_current_item_names += ["Goodwill", "Property, Plant & Equipment", "Other Intangible Assets"]
    non_current_item_names = np.unique(non_current_item_names)
    non_current_item_names = list(non_current_item_names)
    non_current_value = sum([
        float(x) for x in data_assets[data_assets["nding"].isin(non_current_item_names)].iloc[:,1]
    ])
    current_assets = total_assets-non_current_value

  logging.info(f"Activos corrientes - current_assets: {current_assets}")

  # pasivos corrientes
  try:
    current_liabili = balance["Total Current Liabilities"].iloc[0]
  except Exception as e:
    logging.warning(f"'Total Current Liabilities' no existe en el dataframe 'balance' - {e}")
    logging.warning(f" '-> Realizando calculo manual de current_liabili")
    ixtotalliabilities = np.where(balance_complete["nding"]=="Total Liabilities")[0][0]
    total_liabilities = float(balance_complete.iloc[ixtotalliabilities, 1])
    data_liabilities = balance_complete.iloc[(ixtotalassets+1):ixtotalliabilities, :]

    # quitarle el long term al total para calcular el current
    non_current_item_names = data_liabilities[data_liabilities["nding"].str.contains("Long")]["nding"].to_list()
    non_current_item_names = [x for x in non_current_item_names if "Current" not in x]
    non_current_value = sum([
        float(x) for x in data_liabilities[data_liabilities["nding"].isin(non_current_item_names)].iloc[:,1] if x!="-"
    ])
    current_liabili = total_liabilities-non_current_value    

  logging.info(f"Pasivos corrientes - current_liabili: {current_liabili}")

  # current ratio>0.7?
  current_ratio = round(current_assets/current_liabili, 2)
  logging.info(f"current_ratio = current_assets/current_liabili: {current_ratio}")

  # Inventario
  try:
    inventory = balance["Inventory"].iloc[0]
    # quickRatio>0.7?
    quick_ratio = round((current_assets-inventory)/current_liabili, 2)
  except Exception as e:
    quick_ratio = None
    logging.warning(f"'Inventory' no existe en el dataframe 'balance' - {e}")

  logging.info(f"Prueba acida (descontando inventarios de activos corrientes) - quick_ratio: {quick_ratio}")

  # Total Debt
  total_debt = balance["Total Debt"].iloc[0]

  # total Assets
  total_assets = balance["Total Assets"].iloc[0]

  # Total Debt / Total Assets
  debt_ratio = round(total_debt/total_assets, 2)
  logging.info(f"Relación deuda vs activos - debt_ratio = total_debt/total_assets: {debt_ratio}")

  kpis_balance = {
      "balance": balance,
      "operation_expenses_month": operation_expenses_month,
      "cash": cash,
      "months_operation": months_operation,
      "current_ratio": current_ratio,
      "quick_ratio": quick_ratio,
      "debt_ratio": debt_ratio
  }
  return kpis_balance


def score_balance_general(kpis_balance: dict):
  
  months_operation = kpis_balance["months_operation"]
  current_ratio = kpis_balance["current_ratio"]
  quick_ratio = kpis_balance["quick_ratio"]
  debt_ratio = kpis_balance["debt_ratio"]

  # reglas de sanidad de una empresa
  kpis_rules = {
      "months_operation": {"var": months_operation, "val": 3},
      "current_ratio": {"var": current_ratio, "val": 0.7},
      "debt_ratio": {"var": debt_ratio, "val": 0.5}
  }
  if quick_ratio:
    kpis_rules["quick_ratio"] = {"var": quick_ratio, "val": 0.7}

  score_balance = []
  for kpiname, info_dict in kpis_rules.items():
    kpi = info_dict["var"]
    rule = info_dict["val"]
    if kpi:
      if kpiname in ["debt_ratio"]:
        score_balance += [1] if kpi<=rule else [0]
      else:
        score_balance += [1] if kpi>=rule else [0]

  score_balance = 10*sum(score_balance)/len(score_balance)

  logging.info("=="*20)
  logging.info(f"Score final balance general - score_balance: {score_balance}")

  return score_balance


def get_historic_price(tick_yf: yf.Ticker):
    """Funcion que trae el precio historico de los ultimos 5 años una accion dada"""

    hist_price = tick_yf.history(period="5Y")
    hist_price.index = [x.strftime("%Y-%m-%d") for x in hist_price.index]
    hist_price = hist_price[["Close", "Volume"]]

    logging.info(f"Intervalo de tiempo extraido: {hist_price.index.min()}; {hist_price.index.max()}")
    
    hist_price = hist_price.reset_index()
    hist_price = hist_price.rename(columns={"index": "period"})

    return hist_price


def get_multiples(ticker: str, kpis_cfg: dict):
    """Funcion para calcular los multiplos de un ticker dado"""

    tick = yf.Ticker(ticker)

    # precio historico de la accion en analisis
    logging.info(f"Obteniendo precio historico para el ticker: {ticker}")
    hist_price_interes = get_historic_price(tick)
    
    logging.info("Obteniendo los indicadores de los earnings ttm")
    data_type = "income"
    _, historic_income_ttm_interes = get_financial_data(
        ticker=ticker, 
        data_type=data_type, 
        kpis=kpis_cfg["ttm"][data_type], 
        is_ttm=True
    )
    logging.info(f"Estado de resultados historic_income_ttm_interes.shape: {historic_income_ttm_interes.shape}")

    data_type = "cash_flow"
    _, historic_cash_ttm_interes = get_financial_data(
        ticker=ticker, 
        data_type=data_type, 
        kpis=kpis_cfg["ttm"][data_type], 
        is_ttm=True
    )
    logging.info(f"Flujo de caja historic_cash_ttm_interes.shape: {historic_cash_ttm_interes.shape}")

    # income ttm historico + cash ttm historico
    logging.info("Uniendo los estados de resultados y el flujo de caja")
    historic_ttm_interes = historic_income_ttm_interes.merge(
        historic_cash_ttm_interes,
        on=["earning_date"]
    )
    historic_ttm_interes = historic_ttm_interes.sort_values(["earning_date"])
    logging.info(f"historic_ttm_interes.shape: {historic_ttm_interes.shape}")

    logging.info("Replicando los earnings de manera diaria para cruzar con el precio historico")
    historic_ttm_interes = historic_ttm_interes.reset_index()
    hist_ttm_replicated = []

    for i in range(historic_ttm_interes.shape[0]):

        row_i = historic_ttm_interes.iloc[i]
        try:
            row_iplus1 = historic_ttm_interes.iloc[i+1]
            ends = row_iplus1["earning_date"]
            inclusive = "left"
        except Exception as e:
            ends = datetime.now().strftime("%Y-%m-%d")
            inclusive = "both"

        dts = pd.date_range(
            row_i["earning_date"],
            ends,
            inclusive=inclusive
        )
        dts = dts.strftime("%Y-%m-%d")
        replicated_i = pd.DataFrame(dts, columns=["period"])
        for var, val in row_i.items():
            replicated_i[var] = val

        hist_ttm_replicated.append(replicated_i)

    hist_ttm_replicated = pd.concat(hist_ttm_replicated)
    logging.info(f"Earnings replicados, hist_ttm_replicated.shape: {hist_ttm_replicated.shape}")

    # se revisa la moneda de los earnings para calcular los multiplos usando el precio
    # y los earnings en la misma moneda. Por ejemplo BABA, tiene los earnings en Yuanes
    # y el precio en USD, por lo que pasamos el precio a Yuanes
    earnings_currency = tick.info["financialCurrency"]
    logging.info(f"Revisando la moneda de los earnings - earnings_currency: {earnings_currency}")

    if earnings_currency!="USD":
        logging.info("Ajustando el precio a la moneda de los earnings...")
        
        tick_currency = yf.Ticker(f"{earnings_currency}=X")
        exchange_rate = tick_currency.history(period="5Y")[["Close"]]
        exchange_rate = exchange_rate.reset_index()
        exchange_rate.columns = ["period", "exchange"]
        exchange_rate["period"] = exchange_rate["period"].dt.strftime("%Y-%m-%d")
        exchange_rate["exchange"] = exchange_rate["exchange"].astype(float)
        exchange_rate = exchange_rate.sort_values(["period"])

        # cruce con el precio de la accion para dejar el precio en moneda local
        # o la misma moneda de los estados financieros, ya que el precio
        # por defecto viene en usd
        hist_price_adj = hist_price_interes.merge(exchange_rate, on=["period"], how="left")
        hist_price_adj["close_adj_currency"] = hist_price_adj["Close"]*hist_price_adj["exchange"]
    else:
        hist_price_adj = hist_price_interes.copy()
        hist_price_adj["close_adj_currency"] = hist_price_adj["Close"].copy()

    logging.info(f"Cruce del precio y los earnings - hist_price_adj.shape: {hist_price_adj.shape}")
    hist_price_kpis = hist_price_adj.merge(
        hist_ttm_replicated,
        on=["period"],
        how="left"
    )
    logging.info(f"Dimension resultante del cruce - hist_price_kpis.shape: {hist_price_kpis.shape}")

    # calculo de ratios
    logging.info("Calculando los ratios/multiplos")
    price_var = "close_adj_currency"
    shares_var = "Shares Outstanding (Basic)"
    hist_price_kpis["pe_ratio"] = (
        hist_price_kpis[price_var] * hist_price_kpis[shares_var] / hist_price_kpis["Net Income"]
    )
    logging.info("P/E ratio calculado!")
    
    hist_price_kpis["ps_ratio"] = (
        hist_price_kpis[price_var] * hist_price_kpis[shares_var] / hist_price_kpis["Revenue"]
    )
    logging.info("P/S ratio calculado!")

    hist_price_kpis["pgp_ratio"] = (
        hist_price_kpis[price_var] * hist_price_kpis[shares_var] / hist_price_kpis["Gross Profit"]
    )
    logging.info("P/GP ratio calculado!")

    hist_price_kpis["pfcf_ratio"] = (
        hist_price_kpis[price_var] * hist_price_kpis[shares_var] / hist_price_kpis["Free Cash Flow"]
    )
    logging.info("P/FCF ratio calculado!")

    return hist_price_kpis