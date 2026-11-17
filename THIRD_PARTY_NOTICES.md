# 외부 구성요소·저작권

이 프로젝트는 iLovePDF 공식 제품이 아닙니다. 이름·로고·참고 디자인·이미지는 각 권리자의 자산이며 학습용 재현 과정의 리소스입니다. 이 저장소가 해당 자산의 상업적 재배포 권리를 부여하지 않습니다. 외부 공개/상업 사용 전 고유 브랜드와 적법한 자산으로 교체하고 권리를 확인하세요.

포함 자산의 라이선스 파일은 원래 경로에 보존합니다. 모든 자산에 일괄 MIT 라이선스를 부여하지 않습니다.

- Noto Sans KR 글꼴: app/public/font의 OFL/라이선스, SIL Open Font License.
- PDF.js: app/public/pdfjs의 LICENSE 및 구성요소 고지, Apache-2.0 계열.
- Tesseract.js, 코어, 언어 데이터: app/public/ocr 내 LICENSE/고지와 upstream 라이선스.
- JavaScript 패키지: app/package-lock.json에 버전 고정. 설치 후 app/node_modules/<패키지>/LICENSE 확인.
- Python 패키지: scripts/python-requirements.lock에 고정. 각 배포 메타데이터 라이선스를 따릅니다. 특히 PyMuPDF/MuPDF 및 관련 패키지는 AGPL/상용 라이선스 조건을 확인하세요.
- LibreOffice: MPL-2.0 및 포함 구성요소 고지. 설치 후 tools/libreoffice/runtime의 라이선스 확인.
- veraPDF: GPLv3+/MPLv2+ 관련 upstream 배포 고지.
- Eclipse Temurin Java: GPLv2 with Classpath Exception 및 배포 고지.
- uv, Node.js, Playwright/Chromium, lessmsi, Ollama, Strata: 각 공식 배포의 라이선스와 포함 제3자 고지.
- Qwen 모델: 선택한 모델 배포의 모델 카드·라이선스를 별도로 따릅니다.

실행 도구·모델 바이너리는 Git에 포함하지 않습니다. 공식 다운로드 주소·버전·실행 도구 SHA-256은 dependencies.lock.json에 있습니다. 라이선스 확인은 설치 성공과 별개입니다.
