import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root = 'C:/Users/aaron/Documents/ERP-SOM';
const out = root + '/outputs/activos-fijos-20261019';
await fs.mkdir(out,{recursive:true});
const data = JSON.parse(await fs.readFile(new URL('./source.json',import.meta.url),'utf8'));
const assets = data.assets.sort((a,b)=>a.asset_code.localeCompare(b.asset_code));
const cents = v=>Math.round(Number(v)*100);
const sums = rows=>rows.reduce((s,r)=>s+cents(r.depreciation_amount_crc),0)/100;
const rows = assets.map(a=>{
  const sched=data.schedule.filter(s=>s.asset_id===a.id);
  const closed=sched.filter(s=>s.depreciation_date<='2026-09-30');
  const posted=sched.filter(s=>s.depreciation_date<='2026-10-19' && s.status==='POSTED' && s.accounting_entry_id);
  const current=sched.filter(s=>s.period==='2026-10');
  if(!a.asset_code.startsWith('MSL-') || a.currency_code!=='USD') throw Error('Unexpected company/currency');
  return {a,closed:sums(closed),posted:sums(posted),current:sums(current)};
});
const wb=Workbook.create();
const msl=wb.worksheets.add('MSL');
const mci=wb.worksheets.add('MCI');
const base=wb.worksheets.add('Base SOM');
const money='#,##0.00;(#,##0.00);"-"';
const ink='#203848', header='#294B60', pale='#EDF3F6', amber='#FFF1CF';
function setup(s,lastCol,lastRow){
 s.showGridLines=false;
 s.getRange(`A1:${lastCol}${lastRow}`).format.font={name:'Arial',size:10,color:ink};
 s.getRange(`A1:${lastCol}${lastRow}`).format.rowHeight=23;
 s.getRange(`A1:${lastCol}${lastRow}`).format.verticalAlignment='center';
 s.tabColor=header;
}
function title(s,text){s.getRange('A2').values=[[text]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:ink};s.getRange('A2:P2').format.rowHeight=30;}
function headers(s,range,values){s.getRange(range).values=[values];s.getRange(range).format={fill:header,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:50};}
setup(base,'U',rows.length+5);
title(base,'Datos de SOM al 19/10/2026');
base.getRange('A3').values=[['Fuente: Accounting / Activos fijos y calendario de depreciacion. Consulta de solo lectura. Importacion: Activos e Inventario MSL FY2025.xlsx.']];
const sourceHeaders=['ID','Codigo','Descripcion original','Compra registrada','Costo USD','TC historico','Costo CRC','Dep. mensual CRC','Vida util meses','Residual CRC','Estado','Clasificacion','Dep. acumulada guardada CRC','Neto guardado CRC','Dep. calendario POSTED CRC','Dep. calendario hasta septiembre CRC','Cuota octubre CRC','Serie','Ubicacion','Observaciones originales','Fecha TC'];
headers(base,'A5:U5',sourceHeaders);
base.getRange(`A6:U${rows.length+5}`).values=rows.map(({a,closed,posted,current})=>[a.id,a.asset_code,a.description,new Date(a.purchase_date+'T00:00:00Z'),Number(a.original_amount),Number(a.exchange_rate),Number(a.value_crc),Number(a.monthly_depreciation_crc),a.useful_life_months,Number(a.salvage_value_crc),a.status,a.classification,Number(a.accumulated_depreciation_crc),Number(a.book_value_crc),posted,closed,current,a.serial,a.location,a.notes,new Date(a.exchange_rate_date+'T00:00:00Z')]);
base.getRange(`E6:Q${rows.length+5}`).setNumberFormat(money);
base.getRange(`I6:I${rows.length+5}`).setNumberFormat('0');
base.getRange(`D6:D${rows.length+5}`).setNumberFormat('dd/mm/yyyy');
base.getRange(`U6:U${rows.length+5}`).setNumberFormat('dd/mm/yyyy');
base.getRange('A1:U91').format.columnWidth=19;
base.getRange('A1:A91').format.columnWidth=8;
base.getRange('C1:C91').format.columnWidth=65;
base.getRange('T1:T91').format.columnWidth=50;
base.getRange('C6:C91').format.wrapText=true;
base.getRange('T6:T91').format.wrapText=true;
base.getRange('A6:U91').format.rowHeight=46;
base.tables.add(`A5:U${rows.length+5}`,true,'DatosSOM');
base.freezePanes.freezeRows(5);

