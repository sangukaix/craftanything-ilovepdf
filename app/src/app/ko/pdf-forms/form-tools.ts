import type {PDFDocument} from "pdf-lib";

export function flattenForm(document:PDFDocument,api:typeof import("pdf-lib")) {
 // pdf-lib 1.17.1 removes field objects but can leave their widget references
 // in page Annots. Capture actual widget references before flatten deletes them.
 const widgets=document.getPages().map(page=>({page,refs:(page.node.Annots()?.asArray()||[]).filter(ref=>{
  const annotation=document.context.lookup(ref);
  return annotation instanceof api.PDFDict&&annotation.get(api.PDFName.of("Subtype"))?.toString()==="/Widget";
 })}));
 document.getForm().flatten({updateFieldAppearances:false});
 for(const {page,refs} of widgets)for(const ref of refs)if(ref instanceof api.PDFRef)page.node.removeAnnot(ref);
}
