# app.py : AML Compliance Agent API




from fastapi import FastAPI, APIRouter

from services.analysis_service import run_analysis


from evaluate import evaluate as run_evaluate

from api.routes.analysis import router as analysis_router
from api.routes.account_detail import router as account_detail_router
from api.routes.evaluation import router as evaluation_router
from llm_layer import analyze_with_llm



app = FastAPI(title="AML Compliance Agent")


app.include_router(analysis_router)
app.include_router(account_detail_router)
app.include_router(evaluation_router)

@app.post("/health")
async def health_check():
    return {"backend": "AML Compliance Agent", "status": "healthy"}




