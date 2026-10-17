from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from database import get_db
from security.auth import get_current_user
from routers.mobile_auth import _has_visual_permission
from services.tenanting import company_code
from services.portia_analysis import build_evidence, answer, today
from ai.som_portia_knowledge import SOM_QA, PORTIA_SUGGESTED_QUESTIONS

router=APIRouter(prefix='/portia',tags=['PORTIA SOM'])


class Message(BaseModel):
    role: Literal['user','assistant']
    content: str = Field(max_length=12000)


class PortiaQuestion(BaseModel):
    question: str = Field(min_length=2,max_length=4000)
    scope: Literal['erp','qa','general_chat'] = 'erp'
    start: date | None = None
    end: date | None = None
    history: list[Message] = Field(default_factory=list,max_length=8)

    @model_validator(mode='after')
    def dates(self):
        self.start=self.start or today().replace(day=1)
        self.end=self.end or today()
        if self.start>self.end or (self.end-self.start).days>366:
            raise ValueError('Seleccione un periodo entre 1 y 367 dias')
        if not self.question.strip():raise ValueError('Escriba una pregunta')
        return self


def access(user=Depends(get_current_user), x_company_code: str=Header(default='MSL-CR')):
    check=lambda module:_has_visual_permission(user['usuario'],user['rol'],module,'view')
    if not check('portia'):raise HTTPException(403,'Sin permiso para PORTIA')
    privileged=user['rol'] in {'admin','master'}
    return dict(company=company_code(header_value=x_company_code),allowed={
        'finance':check('finanzas'),'services':check('servicios'),
        'hr':privileged and (check('hhrre') or check('hhrr'))})


@router.get('/assets/{name}',include_in_schema=False)
def asset(name:str):
    if name not in {'portia.js','portia.css'}:raise HTTPException(404)
    return FileResponse(Path(__file__).resolve().parents[1]/'assets'/'portia'/name,headers={'Cache-Control':'no-store'})


@router.get('/qa')
def get_portia_qa(ctx=Depends(access)):
    return {'data':SOM_QA}


@router.get('/suggestions')
def get_portia_suggestions(ctx=Depends(access)):
    return {'data':PORTIA_SUGGESTED_QUESTIONS}


@router.get('/context')
def get_portia_context(start:date|None=None,end:date|None=None,ctx=Depends(access),db=Depends(get_db)):
    try:period=PortiaQuestion(question='Resumen',start=start,end=end)
    except ValueError:raise HTTPException(422,'Periodo invalido; maximo 367 dias')
    return {'data':build_evidence(db,ctx['company'],period.start,period.end,ctx['allowed'])}


@router.post('/ask')
def ask_portia(payload:PortiaQuestion,ctx=Depends(access),db=Depends(get_db)):
    evidence=build_evidence(db,ctx['company'],payload.start,payload.end,ctx['allowed']) if payload.scope=='erp' else {}
    result=answer(payload.question,evidence,[m.model_dump() for m in payload.history],payload.scope,SOM_QA)
    return {**result,'question':payload.question,'scope':payload.scope,'context':evidence,
            'sources':list({s['source'] for s in evidence.get('sections',{}).values()}) if payload.scope=='erp' else (['Manual SOM'] if payload.scope=='qa' else [])}
