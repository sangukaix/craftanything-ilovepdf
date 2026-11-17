# 새 컴퓨터의 Codex에 붙여 넣을 요청

이 저장소의 PDF 앱을 이 Windows x64 컴퓨터에서 설치하고 실행해 줘.

1. AGENTS.md, README.md, docs/INSTALL.md, docs/FEATURES.md, docs/VERIFICATION.md를 읽어 줘.
2. CPU/RAM/GPU/SSD 여유 공간과 포트 8766/8767/8768/8080/11435 충돌 여부를 확인해 줘. 다른 프로젝트나 개인 파일은 읽지 마.
3. 루트에서 setup.cmd를 실행해 모든 문서 엔진과 패키지를 설치하고 웹을 빌드해 줘. 도구는 프로젝트 안에 설치하고 전역 PATH·실행 정책·다른 프로그램은 바꾸지 마.
4. AI는 Auto의 선택을 먼저 설명해 줘. 원본과 같은 대형 모델은 -AiEngine Strata, 작은 모델은 -AiEngine Ollama야. 작은 모델을 같은 모델이라고 보고하지 마.
5. .local-data/doctor.json과 .local-data/verification/result.json을 확인하고 verify.cmd를 실행해 줘. AI 제외 시 PDF_SKIP_AI_TESTS=1을 설정하고 실제 AI 테스트 2개가 생략되었다고 보고해 줘.
6. start-local-pdf.cmd로 서비스를 실행하고 웹을 열어 줘. 생성한 PDF로 드래그·병합·분할·다운로드를 직접 확인해 줘. 요약·번역은 선택한 실제 모델로 확인해 줘.
7. 실패한 항목은 원인을 고쳐 다시 검사하고 경로, URL, AI 모델, 통과/실패/미검증 항목을 간단히 알려 줘. 테스트하지 않은 기능을 성공했다고 하지 마.

외부 클라우드·실제 결제·이메일 인증·신뢰 기관 인증서는 별도 계정과 키가 필요해. 비밀 키는 채팅에 요청하지 말고 사용자가 로컬 설정에 입력하도록 안내해 줘. 서버를 외부 공개하거나 기존 프로세스를 강제로 종료하지 마.
