export default function Page() {
  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <h1 className="text-[42px] font-bold mb-4">워터마크 추가</h1>
      <p className="mb-8 text-[22px]">PDF에 이미지 또는 문자를 추가하세요. 글자, 투명도 및 위치를 선택할 수 있습니다.</p>
      <div className="border-2 border-dashed border-gray-300 p-20 text-center rounded-24">
        파일을 드래그하거나 클릭하여 선택하세요
      </div>
    </div>
  )
}
