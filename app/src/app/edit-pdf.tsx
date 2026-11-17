export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">PDF 편집</h1>
      <p className="mb-8 text-[22px]">PDF 문서에 텍스트, 이미지, 도형 또는 주석을 추가하세요. 추가된 컨텐츠의 크기, 글꼴 및 색상을 편집할 수 있습니다.</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        파일을 드래그하거나 클릭하여 선택하세요
      </div>
    </div>
  )
}
