import requests
import logging
import pandas as pd
from constants import FetchData


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
    url = FetchData.url_income.format(ticker=ticker.lower(), suffix_url=suffix_url)
  elif data_type=="cash_flow":
    url = FetchData.url_cash_flow.format(ticker=ticker.lower(), suffix_url=suffix_url)
  elif data_type=="balance_sheet":
    url = FetchData.url_balance.format(ticker=ticker.lower(), suffix_url=suffix_url)

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
