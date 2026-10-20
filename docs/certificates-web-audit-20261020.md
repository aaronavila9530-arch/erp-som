# Certificados de Informes: auditoria y migracion web

## Alcance

Revision de los formularios, tablas, rutas y exportadores de escritorio de
Weight, Vessel Holds Inspection, Sampling, Sealing y Cargo Lashing.
La implementacion web usa rutas nuevas bajo `/informes/certificates`.
No modifica formularios, rutas antiguas, plantillas ni ejecutables de escritorio.

## Paridad

| Certificado | Datos particulares | Exportacion |
| --- | --- | --- |
| Peso | Buque, viaje, carga, B/L, metodo, cantidad y observaciones | Word y PDF |
| Inspeccion de bodegas | Bodegas, estado, aceptacion, hose test y firma | Excel y PDF |
| Muestreo | Diez sellos, bodegas inspeccionadas, observaciones y cierre | Excel y PDF |
| Sellado | Seis bodegas, tres posiciones de sello por bodega, cierre y firma | Excel y PDF |
| Trincado | Flat rack, carga, material, tensores y finalizacion | Word y PDF |

Los cinco permiten consulta, borrador, envio a revision y aprobacion/rechazo
administrativo. Los aprobados no se editan hasta rechazarlos. La exportacion es
independiente del guardado. Fechas DD/MM/YYYY en pantalla, ISO en base de datos;
horas HH:MM. Sellos, cantidades e identificadores se conservan como texto.

## Hallazgos

- Las cinco tablas antiguas no tienen empresa. Se resuelve exclusivamente por
  `servicios.num_informe` cuando la empresa es inequivoca. No se asigna una
  empresa por suposicion a un certificado sin servicio.
- Se encontro un certificado de peso sin servicio vinculado. Se conserva intacto
  y no se expone en ninguna empresa hasta aclarar su asociacion.
- Muestreo carecia de cinco columnas que envia su formulario de escritorio:
  holds_inspected, observations, closing_date, closing_time y master.
  La migracion agrega solo columnas text opcionales; no actualiza registros.
- La copia web de la plantilla de muestreo muestra los diez sellos; la original
  solo referenciaba cuatro.
- En la copia web de sellado se corrige la referencia repetida del segundo sello
  de la bodega 2.
- En la copia web de inspeccion se usan el producto, las bodegas aceptadas y el
  lugar/fecha de aceptacion correspondientes, sin heredar valores fijos.
- En la copia web de trincado se quita el literal THIRTENN ante la cantidad.
- Firmas y estructura de las plantillas originales se conservan. No se sustituye
  el firmante por el usuario que realiza la edicion.

## Seguridad y compatibilidad

- Permisos de Informes existentes para consultar, crear y editar; aprobacion
  limitada a admin/master con permiso de edicion.
- El token limitado de Tally no concede acceso a certificados.
- SQL con tablas/campos de listas cerradas y valores parametrizados.
- PATCH parcial conserva columnas antiguas no editadas.
- Version del registro completo y bloqueo transaccional impiden que la web
  sobrescriba una edicion previa de escritorio inadvertidamente. Las rutas
  antiguas no incorporan este control y conservan su comportamiento.
- No se habilita eliminacion de certificados.
- Descargas generan copias temporales; nunca escriben en las plantillas.
- El Excel oculta datos auxiliares, limita ancho de impresion y conserva
  identificadores como texto, sin ejecutar formulas procedentes de entradas.

## Verificacion

- 16 pruebas unitarias especificas de contratos, permisos, aislamiento,
  concurrencia, exportaciones, referencias y preservacion de plantillas.
- 58 pruebas locales al incluir regresion de Containers y LOGRA.
- Pruebas reales de SQL en tablas temporales de PostgreSQL para los cinco tipos:
  crear, consultar por empresa, editar, detectar conflicto y aprobar.
- Lectura de esos registros temporales con las cinco funciones existentes de
  escritorio. No se escribieron registros ni secuencias publicas.
- Navegador automatizado a 1440, 800 y 390 px para los cinco formularios:
  creacion, edicion parcial, conflictos, revision, aprobacion y solo lectura.
- La generacion nativa Word/Excel se verifica estructuralmente. La conversion PDF
  requiere LibreOffice del servidor y una comprobacion visual adicional con un
  certificado real vinculado. No se crean certificados ficticios en produccion.
