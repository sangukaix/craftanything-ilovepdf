import {pdfTools} from "./pdf-tools";
export default function Page(){return <section className="tool-content"><h1>모든 PDF 도구</h1><h2>필요한 작업을 선택하세요.</h2><div className="tool-work"><ul>{pdfTools.map(([name,path])=><li key={path}><a href={`/ko/${path}/`}>{name}</a></li>)}</ul><p><a href="/ko/user/workflows/">여러 작업을 한 번에 실행하기</a> · <a href="/ko/help/documentation/">사용 방법</a></p></div></section>;}
