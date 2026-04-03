# api/routes/analysis.py: API route for analysis

from fastapi import APIRouter

from services.analysis_service import run_analysis

router = APIRouter()

@router.post("/analyze")
async def analysis(sample: int, include_llm: bool = False):
    return await run_analysis(sample=sample, include_llm=include_llm)

