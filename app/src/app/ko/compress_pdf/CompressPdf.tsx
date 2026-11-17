"use client";
import {useState} from "react";
import JSZip from "jszip";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
import {postDocument,downloadDocument} from "../local-api";
import CloudButtons from "../CloudButtons";
export default function CompressPdf({description}:{description:string}){
 const [files,setFiles]=useState<File[]>([]),[busy,setBusy]=useState(false),[status,setStatus]=useState("");
 function receive(incoming:File[]){if(busy)return;const error=validateFiles(incoming,".pdf,application/pdf",true);if(error){setStatus(error);return;}const next=[...files,...incoming];if(next.length>10||next.some(f=>f.size>25*1024*1024)||next.reduce((n,f)=>n+f.size,0)>100*1024*1024){setStatus("최대 10개, 파일당 25MB·합계 100MB까지 선택하세요.");return;}setFiles(next);setStatus("");}
 const dragging=useFileDrop(receive,busy);
 async function compress(){if(busy||!files.length)return;setBusy(true);try{const zip=new JSZip();let input=0,output=0;let single:Blob|undefined;let singleName="";
 for(let i=0;i<files.length;i++){const file=files[i];setStatus(`${i+1}/${files.length}: ${file.name} 최적화 중…`);const response=await postDocument("compress",file,{},120000),blob=await response.blob();const name=`${String(i+1).padStart(2,"0")}-optimized-${file.name.replace(/[^\p{L}\p{N}_. -]/gu,"_")}`;zip.file(name,await blob.arrayBuffer());input+=file.size;output+=blob.size;single=blob;singleName=name;}
 if(files.length===1&&single)downloadDocument(single,singleName);else downloadDocument(await zip.generateAsync({type:"blob",compression:"STORE"}),"optimized-pdfs.zip");setStatus(`완료: ${files.length}개 PDF · ${input.toLocaleString()} → ${output.toLocaleString()}바이트. ${output<input?((1-output/input)*100).toFixed(1)+"% 감소.":"이미 최적화된 파일은 원본 크기를 유지했습니다."} ${files.length>1?"ZIP 안의 PDF를 확인하세요.":"다운로드한 PDF를 확인하세요."}`);
 }catch(e){setStatus(e instanceof Error?e.message:"최적화하지 못했습니다. 파일을 확인하고 다시 실행하세요.");}finally{setBusy(false);}}
 return <section className="tool-content">{dragging&&<div className="file-drop-overlay" role="status">PDF 파일을 놓아 추가하세요</div>}<h1>PDF 압축</h1><h2>{description}</h2><div className="tool-picker"><label className="tool-file-button">여러 PDF 파일 선택<input type="file" multiple accept=".pdf,application/pdf" disabled={busy} onChange={e=>{receive(Array.from(e.target.files||[]));e.target.value="";}}/></label><CloudButtons/></div><p className="tool-drop">또는 PDF를 여기에 두기</p>{(files.length>0||status)&&<div className="tool-work"><p>최대 10개 · 파일당 25MB · 합계 100MB. 이미지 품질을 낮추지 않는 무손실 최적화입니다. 이미 최적화된 파일은 줄지 않을 수 있습니다. 전자서명 문서는 재저장으로 서명이 무효가 될 수 있습니다.</p><ol>{files.map((file,i)=><li key={i}><span>{file.name}</span><button type="button" disabled={busy} aria-label={`${i+1}번 파일 제거`} onClick={()=>setFiles(old=>old.filter((_,index)=>i!==index))}>×</button></li>)}</ol>{files.length>0&&<button type="button" className="tool-run" disabled={busy} onClick={compress}>{busy?"최적화 중…":files.length>1?"PDF 최적화 · ZIP 다운로드":"PDF 최적화 · 다운로드"}</button>}<p role="status">{status}</p></div>}</section>;
}
