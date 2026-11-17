export function pagesToRemove(value:string,count:number){
 const selected=new Set<number>();if(!value.trim())throw new Error("삭제할 페이지를 입력하세요.");
 for(const part of value.split(",")){const match=part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);if(!match)throw new Error("페이지를 2,4-6 형식으로 입력하세요.");const first=Number(match[1]),last=Number(match[2]||match[1]);if(first<1||last<first||last>count)throw new Error(`1~${count}쪽 범위 안에서 선택하세요.`);for(let n=first;n<=last;n++)selected.add(n-1);}
 if(selected.size===count)throw new Error("모든 페이지를 삭제할 수 없습니다. 한 페이지 이상 남겨 주세요.");
 return [...selected].sort((a,b)=>b-a);
}
