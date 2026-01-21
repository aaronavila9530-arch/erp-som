@router.get(
    "/board",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_board(
    cliente: Optional[str] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    surveyor: Optional[str] = Query(None),
    estados: Optional[List[str]] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    🔒 BLINDADO / ANTI-LAG:
    - Si NO hay filtros → retorna []
    - CONFIRMADO / BUQUE POR CONFIRMAR → solo año en curso
    - Otros estados → sin restricción de año
    """

    if not any([
        cliente,
        continente,
        pais,
        puerto,
        surveyor,
        estados,
        fecha_desde,
        fecha_hasta
    ]):
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = []
    params = {}

    # ----------------------------
    # FILTROS BÁSICOS
    # ----------------------------
    if cliente:
        filtros.append("cliente ILIKE %(cliente)s")
        params["cliente"] = f"%{cliente.strip()}%"

    if continente:
        filtros.append("continente = %(continente)s")
        params["continente"] = continente.strip()

    if pais:
        filtros.append("pais = %(pais)s")
        params["pais"] = pais.strip()

    if puerto:
        filtros.append("puerto = %(puerto)s")
        params["puerto"] = puerto.strip()

    if surveyor:
        filtros.append("surveyor ILIKE %(surveyor)s")
        params["surveyor"] = f"%{surveyor.strip()}%"

    # ----------------------------
    # ESTADOS + REGLA DE AÑO
    # ----------------------------
    estados_norm = []
    if estados:
        for e in estados:
            if e:
                estados_norm.append(str(e).strip().upper())

        if estados_norm:
            filtros.append("UPPER(estado) = ANY(%(estados)s)")
            params["estados"] = estados_norm

            # 🎯 REGLA CLAVE:
            # Si incluye CONFIRMADO o BUQUE POR CONFIRMAR
            estados_restringidos = {"CONFIRMADO", "BUQUE POR CONFIRMAR"}

            if estados_restringidos.intersection(estados_norm):
                filtros.append(
                    "EXTRACT(YEAR FROM fecha_inicio) = EXTRACT(YEAR FROM CURRENT_DATE)"
                )

    # ----------------------------
    # FECHAS (si vienen explícitas)
    # ----------------------------
    if fecha_desde:
        filtros.append("fecha_inicio::date >= %(fecha_desde)s::date")
        params["fecha_desde"] = fecha_desde.strip()

    if fecha_hasta:
        filtros.append("fecha_inicio::date <= %(fecha_hasta)s::date")
        params["fecha_hasta"] = fecha_hasta.strip()

    if not filtros:
        cur.close()
        return []

    where_sql = " AND ".join(filtros)

    sql = f"""
        SELECT
            consec,
            tipo,
            estado,
            num_informe,
            buque_contenedor,
            cliente,
            detalle,
            continente,
            pais,
            puerto,
            operacion,
            surveyor,
            fecha_inicio,
            hora_inicio,
            fecha_fin,
            hora_fin,
            demoras,
            duracion
        FROM servicios
        WHERE {where_sql}
        ORDER BY fecha_inicio DESC
        LIMIT 500
    """

    cur.execute(sql, params)
    data = cur.fetchall()
    cur.close()

    return data
