import {pdfTools} from "../pdf-tools";
const information:Record<string,{title:string;paragraphs:string[]}>= {
 "help/privacy":{title:"파일과 개인정보 처리 안내",paragraphs:["PDF와 사진은 기능에 따라 이 브라우저 또는 이 PC의 로컬 문서 서비스에서 처리합니다. AI 요약·번역은 로컬 Qwen을 사용합니다.","Office·PDF/A 변환은 이 PC의 임시 작업 폴더를 사용하고 작업 종료 후 삭제합니다. 프로그램이 강제 종료되면 임시 파일이 남을 수 있습니다. 다운로드한 결과는 사용자가 보관합니다.","HTML 공개 주소 변환이나 외부 리소스 허용을 선택하면 해당 웹 사이트에 연결합니다. 카메라는 사용자가 켰을 때만 권한을 요청합니다. 인증서 서명에서는 개인키·비밀번호를 로컬 메모리에서 처리하며 서명된 PDF에는 공개 인증서가 포함됩니다."]},
 "help/security":{title:"안전한 PDF 작업",paragraphs:["편집·변환·페이지 삭제를 하면 기존 전자서명이 무효가 될 수 있습니다. 원본을 보관하고 결과를 확인하세요.","검열은 선택 영역의 내용을 삭제합니다. 문서 전체의 메타데이터·첨부파일 삭제를 보장하지 않습니다. 자르기는 보이는 범위만 바꿉니다.","디지털 서명 검사는 문서 무결성을 확인하며, 인증기관 신뢰·폐기 여부·공인 타임스탬프는 별도로 확인해야 합니다."]},
 "help/cookies":{title:"브라우저 저장 안내",paragraphs:["선택한 문서의 작업 상태는 열려 있는 도구 화면에서 사용합니다. 다운로드한 파일은 브라우저의 다운로드 폴더에 저장됩니다.","PDF 도구는 로그인 없이 사용할 수 있습니다. 개인 보관함 로그인은 HttpOnly 세션 쿠키를 사용합니다. 계정과 암호화된 보관 파일은 이 PC의 .local-data 폴더에 저장됩니다."]},
 "help/faq":{title:"자주 묻는 질문",paragraphs:["파일을 놓아도 인식되지 않나요? 도구에 맞는 파일 형식을 확인하고 큰 파일 선택 버튼이나 화면의 빈 곳에 놓아보세요. 폴더와 바로가기는 지원하지 않습니다.","처리 연결 오류가 나나요? 이 PC의 로컬 문서 서비스가 실행 중인지 확인하세요. AI 요약·번역에는 로컬 Qwen 모델도 필요합니다.","스캔 PDF의 글자를 읽지 못하나요? OCR 도구로 검색 가능한 PDF를 만든 다음 요약·번역·Word 변환을 사용하세요.","원래 글꼴을 유지할 수 없나요? PDF에 글꼴이 없거나 새 문자의 글리프가 빠져 있을 수 있습니다. 글꼴 보존 모드에서는 중단하고, 대체 허용 모드에서는 가능한 원래 글꼴을 유지하면서 대체합니다."]},
 "help/documentation":{title:"PDF 도구 사용 방법",paragraphs:["도구 선택 → 파일 선택 또는 드래그 → 옵션 지정 → 실행 → 결과 다운로드 순서로 사용합니다.","문단 재배치는 PDF 편집에서 선택할 수 있습니다. 원본 문단을 누른 뒤 새 글자와 위치·영역 크기를 지정하세요. 주변 내용과 겹치면 저장하지 않습니다.","카메라·사진 스캔은 사진을 보정하고 순서를 정해 PDF로 만듭니다. 검색 가능한 글자는 OCR 도구에서 추가하세요."]},
 "features":{title:"사용할 수 있는 PDF 도구",paragraphs:["병합·분할·변환·OCR·편집·문단 재배치·양식·서명·검열·요약·번역을 아래에서 선택할 수 있습니다. 파일 크기와 지원 범위는 각 도구 화면에 표시됩니다."]},
 "help/about":{title:"이 PDF 작업 공간 소개",paragraphs:["이 PC에서 문서를 처리하는 로컬 PDF 작업 공간입니다. iLovePDF 공식 클라우드 서비스의 계정·결제·저장소와 연결되어 있지 않습니다."]},
 "help/terms":{title:"로컬 도구 이용 안내",paragraphs:["결과 파일의 글자·레이아웃·변환 결과를 원본과 대조하세요. AI 요약·번역과 OCR에는 오류가 있을 수 있습니다. 중요한 원본은 별도로 보관하세요.","이 페이지는 현재 로컬 도구의 사용 범위 안내입니다. 개인 보관함의 자체 계정과 모의 결제를 시험할 수 있습니다. 이메일 인증·계정 복구·실제 결제·외부 클라우드는 아직 연결되지 않았습니다."]},
 "help/legal":{title:"서비스 범위 안내",paragraphs:["이 작업 공간은 로컬 PDF 작업 도구입니다. 공식 클라우드 서비스와 별개이며, 유료 서비스 구매·전자서명 요청 메일 발송·인증기관의 신원 확인은 제공하지 않습니다."]},
 "education":{title:"문서 학습·수업 작업",paragraphs:["시험용 문서로 변환 결과를 확인한 뒤 필요한 파일에 적용하세요. OCR·Word·Excel 변환과 AI 요약·번역을 함께 사용할 수 있습니다. 원본 파일은 보관하세요."]},
 "blog":{title:"PDF 작업 팁",paragraphs:["스캔 → OCR → 요약·번역 순서로 처리하면 이미지 문서의 글자를 활용할 수 있습니다.","원문 글자 수정은 한 줄 또는 문단을 선택해 실행합니다. 완성된 문서는 마지막에 서명하세요. 서명 후 편집하면 무결성 검사가 달라질 수 있습니다."]},
 "contact":{title:"문제 확인 방법",paragraphs:["문제가 생긴 도구와 오류 문구, 입력 형식·크기를 확인하세요. 시험용 파일로 같은 현상이 발생하는지 확인하면 문제를 구분하기 쉽습니다.","외부 문의 메일을 보내거나 개인 문서를 업로드하는 기능은 제공하지 않습니다. 아래 도움말과 도구를 이용할 수 있습니다."]},
 "press":{title:"로컬 PDF 작업 공간",paragraphs:["사용 가능한 PDF 도구와 사용 방법은 아래 목록과 도움말에서 확인할 수 있습니다."]},
};
export const dynamicParams=false;
export function generateStaticParams(){return Object.keys(information).map(path=>({info:path.split("/")}));}
export default async function Page({params}:{params:Promise<{info:string[]}>}){const path=(await params).info.join("/"),entry=information[path];return <section className="tool-content"><h1>{entry.title}</h1><div className="tool-work">{entry.paragraphs.map((paragraph,i)=><p key={i}>{paragraph}</p>)}<p><a href="/ko/help/faq/">자주 묻는 질문</a> · <a href="/ko/help/documentation/">사용 방법</a> · <a href="/ko/help/privacy/">파일 처리 안내</a></p><ul>{pdfTools.map(([name,route])=><li key={route}><a href={`/ko/${route}/`}>{name}</a></li>)}</ul></div></section>;}
