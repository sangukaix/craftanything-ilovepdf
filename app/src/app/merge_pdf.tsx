export default function Page() {
  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4 text-[#33333b]">PDF 도구</h1>
      <p className="mb-8 text-[16px] text-[#707078]">PDF 파일을 선택하거나 드래그하여 업로드하세요.</p>
      <div className="border-2 border-dashed border-[#cccccc] p-20 text-center rounded-[16px] bg-[#f8f9fa]">
        <p className="mb-4 text-[16px] text-[#33333b]">파일을 여기에 드래그하거나 클릭하여 선택하세요</p>
        <button className="bg-[#e5322d] text-white px-8 py-3 rounded-[8px] font-bold text-[18px] hover:bg-[#c42824] transition-colors">
          파일 선택
        </button>
      </div>
      <div className="mt-12">
        <button id="convert-btn" className="bg-[#cccccc] text-white px-8 py-3 rounded-[8px] font-bold text-[18px] hover:bg-[#b3b3b3] transition-colors">
          변환 시작
        </button>
        <p className="mt-2 text-[14px] text-[#707078]">버튼을 누르면 변환이 시작됩니다. (미구현 기능)</p>
      </div>
    </div>
  )
}