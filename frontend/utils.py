import yaml
import json
import requests
import pandas as pd
import seaborn as sns


def get_documentation():

    with open("frontend/doc.yml") as stream:
        try:
            doc = yaml.safe_load(stream)
            return doc
        except yaml.YAMLError as exc:
            print(exc)


def is_payload_ok(payload: dict):

    missing_ticker = payload["ticker"]==""
    if payload["peers"]["custom"] is not None:
        missing_peers = "" in payload["peers"]["custom"]
    else:
        missing_peers = False
    not_ok = missing_ticker | missing_peers
    if not_ok:
        return False

    return True


def request_data(payload: dict):

    # with open("frontend/response.json") as stream:
    #     try:
    #         response = json.load(stream)
    #     except yaml.YAMLError as exc:
    #         print(exc)
    url = "https://sebasjp-app-valuation-company.hf.space/api/analyze_company/"
    response = requests.post(url, json=payload)
    response = json.loads(response.content)
    
    # ============== INCOME ================== #
    # estado de resultados
    income_df = pd.DataFrame(response['financials']['income']['income'])
    income_df = income_df.apply(lambda x: [x.values[::-1]], axis=0).T
    income_df.columns = ["data"]

    # margenes de los estados de resultados
    margins_df = pd.DataFrame({
        payload["ticker"]: response['financials']['income']['margin_ticker_interes'], 
        **response['financials']['income']['margin_peers']
    })

    idx = pd.IndexSlice
    margins = margins_df.style
    for peer in margins_df.columns[1:]:
        slice_ = idx[idx[(margins_df[payload["ticker"]]) < margins_df[peer]], [peer]]
        margins = margins.set_properties(**{'background-color': '#FEC6C4'}, subset=slice_)

        slice_ = idx[idx[(margins_df[payload["ticker"]]) > margins_df[peer]], [peer]]
        margins = margins.set_properties(**{'background-color': '#C8FFC3'}, subset=slice_)

    margins = margins.format("{:.2%}")

    # ============== CASH FLOW ================== #
    cash_flow_df = pd.DataFrame(response['financials']['cash_flow']['cash_flow'])
    cash_flow_df = cash_flow_df.reset_index()
    cash_flow_df = cash_flow_df.rename(columns={"index": "Fecha"})

    # ========== PRECIO HISTORICO - MULTIPLOS ========== #
    multiples_df = pd.DataFrame(response['price_historic']['detail_multiples'])
    multiples_df = multiples_df.round(2)
    multiples_df.columns = multiples_df.columns.str.replace("_ratio", "").str.upper()
    multiples_df = multiples_df.rename(index={
        "current_value": "Valor actual",
        "min_historic": "Mínimo histórico",
        "max_historic": "Máximo histórico"
    })
    multiples_df = multiples_df.drop(index=["score_multiplo"])

    # ========== PRECIO COMPETENCIA - MULTIPLOS ========== #
    color = sns.light_palette("#81B350", as_cmap=True, reverse=True)
    multiples_peers_df = pd.DataFrame(response['price_competitors']['detail_multiples']).T
    multiples_peers_df = multiples_peers_df[multiples_peers_df.index.isin(["pe_ratio", "ps_ratio", "pgp_ratio", "pfcf_ratio"])]
    multiples_peers_df.index = multiples_peers_df.index.str.replace("_ratio", "").str.upper()
    multiples_peers_df = multiples_peers_df.T.apply(lambda x: x.astype(float))
    multiples_peers = multiples_peers_df.style.background_gradient(axis=0, cmap=color).format("{:.2f}")

    result = {
        'income_indicator': response["financials"]["income"]["score_final"],
        'income_df': income_df,
        'income_indicator_growth': response["financials"]["income"]["score_stmt_growth"],
        'margins_df': margins,
        'income_indicator_margins_peer': round(response["financials"]["income"]["score_margins_peers"], 2),
        'balance_indicator': response["financials"]["balance"]["score_final"],

        'balance_months_operation': response["financials"]["balance"]["months_operation"],
        'balance_current_ratio': response["financials"]["balance"]["current_ratio"],
        'balance_quick_ratio': response["financials"]["balance"]["quick_ratio"],
        'balance_debt_ratio': response["financials"]["balance"]["debt_ratio"],

        'cash_flow_indicator': response["financials"]["cash_flow"]["score_final"],
        'cash_flow_df': cash_flow_df,

        'financial_indicator': response["financials"]["score_final"],

        'price_historic_score': response["price_historic"]["score_final"],
        'price_historic_multiples_df': multiples_df,

        'price_competitors_score': response["price_competitors"]["score_final"][payload["ticker"]],
        'price_competitors_peers_df': multiples_peers
    }
    return result


def msg_balance(decision: str):

    check_emoji = ":white_check_mark:"
    x_emoji = ":x:"                    
    # check_emoji = "&#x2705"
    # x_emoji = "&#x274C"
    if decision=="cumple":
        emoji = check_emoji
    elif decision=="no_cumple":
        emoji = x_emoji
    else:
        emoji = ""

    return emoji
