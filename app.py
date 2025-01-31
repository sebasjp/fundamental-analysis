import logging
from fastapi import FastAPI

from main import execute_process


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=logging.INFO,
)
logging.getLogger(__name__)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("httpx").setLevel(logging.WARNING)


app = FastAPI()


@app.middleware('http')
async def log_requests(request, call_next):
    logging.info(f'[POST] Received request: {request.method} {request.url.path}')
    response = await call_next(request)
    return response


@app.post("/api/analyze_company/")
async def app_analyze_zone(request: dict) -> dict:
    
    logging.info('Python HTTP trigger function processed a request.')
    
    ticker = request.get("ticker")
    weights = request.get("financial_weights")
    peers_cfg = request.get("peers")
    multiples_weights = request.get("multiples_weights")

    try:
        response = execute_process(
            ticker=ticker,
            financial_weights=weights,
            peers=peers_cfg,
            multiples_weights=multiples_weights
        )
        return response
    except Exception as e:
        return {"response": e}