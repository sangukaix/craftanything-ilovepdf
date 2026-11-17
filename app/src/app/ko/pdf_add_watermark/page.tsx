import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title={"워터마크"} description={"PDF 문서의 각 페이지에 문구를 추가하세요."} button="PDF 파일 선택" accept=".pdf" multiple={false} drop="또는 PDF를 여기에 두기" />; }
