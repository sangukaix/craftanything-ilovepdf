export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">PDF 회전</h1>
      <p className="mb-8 text-[22px]">원하는대로 PDF를 회전하세요. 한 번에 여러 PDF 파일을 회전하세요!</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        파일을 드래그하거나 클릭하여 선택하세요
      </div>
    </div>
  )
}
