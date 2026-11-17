export const ACCOUNT_API=process.env.NEXT_PUBLIC_ACCOUNT_API||"http://127.0.0.1:8768";
export type Account={id:string;email:string;csrf:string;plan:string;paidUntil:number;files:number;bytes:number;maxFiles:number;maxBytes:number;emailVerified:boolean};
export type VaultFile={id:string;name:string;size:number;created:number};
export type Order={id:string;name:string;amount:number;currency:string;provider:string;status:string;created:number;applied:number};
export type AccountConfig={mode:string;providers:string[];tossClientKey:string;catalog:Record<string,{name:string;amount:number;currency:string;days:number}>};
export async function accountRequest(path:string,method="GET",body?:unknown,csrf?:string){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),45000);
 try{const response=await fetch(ACCOUNT_API+path,{method,credentials:"include",cache:"no-store",headers:{...(body!==undefined?{"Content-Type":"application/json"}:{}),...(csrf?{"X-CSRF-Token":csrf}:{})},body:body!==undefined?JSON.stringify(body):undefined,signal:controller.signal});
 if(!response.ok){const data=await response.json();throw new Error(data.error||"요청에 실패했습니다.");}return response;
 }catch(error){if(error instanceof TypeError)throw new Error("계정 서비스에 연결하지 못했습니다. start-local-pdf.cmd를 실행하세요.");if(error instanceof Error&&error.name==="AbortError")throw new Error("응답 시간이 초과되었습니다. 주문 내역을 확인한 뒤 다시 시도하세요.");throw error;}finally{clearTimeout(timer);}
}
export async function currentAccount():Promise<Account>{return (await accountRequest("/api/me")).json();}
export const sizeLabel=(bytes:number)=>`${(bytes/1024/1024).toFixed(2)} MB`;
