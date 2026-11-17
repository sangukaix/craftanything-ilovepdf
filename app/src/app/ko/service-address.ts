// Shared HTTPS pages call the gateway on their own origin, never the visitor's PC.
export function serviceAddress(kind:"pdf"|"account"){
 const override=kind==="pdf"?process.env.NEXT_PUBLIC_PDF_API:process.env.NEXT_PUBLIC_ACCOUNT_API;
 if(override)return override;
 if(typeof window==="undefined"||(["127.0.0.1","localhost","[::1]"].includes(window.location.hostname)&&window.location.port==="8766"))return kind==="pdf"?"http://127.0.0.1:8767":"http://127.0.0.1:8768";
 return kind==="pdf"?"/pdf-api":"/account-api";
}
