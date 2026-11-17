const fs=require('fs'),path=require('path'),assert=require('assert'),{createRequire}=require('module');
const app=path.resolve(__dirname,'../app'),req=createRequire(path.join(app,'package.json')),ts=req('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);
const {JSDOM}=req('jsdom');const dom=new JSDOM('<div id="root"></div>',{url:'http://127.0.0.1:8766'});
global.window=dom.window;global.document=dom.window.document;Object.defineProperty(global,'navigator',{configurable:true,value:dom.window.navigator});global.IS_REACT_ACT_ENVIRONMENT=true;
dom.window.HTMLMediaElement.prototype.play=async()=>{};
const React=req('react'),{act}=React,{createRoot}=req('react-dom/client');
const Scan=require(path.join(app,'src/app/ko/scan-pdf/page.tsx')).default;
const {pagesToRemove}=require(path.join(app,'src/app/ko/remove-pages/remove.ts'));
const {homography,quadArea}=require(path.join(app,'src/app/ko/scan-pdf/scan-image.ts'));
let root;
async function mount(getUserMedia){Object.defineProperty(dom.window.navigator,'mediaDevices',{configurable:true,value:{getUserMedia}});root=createRoot(document.getElementById('root'));await act(async()=>root.render(React.createElement(Scan)));}
function button(label){return [...document.querySelectorAll('button')].find(b=>b.textContent===label);}
async function click(label){const target=button(label);assert(target,label);await act(async()=>{target.click();await Promise.resolve();});}
async function unmount(){await act(async()=>root.unmount());}
(async()=>{
 const {serviceAddress}=require(path.join(app,'src/app/ko/service-address.ts'));
 assert.strictEqual(serviceAddress('pdf'),'http://127.0.0.1:8767');assert.strictEqual(serviceAddress('account'),'http://127.0.0.1:8768');
 dom.reconfigure({url:'https://share.example.invalid/ko/pdf_to_word/'});assert.strictEqual(serviceAddress('pdf'),'/pdf-api');assert.strictEqual(serviceAddress('account'),'/account-api');
 dom.reconfigure({url:'http://127.0.0.1:8770/'});assert.strictEqual(serviceAddress('pdf'),'/pdf-api');
 dom.reconfigure({url:'http://127.0.0.1:8766/'});
 console.log('PASS service addresses: local preview stays local; shared HTTPS and gateway never target the visitor PC');
 assert.deepStrictEqual(pagesToRemove('2,4-5,2',6),[4,3,1]);
 for(const range of ['','0','7','4-2','1-6','bad'])assert.throws(()=>pagesToRemove(range,6));
 console.log('PASS page deletion: ranges, duplicates, descending order, bounds, retain at least one page');
 const quad=[[20,10],[210,20],[230,320],[15,290]],h=homography(quad),unit=[[0,0],[1,0],[1,1],[0,1]];
 unit.forEach(([u,v],i)=>{const z=h[6]*u+h[7]*v+1;assert(Math.abs((h[0]*u+h[1]*v+h[2])/z-quad[i][0])<1e-6);assert(Math.abs((h[3]*u+h[4]*v+h[5])/z-quad[i][1])<1e-6);});
 assert(quadArea(quad)>100);assert.throws(()=>homography([[0,0],[0,0],[0,0],[0,0]]));
 console.log('PASS perspective transform: all four document corners map exactly; singular input rejected');
 let resolve,calls=0,stops=0;
 await mount(()=>{calls++;return new Promise(r=>{resolve=r;});});
 await click('카메라 켜기');assert.strictEqual(calls,1);assert(button('카메라 연결 중…').disabled);
 await click('카메라 연결 중…');assert.strictEqual(calls,1);
 await click('카메라 요청 취소');assert(document.body.textContent.includes('카메라 요청을 취소'));
 await act(async()=>resolve({getTracks:()=>[{stop:()=>stops++}]}));assert.strictEqual(stops,1);await unmount();
 console.log('PASS camera: duplicate request blocked, cancellation immediate, late stream stopped');
 stops=0;await mount(()=>new Promise(r=>{resolve=r;}));await click('카메라 켜기');await unmount();
 await act(async()=>resolve({getTracks:()=>[{stop:()=>stops++}]}));assert.strictEqual(stops,1);
 console.log('PASS camera: unmount stops stream even when permission resolves later');
 stops=0;await mount(async()=>({getTracks:()=>[{stop:()=>stops++}]}));await click('카메라 켜기');assert(button('문서 촬영'));await click('카메라 끄기');assert.strictEqual(stops,1);await unmount();
 console.log('PASS camera: active stream stops on user request');
 await mount(async()=>{throw new dom.window.DOMException('No camera','NotFoundError');});
 // The app checks DOMException from the host realm as browsers do.
 const original=global.DOMException;global.DOMException=dom.window.DOMException;
 await click('카메라 켜기');assert(document.body.textContent.includes('연결된 카메라가 없습니다'));global.DOMException=original;await unmount();
 console.log('PASS camera: missing device produces actionable photo-upload fallback');
})().catch(error=>{console.error(error);process.exitCode=1;});
