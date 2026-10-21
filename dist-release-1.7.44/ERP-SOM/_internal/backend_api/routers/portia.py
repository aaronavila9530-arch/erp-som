from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_db
from ai.som_portia import answer_som_portia
from ai.som_portia_knowledge import PORTIA_SUGGESTED_QUESTIONS, SOM_QA
from services.som_portia_context import build_som_portia_context


router = APIRouter(prefix="/portia", tags=["PORTIA SOM"])


class PortiaQuestion(BaseModel):
    question: str
    scope: str | None = "erp"


@router.get("/qa")
def get_portia_qa():
    return {"data": SOM_QA}


@router.get("/suggestions")
def get_portia_suggestions():
    return {"data": PORTIA_SUGGESTED_QUESTIONS}


@router.get("/context")
def get_portia_context(db=Depends(get_db)):
    return {"data": build_som_portia_context(db)}


@router.post("/ask")
def ask_portia(payload: PortiaQuestion, db=Depends(get_db)):
    context = build_som_portia_context(db)
    result = answer_som_portia(payload.question, context, SOM_QA, scope=payload.scope or "erp")
    return {
        "question": payload.question,
        "scope": payload.scope,
        "answer": result["answer"],
        "mode": result["mode"],
        "sources": result["sources"],
        "context": context,
    }
