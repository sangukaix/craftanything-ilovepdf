import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title="PDF 회전" description="원하는대로 PDF를 회전하세요." button="PDF 파일 선택" accept=".pdf" multiple={false} drop="또는 PDF를 여기에 두기" />; }
