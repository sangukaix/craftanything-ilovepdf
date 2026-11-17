export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">PDF 분할</h1>
      <p className="mb-8 text-[22px]">페이지 범위를 선택하고, 한 페이지를 분리하거나 문서의 각 페이지를 독립된 PDF 파일로 변환하세요.</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        파일을 드래그하거나 클릭하여 선택하세요
      </div>
    </div>
  )
}