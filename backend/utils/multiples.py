import logging
import yfinance as yf
import pandas as pd
from datetime import datetime
from constants import IncomeKpis, CashFlowKpis
from utils.fetch_data import get_financial_data


def get_historic_price(tick_yf: yf.Ticker):
    """Funcion que trae el precio historico de los ultimos 5 años una accion dada"""

    hist_price = tick_yf.history(period="5Y")
    hist_price.index = [x.strftime("%Y-%m-%d") for x in hist_price.index]
    hist_price = hist_price[["Close", "Volume"]]

    logging.info(f"Intervalo de tiempo extraido: {hist_price.index.min()}; {hist_price.index.max()}")
    
    hist_price = hist_price.reset_index()
    hist_price = hist_price.rename(columns={"index": "period"})

    return hist_price


def get_multiples(ticker: str):
    """Funcion para calcular los multiplos de un ticker dado"""

    tick = yf.Ticker(ticker)

    # precio historico de la accion en analisis
    logging.info(f"Obteniendo precio historico para el ticker: {ticker}")
    hist_price_interes = get_historic_price(tick)
    
    logging.info("Obteniendo los indicadores de los earnings ttm")
    _, historic_income_ttm_interes = get_financial_data(
        ticker=ticker, 
        data_type="income", 
        kpis=IncomeKpis.TTM, 
        is_ttm=True
    )
    logging.info(f"Estado de resultados historic_income_ttm_interes.shape: {historic_income_ttm_interes.shape}")

    _, historic_cash_ttm_interes = get_financial_data(
        ticker=ticker, 
        data_type="cash_flow", 
        kpis=CashFlowKpis.TTM, 
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