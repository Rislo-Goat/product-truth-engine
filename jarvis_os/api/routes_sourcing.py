"""Endpoints de sourcing (spec §39).

- POST /sourcing/analyze     : analyse synchrone (immédiate) d'un lot de candidats
- POST /sourcing/jobs        : crée un job asynchrone (progression suivie)
- GET  /sourcing/jobs/{id}   : état + résultat du job
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..engines.sourcing_pipeline import rank_candidates
from ..jobs import store
from ..schemas.api import (AnalyzeRequest, AnalyzeResponse, JobCreated, JobStatus)

router = APIRouter(prefix="/sourcing", tags=["sourcing"])


def _run(req: AnalyzeRequest, progress=None) -> AnalyzeResponse:
    if progress:
        progress(10, "discovery")
    target = store.parse_target_date(req.target_date)
    if progress:
        progress(40, "analysis (truth/economics/shipping)")
    opps = rank_candidates(
        req.claim, req.candidates, req.category,
        selling_price=req.selling_price, destination=req.destination,
        target_date=target, weights=req.weights,
    )
    if progress:
        progress(90, "ranking")
    return AnalyzeResponse(count=len(opps), opportunities=opps)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    if not req.candidates:
        raise HTTPException(status_code=400,
                            detail="Aucun candidat fournisseur fourni. Ajoute des candidats "
                                   "(connecteur manuel) ou configure un connecteur API.")
    return _run(req)


@router.post("/jobs", response_model=JobCreated)
def create_job(req: AnalyzeRequest) -> JobCreated:
    jid = store.create_job()
    store.run_async(jid, lambda progress: _run(req, progress).model_dump())
    return JobCreated(job_id=jid, status="created")


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str) -> JobStatus:
    j = store.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="job inconnu")
    result = j.get("result")
    return JobStatus(
        job_id=j["job_id"], status=j["status"], progress=j.get("progress", 0),
        step=j.get("step", ""), error=j.get("error"),
        result=AnalyzeResponse(**result) if result else None,
    )
