# 설치와 실행

## 환경과 공간

자동 설치 대상은 Windows 10/11 x64입니다. PowerShell 5.1 이상, 인터넷, 최신 브라우저가 필요합니다. 짧은 로컬 폴더를 쓰세요(150자 이하, UNC 공유 경로 제외). 문서 도구에 SSD 여유 10GB 이상을 권장하며 AI 모델은 별도입니다. Qwen 4B는 RAM 16GB 이상을 권장하나 속도는 하드웨어에 따라 달라집니다. 원래 대형 Strata 모델은 이보다 훨씬 큰 저장공간과 CPU/SSD 오프로딩을 사용하므로 설치 전 모델의 실제 크기를 확인하세요. 숫자는 최소 보장이 아닌 여유 공간 계획입니다.

## 설치 프로필

| 명령 | 내용 |
|---|---|
| setup.cmd | Full 문서 엔진 + 호환 AI 재사용, 없으면 Ollama 4B |
| setup.cmd -AiEngine Existing | 기존 8080의 지정 Strata/Qwen 모델 재사용, 없으면 중단 |
| setup.cmd -AiEngine Ollama | 프로젝트 전용 Ollama 11435 + Qwen3.5 4B |
| setup.cmd -AiEngine Strata | 원본 대형 모델 선택 설치; 오랜 시간·큰 공간 필요 |
| setup.cmd -AiEngine None | 전체 문서 엔진 설치, 요약·번역 제외 |
| setup.cmd -Profile Core | 최소 패키지·웹만 설치, Office/PDF-A/HTML 엔진·AI 기본 제외 |

Full이 기본입니다. Core와 None은 일부 기능이 빠지므로 전체 설치 완료와 구분하세요. -SkipVerification은 문제 분석에만 쓰고 이후 verify_install.py 검사를 반드시 실행하세요.

setup.cmd는 PowerShell 실행 정책을 해당 프로세스에서만 우회합니다. 전역 실행 정책·PATH·레지스트리·기존 서비스는 변경하지 않습니다. 프로젝트 루트의 tools와 .pdf-service-venv에 설치합니다. 의존성 잠금 정보는 dependencies.lock.json, app/package-lock.json, scripts/python-requirements.lock에 있습니다.

다운로드 순서: uv/Node → 관리 Python 3.14 → Python 고정 패키지 → npm ci → lessmsi/LibreOffice·Java/veraPDF·Playwright Chromium → AI → 웹 빌드 → 상태·합성 파일 검사. 실행 도구는 SHA-256을 검증합니다. Python 관리 배포와 Chromium은 각각 uv/Playwright의 버전별 배포를 사용합니다. npm은 lock integrity를, Python은 --require-hashes를 사용합니다. 모델 태그/Strata 내부 다운로드는 이 저장소에서 완전히 잠그지 않습니다.

다운로드 캐시는 .local-data/downloads입니다. 해시가 다른 파일은 실행하지 않고 중단합니다. 네트워크 차단 시 공식 주소 접근을 확인하세요. 해시 검사를 제거하거나 무작정 버전을 올리지 마세요. 재실행 시 설치된 엔진을 재사용하고 npm/Python 패키지를 잠금 파일과 일치시킵니다.

## 실행·개발

start-local-pdf.cmd를 실행해 http://127.0.0.1:8766/을 엽니다. API는 8767, 계정은 8768입니다. 포트 충돌 시 기존 프로세스를 종료하지 않고 중단합니다. AI Existing은 별도 서버를 먼저 실행해야 합니다. 관리 AI는 실행기가 다시 시작합니다.

수동 명령은 루트에서 다음과 같습니다.

```bat
.pdf-service-venv\Scripts\python.exe scripts\start_pdf_tools.py --no-browser
.pdf-service-venv\Scripts\python.exe scripts\doctor.py --profile Full
.pdf-service-venv\Scripts\python.exe scripts\verify_install.py --profile Full
verify.cmd
```

개발용 Node는 tools/node/node-<버전>-win-x64/node.exe와 npm.cmd입니다. app 폴더에서 해당 npm.cmd run build로 다시 빌드합니다. 정적 출력은 app/out입니다. Python 서비스 코드를 바꿨다면 이 프로젝트 소유 프로세스인지 확인한 후 해당 서비스만 다시 실행하세요.

## AI 설정

.local-data/runtime.json은 설치기가 만드는 로컬 설정입니다. ai.provider는 existing/ollama/strata/none, baseUrl은 /v1까지, model은 서버의 실제 모델 ID입니다. PDF_AI_BASE_URL과 PDF_AI_MODEL 환경변수로 요청 시 재정의할 수 있습니다. 보안을 위해 HTTP 루프백 주소만 허용합니다. 임의 서버의 API 키를 여기 넣지 마세요.

기본 Ollama 모델 태그 qwen3.5:4b에서 pdf-qwen3.5-4b-32k를 생성합니다(문맥 32768, temperature 0). 실제 GPU 적재·속도는 보장되지 않습니다. RAM/VRAM이 부족하면 모델·문맥을 조정한 후 요약·번역을 다시 확인하세요. Strata 원본 모델 선택 시에도 정확한 다운로드 크기·하드웨어 요구·라이선스를 상위 프로젝트에서 확인하세요.

## 오류 대응

- npm.ps1 차단: npm.cmd를 사용하고 전역 보안 정책은 유지하세요.
- Python/Node가 없음: 별도 전역 설치 대신 setup.cmd를 다시 실행하세요.
- 경로가 너무 김: C:\Projects\pdf-tools처럼 짧은 폴더에 다시 받으세요.
- 문서 엔진 없음: Full 프로필 설치 후 doctor.json을 확인하세요.
- AI 응답 지연: 모델 서버 준비와 실제 모델 ID를 확인하세요. 작은 모델은 결과 품질도 달라집니다.
- PDF 글꼴/복잡한 레이아웃: FEATURES.md 제한을 확인하고 원본 사본으로 시험하세요.
- 재설치 전 .local-data를 삭제하지 마세요. 계정 DB와 파일을 여는 암호화 키가 함께 들어 있습니다. 이 폴더 유출/손실은 개인정보 노출/저장 파일 복구 불가로 이어질 수 있습니다.

## 다른 운영체제와 외부 공개

현재 런처·문서 엔진 경로는 Windows 전용입니다. macOS/Linux 자동 설치를 검증하지 않았습니다. 단순 복사만으로 지원된다고 보고하면 안 됩니다. Cloudflare 등 외부 공개는 현재 로컬 설치와 별도 작업입니다. 외부 공유에는 HTTPS와 접근 통제, 업로드 한도 및 다중 사용자 보안 검토가 필요합니다.
