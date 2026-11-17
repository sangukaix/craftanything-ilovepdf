import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title={"PDF 구성"} description={"페이지 순서를 지정하거나 원하는 페이지를 선택하세요."} button="PDF 파일 선택" accept=".pdf" multiple={false} drop="또는 PDF를 여기에 두기" />; }
