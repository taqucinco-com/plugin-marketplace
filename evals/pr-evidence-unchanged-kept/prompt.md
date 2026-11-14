---
max_turns: 15
plugins: ["../../plugins/pr-ui-evidence", "../../plugins/android-emulator-operate", "../../plugins/ios-simulator-operate"]
timeout_seconds: 300
allowed_tools: [Read, Write, Glob, Skill]
---

PR 12 の UI 証跡を作っています。撮影は済んでいて、画面は home の1つだけです(到達手順はアプリ起動直後)。work/pr-evidence/12/ に home_before.png と home_after.png があり、手順 3.5 の変更判定の結果は work/pr-evidence/12/decision-home.json です(`summary.next` がその画面の判定)。撮影条件は Pixel 8 / Android 15 / ライト / 日本語です。pr-ui-evidence スキルの手順 4 に従って、work/pr-evidence/12/evidence.md を作ってください。画像の URL はまだ決まっていないので、画像のホスティングと PR への反映(手順 5)は行わないでください。
