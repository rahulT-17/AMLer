
from fastapi import APIRouter

from evaluate import evaluate as run_evaluate

router = APIRouter()


@router.get("/evaluate")
async def evaluate_endpoint():
    return await run_evaluate()