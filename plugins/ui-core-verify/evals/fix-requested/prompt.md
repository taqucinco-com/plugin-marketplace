---
max_turns: 20
timeout_seconds: 400
allowed_tools: [Read, Write, Edit, Glob, Skill]
---

Android エミュレータで「ホーム画面に地図が表示されるように lib/home_screen.dart を直して」という依頼を受け、ui-verify-loop の手順を進めています。スクリーンショットの準備と ui-checker の1回目の判定は済んでいて、ui-checker の最終応答は work/screenshots/checker-output.json にあります(画面名は home、標準サイズは 480x1040、Figma は使っていません)。エミュレータやビルドの環境はこの場では使えないので、再ビルド以降は行わず、コードの修正までを行ってください。
