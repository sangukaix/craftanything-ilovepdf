type PositionedText={text:string;x:number;y:number;width:number;height:number};
export function textToRows(items:PositionedText[]):string[][]{
 const lines:{y:number;height:number;items:PositionedText[]}[]=[];
 for(const item of [...items].filter(i=>i.text.trim()).sort((a,b)=>b.y-a.y||a.x-b.x)){
  let line=lines.find(l=>Math.abs(l.y-item.y)<=Math.max(2,Math.min(l.height,item.height)*.35));
  if(!line){line={y:item.y,height:item.height,items:[]};lines.push(line);}line.items.push(item);
 }
 const groups=lines.sort((a,b)=>b.y-a.y).map(line=>{
  const cells:{x:number;end:number;text:string;height:number}[]=[];
  for(const item of line.items.sort((a,b)=>a.x-b.x)){
   const previous=cells[cells.length-1];
   if(previous&&item.x-previous.end<Math.max(8,item.height*.75)){
    previous.text+=(previous.text.endsWith(" ")||item.text.startsWith(" ")?"":" ")+item.text;previous.end=Math.max(previous.end,item.x+item.width);
   }else cells.push({x:item.x,end:item.x+item.width,text:item.text,height:item.height});
  }
  return cells;
 });
 const columns:number[]=[];
 for(const cell of groups.flat().sort((a,b)=>a.x-b.x))if(!columns.some(x=>Math.abs(x-cell.x)<=12))columns.push(cell.x);
 if(columns.length>256||groups.length>65536)throw new Error("추출된 표가 너무 큽니다. PDF를 분할한 뒤 다시 시도하세요.");
 return groups.map(cells=>{
  const row=Array<string>(columns.length).fill("");
  for(const cell of cells){let index=0;for(let i=1;i<columns.length;i++)if(Math.abs(columns[i]-cell.x)<Math.abs(columns[index]-cell.x))index=i;row[index]+=(row[index]?" ":"")+cell.text.trim();}
  return row;
 });
}
function xml(value:string){return value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g,"").replace(/_x[0-9a-f]{4}_/gi,s=>"_x005F_"+s.slice(1)).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function columnName(index:number){let result="";for(let n=index+1;n>0;n=Math.floor((n-1)/26))result=String.fromCharCode(65+(n-1)%26)+result;return result;}
const ns="http://schemas.openxmlformats.org/spreadsheetml/2006/main";
const rel="http://schemas.openxmlformats.org/officeDocument/2006/relationships";
const declaration='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
export async function createWorkbook(sheets:string[][][]){
 const {default:JSZip}=await import("jszip");const zip=new JSZip();
 const types=sheets.map((_,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("");
 zip.file("[Content_Types].xml",declaration+`<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>${types}</Types>`);
 zip.file("_rels/.rels",declaration+`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>`);
 zip.file("xl/workbook.xml",declaration+`<workbook xmlns="${ns}" xmlns:r="${rel}"><sheets>${sheets.map((_,i)=>`<sheet name="Page ${i+1}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join("")}</sheets></workbook>`);
 zip.file("xl/_rels/workbook.xml.rels",declaration+`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${sheets.map((_,i)=>`<Relationship Id="rId${i+1}" Type="${rel}/worksheet" Target="worksheets/sheet${i+1}.xml"/>`).join("")}<Relationship Id="styles" Type="${rel}/styles" Target="styles.xml"/></Relationships>`);
 zip.file("xl/styles.xml",declaration+`<styleSheet xmlns="${ns}"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="1"><xf xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`);
 sheets.forEach((rows,i)=>{
  const count=Math.max(1,...rows.map(row=>row.length));
  const data=rows.map((row,r)=>`<row r="${r+1}">${row.map((value,c)=>{if(value.length>32767)throw new Error("한 셀의 텍스트가 Excel 제한을 초과했습니다.");return value?`<c r="${columnName(c)}${r+1}" t="inlineStr"><is><t xml:space="preserve">${xml(value)}</t></is></c>`:"";}).join("")}</row>`).join("");
  zip.file(`xl/worksheets/sheet${i+1}.xml`,declaration+`<worksheet xmlns="${ns}"><dimension ref="A1:${columnName(count-1)}${Math.max(1,rows.length)}"/><sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="18"/><cols><col min="1" max="${count}" width="26" customWidth="1"/></cols><sheetData>${data}</sheetData></worksheet>`);
 });
 return zip.generateAsync({type:"uint8array",compression:"DEFLATE"});
}
