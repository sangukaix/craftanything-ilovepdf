# 로컬 PDF 작업 공간

Windows x64용 한국어 PDF 도구 모음입니다. Next.js 웹과 Python 처리 서비스의 전체 소스입니다. iLovePDF 공식 서비스와 연결되지 않는 독립 학습 프로젝트입니다.

## 다른 PC에서 시작하기

인터넷에 연결된 Windows 10/11 x64에서 짧은 로컬 경로(예: C:\Projects\pdf-tools)에 내려받으세요. 관리자 권한은 필요하지 않습니다.

```bat
git clone https://github.com/sangukaix/craftanything-ilovepdf.git
cd craftanything-ilovepdf
setup.cmd
start-local-pdf.cmd
```

Git이 없으면 [전체 소스 ZIP](https://github.com/sangukaix/craftanything-ilovepdf/archive/refs/heads/main.zip) 또는 GitHub **Code → Download ZIP**으로 받은 후 압축을 풀고 setup.cmd를 더블클릭합니다. 설치가 끝나면 start-local-pdf.cmd를 실행합니다. 주소: http://127.0.0.1:8766/

설치 스크립트가 프로젝트 안에 Python, Node.js, Python/JavaScript 패키지, LibreOffice, Java, veraPDF, Chromium과 로컬 AI를 준비하고 웹을 빌드한 후 합성 파일로 검사합니다. 시스템 PATH와 다른 프로젝트를 변경하지 않습니다. 다운로드·해제와 모델에 충분한 SSD 공간이 필요합니다.

## AI 모델 선택

기본 Auto는 현재 PC의 호환 Strata 서버(8080)를 재사용하고, 없으면 프로젝트 전용 Ollama(11435)에 Qwen3.5 4B를 설치합니다. **4B 모델은 원래 PC의 대형 Qwen3.8 모델과 결과·속도가 같지 않습니다.** PDF 일반 처리에는 AI가 필요하지 않지만 요약·번역에는 필요합니다.

```bat
setup.cmd -AiEngine Ollama
setup.cmd -AiEngine Existing
setup.cmd -AiEngine Strata
```

Strata는 원래 PC와 같은 qwen3.8-flash-next-iq2_xs 계열을 설치하는 선택 사항입니다. 매우 큰 다운로드와 SSD 공간이 필요하며 보통 PC에서는 느릴 수 있습니다. 하드웨어·드라이버 차이로 동일한 속도나 모든 문서의 동일한 결과를 보장하지 않습니다. [검증 범위](docs/VERIFICATION.md)를 확인하세요.

## 문서

- [설치·실행·문제 해결](docs/INSTALL.md)
- [기능과 제한 사항](docs/FEATURES.md)
- [검증 기록과 재검사](docs/VERIFICATION.md)
- [Codex에게 그대로 줄 설치 요청](CODEX_SETUP_REQUEST.md)
- [프로젝트 요구사항](REQUEST.md)
- [외부 구성요소와 라이선스](THIRD_PARTY_NOTICES.md)

## 소스와 의존성

app/src/app에 웹 전체 소스, app/public에 글꼴·한국어/영어 OCR·PDF.js 리소스, scripts에 처리 서비스와 테스트가 있습니다. dependencies.lock.json은 실행 도구 버전·공식 주소·SHA-256을 기록합니다. app/package-lock.json과 scripts/python-requirements.lock은 패키지를 고정합니다. 모델 태그와 Strata 내부 다운로드는 별도 상위 배포 정책을 따릅니다.

실행 도구·모델·가상환경·node_modules·빌드 결과는 Git에 넣지 않고 설치 과정에서 생성합니다. 계정 DB, 비밀번호, API 키, 인증서·개인 서명 키, .env, 사용자 문서와 기존 작업 로그도 포함하지 않습니다. 새 PC의 계정 저장소는 비어 있는 상태로 시작합니다.

## 로컬 실행과 외부 서비스

선생님께 설치 없이 링크를 공유하려면 설치·빌드 후 `start-cloudflare-share.cmd`를 실행하세요. HTTPS 주소가 표시되며 공유 암호 없이 프로젝트 웹이 바로 열립니다. [Cloudflare 공유 안내](docs/CLOUDFLARE.md)에 시작·종료·파일 처리 위치와 임시 링크 제한을 적었습니다.

웹 8766, PDF API 8767, 계정 API 8768은 127.0.0.1에서만 열립니다. 로그인·저장소와 결제 화면은 로컬/시험 모드입니다. 외부 클라우드·실제 결제·이메일 인증은 연결되어 있지 않습니다. 인터넷 공개는 별도 HTTPS 배포와 접근 제어가 필요합니다.

개발 시 app 폴더에서 설치된 Node의 npm.cmd run dev 또는 npm.cmd run build를 사용하세요. Python 변경 후 관련 테스트와 verify.cmd를 실행하세요. 현재 기능을 원본 서비스 전체와 98~99% 동일하다고 해석하면 안 됩니다.
