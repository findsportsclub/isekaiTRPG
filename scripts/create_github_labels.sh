#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ./create_github_labels.sh OWNER/REPO"
  exit 1
fi

REPO="$1"

create_label() {
  local name="$1"
  local color="$2"
  local desc="$3"

  if gh label list --repo "$REPO" --limit 500 | awk '{print $1}' | grep -Fxq "$name"; then
    echo "label exists: $name"
  else
    gh label create "$name" --repo "$REPO" --color "$color" --description "$desc"
    echo "created: $name"
  fi
}

# Priority
create_label "P0" "B60205" "最優先"
create_label "P1" "D93F0B" "MVP必須"
create_label "P2" "FBCA04" "MVP後"

# Area
create_label "frontend" "1D76DB" "フロントエンド"
create_label "backend" "5319E7" "バックエンド"
create_label "db" "0E8A16" "データベース"
create_label "api" "006B75" "API"
create_label "ui" "C2E0C6" "UI / UX"
create_label "game-logic" "7057FF" "ゲームロジック"
create_label "infra" "8B5CF6" "インフラ"
create_label "docs" "0075CA" "ドキュメント"

# Status
create_label "todo" "D4C5F9" "未着手"
create_label "in-progress" "0052CC" "進行中"
create_label "review" "5319E7" "レビュー中"
create_label "blocked" "B60205" "要因待ち / ブロック"
create_label "done" "0E8A16" "完了"

echo "All labels processed for $REPO"
