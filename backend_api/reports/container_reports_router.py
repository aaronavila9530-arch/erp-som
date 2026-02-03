# ============================================================
# ROUTER — CONTAINER REPORTS (1:1 TABLE)
# Archivo: routers/container_reports_router.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/container-reports",
    tags=["Container Reports"]
)

# ============================================================
# CREATE
# ============================================================

@router.post("")
def create_container_report(
    payload: dict,
    db: Session = Depends(get_db)
):
    payload["created_at"] = datetime.utcnow()
    payload["updated_at"] = datetime.utcnow()

    columns = ", ".join(payload.keys())
    values = ", ".join([f":{k}" for k in payload.keys()])

    query = text(f"""
        INSERT INTO public.container_reports ({columns})
        VALUES ({values})
        RETURNING id
    """)

    result = db.execute(query, payload).fetchone()
    db.commit()

    return {
        "success": True,
        "id": result[0]
    }


# ============================================================
# UPDATE
# ============================================================

@router.put("/{report_id}")
def update_container_report(
    report_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    if not payload:
        raise HTTPException(status_code=400, detail="No data provided")

    payload["updated_at"] = datetime.utcnow()

    set_clause = ", ".join([f"{k} = :{k}" for k in payload.keys()])
    payload["id"] = report_id

    query = text(f"""
        UPDATE public.container_reports
        SET {set_clause}
        WHERE id = :id
    """)

    result = db.execute(query, payload)
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"success": True}


# ============================================================
# DELETE
# ============================================================

@router.delete("/{report_id}")
def delete_container_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        DELETE FROM public.container_reports
        WHERE id = :id
    """)

    result = db.execute(query, {"id": report_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"success": True}


# ============================================================
# GET ALL
# ============================================================

@router.get("")
def get_container_reports(
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT *
        FROM public.container_reports
        ORDER BY created_at DESC
    """)

    rows = db.execute(query).mappings().all()

    return {
        "success": True,
        "data": rows
    }





# ============================================================
# GET BY ID
# ============================================================

@router.get("/{report_id}")
def get_container_report_by_id(
    report_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT *
        FROM public.container_reports
        WHERE id = :id
    """)

    row = db.execute(query, {"id": report_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "success": True,
        "data": row
    }
