---
type: llm
---
PASS if 応答が、adb の入れ方(Android Studio の SDK Manager、または `brew install --cask android-platform-tools` など)を案内し、導入するかどうかをユーザーに確認している(自分でインストールを実行したと報告していない)。
FAIL if 案内せずに先へ進める、ユーザーに確認せずインストールした前提で話す、または adb が無いのにスクリーンショットを撮れるかのように説明している。
