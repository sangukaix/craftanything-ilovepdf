"use client";
import {useState,type ChangeEvent} from "react";
import {useFileDrop} from "../use-file-drop";
import {validateFiles} from "../file-drop";
import {postDocument,downloadDocument} from "../local-api";
import {useReady} from "../use-ready";
export default function Page(){
 const ready=useReady();
 const [file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState(""),[language,setLanguage]=useState("ko"),[length,setLength]=useState("short"),[summary,setSummary]=useState(""),[info,setInfo]=useState("");
 function receive(files:File[]){if(busy)return;const error=validateFiles(files,".pdf,application/pdf",false);if(error){setStatus(error);return;}if(files[0].size>25*1024*1024){setStatus("25MB 이하 PDF를 사용하세요.");return;}setFile(files[0]);setSummary("");setInfo("");setStatus("");}
 const dragging=useFileDrop(receive,busy);
 function choose(e:ChangeEvent<HTMLInputElement>){receive(Array.from(e.target.files||[]));e.target.value="";}
 async function summarize(){if(!file||busy)return;setBusy(true);setSummary("");setStatus("로컬 Qwen이 문서를 요약 중입니다. 긴 문서는 여러 부분으로 나누어 처리하므로 수 분 걸릴 수 있습니다…");try{const response=await postDocument("summarize",file,{language,length});const result=await response.json();setSummary(result.summary);setInfo(`${result.pages}쪽 · ${result.characters.toLocaleString()}자 · 로컬 ${result.model}`);setStatus("완료했습니다. 숫자·날짜·페이지 표시는 원문과 대조하세요.");}catch(e){setStatus(e instanceof Error?e.message:"요약에 실패했습니다.");}finally{setBusy(false);}}
 function textDownload(){downloadDocument(new Blob([summary],{type:"text/plain;charset=utf-8"}),"pdf-summary.txt");}
 async function pdfDownload(){if(!file)return;setBusy(true);try{const response=await postDocument("summary-pdf",file,{summary});downloadDocument(await response.blob(),"pdf-summary.pdf");}catch(e){setStatus(e instanceof Error?e.message:"PDF로 저장하지 못했습니다.");}finally{setBusy(false);}}
 return <section className="tool-content">{dragging&&<div className="file-drop-overlay" role="status">요약할 PDF를 놓아주세요</div>}<h1>AI PDF 요약</h1><h2>로컬 Qwen으로 문서의 핵심 내용을 정리합니다.</h2><div className="tool-picker"><label className="tool-file-button">PDF 파일 선택<input type="file" accept=".pdf,application/pdf" disabled={!ready||busy} onChange={choose}/></label></div><div className="tool-work"><p>25MB·50쪽·추출 텍스트 30,000자까지 지원합니다. 이 PC의 로컬 Qwen 서버를 사용하며 클라우드 API 키가 필요하지 않습니다. AI의 요약·페이지 인용에는 누락·오류가 있을 수 있습니다. 스캔은 먼저 <a href="/ko/ocr-pdf/">OCR</a>을 실행하세요.</p><label>요약 언어<select value={language} disabled={!ready||busy} onChange={e=>setLanguage(e.target.value)}><option value="ko">한국어</option><option value="en">영어</option></select></label><label>요약 길이<select value={length} disabled={!ready||busy} onChange={e=>setLength(e.target.value)}><option value="short">간단히</option><option value="detailed">자세히</option></select></label>{file&&<><p>{file.name}</p><button className="tool-run" disabled={!ready||busy} onClick={summarize}>{busy?"처리 중…":"로컬 AI로 요약"}</button></>}<p role="status">{status}</p>{summary&&<><p>{info}</p><div style={{whiteSpace:"pre-wrap",lineHeight:1.7,border:"1px solid #ddd",padding:16,background:"#fafafa"}}>{summary}</div><button className="tool-run" disabled={!ready||busy} onClick={textDownload}>요약 TXT 다운로드</button> <button className="tool-run" disabled={!ready||busy} onClick={pdfDownload}>요약 PDF 다운로드</button></>}</div></section>;
}
