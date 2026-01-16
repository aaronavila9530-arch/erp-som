import psycopg2


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


POLICIES = [

    # =========================================================
    # DISPOSICIONES GENERALES
    # =========================================================
    (
        "Disposiciones Generales",
        "Alcance y obligatoriedad del Reglamento Interno",
        """
El Reglamento Interno de Trabajo de MSL establece las normas que regulan la relación
laboral entre la empresa y todas las personas trabajadoras. Su finalidad es garantizar
un ambiente de trabajo ordenado, respetuoso y conforme a la legislación laboral
costarricense.

Estas disposiciones son de cumplimiento obligatorio para todo el personal, sin
importar su puesto, jerarquía o modalidad de contratación. El desconocimiento de
estas normas no exime de su cumplimiento ni de las posibles sanciones derivadas
de su incumplimiento.

Esta política se fundamenta en los artículos 1 y 2 del Reglamento Interno, los cuales
definen el alcance, los conceptos básicos y las partes involucradas en la relación
laboral.
        """,
        "Art. 1 y 2"
    ),

    # =========================================================
    # CONTRATACIÓN
    # =========================================================
    (
        "Contratación",
        "Contrato de trabajo y formalización de la relación laboral",
        """
Toda persona que preste servicios para MSL debe estar amparada por un contrato de
trabajo, ya sea escrito o mediante acción de personal. Dicho contrato establece de
manera clara las condiciones bajo las cuales se desarrollará la relación laboral,
incluyendo funciones, jornada, salario y demás obligaciones.

En el caso de personas trabajadoras adolescentes, se aplicará adicionalmente la
normativa especial de protección contenida en el Código de la Niñez y la Adolescencia,
garantizando siempre el respeto a sus derechos.

Esta política se basa en el artículo 3 del Reglamento Interno, el cual regula la
formalización de la relación laboral.
        """,
        "Art. 3"
    ),

    # =========================================================
    # JORNADA Y HORARIOS
    # =========================================================
    (
        "Jornada y Horarios",
        "Jornada ordinaria de trabajo",
        """
La jornada ordinaria de trabajo en MSL se desarrolla en el centro de trabajo designado
por la empresa o en cualquier otro sitio que esta determine conforme a sus
necesidades operativas.

Para el personal administrativo, la jornada es diurna, fraccionada y acumulativa, de
lunes a viernes, con un período de descanso para alimentación. El cumplimiento del
horario asignado es una obligación fundamental de la persona trabajadora y forma
parte esencial de sus responsabilidades laborales.

Esta política se fundamenta en los artículos 4 y 5 del Reglamento Interno.
        """,
        "Art. 4 y 5"
    ),

    (
        "Jornada y Horarios",
        "Horas extraordinarias",
        """
Cuando existan necesidades imperiosas de la empresa, MSL podrá requerir a las
personas trabajadoras la realización de horas extraordinarias, siempre dentro de los
límites permitidos por la ley.

Las horas extraordinarias deben ser comunicadas con al menos tres días de
anticipación, salvo situaciones excepcionales. Estas horas serán remuneradas con
un recargo del cincuenta por ciento adicional al valor de la hora ordinaria.

No se permite la realización de jornadas extraordinarias de forma permanente. Esta
política se basa en lo establecido en el artículo 9 del Reglamento Interno.
        """,
        "Art. 9"
    ),

    # =========================================================
    # SALARIO
    # =========================================================
    (
        "Salario",
        "Forma y periodicidad de pago del salario",
        """
MSL paga el salario de forma mensual, con adelantos quincenales, mediante
transferencia bancaria electrónica. El pago se realiza los días 15 y 30 de cada mes,
o el día hábil inmediato anterior si coincide con un feriado o día de descanso.

La empresa garantiza el pago puntual del salario conforme a la legislación vigente.
Cualquier reclamo relacionado con el pago debe presentarse oportunamente ante la
jefatura inmediata.

Esta política se fundamenta en los artículos 12, 13 y 14 del Reglamento Interno.
        """,
        "Art. 12, 13 y 14"
    ),

    # =========================================================
    # VACACIONES Y DESCANSOS
    # =========================================================
    (
        "Vacaciones y Descansos",
        "Derecho a vacaciones anuales",
        """
Todas las personas trabajadoras de MSL tienen derecho a disfrutar, como mínimo, de
dos semanas de vacaciones anuales remuneradas por cada cincuenta semanas de
servicio continuo.

En caso de finalización de la relación laboral antes de cumplir dicho período, la
persona trabajadora tendrá derecho al pago proporcional de las vacaciones
correspondientes.

Esta política se fundamenta en los artículos 15 y 16 del Reglamento Interno.
        """,
        "Art. 15 y 16"
    ),

    # =========================================================
    # USO DE TECNOLOGÍA
    # =========================================================
    (
        "Uso de Tecnología",
        "Uso adecuado de herramientas informáticas",
        """
Las herramientas informáticas, el acceso a internet y el correo electrónico
corporativo proporcionados por MSL deben utilizarse exclusivamente para fines
laborales.

El uso indebido, abusivo o no autorizado de estos recursos podrá dar lugar a
sanciones disciplinarias, incluyendo la suspensión temporal o definitiva del acceso a
dichas herramientas.

Esta política se fundamenta en los artículos 22 al 29 del Reglamento Interno.
        """,
        "Art. 22 al 29"
    ),

    # =========================================================
    # ACOSO Y HOSTIGAMIENTO SEXUAL
    # =========================================================
    (
        "Acoso y Hostigamiento",
        "Prevención y sanción del acoso y hostigamiento sexual",
        """
MSL mantiene una política de tolerancia cero frente al acoso y hostigamiento sexual
en el entorno laboral. Cualquier conducta de naturaleza sexual no deseada, reiterada
o grave, que afecte la dignidad de una persona, está estrictamente prohibida.

La empresa garantiza mecanismos confidenciales de denuncia y la protección de las
personas denunciantes y testigos, conforme a la Ley contra el Hostigamiento Sexual en
el Empleo y la Docencia.

Esta política se fundamenta en los artículos 30 al 51 del Reglamento Interno.
        """,
        "Art. 30 al 51"
    ),

    # =========================================================
    # RÉGIMEN DISCIPLINARIO
    # =========================================================
    (
        "Régimen Disciplinario",
        "Sanciones disciplinarias",
        """
El incumplimiento de las obligaciones laborales y de las disposiciones del
Reglamento Interno dará lugar a la aplicación de sanciones disciplinarias, las cuales
podrán ir desde una amonestación verbal hasta el despido sin responsabilidad
patronal, dependiendo de la gravedad de la falta.

Las sanciones se aplicarán respetando el debido proceso y dentro de los plazos
establecidos por la normativa vigente.

Esta política se fundamenta en los artículos 52 al 57 del Reglamento Interno.
        """,
        "Art. 52 al 57"
    )
]


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("📥 Insertando políticas iniciales MSL...")

    for categoria, titulo, contenido, articulo_ref in POLICIES:
        cur.execute("""
            INSERT INTO hr_policies (
                categoria,
                titulo,
                contenido,
                articulo_ref,
                activo,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, true, 'system_seed'
            )
        """, (categoria, titulo, contenido.strip(), articulo_ref))

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Seed inicial de políticas MSL cargado correctamente.")


if __name__ == "__main__":
    main()
