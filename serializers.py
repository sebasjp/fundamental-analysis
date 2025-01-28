class ValuationRequest:

    ticker: str = "NU"
    peers: dict = {
        "custom": None,
        "n_competitors": 5
    }
    financial_weights: dict = {
        "income": {"growth": 0.5, "peers": 0.5}
    }
    multiples_weights: dict = {
        "pe_ratio": 0.25,
        "ps_ratio": 0.25,
        "pgp_ratio": 0.25,
        "pfcf_ratio": 0.25
    }