import ast
import sqlite3
import unittest
from pathlib import Path


class InvoiceClientAliasTests(unittest.TestCase):
    def test_names_and_code_resolve_only_same_company_unbilled_services(self):
        source = (Path(__file__).parents[1] / 'routers/invoicing.py').read_text(encoding='utf-8')
        function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'get_servicios_facturables')
        sql = next(n.value for n in ast.walk(function) if isinstance(n, ast.Constant) and isinstance(n.value, str) and 'FROM servicios s' in n.value)
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        columns = 'consec,tipo,buque_contenedor,num_informe,detalle,cliente,continente,pais,puerto,operacion,fecha_inicio,hora_inicio,fecha_fin,hora_fin,demoras,duracion,factura,company_code,estado'
        conn.execute('CREATE TABLE servicios (' + columns + ')')
        conn.execute('CREATE TABLE cliente (codigo,nombrecomercial,nombrejuridico,company_code)')
        conn.execute("INSERT INTO cliente VALUES ('MSL-0032-C','Agency of the Sea','Costa Rica Customs and Logistics Agency SRL','MSL-CR')")
        for number, company, invoice, status in [(529,'MSL-CR',None,'Finalizado'),(530,'MCI-CR',None,'Finalizado'),(531,'MSL-CR','123','Finalizado'),(532,'MSL-CR',None,'Activo')]:
            conn.execute('INSERT INTO servicios (consec,cliente,num_informe,company_code,factura,estado) VALUES (?,?,?,?,?,?)', (number,'Costa Rica Customs and Logistics Agency SRL','2242',company,invoice,status))
        for name in ('Agency of the Sea','Costa Rica Customs and Logistics Agency SRL','MSL-0032-C'):
            rows = conn.execute(sql.replace('%s','?'),(name,name,'MSL-CR')).fetchall()
            self.assertEqual([row[0] for row in rows],[529])
        self.assertEqual(conn.execute(sql.replace('%s','?'),('Agency of the Sea','Agency of the Sea','MCI-CR')).fetchall(),[])


if __name__ == '__main__':
    unittest.main()
