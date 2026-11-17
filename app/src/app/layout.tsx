import './site-global.css';
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>iLovePDF | PDF를 즐겨 쓰시는 분들을 위한 온라인 PDF 툴</title>
        <meta name="description" content="iLovePDF는 PDF 파일 작업을 위한 온라인 서비스로 완전히 무료이며 사용하기 쉽습니다. PDF 병합, PDF 분리, PDF 압축, 오피스 파일에서 PDF로, PDF에서 JPG로 변환 등!" />
      </head>
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
}
