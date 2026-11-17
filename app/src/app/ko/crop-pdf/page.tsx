import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title="PDF 자르기" description="PDF 각 페이지의 여백을 자릅니다." button="PDF 파일 선택" accept=".pdf" multiple={false} drop="또는 PDF를 여기에 두기" />; }
