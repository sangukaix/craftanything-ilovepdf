export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">PDF 엑셀 변환</h1>
      <p className="mb-8 text-[22px]">몇 초만에 PDF 데이터를 Excel 스프레드시트로 가져올 수 있습니다.</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        파일을 드래그하거나 클릭하여 선택하세요
      </div>
    </div>
  )
}
