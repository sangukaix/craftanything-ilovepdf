export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">HTML PDF 변환</h1>
      <p className="mb-8 text-[22px]">HTML 웹 페이지를 PDF로 변환합니다. 원하는 페이지의 URL을 복사하여 붙여넣은 다음 클릭하여 PDF로 변환합니다.</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        URL을 입력하세요
      </div>
    </div>
  )
}
