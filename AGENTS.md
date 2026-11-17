# Repository maintenance

This is an existing Windows x64 local PDF app. Web source: app/src/app; static assets: app/public; Python APIs and tests: scripts.

- Read README.md and docs/INSTALL.md before installing. Use setup.cmd; dependencies are locked. Keep tools project-local and global PATH/execution policy unchanged.
- Read app/AGENTS.md and the relevant installed Next.js guide before frontend edits. Use npm.cmd on Windows.
- Use start-local-pdf.cmd; ports 8766/8767/8768 bind loopback only. Check service identity before stopping a project-owned process. Never stop unrelated programs.
- Keep current handlers and real downloads when editing appearance. Test drag/drop and affected tools with generated documents.
- Keep .local-data, .env, credentials, account DB, vault keys, certificates and user documents out of Git/logs/archives. Do not inspect other projects or school files.
- Full tests: verify.cmd. Install checks: doctor.py and verify_install.py. AI tests require an actual local model. PDF_SKIP_AI_TESTS=1 explicitly skips only the 2 real AI tests and must be reported.
- Local account/vault/demo billing is implemented. Real cloud/payment/email/SSO services remain unconnected; do not label them production-ready.
- Read docs/FEATURES.md limitations. Screen similarity is not whole-service functional parity. Report actual tested scope, failures and omissions.
- Deployment artifacts use scripts/export_source.py's explicit allowlist. Do not publish old Craft logs, model files, caches or private Git history.