const first=15,last=first+rows.length-1;
setup(msl,'P',last);
title(msl,'Activos fijos y depreciacion de MSL');
msl.getRange('A4:D4').values=[['Corte',new Date('2026-10-19T00:00:00Z'),'Activos',rows.length]];
msl.getRange('B4').setNumberFormat('dd/mm/yyyy');
msl.getRange('B4').format.horizontalAlignment='left';
msl.getRange('A6').values=[['Costo historico CRC']];
msl.getRange('B6').formulas=[[`=SUM(G${first}:G${last})`]];
msl.getRange('A7').values=[['Dep. estimada CRC']];
msl.getRange('B7').formulas=[[`=SUM(I${first}:I${last})`]];
msl.getRange('D6').values=[['Valor neto estimado CRC']];
msl.getRange('E6').formulas=[[`=SUM(J${first}:J${last})`]];
msl.getRange('D7').values=[['Dep. mensual CRC']];
msl.getRange('E7').formulas=[[`=SUM(H${first}:H${last})`]];
msl.getRange('B6:B7').setNumberFormat(money);
msl.getRange('E6:E7').setNumberFormat(money);
msl.getRange('A6:B7').format.fill=pale;
msl.getRange('D6:E7').format.fill=pale;
msl.getRange('B6:B7').format.font.bold=true;
msl.getRange('E6:E7').format.font.bold=true;
msl.getRange('A9').values=[['Fecha de compra: 31/12/2024 fue asignada en la importacion. No es una fecha de compra verificada.']];
msl.getRange('A9:P9').format.fill=amber;
msl.getRange('A10').values=[['Estimacion al corte: calendario hasta 30/09/2026 mas 19/31 de la cuota de octubre. No se han contabilizado nuevos asientos.']];
msl.getRange('A11').values=[['Registrada: calendario POSTED con asiento asociado, hasta agosto 2026. Pendiente: diferencia contra la estimacion al corte.']];
msl.getRange('A12').values=[['El valor neto estimado NO es precio de mercado ni una oferta de compra. Nombre abreviado derivado de la descripcion original.']];
headers(msl,'A14:P14',['Codigo','Nombre abreviado','Descripcion','Compra registrada','Costo USD','TC CRC/USD','Costo CRC','Dep. mensual CRC','Dep. acumulada estimada CRC','Valor neto estimado CRC','Dep. registrada calendario CRC','Pendiente estimado CRC','Dep. hasta 30/09 CRC','Octubre 19/31 CRC','Vida util meses','Estado']);
for(let i=0;i<rows.length;i++){
 const r=first+i,b=6+i;
 const {a}=rows[i];
 const link=c=>`='Base SOM'!${c}${b}`;
 msl.getRange(`A${r}:P${r}`).formulas=[[link('B'),' ',link('C'),link('D'),link('E'),link('F'),link('G'),link('H'),`=MIN(G${r}-'Base SOM'!J${b},M${r}+N${r})`,`=G${r}-I${r}`,link('O'),`=I${r}-K${r}`,link('P'),`=ROUND('Base SOM'!Q${b}*DAY($B$4)/DAY(EOMONTH($B$4,0)),2)`,link('I'),link('K')]];
 msl.getRange(`B${r}`).values=[[a.description.trim().split(/\s+/).slice(0,3).join(' ')]];
 if(i%2===1)msl.getRange(`A${r}:P${r}`).format.fill='#F4F7F9';
}
msl.getRange(`D${first}:D${last}`).setNumberFormat('dd/mm/yyyy');
msl.getRange(`E${first}:N${last}`).setNumberFormat(money);
msl.getRange(`O${first}:O${last}`).setNumberFormat('0');
msl.getRange(`A14:P${last}`).format.rowHeight=46;
msl.getRange('A14:P14').format.rowHeight=58;
msl.getRange(`B${first}:C${last}`).format.wrapText=true;
msl.getRange(`E${first}:O${last}`).format.horizontalAlignment='right';
msl.getRange(`A1:P${last}`).format.columnWidth=20;
msl.getRange(`A1:A${last}`).format.columnWidth=22;
msl.getRange(`B1:B${last}`).format.columnWidth=31;
msl.getRange(`C1:C${last}`).format.columnWidth=62;
msl.getRange(`D1:D${last}`).format.columnWidth=26;
msl.getRange(`O1:P${last}`).format.columnWidth=14;
msl.getRange(`I${first}:J${last}`).format.font.bold=true;
msl.tables.add(`A14:P${last}`,true,'ActivosMSL');
msl.freezePanes.freezeRows(14);
msl.freezePanes.freezeColumns(2);

