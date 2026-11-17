import ToolPage from "../ToolPage";
export default function Page() { return <ToolPage title={"JPG PDF 변환"} description={"이미지에서 PDF로 변환. 방향과 여백을 조절하세요."} button={"JPG 이미지 선택"} accept={".jpg,.jpeg,image/jpeg"} multiple={true} drop={"또는 JPG 이미지를 여기에 두기"} />; }
