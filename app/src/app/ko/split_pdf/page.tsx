import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title={"PDF 분할"} description={"페이지 범위를 선택하고, 한 페이지를 분리하거나 문서의 각 페이지를 독립된 PDF 파일로 변환하세요."} button={"PDF 파일 선택"} accept={".pdf"} multiple={false} drop={"또는 PDF를 여기에 두기"} />; }
