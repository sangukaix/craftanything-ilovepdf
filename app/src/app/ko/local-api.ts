import {serviceAddress} from "./service-address";
export async function postDocument(operation:string,file:File,extra:Record<string,unknown>={},timeoutMs=600000){
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeoutMs);
 try{
  const encoded=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=()=>reject(new Error("파일을 읽지 못했습니다."));reader.readAsDataURL(file);});
  const response=await fetch(`${serviceAddress("pdf")}/api/pdf/${operation}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({pdf:encoded,...extra}),signal:controller.signal,cache:"no-store"});
  if(!response.ok){const error=await response.json();throw new Error(error.error||"처리에 실패했습니다.");}
  return response;
 }catch(error){
  if(error instanceof TypeError)throw new Error("로컬 문서 서비스에 연결하지 못했습니다. start-pdf-service.cmd를 실행하세요.");
  if(error instanceof Error&&error.name==="AbortError")throw new Error("처리 시간이 초과되었습니다. 더 작은 파일로 다시 시도하세요.");
  throw error;
 }finally{clearTimeout(timer);}
}
export function downloadDocument(blob:Blob,name:string){const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
