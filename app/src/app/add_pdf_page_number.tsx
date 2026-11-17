export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">페이지 수 추가</h1>
      <p className="mb-8 text-[22px]">PDF 문서에 페이지 번호를 쉽게 추가하세요. 위치, 크기, 폰트 선택이 가능합니다.</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        파일을 드래그하거나 클릭하여 선택하세요
      </div>
    </div>
  )
}
