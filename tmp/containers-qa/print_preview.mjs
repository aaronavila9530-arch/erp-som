import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const book = await SpreadsheetFile.importXlsx(await FileBlob.load(process.argv[2]));
for (const [name,range] of [['top','A1:AJ20'], ['narrative','A21:AJ42'], ['bottom','A43:AJ60']]) {
 const blob = await book.render({sheetName:'DRY CARGO',range,scale:1.3,format:'png'});
 await fs.writeFile(new URL('./'+name+'.png',import.meta.url),new Uint8Array(await blob.arrayBuffer()));
}
