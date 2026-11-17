import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title={"PDF 합치기"} description={"원하는대로 PDF 파일들을 병합하고 통합하세요. 매우 쉽고 빠릅니다!"} button={"여러 PDF 파일 선택"} accept={".pdf"} multiple={true} drop={"또는 PDF를 여기에 두기"} />; }
