import logging
import pandas as pd
import numpy as np
from constants import BalanceKpis
from utils.fetch_data import get_financial_data


def clean_kpi(x: str):
  if x=="-":
    newx = 0
  else:
    newx = x
  
  return float(newx)


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


def calculate_kpis_balance_general(
    ticker: str,
    income_stmt_complete: pd.DataFrame
):
  """Esta función calcula los indicadores del balance general, como:
  1. Razon corriente
  2. Razón corriente "acida"
  3. Deuda sobre los activos totales
  4. Numero de meses de operación con el dinero en caja
  """
  balance_complete, balance = get_financial_data(ticker=ticker, data_type="balance_sheet", kpis=BalanceKpis.ANNUAL)

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
    total_assets = clean_kpi(balance_complete.iloc[ixtotalassets, 1])
    data_assets = balance_complete.iloc[:ixtotalassets, :]

    # quitarle el long term al total para calcular el current
    non_current_item_names = data_assets[data_assets["nding"].str.contains("Long")]["nding"].to_list()
    non_current_item_names += ["Goodwill", "Property, Plant & Equipment", "Other Intangible Assets"]
    non_current_item_names = np.unique(non_current_item_names)
    non_current_item_names = list(non_current_item_names)
    non_current_value = sum([
        clean_kpi(x) for x in data_assets[data_assets["nding"].isin(non_current_item_names)].iloc[:,1]
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
        clean_kpi(x) for x in data_liabilities[data_liabilities["nding"].isin(non_current_item_names)].iloc[:,1]
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


def process_balance_general(
    ticker: str, 
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
        kpis=BalanceKpis.ANNUAL
    )
    score_balance = score_balance_general(kpis_balance)

    response = {"balance": kpis_balance, "score_final": score_balance}

    return response
