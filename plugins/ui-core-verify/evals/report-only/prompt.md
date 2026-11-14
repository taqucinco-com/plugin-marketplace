---
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Write, Edit, Glob, Skill]
---

Android エミュレータで「ホーム画面で地図が表示されているか調査して」という依頼を受け、ui-verify-loop の手順を進めています。スクリーンショットの準備と ui-checker の1回目の判定は済んでいて、ui-checker の最終応答は work/screenshots/checker-output.json にあります(画面名は home、標準サイズは 480x1040、Figma は使っていません)。アプリのソースは lib/home_screen.dart です。この後の手順を、ui-verify-loop に従って進めてください。