setup(mci,'H',14);title(mci,'Activos fijos de MCI');
mci.getRange('A4:B4').values=[['Corte',new Date('2026-10-19T00:00:00Z')]];
mci.getRange('B4').setNumberFormat('dd/mm/yyyy');
mci.getRange('A6').values=[['Sin activos identificables como MCI en el registro consultado.']];
mci.getRange('A6:H6').format.fill=amber;
mci.getRange('A8').values=[['Los 86 registros encontrados tienen codigo MSL y sus asientos asociados pertenecen a MSL-CR.']];
mci.getRange('A10').values=[['No se duplicaron activos de MSL. Costo y valor neto de MCI: no disponibles, no cero.']];
mci.getRange('A12').values=[['La tabla de activos no tiene un campo propio de empresa. Para completar MCI se requiere su inventario o una asignacion verificable.']];
mci.getRange('A1:H14').format.columnWidth=22;

wb.recalculate();
const originalOctober=base.getRange('Q6').values[0][0];
const originalNet=msl.getRange('J15').values[0][0];
base.getRange('Q6').values=[[originalOctober+31]];
wb.recalculate();
if(Math.abs(msl.getRange('J15').values[0][0]-(originalNet-19))>0.01)throw Error('Proration recalculation failed');
base.getRange('Q6').values=[[originalOctober]];
wb.recalculate();
const sumsExpected={cost:rows.reduce((s,{a})=>s+cents(a.value_crc),0)/100,
 accum:rows.reduce((s,r)=>s+cents(r.closed)+Math.round(cents(r.current)*19/31),0)/100};
const actualCost=msl.getRange('B6').values[0][0];
const actualAccum=msl.getRange('B7').values[0][0];
if(Math.abs(actualCost-sumsExpected.cost)>0.01 || Math.abs(actualAccum-sumsExpected.accum)>0.01)throw Error(JSON.stringify({actualCost,actualAccum,sumsExpected}));
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},summary:'Formula errors'});
console.log(errors.ndjson);
console.log(JSON.stringify({assets:rows.length,cost:actualCost,depreciation:actualAccum,net:msl.getRange('E6').values[0][0],monthly:msl.getRange('E7').values[0][0]}));
for(const [sheetName,range,file] of [['MSL','A2:G19','msl-detail.png'],['MSL','G14:P20','msl-values.png'],['MCI','A2:H13','mci.png'],['Base SOM','A5:H10','source.png']]){
 const blob=await wb.render({sheetName,range,scale:1.3,format:'png'});
 await fs.writeFile(out+'/'+file,new Uint8Array(await blob.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(out+'/Activos_fijos_MSL_MCI_19_10_2026.xlsx');
console.log('Saved '+out+'/Activos_fijos_MSL_MCI_19_10_2026.xlsx');
