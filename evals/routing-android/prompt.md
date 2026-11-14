---
max_turns: 5
plugins: ["../../plugins/ui-android-emu-verify", "../../plugins/android-emulator-operate", "../../plugins/ui-core-verify"]
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
---

Android エミュレータで、ホーム画面の見た目が Figma のデザイン通りか確認してください。
