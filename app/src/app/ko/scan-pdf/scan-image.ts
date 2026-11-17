export type Point=[number,number];
export type ScanOptions={rotation:number;gray:boolean;contrast:number;brightness:number;left:number;top:number;right:number;bottom:number;perspective:boolean;corners:Point[]};
export const defaults:ScanOptions={rotation:0,gray:false,contrast:1.15,brightness:1.05,left:0,top:0,right:0,bottom:0,perspective:false,corners:[[0,0],[100,0],[100,100],[0,100]]};
async function loadImage(source:string){const image=new Image();await new Promise<void>((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error("사진을 읽는 시간이 초과되었습니다.")),15000);image.onload=()=>{clearTimeout(timer);resolve();};image.onerror=()=>{clearTimeout(timer);reject(new Error("사진을 읽지 못했습니다."));};image.src=source;});return image;}
export function quadArea(corners:Point[]){return Math.abs(corners.reduce((area,p,i)=>{const q=corners[(i+1)%4];return area+p[0]*q[1]-q[0]*p[1];},0))/2;}
function validQuad(points:Point[]){
 if(points.length!==4||points.some(p=>p.length!==2||p.some(v=>!Number.isFinite(v)||v<0||v>100))||quadArea(points)<300)throw new Error("모서리는 왼쪽 위 → 오른쪽 위 → 오른쪽 아래 → 왼쪽 아래 순서로 지정하세요. 문서 영역이 너무 작으면 보정할 수 없습니다.");
 const cross=points.map((p,i)=>{const q=points[(i+1)%4],r=points[(i+2)%4];return(q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0]);});if(cross.some(v=>v<=0))throw new Error("문서 모서리가 서로 교차하거나 뒤집혔습니다.");
}
export function homography(points:Point[]){
 // Map a unit square to the source quadrilateral, with h33 = 1.
 const unit=[[0,0],[1,0],[1,1],[0,1]],matrix:number[][]=[];
 for(let i=0;i<4;i++){const [u,v]=unit[i],[x,y]=points[i];matrix.push([u,v,1,0,0,0,-u*x,-v*x,x]);matrix.push([0,0,0,u,v,1,-u*y,-v*y,y]);}
 for(let i=0;i<8;i++){let pivot=i;for(let j=i+1;j<8;j++)if(Math.abs(matrix[j][i])>Math.abs(matrix[pivot][i]))pivot=j;[matrix[i],matrix[pivot]]=[matrix[pivot],matrix[i]];const divisor=matrix[i][i];if(Math.abs(divisor)<1e-9)throw new Error("모서리 좌표로 원근 보정할 수 없습니다.");for(let k=i;k<9;k++)matrix[i][k]/=divisor;for(let j=0;j<8;j++){if(j===i)continue;const factor=matrix[j][i];for(let k=i;k<9;k++)matrix[j][k]-=factor*matrix[i][k];}}
 return matrix.map(row=>row[8]);
}
async function warp(source:string,corners:Point[]){
 validQuad(corners);const image=await loadImage(source),scale=Math.min(1,2400/Math.max(image.naturalWidth,image.naturalHeight)),input=document.createElement("canvas");input.width=Math.round(image.naturalWidth*scale);input.height=Math.round(image.naturalHeight*scale);const context=input.getContext("2d",{willReadFrequently:true});if(!context)throw new Error("사진 보정을 사용할 수 없습니다.");context.drawImage(image,0,0,input.width,input.height);
 const points=corners.map(([x,y])=>[x*(input.width-1)/100,y*(input.height-1)/100] as Point),distance=(a:Point,b:Point)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
 const width=Math.max(2,Math.round(Math.max(distance(points[0],points[1]),distance(points[3],points[2])))),height=Math.max(2,Math.round(Math.max(distance(points[0],points[3]),distance(points[1],points[2]))));
 const output=document.createElement("canvas");output.width=width;output.height=height;const target=output.getContext("2d");if(!target)throw new Error("사진 보정을 사용할 수 없습니다.");const pixels=context.getImageData(0,0,input.width,input.height),result=target.createImageData(width,height),h=homography(points);
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){const u=x/(width-1),v=y/(height-1),denominator=h[6]*u+h[7]*v+1,sx=Math.max(0,Math.min(input.width-1,(h[0]*u+h[1]*v+h[2])/denominator)),sy=Math.max(0,Math.min(input.height-1,(h[3]*u+h[4]*v+h[5])/denominator)),x0=Math.floor(sx),y0=Math.floor(sy),x1=Math.min(input.width-1,x0+1),y1=Math.min(input.height-1,y0+1),fx=sx-x0,fy=sy-y0,index=(y*width+x)*4;
  for(let c=0;c<3;c++)result.data[index+c]=pixels.data[(y0*input.width+x0)*4+c]*(1-fx)*(1-fy)+pixels.data[(y0*input.width+x1)*4+c]*fx*(1-fy)+pixels.data[(y1*input.width+x0)*4+c]*(1-fx)*fy+pixels.data[(y1*input.width+x1)*4+c]*fx*fy;result.data[index+3]=255;}
 target.putImageData(result,0,0);return output.toDataURL("image/jpeg",.96);
}
export async function detectPaper(source:string):Promise<Point[]>{
 const image=await loadImage(source),canvas=document.createElement("canvas"),scale=Math.min(1,360/Math.max(image.naturalWidth,image.naturalHeight));canvas.width=Math.round(image.naturalWidth*scale);canvas.height=Math.round(image.naturalHeight*scale);const context=canvas.getContext("2d",{willReadFrequently:true});if(!context)throw new Error("문서 경계를 찾을 수 없습니다.");context.drawImage(image,0,0,canvas.width,canvas.height);const pixels=context.getImageData(0,0,canvas.width,canvas.height).data,total=canvas.width*canvas.height,gray=new Uint8Array(total),hist=new Uint32Array(256);
 for(let i=0;i<total;i++){gray[i]=Math.round(.299*pixels[i*4]+.587*pixels[i*4+1]+.114*pixels[i*4+2]);hist[gray[i]]++;}
 let all=0;for(let i=0;i<256;i++)all+=i*hist[i];let sum=0,background=0,best=0,threshold=180;
 for(let i=0;i<255;i++){background+=hist[i];if(!background)continue;const foreground=total-background;if(!foreground)break;sum+=i*hist[i];const between=background*foreground*(sum/background-(all-sum)/foreground)**2;if(between>best){best=between;threshold=i;}}
 const seen=new Uint8Array(total),queue=new Uint32Array(total);let bestPoints:Point[]|null=null,bestCount=0;
 for(let start=0;start<total;start++){if(seen[start]||gray[start]<=threshold)continue;let head=0,tail=1;queue[0]=start;seen[start]=1;let minSum=Infinity,maxSum=-Infinity,minDiff=Infinity,maxDiff=-Infinity;const corners:Point[]=[[0,0],[0,0],[0,0],[0,0]];
  while(head<tail){const index=queue[head++],x=index%canvas.width,y=Math.floor(index/canvas.width),sum=x+y,diff=x-y;if(sum<minSum){minSum=sum;corners[0]=[x,y];}if(diff>maxDiff){maxDiff=diff;corners[1]=[x,y];}if(sum>maxSum){maxSum=sum;corners[2]=[x,y];}if(diff<minDiff){minDiff=diff;corners[3]=[x,y];}const neighbours=[x?index-1:-1,x+1<canvas.width?index+1:-1,y?index-canvas.width:-1,y+1<canvas.height?index+canvas.width:-1];for(const n of neighbours)if(n>=0&&!seen[n]&&gray[n]>threshold){seen[n]=1;queue[tail++]=n;}}
  if(tail>bestCount){bestCount=tail;bestPoints=corners;}}
 if(!bestPoints||bestCount<total*.1)throw new Error("밝은 문서 경계를 찾지 못했습니다. 모서리를 직접 조정하세요.");
 const points=bestPoints.map(([x,y])=>[x/(canvas.width-1)*100,y/(canvas.height-1)*100] as Point);validQuad(points);return points;
}
export async function processScan(source:string,options:ScanOptions):Promise<HTMLCanvasElement>{
 if(!Number.isFinite(options.contrast)||!Number.isFinite(options.brightness)||options.contrast<.5||options.contrast>2||options.brightness<.5||options.brightness>2)throw new Error("밝기와 대비는 0.5~2 범위로 설정하세요.");
 if(options.perspective)return processScan(await warp(source,options.corners),{...options,perspective:false});
 const image=new Image();await new Promise<void>((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error("사진을 읽는 시간이 초과되었습니다.")),15000);image.onload=()=>{clearTimeout(timeout);resolve();};image.onerror=()=>{clearTimeout(timeout);reject(new Error("사진을 읽지 못했습니다. JPG·PNG·WEBP를 사용하세요."));};image.src=source;});
 const {left,top,right,bottom}=options;if([left,top,right,bottom].some(v=>!Number.isFinite(v)||v<0||v>49)||left+right>=95||top+bottom>=95)throw new Error("자르기 비율을 확인하세요.");
 const width=image.naturalWidth*(1-(left+right)/100),height=image.naturalHeight*(1-(top+bottom)/100),scale=Math.min(1,2400/Math.max(width,height));
 const turn=((options.rotation%360)+360)%360;if(![0,90,180,270].includes(turn))throw new Error("회전 각도를 확인하세요.");
 const canvas=document.createElement("canvas");canvas.width=Math.max(1,Math.round((turn%180?height:width)*scale));canvas.height=Math.max(1,Math.round((turn%180?width:height)*scale));const ctx=canvas.getContext("2d");if(!ctx)throw new Error("사진 처리 기능을 사용할 수 없습니다.");
 ctx.fillStyle="white";ctx.fillRect(0,0,canvas.width,canvas.height);ctx.translate(canvas.width/2,canvas.height/2);ctx.rotate(turn*Math.PI/180);ctx.filter=`${options.gray?"grayscale(1)":""} contrast(${options.contrast}) brightness(${options.brightness})`;
 ctx.drawImage(image,image.naturalWidth*left/100,image.naturalHeight*top/100,width,height,-width*scale/2,-height*scale/2,width*scale,height*scale);
 return canvas;
}
