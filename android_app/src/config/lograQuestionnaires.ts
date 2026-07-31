export type LograQuestion = { number?: string; id?: string; priority?: string; block?: string; question: string; source?: string };

export type LograQuestionnaire = { title: string; source_file: string; slug: string; critical_questions: LograQuestion[]; detailed_questions: LograQuestion[]; evidence_requests?: Array<{ id: string; document: string; source?: string }> };

export const ONG_QUESTIONNAIRES: LograQuestionnaire[] = [
  {
    "title": "Agencias Navieras Y Agentes",
    "source_file": "Agencias_navieras_y_agentes modificado.docx",
    "slug": "agencias_navieras_y_agentes",
    "critical_questions": [
      {
        "number": "1",
        "question": "¿Cuál ha sido el mayor buque atendido en Puerto Andres / Boca Chica por LOA, manga, DWT y calado real de llegada o salida?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "¿Han atendido bulk carriers, Handy, Handymax o buques de características similares? Identificar fechas, carga y terminal.",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "¿Existe una restricción práctica de calado, eslora, manga, horario o clima que la agencia aplica aunque no esté documentada?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "¿Qué servicios son obligatorios y cuáles suelen ser el cuello de botella: prácticos, remolcadores, amarradores, autoridades, aduana, lanchas?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "¿Se han reportado varaduras, contactos con fondo, golpes al muelle, demoras por viento/corriente o abortos de maniobra?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "¿Qué documentos pueden respaldar la experiencia: SOF, NOR, PDA/FDA, facturas, bitácoras, correos, reportes de incidentes?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "¿Cuánto tiempo toma programar una escala con buque mayor y cuáles son los puntos de aprobación previos?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "Desde la perspectiva comercial, ¿qué condición mínima haría inviable o demasiado riesgosa la operación Handymax?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "AG-01",
        "priority": "C",
        "block": "Experiencia y comparables",
        "question": "Indique los últimos buques de mayor porte atendidos en Puerto Andres / Boca Chica, incluyendo nombre, fecha, LOA, manga, DWT, calado de llegada/salida y tipo de carga. Validar/solicitar: SOF, PDA/FDA, manifiestos, vessel particulars.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-02",
        "priority": "C",
        "block": "Experiencia y comparables",
        "question": "¿Existe evidencia de buques graneleros secos, cementeros, clinker, fertilizantes, agregados, minerales u otros graneles atendidos en la zona? Validar/solicitar: Lista de escalas, BL, manifiestos, fotos, reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-03",
        "priority": "A",
        "block": "Experiencia y comparables Cuales son",
        "question": "los buques que la agencia considera comparables al Handymax de diseno y por que? Validar/solicitar: Fichas tecnicas de buques, calados y maniobras.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-04",
        "priority": "A",
        "block": "Experiencia y comparables",
        "question": "Que diferencia operacional observaron entre buques pequenos, Handysize y buques mayores en la aproximacion o atraque? Validar/solicitar: Notas de operaciones, comentarios de capitanes o practicos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-05",
        "priority": "A",
        "block": "Experiencia y comparables",
        "question": "Han atendido buques con calado restringido por marea o con condicion de carga parcial? Describir el caso. Validar/solicitar: Instrucciones de carga, draft survey, SOF.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-06",
        "priority": "M",
        "block": "Experiencia y comparables",
        "question": "Que otros agentes locales tienen experiencia directa con maniobras relevantes en Boca Chica? Validar/solicitar: Contactos y referencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-07",
        "priority": "C",
        "block": "Restricciones reales",
        "question": "Cual es el calado maximo que ustedes planifican comercialmente para una escala en Boca Chica y de donde proviene ese criterio? Validar/solicitar: Port Handbook, Capitania, practicos, experiencia propia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-08",
        "priority": "C",
        "block": "Restricciones reales",
        "question": "Existen restricciones de eslora, manga, DWT, calado aereo, viento, ola, corriente, marea o visibilidad usadas para aceptar o rechazar escalas? Validar/solicitar: Comunicaciones, aprobaciones, instructivos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-09",
        "priority": "C",
        "block": "Restricciones reales",
        "question": "Se permiten maniobras nocturnas o solo diurnas? En que casos se exige luz diurna? Validar/solicitar: Circular, correo de autoridad, practica de pilotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-10",
        "priority": "A",
        "block": "Restricciones reales",
        "question": "Que informacion solicita la autoridad o el practico antes de aprobar un buque no habitual o de mayor porte? Validar/solicitar: Checklists de arribo, formularios, correos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-11",
        "priority": "A",
        "block": "Restricciones reales Hay periodos del ano",
        "question": "con mayor probabilidad de cierre operacional por vientos, mar de fondo, huracanes, sargazo, lluvia o visibilidad? Validar/solicitar: Registros de demoras, weather logs.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-12",
        "priority": "M",
        "block": "Restricciones reales Cuales son",
        "question": "las causas mas frecuentes de demora en arribo, atraque, descarga o zarpe? Validar/solicitar: SOF, notas de demora, claims.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-13",
        "priority": "C",
        "block": "Servicios nauticos",
        "question": "Como se coordina el practicaje: solicitud, anticipacion, canales de comunicacion, horarios y tiempos de respuesta? Validar/solicitar: Procedimiento de agencia, correos, contactos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-14",
        "priority": "C",
        "block": "Servicios nauticos Cuantos remolcadores",
        "question": "se han usado historicamente para buques mayores o maniobras complejas en Boca Chica? Validar/solicitar: Facturas, SOF, reportes de maniobra.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-15",
        "priority": "C",
        "block": "Servicios nauticos",
        "question": "Existe disponibilidad confiable de remolcadores con potencia suficiente o deben movilizarse desde otro puerto? Validar/solicitar: Contratos, tarifas, tiempos de movilizacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-16",
        "priority": "A",
        "block": "Servicios nauticos",
        "question": "Que papel tienen amarradores, lanchas, guardacostas o seguridad en la maniobra y cuales son sus limitaciones? Validar/solicitar: Lista de proveedores, procedimientos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-17",
        "priority": "A",
        "block": "Servicios nauticos",
        "question": "Que servicios portuarios deben reservarse con mayor anticipacion para evitar demoras? Validar/solicitar: Checklists y SLA informales.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-18",
        "priority": "M",
        "block": "Servicios nauticos",
        "question": "Han ocurrido cancelaciones o retrasos por falta de practico, remolcador o autorizacion? Validar/solicitar: SOF, correspondencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-19",
        "priority": "C",
        "block": "Costos y competitividad",
        "question": "Proveer PDA/FDA o estructura de costos para una escala tipica y para un buque mayor, separando tasas, practicaje, tugs, amarre, agencia y seguridad. Validar/solicitar: PDA/FDA anonimizados.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-20",
        "priority": "A",
        "block": "Costos y competitividad",
        "question": "Que costos crecerian de forma no lineal si se atiende un Handymax cargado? Validar/solicitar: Tarifario y supuestos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-21",
        "priority": "A",
        "block": "Costos y competitividad",
        "question": "Que demoras o restricciones podrian generar demurrage o perdidas comerciales significativas? Validar/solicitar: SOF, contratos de fletamento, historico de demoras.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-22",
        "priority": "M",
        "block": "Costos y competitividad",
        "question": "Cual es el tiempo tipico desde arribo en fondeo hasta atraque y desde fin de operaciones hasta zarpe? Validar/solicitar: SOF y estadisticas internas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-23",
        "priority": "M",
        "block": "Costos y competitividad",
        "question": "Como comparan Boca Chica con puertos alternativos para cargas graneleras en costos, tiempos y confiabilidad? Validar/solicitar: Benchmark, PDA comparativos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-24",
        "priority": "A",
        "block": "Procedimientos de escala",
        "question": "Describa paso a paso la secuencia de pre-arribo, arribo, fondeo, autorizacion, toma de practico, atraque, descarga, desatraque y zarpe. Validar/solicitar: Procedimientos y SOF.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-25",
        "priority": "A",
        "block": "Procedimientos de escala",
        "question": "Que documentos requiere la autoridad antes de permitir entrada y cuales suelen generar observaciones? Validar/solicitar: Lista documental.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-26",
        "priority": "A",
        "block": "Procedimientos de escala",
        "question": "Existen ventanas de marea o condiciones meteorologicas que se coordinan con el buque antes de autorizar entrada? Validar/solicitar: Correos, instrucciones a master.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-27",
        "priority": "M",
        "block": "Procedimientos de escala",
        "question": "Que ocurre si el buque llega y no puede entrar por clima o calado? Donde espera y que costos se generan? Validar/solicitar: SOF y tarifas de fondeo/demora.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-28",
        "priority": "M",
        "block": "Procedimientos de escala",
        "question": "Se han emitido cartas de protesta por demoras, calado, remolcadores, practicos o condiciones de atraque? Validar/solicitar: Cartas de protesta anonimizadas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-29",
        "priority": "C",
        "block": "Canal y maniobra",
        "question": "Que percepcion operativa tienen los capitanes sobre el canal de acceso, alineamiento, ayudas, corriente, viento o margen de seguridad? Validar/solicitar: Mensajes de master, voyage reports.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-30",
        "priority": "C",
        "block": "Canal y maniobra",
        "question": "Han recibido observaciones sobre falta de balizamiento, visibilidad, iluminacion o referencias para entrada/salida? Validar/solicitar: Correos, reportes, fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-31",
        "priority": "C",
        "block": "Canal y maniobra",
        "question": "Se ha tenido que abortar o postergar una maniobra por condiciones de viento, corriente, ola, trafico o visibilidad? Validar/solicitar: SOF, reportes de practico.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-32",
        "priority": "M",
        "block": "Canal y maniobra",
        "question": "Que condiciones solicitan los practicos o masters antes de mover un buque de mayor porte? Validar/solicitar: Instrucciones, mensajes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-33",
        "priority": "M",
        "block": "Canal y maniobra",
        "question": "Existen interferencias con trafico local, pesca, embarcaciones menores, fondeo o turismo durante maniobras? Validar/solicitar: Reportes y observaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-34",
        "priority": "C",
        "block": "Muelle y operacion",
        "question": "Que limitaciones de muelle se reportan: defensas, bitas, lineas, profundidad al costado, longitud util, gangway, iluminacion? Validar/solicitar: Fotos, reportes de capitan, survey.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-35",
        "priority": "C",
        "block": "Muelle y operacion",
        "question": "Se han presentado problemas para mantener el buque al costado por viento, oleaje, passing ships, lineas o defensas? Validar/solicitar: SOF, reportes de seguridad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-36",
        "priority": "A",
        "block": "Muelle y operacion",
        "question": "Cual es la productividad real de carga/descarga de graneles y que factores la limitan? Validar/solicitar: SOF, reportes de operacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-37",
        "priority": "A",
        "block": "Muelle y operacion",
        "question": "Existen limitaciones de recepcion terrestre, almacenamiento, turnos, equipos o acceso vial que afecten permanencia del buque? Validar/solicitar: Plan de operaciones, turnos, capacidad patio.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-38",
        "priority": "M",
        "block": "Muelle y operacion",
        "question": "Que servicios al buque estan disponibles: agua, combustible, basura, slops, lancha, reparaciones, medical, cambio de tripulacion? Validar/solicitar: Lista de proveedores y tarifas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-39",
        "priority": "C",
        "block": "Riesgos e incidentes",
        "question": "Liste incidentes, casi incidentes o reclamos relacionados con canal, calado, atraque, defensas, lineas, carga, demoras o seguridad. Validar/solicitar: Reportes, cartas, seguros, correspondencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-40",
        "priority": "C",
        "block": "Riesgos e incidentes",
        "question": "Existen casos conocidos de contacto con fondo, toque de defensa/bita, rotura de amarras o dano a casco/muelle? Validar/solicitar: Survey reports, fotos, P&I.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-41",
        "priority": "A",
        "block": "Riesgos e incidentes",
        "question": "Que autoridad o actor lidera la investigacion y registro de incidentes en la zona? Validar/solicitar: Protocolos, contactos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-42",
        "priority": "M",
        "block": "Riesgos e incidentes",
        "question": "Que riesgos suelen advertir los aseguradores, capitanes o fletadores para Boca Chica? Validar/solicitar: Correspondencia P&I, clauses.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-43",
        "priority": "C",
        "block": "Datos para decision",
        "question": "Que informacion considera imprescindible verificar antes de contratar batimetria y dragado? Validar/solicitar: Listado priorizado.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-44",
        "priority": "C",
        "block": "Datos para decision",
        "question": "Que informacion cree que debe levantarse con batimetria: canal, darsena, berth pocket, aproximacion, fondeo u obstrucciones? Validar/solicitar: Comentarios tecnicos y mapa.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-45",
        "priority": "C",
        "block": "Datos para decision",
        "question": "Desde su experiencia, la operacion Handymax seria Go, Go condicionado o No-Go? Bajo que condiciones? Validar/solicitar: Razonamiento y evidencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-46",
        "priority": "A",
        "block": "Datos para decision",
        "question": "Que condicion comercial minima tendria que cumplirse para que un fletador acepte escalar en Boca Chica con Handymax? Validar/solicitar: Requisitos fletador / charter party.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AG-47",
        "priority": "M",
        "block": "Datos para decision",
        "question": "Que cambios en permisos, servicios, muelle o procedimiento mejorarian la confiabilidad de la escala? Validar/solicitar: Lista de mejoras.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": [
      {
        "id": "E-01",
        "document": "Lista de buques atendidos con nombre, fecha, LOA, manga, DWT, GT, calado y carga.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-02",
        "document": "SOF / Statement of Facts anonimizados de escalas relevantes.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-03",
        "document": "PDA/FDA, facturas o proformas de costos portuarios y servicios nauticos.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-04",
        "document": "Correos de aprobacion de practicos, remolcadores, autoridad o terminal.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-05",
        "document": "Cartas de protesta, reportes de demoras, reclamos o incidentes.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-06",
        "document": "Vessel particulars de buques comparables.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-07",
        "document": "Tarifarios vigentes de agencia, prácticos, remolcadores, amarradores y servicios.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-08",
        "document": "Contactos de capitanes, port captains, surveyors y proveedores con experiencia directa.",
        "source": "Documentos y evidencia a solicitar"
      }
    ]
  },
  {
    "title": "Administrador Y Autoridad Portuaria",
    "source_file": "02_Administrador_y_autoridad_portuaria modificado.docx",
    "slug": "administrador_y_autoridad_portuaria",
    "critical_questions": [
      {
        "number": "1",
        "question": "¿Cuáles son las restricciones oficiales vigentes de LOA, manga, calado, DWT, horario, viento, visibilidad y remolcadores para Puerto Andres / Boca Chica?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "¿Existe Port Handbook, reglamento de operaciones o circular que defina canal, dársena, fondeo, practicaje, remolcadores y maniobras nocturnas?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "¿Cuál es la última batimetría oficial o disponible del canal, dársena y área de atraque, y qué nivel de confianza tiene?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "¿Hay antecedentes de dragado, sedimentación, obstrucciones, rocas, coral, estructuras sumergidas o zonas con restricciones ambientales?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "El muelle, defensas, bitas y berth pocket están autorizados o son adecuados para un Handymax cargado bajo asistencia?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "Que permisos o no objeciones serian necesarios para batimetria, geotecnia, sedimentos, dragado y disposicion en Fase 2?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "¿Qué incidentes o restricciones de seguridad marítima han ocurrido en los últimos años?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "Desde la perspectiva de la autoridad/administrador, el Handymax es Go, Go condicionado o No-Go y por que?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "AP-01",
        "priority": "C",
        "block": "Gobernanza y jurisdicción Defina",
        "question": "la entidad administradora, autoridad maritima competente, concesionario/operador y responsabilidades sobre canal, muelle, ayudas, seguridad y autorizacion de maniobras. Validar/solicitar: Organigrama, decretos, concesion, reglamentos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-02",
        "priority": "C",
        "block": "Gobernanza y jurisdiccion Cuales son",
        "question": "los limites fisicos y juridicos del puerto, canal, area de maniobra, fondeo y zona de seguridad? Validar/solicitar: Plano georreferenciado, coordenadas, resoluciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-03",
        "priority": "A",
        "block": "Gobernanza y jurisdiccion",
        "question": "Que permisos o autorizaciones vigentes amparan la operacion portuaria actual y que tipo de cargas permite? Validar/solicitar: Permisos, licencias, autorizaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-04",
        "priority": "A",
        "block": "Gobernanza y jurisdiccion",
        "question": "Existe separacion entre autoridad portuaria, capitania, marina, operador privado y aduanas en aprobacion de buques? Validar/solicitar: Flujograma de aprobacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-05",
        "priority": "M",
        "block": "Gobernanza y jurisdiccion",
        "question": "Que cambios administrativos serian necesarios para recibir graneleros Handymax o cargas graneleras adicionales? Validar/solicitar: Requisitos formales y responsables.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-06",
        "priority": "C",
        "block": "Reglas y restricciones",
        "question": "Proveer restricciones oficiales de calado, LOA, manga, GT, DWT, tipo de buque, tipo de carga y condiciones de operacion. Validar/solicitar: Port Handbook, circulares, procedimientos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-07",
        "priority": "C",
        "block": "Reglas y restricciones",
        "question": "Las restricciones son absolutas o pueden evaluarse caso por caso con analisis, batimetria, simulacion o autorizacion especial? Validar/solicitar: Criterios de excepcion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-08",
        "priority": "C",
        "block": "Reglas y restricciones",
        "question": "Se autorizan maniobras nocturnas? Si no, que acondicionamientos permitirian evaluarlas? Validar/solicitar: Reglamento, iluminacion, AtoN, criterio de practicos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-09",
        "priority": "A",
        "block": "Reglas y restricciones Cuales son",
        "question": "las reglas para cierre por viento, ola, corriente, visibilidad, tormenta tropical, huracan o emergencia? Validar/solicitar: Procedimientos y registros.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-10",
        "priority": "A",
        "block": "Reglas y restricciones",
        "question": "Existe obligatoriedad de practico, numero minimo de remolcadores, lanchas o amarradores por porte de buque? Validar/solicitar: Tarifa/reglamento.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-11",
        "priority": "C",
        "block": "Cartografia y batimetria",
        "question": "Indique la ultima batimetria disponible para canal, darsena, berth pocket y zona de aproximacion: fecha, metodo, datum, responsable y formato. Validar/solicitar: Archivos XYZ, CAD, PDF, informe.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-12",
        "priority": "C",
        "block": "Cartografia y batimetria",
        "question": "Que cartas nauticas oficiales o planos internos usa la autoridad para aprobar maniobras? Validar/solicitar: Cartas, planos, fuentes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-13",
        "priority": "C",
        "block": "Cartografia y batimetria",
        "question": "Existen zonas con datos antiguos, baja densidad, sondajes dudosos, sedimentacion acelerada u obstrucciones no levantadas? Validar/solicitar: Informe de calidad o notas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-14",
        "priority": "A",
        "block": "Cartografia y batimetria",
        "question": "Que datum vertical y horizontal se usa: chart datum, MLLW, nivel medio del mar, WGS84 u otro? Validar/solicitar: Especificacion hidrografica.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-15",
        "priority": "A",
        "block": "Cartografia y batimetria",
        "question": "Existe registro de tasas de sedimentacion o necesidades de dragado de mantenimiento? Validar/solicitar: Historico de dragados, comparativos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-16",
        "priority": "C",
        "block": "Canal y aproximacion",
        "question": "Describa el canal de acceso: alineamiento, ancho nominal, ancho util, tramos criticos, curvas, marcas, boyas y ayudas visuales. Validar/solicitar: Plano y coordenadas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-17",
        "priority": "C",
        "block": "Canal y aproximacion Cuales son",
        "question": "los criterios de margen lateral, velocidad, seguridad y trafico aplicados a buques grandes? Validar/solicitar: Manual de maniobra o criterio de practicos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-18",
        "priority": "C",
        "block": "Canal y aproximacion Hay interferencias",
        "question": "con embarcaciones menores, turismo, pesca, fondeo, cables, tuberias, zonas militares o zonas ambientales? Validar/solicitar: Plano de restricciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-19",
        "priority": "A",
        "block": "Canal y aproximación",
        "question": "Existe control de trafico, VTS, radio canales, reportes obligatorios y puntos de llamada? Validar/solicitar: Procedimientos VHF/VTS.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-20",
        "priority": "A",
        "block": "Canal y aproximacion",
        "question": "Que ayudas a la navegacion estan operativas y cual es su plan de mantenimiento? Validar/solicitar: Inventario AtoN, reporte IALA si existe.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-21",
        "priority": "C",
        "block": "Profundidad, UKC y squat",
        "question": "Que criterio de UKC minimo exige la autoridad para buques cargados y quien lo aprueba? Validar/solicitar: Regla escrita o criterio tecnico.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-22",
        "priority": "C",
        "block": "Profundidad, UKC y squat",
        "question": "El puerto exige calculo de squat o tabla de mareas para aprobar un buque? Validar/solicitar: Formatos de aprobacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-23",
        "priority": "A",
        "block": "Profundidad, UKC y squat",
        "question": "Existe registro de mareas local, corriente, oleaje y nivel de agua para planificar maniobras? Validar/solicitar: Estaciones, series, fuentes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-24",
        "priority": "M",
        "block": "Profundidad, UKC y squat",
        "question": "Que tolerancia por sedimentacion o incertidumbre se aplica entre batimetrias? Validar/solicitar: Criterios de conservadurismo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-25",
        "priority": "C",
        "block": "Darsena y giro",
        "question": "Indique dimensiones utiles de darsena/circulo de maniobra y restricciones para giro de buques de mayor porte. Validar/solicitar: Planos y criterios de maniobra.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-26",
        "priority": "C",
        "block": "Darsena y giro",
        "question": "¿Existe espacio para abortar, detener, girar o maniobrar de emergencia un Handymax asistido? Validar/solicitar: Analisis existente, experiencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-27",
        "priority": "A",
        "block": "Darsena y giro",
        "question": "El tráfico local o el uso de otros muelles reduce el area disponible para la maniobra? Validar/solicitar: Plano de trafico y ocupacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-28",
        "priority": "C",
        "block": "Muelle y atraque",
        "question": "Indique longitud util, orientacion, elevacion, profundidad al costado y condicion del berth pocket. Validar/solicitar: Planos as-built, batimetria al costado.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-29",
        "priority": "C",
        "block": "Muelle y atraque",
        "question": "Proveer especificaciones de defensas: tipo, separacion, energia, fecha de instalacion, estado y mantenimiento. Validar/solicitar: Fichas tecnicas, inspecciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-30",
        "priority": "C",
        "block": "Muelle y atraque",
        "question": "Proveer capacidad de bitas, ganchos, cornamusas, puntos de amarre y restricciones de lineas. Validar/solicitar: Planos, certificados, pruebas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-31",
        "priority": "C",
        "block": "Muelle y atraque Hay estudios estructurales",
        "question": "que validen cargas de atraque y amarre para un Handymax cargado? Validar/solicitar: Informe estructural.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-32",
        "priority": "A",
        "block": "Muelle y atraque",
        "question": "Que restricciones existen para permanencia al costado: oleaje, viento, surge, passing ships, lineas, gangway, equipos? Validar/solicitar: Registros operativos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-33",
        "priority": "M",
        "block": "Muelle y atraque",
        "question": "Que reparaciones o mejoras de muelle se consideran necesarias antes de buques mayores? Validar/solicitar: Plan de mantenimiento/inversion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-34",
        "priority": "C",
        "block": "Operaciones y seguridad",
        "question": "Describa procedimiento de autorizacion de entrada, fondeo, practico a bordo, remolcadores, atraque, amarre, operaciones y zarpe. Validar/solicitar: Manual operativo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-35",
        "priority": "A",
        "block": "Operaciones y seguridad",
        "question": "Existen procedimientos de emergencia para varadura, perdida de propulsion, falla de remolcador, incendio, derrame o huracan? Validar/solicitar: Plan de emergencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-36",
        "priority": "A",
        "block": "Operaciones y seguridad Cuales son",
        "question": "los recursos de respuesta: lanchas, bomberos, oil spill, seguridad, ambulancia, salvamento, comunicaciones? Validar/solicitar: Inventario de recursos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-37",
        "priority": "M",
        "block": "Operaciones y seguridad",
        "question": "Que requisitos ISPS, seguridad portuaria o control de acceso aplican durante la visita y futuras operaciones? Validar/solicitar: Plan de proteccion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-38",
        "priority": "M",
        "block": "General",
        "question": "Operaciones y seguridad Hay restricciones por instalaciones vecinas, combustible, carga peligrosa, comunidad o zonas sensibles? Validar/solicitar: Mapa de riesgos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-39",
        "priority": "C",
        "block": "Remolcadores y apoyo",
        "question": "La autoridad define bollard pull minimo o numero de remolcadores por tamaño de buque? Validar/solicitar: Reglamento o criterio.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-40",
        "priority": "C",
        "block": "Remolcadores y apoyo",
        "question": "Que proveedores estan autorizados y desde donde operan? Validar/solicitar: Lista de proveedores.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-41",
        "priority": "A",
        "block": "Remolcadores y apoyo",
        "question": "Se exige plan de remolcadores o maniobra firmado por practico/autoridad para buques no habituales? Validar/solicitar: Formato o ejemplos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-42",
        "priority": "C",
        "block": "Ambiental y dragado",
        "question": "Que condicionantes ambientales aplican a batimetria, geotecnia, sedimentos, dragado y disposicion de material? Validar/solicitar: Permisos, terminos de referencia regulatorios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-43",
        "priority": "C",
        "block": "Ambiental y dragado Hay zonas de coral, pastos marinos, manglar, areas protegidas, pesca o restricciones",
        "question": "que afecten dragado? Validar/solicitar: Mapas ambientales y autorizaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-44",
        "priority": "A",
        "block": "Ambiental y dragado",
        "question": "¿Cuáles son las rutas institucionales para aprobar batimetria, muestreo de sedimentos, dragado y disposicion? Validar/solicitar: Flujograma, contactos, tiempos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-45",
        "priority": "A",
        "block": "Ambiental y dragado",
        "question": "¿Existe sitio de disposición autorizado o histórico para material dragado? Validar/solicitar: Permisos, estudios, coordenadas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-46",
        "priority": "M",
        "block": "Ambiental y dragado",
        "question": "¿Qué información técnica exigiría la autoridad antes de evaluar un dragado de profundización? Validar/solicitar: Requisitos de estudio.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-47",
        "priority": "C",
        "block": "Incidentes y lecciones",
        "question": "Proveer resumen de incidentes, cierres, varaduras, golpes, roturas de amarras, fallas de remolcador o reclamos relevantes. Validar/solicitar: Registro oficial o anonimo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-48",
        "priority": "A",
        "block": "Incidentes y lecciones",
        "question": "Como se registran e investigan incidentes nauticos dentro del puerto? Validar/solicitar: Procedimiento, autoridad competente.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-49",
        "priority": "M",
        "block": "Incidentes y lecciones",
        "question": "Que medidas correctivas se han implementado luego de incidentes o near misses? Validar/solicitar: Actas y planes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-50",
        "priority": "C",
        "block": "Decision Fase 1 Bajo",
        "question": "que condiciones la autoridad consideraria aceptable evaluar un Handymax cargado? Validar/solicitar: Condiciones precedentes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-51",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Que elemento podria ser No-Go aun con dragado: geometria, muelle, remolcadores, ambiente, trafico, permisos o seguridad? Validar/solicitar: Razonamiento tecnico.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-52",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Que areas deben incluirse obligatoriamente en batimetria de Fase 2 si la decision es Go o Go condicionado? Validar/solicitar: Mapa o listado de coordenadas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-53",
        "priority": "A",
        "block": "Data Room",
        "question": "Que documentos pueden entregarse durante la visita y cuales requieren solicitud formal? Validar/solicitar: Registro de entrega.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "AP-54",
        "priority": "A",
        "block": "General",
        "question": "Data Room Quien sera punto focal para aclaraciones posteriores y validacion de minutas? Validar/solicitar: Contacto oficial.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": [
      {
        "id": "E-01",
        "document": "Port Handbook, reglamento operativo, circulares y restricciones vigentes.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-02",
        "document": "Plano general del puerto, canal, darsena, muelles, fondeo, ayudas y limites de jurisdiccion.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-03",
        "document": "Batimetria existente con fecha, metodo, datum, control de calidad y archivos editables.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-04",
        "document": "Planos as-built del muelle, defensas, bitas, estructuras y areas de amarre.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-05",
        "document": "Inventario y estado de ayudas a la navegacion e iluminacion.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-06",
        "document": "Registro de dragados, sedimentacion, obstrucciones e incidentes nauticos.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-07",
        "document": "Procedimientos de emergencia, seguridad, ISPS y cierre por clima.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-08",
        "document": "Requisitos regulatorios para batimetria, geotecnia, sedimentos, dragado y disposicion.",
        "source": "Documentos y evidencia a solicitar"
      }
    ]
  },
  {
    "title": "Pilotos Y Practicos",
    "source_file": "03_Pilotos_y_practicos modificado (1).docx",
    "slug": "pilotos_y_practicos",
    "critical_questions": [
      {
        "number": "1",
        "question": "Con la informacion actual, considera fisicamente viable la entrada cargado de un Handymax a Boca Chica? Bajo que calado y condiciones?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "Cual es el tramo del canal o aproximacion que mas limita la maniobra: profundidad, ancho, alineamiento, corriente, viento, visibilidad o trafico?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "Existe espacio suficiente para girar, controlar abatimiento y alinear el buque al muelle? Donde estaria el punto de falla?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "Cuantos remolcadores y con que bollard pull serian necesarios para entrada, atraque, desatraque y emergencia?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "Cuales son los limites de viento, corriente, ola, marea, luz diurna y visibilidad para un buque de ese porte?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "Que UKC y margen por squat considera aceptables para un buque cargado en la aproximacion y al costado?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "Que datos batimetricos o simulaciones son indispensables antes de pasar a Fase 2 o a una aprobacion operativa?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "La recomendacion preliminar del piloto seria Go, Go condicionado o No-Go para el Handymax de diseno?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "PI-01",
        "priority": "C",
        "block": "Experiencia del piloto Cuantos anos de experiencia tiene",
        "question": "como piloto/practico en Boca Chica y que tipos de buques ha maniobrado alli? Validar/solicitar: Licencia, registro de maniobras, ejemplos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-02",
        "priority": "C",
        "block": "Experiencia del piloto",
        "question": "Indique los mayores buques maniobrados en la zona: nombre, LOA, manga, calado, tipo de carga, fecha y condiciones. Validar/solicitar: Registro de practico, SOF, memoria de maniobra.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-03",
        "priority": "A",
        "block": "Experiencia del piloto",
        "question": "Ha maniobrado graneleros, bulk carriers, cementeros o buques con calados cercanos al objetivo? Validar/solicitar: Ejemplos verificables.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-04",
        "priority": "A",
        "block": "General",
        "question": "Experiencia del piloto Cuales maniobras historicas considera comparables y cuales no lo son? Validar/solicitar: Diferencias tecnicas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-05",
        "priority": "C",
        "block": "Buque de diseno Para un Handymax,",
        "question": "que LOA, manga y calado maximo considera el limite practico de evaluacion en Boca Chica? Validar/solicitar: Criterio propio y supuestos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-06",
        "priority": "C",
        "block": "Buque de diseno",
        "question": "Que caracteristicas del buque afectan mas la maniobra: calado, obra muerta, potencia, bow thruster, timon, respuesta de maquina, estado cargado? Validar/solicitar: Vessel particulars.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-07",
        "priority": "A",
        "block": "General",
        "question": "Buque de diseno Hay diferencia critica entre entrar cargado y salir en lastre o parcialmente cargado? Validar/solicitar: Explicacion de control y viento.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-08",
        "priority": "C",
        "block": "Ruta de entrada",
        "question": "Describa desde mar abierto/fondeo hasta el muelle: punto de embarque del practico, rumbos, tramos, velocidades, puntos de llamada y referencias. Validar/solicitar: Croquis marcado por el piloto.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-09",
        "priority": "C",
        "block": "Ruta de entrada Donde inicia realmente",
        "question": "el tramo critico de la aproximacion y por que? Validar/solicitar: Coordenadas o referencia visual.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-10",
        "priority": "C",
        "block": "Ruta de entrada Cuales son",
        "question": "los rumbos o alineaciones que el buque debe mantener y donde existe riesgo de abatimiento? Validar/solicitar: Croquis, marcas de enfilacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-11",
        "priority": "C",
        "block": "Ruta de entrada",
        "question": "Que velocidad sobre el fondo y sobre el agua considera segura por tramo para un Handymax? Validar/solicitar: Criterio y condiciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-12",
        "priority": "C",
        "block": "Ruta de entrada",
        "question": "Existe posibilidad real de abortar la entrada una vez comprometido el buque? Donde y bajo que condiciones? Validar/solicitar: Puntos de abortaje.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-13",
        "priority": "A",
        "block": "Ruta de entrada",
        "question": "Que ayudas a la navegacion, boyas, luces, marcas o referencias usa actualmente y cuales faltan o son poco confiables? Validar/solicitar: Inventario, fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-14",
        "priority": "A",
        "block": "Ruta de entrada",
        "question": "Las maniobras son seguras de noche? Que faltaria para evaluarlo? Validar/solicitar: Iluminacion, AtoN, criterios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-15",
        "priority": "C",
        "block": "Canal y geometria",
        "question": "Cual es el ancho util real del canal percibido por el piloto y donde se reduce el margen? Validar/solicitar: Tramos en croquis.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-16",
        "priority": "C",
        "block": "Canal y geometria Hay curvas, cambios de rumbo o zonas de poca referencia",
        "question": "que compliquen el control de un buque largo? Validar/solicitar: Croquis y comentarios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-17",
        "priority": "C",
        "block": "Canal y geometria",
        "question": "Existen efectos de banco, succion, corriente cruzada o remolinos que deban considerarse? Validar/solicitar: Experiencias previas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-18",
        "priority": "A",
        "block": "Canal y geometria",
        "question": "Que interferencias de trafico local o embarcaciones menores ocurren durante maniobras? Validar/solicitar: Ejemplos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-19",
        "priority": "C",
        "block": "Profundidad, UKC y squat",
        "question": "Que profundidad minima considera necesaria para el calado objetivo, separando UKC estatico, squat, oleaje, marea e incertidumbre batimetrica? Validar/solicitar: Calculo preliminar del piloto.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-20",
        "priority": "C",
        "block": "Profundidad, UKC y squat",
        "question": "Que UKC minimo aceptaria para canal y para permanencia al costado? Validar/solicitar: Regla de practico o autoridad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-21",
        "priority": "C",
        "block": "General",
        "question": "Profundidad, UKC y squat Donde espera mayor squat o perdida de control por poca agua? Validar/solicitar: Tramos criticos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-22",
        "priority": "A",
        "block": "Profundidad, UKC y squat",
        "question": "La marea es operacionalmente util para ganar margen o es demasiado pequena/incierta? Validar/solicitar: Tablas, experiencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-23",
        "priority": "A",
        "block": "General",
        "question": "Profundidad, UKC y squat Hay evidencia de sedimentacion, fondo duro, obstrucciones o variaciones de profundidad no capturadas en planos? Validar/solicitar: Experiencias, sondajes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-24",
        "priority": "C",
        "block": "General",
        "question": "Viento, corriente, ola y clima Cuales son direcciones y rangos de viento mas criticos para entrada, giro, atraque y permanencia al costado? Validar/solicitar: Limites operativos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-25",
        "priority": "C",
        "block": "Viento, corriente, ola y clima",
        "question": "Que corriente predomina y donde se manifiesta mas: canal, bocana, darsena, muelle? Validar/solicitar: Croquis y estacionalidad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-26",
        "priority": "C",
        "block": "Viento, corriente, ola y clima",
        "question": "El oleaje o mar de fondo afecta el control, el UKC o la seguridad junto al muelle? Validar/solicitar: Condiciones y ejemplos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-27",
        "priority": "A",
        "block": "Viento, corriente, ola y clima",
        "question": "Que meses, horas o condiciones se evitan para maniobras mayores? Validar/solicitar: Ventanas operativas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-28",
        "priority": "A",
        "block": "Viento, corriente, ola y clima",
        "question": "Que fuentes meteorologicas y oceanograficas consulta el practico antes de decidir? Validar/solicitar: Fuentes y umbrales.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-29",
        "priority": "C",
        "block": "Giro y darsena",
        "question": "Describa como giraria el Handymax: lugar, sentido de giro, velocidad, tugs, uso de maquina/timon y margen restante. Validar/solicitar: Croquis de giro.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-30",
        "priority": "C",
        "block": "General",
        "question": "Giro y darsena Es necesario girar antes de atracar, despues de descargar o puede salir de proa/popa? Validar/solicitar: Secuencias alternativas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-31",
        "priority": "C",
        "block": "Giro y darsena",
        "question": "Que diametro util considera disponible y que margen minimo exigiria respecto a LOA? Validar/solicitar: Criterio geometrico.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-32",
        "priority": "C",
        "block": "Giro y darsena Donde podria tocar fondo, estructura, talud, boya o trafico durante",
        "question": "el giro? Validar/solicitar: Puntos de falla.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-33",
        "priority": "A",
        "block": "Giro y darsena",
        "question": "El giro se afecta por otros buques atracados, fondeados o operaciones simultaneas? Validar/solicitar: Condiciones de exclusividad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-34",
        "priority": "C",
        "block": "Atraque cargado",
        "question": "Describa la aproximacion final al muelle: angulo, velocidad, posicion de tugs, lineas iniciales y limites de control. Validar/solicitar: Croquis de atraque.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-35",
        "priority": "C",
        "block": "Atraque cargado",
        "question": "La profundidad al costado y berth pocket permiten aproximacion lenta y permanencia sin riesgo de contacto con fondo? Validar/solicitar: Datos y supuestos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-36",
        "priority": "C",
        "block": "Atraque cargado",
        "question": "Que restricciones de fenders, bitas, longitud de muelle o lineas de amarre afectan al Handymax? Validar/solicitar: Observaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-37",
        "priority": "C",
        "block": "Atraque cargado",
        "question": "Que velocidad maxima de contacto recomendaria y como se controla? Validar/solicitar: Criterio de seguridad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-38",
        "priority": "A",
        "block": "Atraque cargado",
        "question": "Se requiere apoyo de amarradores adicionales, lanchas o equipo especial? Validar/solicitar: Procedimiento.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-39",
        "priority": "C",
        "block": "Permanencia al costado Bajo",
        "question": "que condiciones de viento/oleaje/corriente el buque podria permanecer seguro durante descarga? Validar/solicitar: Limites operativos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-40",
        "priority": "A",
        "block": "Permanencia al costado Hay riesgo de surge, movimientos excesivos, rotura de amarras o contacto",
        "question": "con defensas? Validar/solicitar: Experiencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-41",
        "priority": "C",
        "block": "Desatraque y zarpe",
        "question": "Describa la secuencia de desatraque y zarpe con Handymax: lineas, tugs, giro, salida, velocidad y abortaje. Validar/solicitar: Croquis de salida.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-42",
        "priority": "C",
        "block": "Desatraque y zarpe",
        "question": "La salida es mas o menos critica que la entrada? Por que? Validar/solicitar: Comparacion de riesgos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-43",
        "priority": "C",
        "block": "Desatraque y zarpe",
        "question": "Que condicion de calado/lastre seria preferible para zarpar de manera segura? Validar/solicitar: Requisitos de lastre/trim.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-44",
        "priority": "A",
        "block": "Desatraque y zarpe Puede zarpar de noche si",
        "question": "la entrada fue de dia? Que limitaciones aplican? Validar/solicitar: Criterio de horario.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-45",
        "priority": "C",
        "block": "General",
        "question": "Remolcadores Cuantos remolcadores son minimos para entrada/atraque y para desatraque/zarpe? Validar/solicitar: Configuracion por fase.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-46",
        "priority": "C",
        "block": "Remolcadores",
        "question": "Que bollard pull, tipo de propulsion y posicionamiento de tugs requiere para controlar un Handymax? Validar/solicitar: BP requerido y roles.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-47",
        "priority": "C",
        "block": "Remolcadores",
        "question": "Que ocurre si falla un remolcador durante tramo critico? Existe margen o plan de contingencia? Validar/solicitar: Escenario de emergencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-48",
        "priority": "A",
        "block": "Remolcadores",
        "question": "Los remolcadores locales tienen experiencia y capacidad para esta maniobra? Validar/solicitar: Nombres, BP, disponibilidad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-49",
        "priority": "M",
        "block": "Remolcadores",
        "question": "Se requeriria escort tug o tugs de mayor potencia movilizados desde otro puerto? Validar/solicitar: Condicion precedente.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-50",
        "priority": "C",
        "block": "General",
        "question": "Seguridad y emergencias Defina puntos de no retorno, abortaje, fondeo de emergencia y medidas ante falla de maquina/timon. Validar/solicitar: Mapa de contingencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-51",
        "priority": "C",
        "block": "Seguridad y emergencias",
        "question": "Que incidente seria mas probable con Handymax: varadura, golpe al muelle, perdida de control, rotura de linea, demora por clima? Validar/solicitar: Ranking de riesgos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-52",
        "priority": "A",
        "block": "Seguridad y emergencias",
        "question": "Que comunicaciones VHF, personal y coordinacion se requieren para la maniobra? Validar/solicitar: Canales y roles.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-53",
        "priority": "M",
        "block": "Seguridad y emergencias",
        "question": "Se necesita simulacion de puente para validar maniobra antes de aprobar? Que escenarios incluiria? Validar/solicitar: Escenarios de simulacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-54",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Liste condiciones minimas para emitir Go condicionado: batimetria, dragado, ayudas, tugs, horario, clima, muelle, simulacion. Validar/solicitar: Lista priorizada.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-55",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Que condicion seria No-Go aunque se dragara a la profundidad objetivo? Validar/solicitar: Restriccion no mitigable.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-56",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Que areas exactas deben levantarse con batimetria multihaz para cerrar incertidumbres? Validar/solicitar: Mapa/croquis.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-57",
        "priority": "A",
        "block": "Condiciones minimas",
        "question": "Que datum, precision y entrega espera el piloto para confiar en una nueva batimetria? Validar/solicitar: Criterio de aceptacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-58",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Con lo conocido hoy, emita recomendacion preliminar Go, Go condicionado o No-Go y justifique. Validar/solicitar: Dictamen verbal y condiciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PI-59",
        "priority": "M",
        "block": "Decision Fase 1",
        "question": "Que actor local deberia ser entrevistado para confirmar o contradecir esta evaluacion? Validar/solicitar: Contactos.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": []
  },
  {
    "title": "Operadores De Remolcadores",
    "source_file": "04_Operadores_de_remolcadores modificado (1).docx",
    "slug": "operadores_de_remolcadores",
    "critical_questions": [
      {
        "number": "1",
        "question": "Que remolcadores pueden estar disponibles para Boca Chica, con que bollard pull certificado y en cuanto tiempo?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "Cuantos remolcadores considera minimos para entrada, giro, atraque cargado, desatraque y emergencia de un Handymax?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "Los remolcadores pueden operar con seguridad dentro del canal, darsena y al costado con el espacio/profundidad disponible?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "Existe remolcador de respaldo si falla uno durante la maniobra o si cambia el clima?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "Que limites de viento, corriente, ola y visibilidad aplican al servicio?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "Han asistido buques comparables en Boca Chica o puertos similares? Identificar casos.",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "Que informacion tecnica necesitan antes de comprometerse a la maniobra?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "Desde el punto de vista de remolcadores, el Handymax es Go, Go condicionado o No-Go?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "RE-01",
        "priority": "C",
        "block": "Flota disponible",
        "question": "Liste remolcadores propios o contratables para Boca Chica, con nombre, ano, tipo, HP, bollard pull, dimensiones, calado y puerto base. Validar/solicitar: Fichas tecnicas, certificados BP.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-02",
        "priority": "C",
        "block": "Flota disponible",
        "question": "Indique cuales estan disponibles localmente y cuales requieren movilizacion desde otro puerto. Validar/solicitar: Ubicacion, ETA de movilizacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-03",
        "priority": "C",
        "block": "Flota disponible",
        "question": "Cual es el estado operativo actual de cada unidad y su disponibilidad durante la ventana de visita/operacion? Validar/solicitar: Certificados, mantenimiento.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-04",
        "priority": "A",
        "block": "Flota disponible",
        "question": "Que tipo de propulsion tienen: ASD, tractor, convencional, Voith, twin screw? Validar/solicitar: Especificaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-05",
        "priority": "A",
        "block": "General",
        "question": "Flota disponible Tienen winch, towing hook, fire fighting, equipos de comunicaciones, lineas propias y defensas adecuadas? Validar/solicitar: Inventario de equipos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-06",
        "priority": "A",
        "block": "Flota disponible",
        "question": "Cual es la certificacion, clase y tripulacion minima requerida para operar? Validar/solicitar: Certificados y licencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-07",
        "priority": "C",
        "block": "Experiencia operacional",
        "question": "Que buques de mayor porte han asistido en Boca Chica o puertos similares? Validar/solicitar: SOF, facturas, reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-08",
        "priority": "A",
        "block": "Experiencia operacional",
        "question": "Han asistido bulk carriers, Handy/Handymax, tanker, cementeros o buques con gran obra muerta? Validar/solicitar: Ejemplos y condiciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-09",
        "priority": "A",
        "block": "Experiencia operacional",
        "question": "Que maniobras fueron mas exigentes: entrada, giro, atraque, desatraque, emergencia o mal tiempo? Validar/solicitar: Lecciones aprendidas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-10",
        "priority": "C",
        "block": "Configuracion de maniobra Para un Handymax cargado, cuantos remolcadores propone en entrada y donde",
        "question": "se ubicarian? Validar/solicitar: Croquis de posiciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-11",
        "priority": "C",
        "block": "General",
        "question": "Configuracion de maniobra Cuantos remolcadores propone para giro en darsena y atraque final? Validar/solicitar: Croquis y BP por posicion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-12",
        "priority": "C",
        "block": "General",
        "question": "Configuracion de maniobra Cuantos remolcadores propone para desatraque y zarpe? Validar/solicitar: Secuencia de salida.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-13",
        "priority": "C",
        "block": "General",
        "question": "Configuracion de maniobra Requiere escort tug durante aproximacion o solo tugs en darsena/muelle? Validar/solicitar: Criterio operacional.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-14",
        "priority": "C",
        "block": "Configuracion de maniobra",
        "question": "Que bollard pull total y efectivo considera necesario considerando viento transversal y corriente? Validar/solicitar: Calculo o criterio.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-15",
        "priority": "A",
        "block": "Configuracion de maniobra",
        "question": "Que limitaciones impone el calado y maniobrabilidad propia del remolcador en aguas someras? Validar/solicitar: Profundidad minima y margen.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-16",
        "priority": "C",
        "block": "Espacio de trabajo",
        "question": "El canal y darsena permiten que los remolcadores trabajen sin riesgo de tocar fondo o quedar atrapados entre buque y estructura? Validar/solicitar: Comentarios y croquis.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-17",
        "priority": "C",
        "block": "Espacio de trabajo",
        "question": "Existen zonas donde un remolcador no puede empujar o tirar por poca profundidad, piedras, oleaje, defensas o trafico? Validar/solicitar: Puntos criticos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-18",
        "priority": "A",
        "block": "Espacio de trabajo",
        "question": "Que longitudes de lineas o puntos de amarre al buque son recomendables para esta maniobra? Validar/solicitar: Procedimiento de remolque.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-19",
        "priority": "A",
        "block": "Espacio de trabajo",
        "question": "El muelle y las defensas permiten operar tugs en aproximacion lateral sin dañar estructura o remolcador? Validar/solicitar: Inspeccion visual.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-20",
        "priority": "C",
        "block": "Limites ambientales",
        "question": "Indique limites de viento para empuje/tiron efectivo por tipo de buque y maniobra. Validar/solicitar: Tabla interna o experiencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-21",
        "priority": "C",
        "block": "Limites ambientales",
        "question": "Indique limites de corriente y oleaje para operar remolcadores de forma segura en Boca Chica. Validar/solicitar: Criterios de seguridad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-22",
        "priority": "A",
        "block": "Limites ambientales",
        "question": "Que condiciones provocan cancelacion o demora del servicio? Validar/solicitar: Registros de cancelacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-23",
        "priority": "A",
        "block": "Limites ambientales",
        "question": "Como afecta la visibilidad, lluvia, noche o iluminacion a la operacion de remolcadores? Validar/solicitar: Criterios de operacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-24",
        "priority": "C",
        "block": "Emergencias",
        "question": "Que plan aplicaria si el Handymax pierde propulsion o timon durante entrada o giro? Validar/solicitar: Plan de contingencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-25",
        "priority": "C",
        "block": "Emergencias",
        "question": "Que plan aplicaria si un remolcador falla durante el tramo critico? Validar/solicitar: Redundancia y backup.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-26",
        "priority": "A",
        "block": "General",
        "question": "Emergencias Tienen equipos para asistencia contra incendio, derrame, salvamento o remolque de emergencia? Validar/solicitar: Certificados y equipos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-27",
        "priority": "M",
        "block": "Emergencias Cuanto tiempo toma activar remolcador de respaldo y",
        "question": "desde donde? Validar/solicitar: ETA y contacto.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-28",
        "priority": "C",
        "block": "Coordinacion",
        "question": "Como se coordina con practicos, capitania, agencia, amarradores y buque? Validar/solicitar: Canales VHF, procedimientos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-29",
        "priority": "A",
        "block": "Coordinacion Quien emite ordenes durante",
        "question": "la maniobra y como se manejan desacuerdos de seguridad? Validar/solicitar: Procedimiento.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-30",
        "priority": "A",
        "block": "Coordinacion",
        "question": "Que informacion del buque requiere antes de confirmar servicio? Validar/solicitar: Vessel particulars, maniobra, calados.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-31",
        "priority": "A",
        "block": "General",
        "question": "Coordinacion Requieren plan de maniobra o reunion previa antes de un primer Handymax? Validar/solicitar: Checklist de pre-maniobra.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-32",
        "priority": "M",
        "block": "Costos y contratos",
        "question": "Indique estructura de tarifas: movilizacion, espera, asistencia, emergencia, noche, clima y cancelacion. Validar/solicitar: Tarifario/proforma.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-33",
        "priority": "M",
        "block": "Costos y contratos",
        "question": "Que condiciones comerciales deben cerrarse con anticipacion para garantizar disponibilidad? Validar/solicitar: Contrato, anticipo, notice.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-34",
        "priority": "M",
        "block": "Costos y contratos",
        "question": "Que notice minimo requiere para movilizar tugs adicionales o de mayor potencia? Validar/solicitar: SLA.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-35",
        "priority": "C",
        "block": "Riesgos Cuales son",
        "question": "los principales riesgos de asistir un Handymax en Boca Chica? Validar/solicitar: Ranking de riesgos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-36",
        "priority": "C",
        "block": "Riesgos",
        "question": "Que restriccion de canal, darsena, muelle o clima podria hacer la maniobra No-Go para remolcadores? Validar/solicitar: Criterio no negociable.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-37",
        "priority": "C",
        "block": "Riesgos",
        "question": "Que condiciones convertirian la maniobra en Go condicionado aceptable? Validar/solicitar: Lista de condiciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-38",
        "priority": "C",
        "block": "Fase 2",
        "question": "Que informacion de batimetria, simulacion o diseno de muelle necesita para confirmar la configuracion final? Validar/solicitar: Alcance de datos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-39",
        "priority": "A",
        "block": "Fase 2 Participarian en simulacion de maniobras o taller HAZID?",
        "question": "Que escenarios recomiendan? Validar/solicitar: Disponibilidad y escenarios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "RE-40",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Con la informacion actual, recomendacion Go, Go condicionado o No-Go desde remolcadores. Validar/solicitar: Justificacion.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": [
      {
        "id": "E-01",
        "document": "Fichas tecnicas y certificados de bollard pull de remolcadores disponibles.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-02",
        "document": "Certificados de clase, navegabilidad, seguro, tripulacion y equipos de emergencia.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-03",
        "document": "Registro de servicios a buques comparables con fechas y condiciones.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-04",
        "document": "Procedimientos de coordinacion con practicos, capitania y buques.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-05",
        "document": "Tarifario o proforma de remolcadores, movilizacion, espera y emergencia.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-06",
        "document": "Plan de mantenimiento y disponibilidad de flota.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-07",
        "document": "Croquis de configuracion minima de remolcadores para Handymax.",
        "source": "Documentos y evidencia a solicitar"
      }
    ]
  },
  {
    "title": "Compania De Batimetria Y Dragado",
    "source_file": "05_Compania_de_batimetria_y_dragado modificado (1).docx",
    "slug": "compania_de_batimetria_y_dragado",
    "critical_questions": [
      {
        "number": "1",
        "question": "¿Existe batimetría reciente y confiable del canal, de la dársena y del frente de atraque? ¿Qué vacíos impiden decidir con confianza?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "¿Qué área mínima debería levantarse con multihaz para validar entrada, giro, atraque y zarpe de Handymax?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "¿Qué datum vertical/horizontal, precisión, control de marea y QA/QC recomienda para que pilotos y autoridad acepten resultados?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "¿Qué riesgos geológicos o ambientales pueden afectar la dragabilidad: fondo duro, roca, coral, obstrucciones, sedimentos contaminados?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "¿Qué permisos o no objeciones son necesarios para batimetría, geotecnia, sedimentos, dragado y disposición?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "¿Existe capacidad local de dragado y disposición para una profundización razonable? ¿Qué plazos y restricciones aplican?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "¿Qué información mínima se requiere para estimar volumen, taludes, overdepth y costo conceptual en Fase 2?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "¿Cuáles son los principales No-Go o Go condicionado por batimetría/dragado?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "BD-01",
        "priority": "C",
        "block": "Datos existentes",
        "question": "Que batimetrias existen de Boca Chica / Puerto Andres y quien las produjo? Indicar fecha, metodo, cobertura, datum y formato. Validar/solicitar: Informes, archivos XYZ/CAD, metadatos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-02",
        "priority": "C",
        "block": "Datos existentes",
        "question": "La informacion existente cubre canal, aproximacion, darsena, berth pocket, zonas laterales y taludes? Validar/solicitar: Mapa de cobertura.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-03",
        "priority": "C",
        "block": "Datos existentes",
        "question": "Que nivel de confianza tienen los datos para tomar una decision preliminar de Handymax? Validar/solicitar: QA/QC o criterio experto.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-04",
        "priority": "A",
        "block": "Datos existentes",
        "question": "Existen levantamientos historicos que permitan estimar sedimentacion o cambios morfologicos? Validar/solicitar: Series historicas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-05",
        "priority": "A",
        "block": "Datos existentes",
        "question": "Existen registros de obstrucciones, roca, estructuras sumergidas, cables, tuberias o restos? Validar/solicitar: Mapas, inspecciones, side scan.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-06",
        "priority": "C",
        "block": "Area de levantamiento Dibuje o",
        "question": "describa el poligono minimo de batimetria para validar entrada, maniobra, atraque y salida. Validar/solicitar: Coordenadas y plano.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-07",
        "priority": "C",
        "block": "Area de levantamiento",
        "question": "Que extension lateral fuera del canal debe cubrirse para abatimiento, contingencia y taludes? Validar/solicitar: Criterio de margen.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-08",
        "priority": "C",
        "block": "General",
        "question": "Area de levantamiento Debe incluirse zona de fondeo, area de espera, rutas alternas o zona de abortaje? Validar/solicitar: Justificacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-09",
        "priority": "C",
        "block": "Area de levantamiento",
        "question": "Que densidad de sondaje y resolucion son necesarias para detectar obstrucciones relevantes para Handymax? Validar/solicitar: Especificacion tecnica.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-10",
        "priority": "A",
        "block": "General",
        "question": "Area de levantamiento Recomienda multihaz, monohaz, side scan sonar, magnetometro o combinacion? Validar/solicitar: Alcance recomendado.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-11",
        "priority": "C",
        "block": "Datum y control",
        "question": "Que datum vertical debe usarse para que el resultado sea aceptado por autoridad, pilotos y diseno de dragado? Validar/solicitar: Criterio y fuentes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-12",
        "priority": "C",
        "block": "Datum y control",
        "question": "Que control de marea/nivel de agua debe implementarse durante el levantamiento? Validar/solicitar: Estacion, mareografo, metodo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-13",
        "priority": "A",
        "block": "Datum y control",
        "question": "Que sistema horizontal y geodesico se recomienda? Validar/solicitar: WGS84, UTM, coordenadas locales.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-14",
        "priority": "A",
        "block": "Datum y control",
        "question": "Que calibraciones y pruebas requiere el equipo: patch test, bar check, sound velocity, offsets? Validar/solicitar: Plan QA/QC.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-15",
        "priority": "C",
        "block": "Datum y control",
        "question": "Que incertidumbre vertical/horizontal seria aceptable para estimar UKC y volumen de dragado preliminar? Validar/solicitar: Norma IHO/criterio.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-16",
        "priority": "C",
        "block": "Productos batimetricos",
        "question": "Que entregables deben exigirse: XYZ, grid, DTM, curvas, perfiles, planos CAD, memoria, QA/QC, reporte de obstrucciones? Validar/solicitar: Lista de entregables.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-17",
        "priority": "A",
        "block": "Productos batimetricos En",
        "question": "que formatos editables deben entregarse los datos para analisis nautico y calculo de volumen? Validar/solicitar: DWG, DXF, CSV, LAS, XYZ.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-18",
        "priority": "A",
        "block": "Productos batimetricos",
        "question": "Como se documentaran areas sin cobertura, interferencias, dudas o baja calidad? Validar/solicitar: Informe de excepciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-19",
        "priority": "C",
        "block": "Profundidad objetivo",
        "question": "Que informacion necesita para evaluar profundidad objetivo preliminar: calado, UKC, squat, marea, oleaje, tolerancia, overdepth? Validar/solicitar: Inputs requeridos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-20",
        "priority": "C",
        "block": "Profundidad objetivo",
        "question": "Como deberia tratarse overdepth, tolerancia de ejecucion y tolerancia de medicion? Validar/solicitar: Criterio de diseno.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-21",
        "priority": "C",
        "block": "Profundidad objetivo",
        "question": "Que taludes preliminares o bermas deben considerarse hasta contar con geotecnia? Validar/solicitar: Supuestos conservadores.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-22",
        "priority": "A",
        "block": "Profundidad objetivo",
        "question": "Que separacion debe hacerse entre dragado de canal, darsena, berth pocket y transiciones? Validar/solicitar: Paquetes de volumen.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-23",
        "priority": "C",
        "block": "Dragabilidad",
        "question": "Que informacion local existe sobre tipo de fondo: arena, limo, arcilla, coral, roca, relleno, escombros? Validar/solicitar: Sondeos, experiencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-24",
        "priority": "C",
        "block": "Dragabilidad",
        "question": "Que riesgos de fondo duro o roca pueden afectar costo, plazo o metodo? Validar/solicitar: Casos previos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-25",
        "priority": "A",
        "block": "Dragabilidad",
        "question": "Que investigaciones geotecnicas recomienda antes de estimar costo de dragado? Validar/solicitar: CPT, vibrocore, boreholes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-26",
        "priority": "A",
        "block": "Dragabilidad",
        "question": "Que muestreo de sedimentos se requiere para clasificar material y permisos de disposicion? Validar/solicitar: Parametros y laboratorio.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-27",
        "priority": "C",
        "block": "General",
        "question": "Dragabilidad Hay presencia o posible presencia de coral, pastos marinos, areas protegidas u otros habitats sensibles? Validar/solicitar: Mapas y estudios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-28",
        "priority": "C",
        "block": "Metodos de dragado",
        "question": "Que equipos serian viables: cutter suction, trailing suction, backhoe dredger, grab, barcazas u otros? Validar/solicitar: Disponibilidad y restricciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-29",
        "priority": "A",
        "block": "Metodos de dragado",
        "question": "Que equipos estan disponibles en RD o Caribe y cual es su plazo de movilizacion? Validar/solicitar: Lista de equipos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-30",
        "priority": "A",
        "block": "Metodos de dragado",
        "question": "Que limitaciones de acceso, profundidad, oleaje, trafico o espacio afectan la ejecucion? Validar/solicitar: Plan preliminar.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-31",
        "priority": "M",
        "block": "Metodos de dragado",
        "question": "Como se mediria el volumen ejecutado y como se controlaria calidad post-dragado? Validar/solicitar: Before/after survey.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-32",
        "priority": "C",
        "block": "Disposicion",
        "question": "Existen sitios autorizados de disposicion marina o terrestre para material dragado? Validar/solicitar: Permisos y coordenadas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-33",
        "priority": "C",
        "block": "Disposicion",
        "question": "Que restricciones aplican para material contaminado, fino, roca, coral o material organico? Validar/solicitar: Normativa y criterios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-34",
        "priority": "A",
        "block": "Disposicion",
        "question": "Que transporte, barcazas, bombeo o tuberia se requeriria para disposicion? Validar/solicitar: Metodo preliminar.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-35",
        "priority": "C",
        "block": "Permisos",
        "question": "Que permisos se requieren para batimetria multihaz? Validar/solicitar: Autoridad, tiempos, requisitos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-36",
        "priority": "C",
        "block": "Permisos",
        "question": "Que permisos se requieren para geotecnia, vibrocores, sedimentos y laboratorio? Validar/solicitar: Autoridad, tiempos, requisitos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-37",
        "priority": "C",
        "block": "Permisos",
        "question": "Que permisos se requieren para dragado de mantenimiento/profundizacion y disposicion? Validar/solicitar: Autoridad, tiempos, requisitos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-38",
        "priority": "A",
        "block": "Permisos",
        "question": "Que linea base ambiental minima suele exigirse antes de dragar? Validar/solicitar: TDR regulatorios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-39",
        "priority": "A",
        "block": "Permisos",
        "question": "Que actores institucionales deben participar: autoridad portuaria, marina, medio ambiente, municipio, pesca, comunidad? Validar/solicitar: Mapa de stakeholders.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-40",
        "priority": "C",
        "block": "Plazo y costos",
        "question": "Cual seria el plazo estimado para contratar, movilizar y ejecutar batimetria de Fase 2? Validar/solicitar: Cronograma preliminar.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-41",
        "priority": "A",
        "block": "Plazo y costos Cuales son",
        "question": "los factores que mas pueden cambiar costo y plazo del dragado? Validar/solicitar: Drivers de costo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-42",
        "priority": "A",
        "block": "Plazo y costos",
        "question": "Que informacion minima permitiria un presupuesto conceptual con rango de precision razonable? Validar/solicitar: Checklist de inputs.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-43",
        "priority": "M",
        "block": "Plazo y costos",
        "question": "Existe capacidad local para apoyo logistico: barcazas, combustible, muelles auxiliares, disposicion, talleres? Validar/solicitar: Inventario de apoyo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-44",
        "priority": "C",
        "block": "Riesgos Cuales son",
        "question": "los tres riesgos mas importantes de batimetria/dragado para la decision del Handymax? Validar/solicitar: Ranking.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-45",
        "priority": "C",
        "block": "Riesgos",
        "question": "Que condicion seria No-Go aunque la maniobra sea nauticamente viable? Validar/solicitar: Restriccion ambiental/tecnica.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-46",
        "priority": "C",
        "block": "Riesgos",
        "question": "Que condicion permitiria Go condicionado a Fase 2 con presupuesto controlado? Validar/solicitar: Condiciones precedentes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-47",
        "priority": "C",
        "block": "TDR Fase 2 Redacte",
        "question": "los puntos indispensables del TDR de batimetria para cerrar incertidumbres de Fase 1. Validar/solicitar: TDR preliminar.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-48",
        "priority": "C",
        "block": "TDR Fase 2 Redacte",
        "question": "los puntos indispensables del TDR de dragado conceptual y estimacion de volumen. Validar/solicitar: TDR preliminar.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-49",
        "priority": "A",
        "block": "TDR Fase 2",
        "question": "Que criterios de aceptacion de productos y QA/QC deben incluirse en contrato? Validar/solicitar: Especificaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "BD-50",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Con los datos disponibles, que recomendacion preliminar daria: Go, Go condicionado o No-Go para avanzar a estudios? Validar/solicitar: Justificacion.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": [
      {
        "id": "E-01",
        "document": "Inventario de batimetrias existentes con fecha, cobertura, datum, metodo y responsable.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-02",
        "document": "Ejemplo de informe batimetrico, QA/QC, XYZ, DTM, DWG/DXF y perfiles.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-03",
        "document": "Mapa preliminar de poligonos de levantamiento recomendados.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-04",
        "document": "Listado de equipos de batimetría, dragado y apoyo disponibles localmente/regionalmente.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-05",
        "document": "Requisitos y tiempos estimados de permisos para batimetría, geotecnia, sedimentos, dragado y disposición.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-06",
        "document": "Información histórica de dragados, sedimentación, tipo de fondo y obstrucciones.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-07",
        "document": "Opciones de disposición de material y restricciones ambientales conocidas.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-08",
        "document": "TDR preliminar recomendado para Fase 2.",
        "source": "Documentos y evidencia a solicitar"
      }
    ]
  },
  {
    "title": "Port Captain Local / Superintendente Maritimo",
    "source_file": "06_Port_Captain_local_superintendente_maritimo modificado (1).docx",
    "slug": "port_captain_local_superintendente_maritimo",
    "critical_questions": [
      {
        "number": "1",
        "question": "Que buque de mayor porte ha coordinado localmente en Boca Chica y cuales fueron sus calados, carga, condiciones y problemas?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "Que requiere un Handymax para llegar cargado, atracar y operar sin comprometer seguridad de casco, amarras, defensas o personal?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "La configuracion actual del muelle permite un plan de amarre seguro para un Handymax durante descarga?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "Que restricciones de carga/descarga, productividad, almacenamiento o acceso terrestre pueden prolongar permanencia al costado?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "Que condiciones de lastre, trim y calado deberian exigirse para entrada y zarpe?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "Que emergencias o contingencias deben planificarse antes de aceptar el buque?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "Que documentos operativos puede aportar para validar escalas y restricciones?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "Desde su experiencia local, el Handymax es Go, Go condicionado o No-Go?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "PC-01",
        "priority": "C",
        "block": "Perfil y experiencia",
        "question": "Describa su rol como Port Captain/superintendente y su participacion en operaciones de Boca Chica. Validar/solicitar: CV, contratos, ejemplos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-02",
        "priority": "C",
        "block": "Perfil y experiencia",
        "question": "Liste buques y cargas en los que ha participado localmente: fechas, calados, eslora, manga, carga y terminal. Validar/solicitar: SOF, reportes, fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-03",
        "priority": "A",
        "block": "Perfil y experiencia",
        "question": "Ha coordinado graneleros, Handy/Handymax o buques con operaciones de granel seco? Validar/solicitar: Ejemplos verificables.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-04",
        "priority": "A",
        "block": "Perfil y experiencia",
        "question": "Que lecciones operativas aplican directamente a un proyecto granelero? Validar/solicitar: Lecciones aprendidas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-05",
        "priority": "C",
        "block": "Planificacion de escala",
        "question": "Describa el proceso de planning desde nominacion del buque hasta zarpe: documentos, aprobaciones, reuniones y responsables. Validar/solicitar: Flujograma y checklists.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-06",
        "priority": "C",
        "block": "Planificacion de escala",
        "question": "Que informacion del buque es indispensable antes de aceptarlo: particulars, stability, mooring plan, cargo plan, draft, trim, ballast? Validar/solicitar: Checklist de aceptacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-07",
        "priority": "C",
        "block": "Planificacion de escala",
        "question": "Que condiciones debe cumplir el buque antes de arribo para evitar rechazo o demora? Validar/solicitar: Instrucciones al master.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-08",
        "priority": "A",
        "block": "Planificacion de escala",
        "question": "Como se coordinan agencia, practico, remolcadores, terminal, surveyors, aduana y autoridad? Validar/solicitar: Cronograma de escala.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-09",
        "priority": "M",
        "block": "Planificacion de escala",
        "question": "Que reuniones previas recomienda para primer Handymax: HAZID, toolbox, pre-arrival, pre-mooring? Validar/solicitar: Agenda propuesta.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-10",
        "priority": "C",
        "block": "Calados, trim y lastre",
        "question": "Que calado maximo considera operativo para llegada cargado con base en informacion actual? Validar/solicitar: Criterio y evidencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-11",
        "priority": "C",
        "block": "Calados, trim y lastre",
        "question": "Que trim y condicion de lastre recomienda para entrada, atraque, descarga y zarpe? Validar/solicitar: Plan de lastre.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-12",
        "priority": "A",
        "block": "Calados, trim y lastre",
        "question": "El buque puede ajustar lastre en condiciones seguras antes de entrada o salida? Validar/solicitar: Capacidad de lastre, restricciones ambientales.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-13",
        "priority": "A",
        "block": "Calados, trim y lastre",
        "question": "Como se controlaria el calado durante descarga para mantener margen junto al muelle? Validar/solicitar: Draft surveys, secuencia de descarga.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-14",
        "priority": "M",
        "block": "Calados, trim y lastre",
        "question": "Que riesgos existen por asiento, hog/sag, estabilidad o excesiva obra muerta al salir en lastre? Validar/solicitar: Comentarios tecnico-operativos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-15",
        "priority": "C",
        "block": "Maniobra y servicios",
        "question": "Desde su experiencia, donde esta el mayor riesgo: entrada, giro, aproximacion, atraque, permanencia, desatraque o salida? Validar/solicitar: Ranking.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-16",
        "priority": "C",
        "block": "Maniobra y servicios",
        "question": "Que numero y tipo de remolcadores exigiria para aceptar el buque desde la perspectiva del armador/fletador? Validar/solicitar: Configuracion minima.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-17",
        "priority": "A",
        "block": "Maniobra y servicios",
        "question": "Que condiciones de clima/horario deben incluirse en las instrucciones al master? Validar/solicitar: Weather limits.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-18",
        "priority": "A",
        "block": "Maniobra y servicios",
        "question": "Que informacion debe confirmarse con practico antes de que el buque arribe? Validar/solicitar: Pilot card / exchange.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-19",
        "priority": "M",
        "block": "Maniobra y servicios",
        "question": "Como se manejaria una demora por falta de remolcador o practico? Validar/solicitar: Plan de contingencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-20",
        "priority": "C",
        "block": "Muelle y amarre",
        "question": "El muelle actual permite un mooring plan seguro para Handymax? Identifique puntos criticos. Validar/solicitar: Mooring plan, fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-21",
        "priority": "C",
        "block": "Muelle y amarre",
        "question": "Que combinacion de lineas de proa, popa, springs y breast lines seria necesaria? Validar/solicitar: Mooring arrangement.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-22",
        "priority": "C",
        "block": "Muelle y amarre",
        "question": "Las bitas, ganchos o puntos de amarre tienen capacidad y ubicacion adecuadas? Validar/solicitar: Certificados, inspeccion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-23",
        "priority": "C",
        "block": "Muelle y amarre",
        "question": "Las defensas tienen energia, altura y separacion adecuada para el casco de un Handymax? Validar/solicitar: Fichas y fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-24",
        "priority": "A",
        "block": "Muelle y amarre",
        "question": "Existen problemas de gangway, seguridad de acceso, iluminacion, guardia, line handlers o caida de personas? Validar/solicitar: Reportes HSE.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-25",
        "priority": "A",
        "block": "Muelle y amarre",
        "question": "Que condiciones obligarian a reforzar amarras, suspender operaciones o desatracar de emergencia? Validar/solicitar: Limites y procedimiento.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-26",
        "priority": "C",
        "block": "Operacion de carga/descarga",
        "question": "Describa productividad real esperada de descarga/carga de graneles y principales cuellos de botella. Validar/solicitar: SOF, plan de operacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-27",
        "priority": "A",
        "block": "Operacion de carga/descarga",
        "question": "Que equipos se usarian: gruas de buque, gruas moviles, grabs, hopper, conveyors, camiones, cargadores? Validar/solicitar: Inventario y capacidades.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-28",
        "priority": "A",
        "block": "Operacion de carga/descarga",
        "question": "El muelle soporta cargas/equipos requeridos para graneles y movimiento continuo? Validar/solicitar: Capacidad de piso/muelle.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-29",
        "priority": "A",
        "block": "Operacion de carga/descarga",
        "question": "Que limitaciones de almacenamiento, patios, silos, camiones, carretera o turnos afectarian la estadia? Validar/solicitar: Capacidades terrestres.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-30",
        "priority": "M",
        "block": "Operacion de carga/descarga",
        "question": "Que riesgo de contaminacion, humedad, polvo, lluvia, fumigacion o merma aplica a graneles? Validar/solicitar: Procedimientos de calidad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-31",
        "priority": "A",
        "block": "Operacion de carga/descarga",
        "question": "Como se coordina seguridad de bodegas, hatch covers, trabajos en altura y equipos de cubierta? Validar/solicitar: Procedimientos HSE.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-32",
        "priority": "C",
        "block": "Permanencia al costado",
        "question": "Que movimientos del buque al costado son aceptables y cuales obligan a suspender operaciones? Validar/solicitar: Criterios de seguridad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-33",
        "priority": "C",
        "block": "Permanencia al costado",
        "question": "Existen riesgos de passing traffic, oleaje, surge, marea o viento que afecten amarras y defensas? Validar/solicitar: Experiencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-34",
        "priority": "A",
        "block": "Permanencia al costado",
        "question": "Que frecuencia de ronda de amarras, verificacion de calados y monitoreo meteorologico recomienda? Validar/solicitar: Checklist de guardia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-35",
        "priority": "M",
        "block": "Permanencia al costado",
        "question": "Se requiere tug standby durante ciertas condiciones o durante primera operacion? Validar/solicitar: Criterio de mitigacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-36",
        "priority": "C",
        "block": "Emergencias",
        "question": "Que escenarios de emergencia deben estar resueltos antes de aceptar el buque? Validar/solicitar: Lista de escenarios.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-37",
        "priority": "C",
        "block": "Emergencias",
        "question": "Que plan se aplicaria para desatraque de emergencia por mal tiempo, incendio, derrame, rotura de amarras o falla de muelle? Validar/solicitar: Plan de emergencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-38",
        "priority": "A",
        "block": "Emergencias",
        "question": "Que recursos locales existen: bomberos, ambulancia, oil spill, lancha, seguridad, reparacion de amarras, buzos? Validar/solicitar: Inventario.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-39",
        "priority": "A",
        "block": "Emergencias",
        "question": "Que seguros, P&I, cartas de garantia o responsabilidades deben aclararse? Validar/solicitar: Documentacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-40",
        "priority": "C",
        "block": "Calidad de datos",
        "question": "Que documentos operativos pueden validar restricciones reales de Boca Chica? Validar/solicitar: SOF, draft survey, reports.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-41",
        "priority": "A",
        "block": "Calidad de datos",
        "question": "Que datos deben estar en el Data Room antes de recomendar Fase 2? Validar/solicitar: Lista priorizada.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-42",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Liste condiciones minimas para primer Handymax: batimetria, tugs, pilotos, muelle, amarras, clima, horario, emergencia. Validar/solicitar: Matriz de condiciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-43",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Que condicion seria No-Go desde el punto de vista del buque/armador? Validar/solicitar: Restriccion no aceptable.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-44",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Recomendacion Go, Go condicionado o No-Go, con supuestos y condiciones precedentes. Validar/solicitar: Justificacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "PC-45",
        "priority": "M",
        "block": "Seguimiento",
        "question": "Que personas deben participar en taller posterior o simulacion de maniobra? Validar/solicitar: Contactos.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": []
  },
  {
    "title": "Surveyors Locales",
    "source_file": "07_Surveyors_locales modificado (1).docx",
    "slug": "surveyors_locales",
    "critical_questions": [
      {
        "number": "1",
        "question": "Que buques de mayor porte ha inspeccionado en Boca Chica y cuales fueron sus calados reales?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "2",
        "question": "Existen draft surveys o reportes que confirmen calados de llegada/salida y densidad del agua?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "3",
        "question": "Ha observado danos, contactos, varaduras, rotura de amarras, danos a defensas/bitas o problemas de muelle?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "4",
        "question": "Que limitaciones reales ha visto en operaciones de granel, equipos, productividad, polvo, lluvia o calidad de carga?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "5",
        "question": "Que tan confiable es la informacion local de calados, profundidades, mareas y condiciones al costado?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "6",
        "question": "Que documentos puede aportar al Data Room con confidencialidad o anonimizado?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "7",
        "question": "Que riesgos de reclamo ve para un Handymax cargado en Boca Chica?",
        "source": "Preguntas criticas de apertura"
      },
      {
        "number": "8",
        "question": "Desde su evidencia independiente, el caso es Go, Go condicionado o No-Go?",
        "source": "Preguntas criticas de apertura"
      }
    ],
    "detailed_questions": [
      {
        "id": "SU-01",
        "priority": "C",
        "block": "Perfil y experiencia",
        "question": "Describa servicios de survey realizados en Puerto Andres / Boca Chica y anos de experiencia local. Validar/solicitar: CV, lista de trabajos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-02",
        "priority": "C",
        "block": "Perfil y experiencia",
        "question": "Liste buques inspeccionados con nombre, fecha, tipo, LOA/manga si se conoce, calados y carga. Validar/solicitar: Reportes anonimizados.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-03",
        "priority": "A",
        "block": "Perfil y experiencia",
        "question": "Que servicios fueron draft survey, condition survey, damage survey, cargo survey, bunker o incident survey? Validar/solicitar: Tipos de reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-04",
        "priority": "A",
        "block": "Perfil y experiencia",
        "question": "Ha participado en operaciones de granel seco o buques comparables a Handy/Handymax? Validar/solicitar: Ejemplos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-05",
        "priority": "C",
        "block": "Calados y draft survey",
        "question": "Que calados maximos ha medido en Boca Chica y bajo que condiciones? Validar/solicitar: Draft survey y fotos de marcas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-06",
        "priority": "C",
        "block": "Calados y draft survey",
        "question": "Como se mide densidad del agua y que variaciones se observan? Validar/solicitar: Registros de densidad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-07",
        "priority": "A",
        "block": "General",
        "question": "Calados y draft survey Hay dificultad para leer marcas de calado por oleaje, acceso, iluminacion o suciedad? Validar/solicitar: Comentarios y fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-08",
        "priority": "A",
        "block": "Calados y draft survey",
        "question": "Que tablas de marea o datos de nivel de agua usan durante draft survey? Validar/solicitar: Fuentes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-09",
        "priority": "A",
        "block": "Calados y draft survey",
        "question": "Se han observado diferencias significativas entre calado declarado, medido y autorizado? Validar/solicitar: Reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-10",
        "priority": "C",
        "block": "Calados y draft survey",
        "question": "Que controles recomienda para primer Handymax: medicion, densidad, marea, trim, asiento, lastre? Validar/solicitar: Checklist.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-11",
        "priority": "C",
        "block": "Muelle y amarre",
        "question": "Ha inspeccionado defensas, bitas, muelle, lineas o danos asociados a atraque? Validar/solicitar: Damage reports, fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-12",
        "priority": "C",
        "block": "Muelle y amarre",
        "question": "Que condiciones del frente de atraque podrian generar reclamos en un Handymax: defensas, bitas, berthing pocket, fender marks? Validar/solicitar: Evidencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-13",
        "priority": "A",
        "block": "Muelle y amarre",
        "question": "Ha observado rotura de amarras, lineas muy tensas, movimiento excesivo o mal reparto de lineas? Validar/solicitar: Reportes, fotos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-14",
        "priority": "A",
        "block": "General",
        "question": "Muelle y amarre Hay dificultad de acceso seguro al buque: gangway, iluminacion, guardrails, seguridad? Validar/solicitar: HSE observations.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-15",
        "priority": "C",
        "block": "Condicion del buque",
        "question": "Que problemas de condicion del buque serian criticos para operar en Boca Chica: maquinas, timon, bow thruster, amarras, hatch covers? Validar/solicitar: Checklists.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-16",
        "priority": "A",
        "block": "Condicion del buque Recomienda condition survey pre-arrival para primer Handymax?",
        "question": "Que incluiria? Validar/solicitar: Alcance recomendado.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-17",
        "priority": "C",
        "block": "Carga y calidad",
        "question": "Que cargas graneleras ha inspeccionado localmente y que riesgos de calidad o contaminacion observa? Validar/solicitar: Cargo survey reports.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-18",
        "priority": "A",
        "block": "Carga y calidad",
        "question": "Existen problemas de humedad, lluvia, polvo, segregacion, contaminacion cruzada o perdidas durante transferencia? Validar/solicitar: Reportes de calidad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-19",
        "priority": "A",
        "block": "Carga y calidad",
        "question": "Como se verifica cantidad: draft survey, balanza, tally, cinta, silos, camiones? Validar/solicitar: Procedimiento y confiabilidad.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-20",
        "priority": "M",
        "block": "Carga y calidad",
        "question": "Que equipos o procesos limitan productividad y aumentan riesgo de demoras o claims? Validar/solicitar: SOF, reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-21",
        "priority": "C",
        "block": "Incidentes y claims",
        "question": "Liste incidentes o reclamos observados: varadura, contacto, danos a muelle, carga danada, demoras, discrepancias de cantidad. Validar/solicitar: Reportes anonimizados.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-22",
        "priority": "C",
        "block": "Incidentes y claims",
        "question": "Que reclamos serian mas probables con un Handymax cargado en Boca Chica? Validar/solicitar: Ranking.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-23",
        "priority": "A",
        "block": "Incidentes y claims",
        "question": "Existen fotografias, reportes o cartas que documenten condiciones de riesgo? Validar/solicitar: Evidencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-24",
        "priority": "A",
        "block": "Incidentes y claims",
        "question": "Que aseguradores, P&I o clubes han requerido surveys especiales en la zona? Validar/solicitar: Referencias.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-25",
        "priority": "C",
        "block": "Condiciones ambientales",
        "question": "Ha observado efectos de viento, ola, corriente, lluvia o mar de fondo durante surveys al costado? Validar/solicitar: Notas de campo.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-26",
        "priority": "A",
        "block": "Condiciones ambientales",
        "question": "Que condiciones hacen insegura la lectura de calados, el acceso o la operacion? Validar/solicitar: Criterios HSE.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-27",
        "priority": "M",
        "block": "Condiciones ambientales",
        "question": "Se han suspendido surveys u operaciones por clima? Validar/solicitar: SOF y reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-28",
        "priority": "C",
        "block": "Datos nauticos",
        "question": "Que tan confiables considera los datos locales de profundidad, marea y calado autorizado? Validar/solicitar: Opinion con evidencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-29",
        "priority": "C",
        "block": "Datos nauticos",
        "question": "Que datos deberian verificarse con batimetria antes de aceptar un Handymax? Validar/solicitar: Areas criticas.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-30",
        "priority": "A",
        "block": "Datos nauticos",
        "question": "Ha participado en surveys de fondo, inspecciones submarinas o verificacion de obstrucciones? Validar/solicitar: Reportes.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-31",
        "priority": "C",
        "block": "Documentacion",
        "question": "Que reportes puede aportar en version anonima o extractada para Data Room? Validar/solicitar: Lista de documentos.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-32",
        "priority": "A",
        "block": "Documentacion",
        "question": "Que permisos de confidencialidad se requieren para compartir reportes de clientes anteriores? Validar/solicitar: Autorizaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-33",
        "priority": "A",
        "block": "Documentacion",
        "question": "Que estandar de reporte usa: fotos georreferenciadas, mediciones, firma de partes, timestamps? Validar/solicitar: Formato de reporte.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-34",
        "priority": "M",
        "block": "Documentacion",
        "question": "Que informacion considera mas confiable para sustentar dictamen Go/No-Go? Validar/solicitar: Ranking de evidencia.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-35",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Que controles de survey recomienda para primera escala Handymax? Validar/solicitar: Plan de surveys.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-36",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Que condicion del muelle, buque o operacion seria No-Go desde la perspectiva de survey/claims? Validar/solicitar: Red flags.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-37",
        "priority": "C",
        "block": "Condiciones minimas",
        "question": "Que condicion seria Go condicionado y verificable con medidas de control? Validar/solicitar: Mitigaciones.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-38",
        "priority": "C",
        "block": "Decision Fase 1",
        "question": "Con la evidencia disponible, recomendacion Go, Go condicionado o No-Go. Validar/solicitar: Justificacion.",
        "source": "Cuestionario detallado de trabajo"
      },
      {
        "id": "SU-39",
        "priority": "M",
        "block": "Seguimiento",
        "question": "Que otros surveyors, capitanes, operadores o P&I correspondents deberian entrevistarse? Validar/solicitar: Contactos.",
        "source": "Cuestionario detallado de trabajo"
      }
    ],
    "evidence_requests": [
      {
        "id": "E-01",
        "document": "Reportes anonimizados de draft survey, condition survey, damage survey y cargo survey.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-02",
        "document": "Fotos de marcas de calado, muelle, defensas, bitas, amarras, equipos y condiciones al costado.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-03",
        "document": "Registros de densidad del agua, marea, calados y cantidades.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-04",
        "document": "Reportes de incidentes, reclamos, demoras, danos, cartas de protesta o P&I.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-05",
        "document": "Checklists de inspeccion recomendados para primera escala Handymax.",
        "source": "Documentos y evidencia a solicitar"
      },
      {
        "id": "E-06",
        "document": "Lista de contactos de surveyors, P&I correspondents, capitanes y operadores locales.",
        "source": "Documentos y evidencia a solicitar"
      }
    ]
  }
];
