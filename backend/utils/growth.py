import logging
import pandas as pd


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
