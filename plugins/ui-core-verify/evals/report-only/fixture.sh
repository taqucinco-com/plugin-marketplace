#!/usr/bin/env bash
set -euo pipefail
git init -q
mkdir -p lib work/screenshots
cat > lib/home_screen.dart <<'DART'
import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ホーム')),
      // MAP_NOT_IMPLEMENTED: 地図ウィジェットは未実装
      body: const Center(child: Text('地図は準備中です')),
    );
  }
}
DART
touch work/screenshots/home-app.png work/screenshots/home-app-norm.png
cat > work/screenshots/checker-output.json <<'JSON'
{
  "screen": "home",
  "figma_node_id": null,
  "criteria": [
    { "aspect": "layout_structure", "verdict": "match", "diff": null },
    { "aspect": "element_presence", "verdict": "mismatch", "diff": "地図が表示されていない(『地図は準備中です』という文言だけが表示されている)" },
    { "aspect": "arrangement_order", "verdict": "not_applicable", "diff": null },
    { "aspect": "text_labels", "verdict": "minor_diff", "diff": "見出しが『ホーム』で、期待の文言と異なる可能性がある" },
    { "aspect": "state_representation", "verdict": "not_applicable", "diff": null }
  ],
  "overall_verdict": "partial_match",
  "fatal": false,
  "fatal_reason": null
}
JSON
