from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import Base, get_db


# =========================================================
# SQLALCHEMY MODEL
# =========================================================

class VesselTruckSupervisionReport(Base):
    __tablename__ = "vessel_truck_supervision_reports"

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    cert_no = Column(String)
    port = Column(String)
    country = Column(String)
    report_date = Column(DateTime)

    vessel_name = Column(String)
    flag_port_registry = Column(String)
    grt = Column(String)
    nrt = Column(String)
    imo_no = Column(String)
    build_year = Column(String)

    captain = Column(String)
    chief_officer = Column(String)

    arrival_date = Column(DateTime)
    inspection_date = Column(DateTime)
    supervision_completed_date = Column(DateTime)

    process_text = Column(Text)
    findings_text = Column(Text)
    conclusion_text = Column(Text)


# =========================================================
# Pydantic Schemas
# =========================================================

class VesselTruckSupervisionBase(BaseModel):
    cert_no: Optional[str] = None
    port: Optional[str] = None
    country: Optional[str] = None
    report_date: Optional[datetime] = None

    vessel_name: Optional[str] = None
    flag_port_registry: Optional[str] = None
    grt: Optional[str] = None
    nrt: Optional[str] = None
    imo_no: Optional[str] = None
    build_year: Optional[str] = None

    captain: Optional[str] = None
    chief_officer: Optional[str] = None

    arrival_date: Optional[datetime] = None
    inspection_date: Optional[datetime] = None
    supervision_completed_date: Optional[datetime] = None

    process_text: Optional[str] = None
    findings_text: Optional[str] = None
    conclusion_text: Optional[str] = None


class VesselTruckSupervisionCreate(VesselTruckSupervisionBase):
    pass


class VesselTruckSupervisionUpdate(VesselTruckSupervisionBase):
    pass


class VesselTruckSupervisionResponse(VesselTruckSupervisionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/vessel-truck-supervision",
    tags=["Vessel Truck Supervision"]
)


# =========================================================
# CREATE
# =========================================================

@router.post("/", response_model=VesselTruckSupervisionResponse)
def create_vessel_truck_supervision(
    payload: VesselTruckSupervisionCreate,
    db: Session = Depends(get_db)
):

    new_report = VesselTruckSupervisionReport(
        **payload.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report


# =========================================================
# LIST ALL
# =========================================================

@router.get("/", response_model=List[VesselTruckSupervisionResponse])
def list_vessel_truck_supervision(
    db: Session = Depends(get_db)
):

    return (
        db.query(VesselTruckSupervisionReport)
        .order_by(VesselTruckSupervisionReport.id.desc())
        .all()
    )


# =========================================================
# GET BY ID
# =========================================================

@router.get("/{report_id}", response_model=VesselTruckSupervisionResponse)
def get_vessel_truck_supervision(
    report_id: int,
    db: Session = Depends(get_db)
):

    report = (
        db.query(VesselTruckSupervisionReport)
        .filter(VesselTruckSupervisionReport.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


# =========================================================
# UPDATE
# =========================================================

@router.put("/{report_id}", response_model=VesselTruckSupervisionResponse)
def update_vessel_truck_supervision(
    report_id: int,
    payload: VesselTruckSupervisionUpdate,
    db: Session = Depends(get_db)
):

    report = (
        db.query(VesselTruckSupervisionReport)
        .filter(VesselTruckSupervisionReport.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    update_data = payload.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(report, key, value)

    report.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(report)

    return report


# =========================================================
# FILTER SERVICIOS (PARA POPUP BUSQUEDA)
# =========================================================

from sqlalchemy import extract, func
from models import Servicio


@router.get("/servicios-filter")
def filter_servicios(
    num_informe: str | None = None,
    buque_contenedor: str | None = None,
    cliente: str | None = None,
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    anio: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Servicio)

    # ================= TEXT FILTERS (case insensitive) =================

    if num_informe:
        query = query.filter(
            func.lower(Servicio.num_informe) == num_informe.lower()
        )

    if buque_contenedor:
        query = query.filter(
            func.lower(Servicio.buque_contenedor) == buque_contenedor.lower()
        )

    if cliente:
        query = query.filter(
            func.lower(Servicio.cliente) == cliente.lower()
        )

    if continente:
        query = query.filter(
            func.lower(Servicio.continente) == continente.lower()
        )

    if pais:
        query = query.filter(
            func.lower(Servicio.pais) == pais.lower()
        )

    if puerto:
        query = query.filter(
            func.lower(Servicio.puerto) == puerto.lower()
        )

    # ================= DATE FILTERS =================

    if anio:
        query = query.filter(
            Servicio.fecha_inicio.isnot(None)
        ).filter(
            extract("year", Servicio.fecha_inicio) == anio
        )

    if mes:
        query = query.filter(
            Servicio.fecha_inicio.isnot(None)
        ).filter(
            extract("month", Servicio.fecha_inicio) == mes
        )

    # ================= ORDER + LIMIT =================

    results = (
        query
        .order_by(Servicio.fecha_inicio.desc().nullslast())
        .limit(500)
        .all()
    )

    data = []

    for r in results:
        data.append({
            "id": r.id,
            "num_informe": r.num_informe,
            "buque_contenedor": r.buque_contenedor,
            "cliente": r.cliente,
            "continente": r.continente,
            "pais": r.pais,
            "puerto": r.puerto,
            "anio": r.fecha_inicio.year if r.fecha_inicio else None,
            "mes": r.fecha_inicio.month if r.fecha_inicio else None
        })

    return {
        "success": True,
        "count": len(data),
        "data": data
    }
