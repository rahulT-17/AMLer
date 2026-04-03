# app.py : AMLer main app entry point

# import libraries:
from fastapi import FastAPI

# import routers:
from api.routes.analysis import router as analysis_router
from api.routes.account_detail import router as account_detail_router
from api.routes.evaluation import router as evaluation_router


app = FastAPI(title="AML Compliance Agent")


app.include_router(analysis_router)
app.include_router(account_detail_router)
app.include_router(evaluation_router)

@app.get("/health")
async def health_check():
    return {"backend": "AML Compliance Agent", "status": "healthy"}




