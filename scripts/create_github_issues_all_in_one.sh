#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ./create_github_issues_all_in_one.sh OWNER/REPO"
  exit 1
fi
REPO="$1"

create_issue() {
  local title="$1"
  local labels_csv="$2"
  local body="$3"
  local tmp
  tmp="$(mktemp)"
  printf "%s" "$body" > "$tmp"
  local -a label_args=()
  IFS="," read -ra parts <<< "$labels_csv"
  for p in "${parts[@]}"; do
    clean="$(echo "$p" | xargs)"
    [ -n "$clean" ] && label_args+=(--label "$clean")
  done
  gh issue create --repo "$REPO" --title "$title" --body-file "$tmp" "${label_args[@]}"
  rm -f "$tmp"
}

title_ISSUE_0001='ISSUE-0001: monorepo初期化'
labels_ISSUE_0001='`P0`, `infra`, `docs`, `todo`'
body_ISSUE_0001=$(cat <<'EOF_ISSUE_0001'
# ISSUE-0001: monorepo初期化

Labels: `P0`, `infra`, `docs`, `todo`

**Labels:** `P0`, `infra`, `docs`, `todo`

**目的**  
frontend / backend / docs の基本構成を作る

**作業**
- `frontend/` 作成
- `backend/` 作成
- `docs/` 作成
- ルートREADME作成

**完了条件**
- ディレクトリ構成が揃っている

---

EOF_ISSUE_0001
)
create_issue "$title_ISSUE_0001" "$labels_ISSUE_0001" "$body_ISSUE_0001"

title_ISSUE_0002='ISSUE-0002: Next.js初期化'
labels_ISSUE_0002='`P0`, `frontend`, `ui`, `todo`'
body_ISSUE_0002=$(cat <<'EOF_ISSUE_0002'
# ISSUE-0002: Next.js初期化

Labels: `P0`, `frontend`, `ui`, `todo`

**Labels:** `P0`, `frontend`, `ui`, `todo`

**目的**  
フロントエンド起動確認

**作業**
- Next.js + TypeScript 初期化
- Tailwind導入
- App Router構成作成

**完了条件**
- `frontend` で開発サーバー起動成功

---

EOF_ISSUE_0002
)
create_issue "$title_ISSUE_0002" "$labels_ISSUE_0002" "$body_ISSUE_0002"

title_ISSUE_0003='ISSUE-0003: FastAPI初期化'
labels_ISSUE_0003='`P0`, `backend`, `api`, `todo`'
body_ISSUE_0003=$(cat <<'EOF_ISSUE_0003'
# ISSUE-0003: FastAPI初期化

Labels: `P0`, `backend`, `api`, `todo`

**Labels:** `P0`, `backend`, `api`, `todo`

**目的**  
バックエンド起動確認

**作業**
- FastAPIプロジェクト作成
- `/health` エンドポイント作成
- Uvicorn起動確認

**完了条件**
- `/health` が 200 を返す

---

EOF_ISSUE_0003
)
create_issue "$title_ISSUE_0003" "$labels_ISSUE_0003" "$body_ISSUE_0003"

title_ISSUE_0004='ISSUE-0004: SQLite接続基盤'
labels_ISSUE_0004='`P0`, `backend`, `db`, `todo`'
body_ISSUE_0004=$(cat <<'EOF_ISSUE_0004'
# ISSUE-0004: SQLite接続基盤

Labels: `P0`, `backend`, `db`, `todo`

**Labels:** `P0`, `backend`, `db`, `todo`

**目的**  
DB接続の土台を作る

**作業**
- SQLAlchemy設定
- DB接続設定
- セッション管理
- Alembic初期化

**完了条件**
- DB接続できる
- migration実行できる

---

EOF_ISSUE_0004
)
create_issue "$title_ISSUE_0004" "$labels_ISSUE_0004" "$body_ISSUE_0004"

title_ISSUE_0005='ISSUE-0005: 既存スキーマSQLの管理方法を決定'
labels_ISSUE_0005='`P0`, `backend`, `db`, `docs`, `todo`'
body_ISSUE_0005=$(cat <<'EOF_ISSUE_0005'
# ISSUE-0005: 既存スキーマSQLの管理方法を決定

Labels: `P0`, `backend`, `db`, `docs`, `todo`

**Labels:** `P0`, `backend`, `db`, `docs`, `todo`

**目的**  
`story_system_schema.sql` を開発に組み込む

**作業**
- SQLAlchemyモデル化するか決める
- 既存SQLをmigrationへ反映
- docsに方針記載

**完了条件**
- スキーマ管理方法が固定される

---

## Epic 1: 認証と世界一覧

EOF_ISSUE_0005
)
create_issue "$title_ISSUE_0005" "$labels_ISSUE_0005" "$body_ISSUE_0005"

title_ISSUE_0101='ISSUE-0101: 仮ユーザーモデル作成'
labels_ISSUE_0101='`P1`, `backend`, `db`, `todo`'
body_ISSUE_0101=$(cat <<'EOF_ISSUE_0101'
# ISSUE-0101: 仮ユーザーモデル作成

Labels: `P1`, `backend`, `db`, `todo`

**Labels:** `P1`, `backend`, `db`, `todo`

**目的**  
ログインに必要な最低限のユーザー情報を持つ

**作業**
- usersテーブル
- user model
- password hash対応

**完了条件**
- ユーザーを保存できる

---

EOF_ISSUE_0101
)
create_issue "$title_ISSUE_0101" "$labels_ISSUE_0101" "$body_ISSUE_0101"

title_ISSUE_0102='ISSUE-0102: ログインAPI'
labels_ISSUE_0102='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0102=$(cat <<'EOF_ISSUE_0102'
# ISSUE-0102: ログインAPI

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
認証を通す

**作業**
- `POST /api/auth/login`
- token or session 発行

**完了条件**
- ログイン成功時に認証情報を返す

---

EOF_ISSUE_0102
)
create_issue "$title_ISSUE_0102" "$labels_ISSUE_0102" "$body_ISSUE_0102"

title_ISSUE_0103='ISSUE-0103: ログイン画面作成'
labels_ISSUE_0103='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0103=$(cat <<'EOF_ISSUE_0103'
# ISSUE-0103: ログイン画面作成

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
ブラウザからログインできるようにする

**作業**
- `/login`
- フォーム
- エラー表示
- ログイン後遷移

**完了条件**
- ログイン成功で `/worlds` に遷移

---

EOF_ISSUE_0103
)
create_issue "$title_ISSUE_0103" "$labels_ISSUE_0103" "$body_ISSUE_0103"

title_ISSUE_0104='ISSUE-0104: 世界一覧API'
labels_ISSUE_0104='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0104=$(cat <<'EOF_ISSUE_0104'
# ISSUE-0104: 世界一覧API

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
自分の世界一覧を返す

**作業**
- `GET /api/worlds`
- world一覧取得
- owner紐付け

**完了条件**
- 世界カード用データが返る

---

EOF_ISSUE_0104
)
create_issue "$title_ISSUE_0104" "$labels_ISSUE_0104" "$body_ISSUE_0104"

title_ISSUE_0105='ISSUE-0105: 世界一覧画面'
labels_ISSUE_0105='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0105=$(cat <<'EOF_ISSUE_0105'
# ISSUE-0105: 世界一覧画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
作成済み世界を選べるようにする

**作業**
- `/worlds`
- 世界カード表示
- 新規作成ボタン
- 未読/召霊通知枠

**完了条件**
- 世界一覧が表示される

---

EOF_ISSUE_0105
)
create_issue "$title_ISSUE_0105" "$labels_ISSUE_0105" "$body_ISSUE_0105"

title_ISSUE_0106='ISSUE-0106: 世界作成API'
labels_ISSUE_0106='`P1`, `backend`, `api`, `game-logic`, `todo`'
body_ISSUE_0106=$(cat <<'EOF_ISSUE_0106'
# ISSUE-0106: 世界作成API

Labels: `P1`, `backend`, `api`, `game-logic`, `todo`

**Labels:** `P1`, `backend`, `api`, `game-logic`, `todo`

**目的**  
新規世界を作る

**作業**
- `POST /api/worlds`
- world レコード作成
- 初期主人公作成
- 初期world_state作成

**完了条件**
- 世界作成後に `worldId` を返す

---

EOF_ISSUE_0106
)
create_issue "$title_ISSUE_0106" "$labels_ISSUE_0106" "$body_ISSUE_0106"

title_ISSUE_0107='ISSUE-0107: 世界作成画面'
labels_ISSUE_0107='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0107=$(cat <<'EOF_ISSUE_0107'
# ISSUE-0107: 世界作成画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
UIから世界を新規作成する

**作業**
- `/worlds/new`
- 世界名
- 主人公名
- 種族
- 初期チート
- seed設定

**完了条件**
- 作成後に世界ダッシュボードへ遷移

---

## Epic 2: 世界ダッシュボード

EOF_ISSUE_0107
)
create_issue "$title_ISSUE_0107" "$labels_ISSUE_0107" "$body_ISSUE_0107"

title_ISSUE_0201='ISSUE-0201: world_state初期化処理'
labels_ISSUE_0201='`P1`, `backend`, `game-logic`, `todo`'
body_ISSUE_0201=$(cat <<'EOF_ISSUE_0201'
# ISSUE-0201: world_state初期化処理

Labels: `P1`, `backend`, `game-logic`, `todo`

**Labels:** `P1`, `backend`, `game-logic`, `todo`

**目的**  
新規世界に最低限の状態を持たせる

**作業**
- 初期Era
- crisis_scores初期値
- currentLocation
- main_event空設定

**完了条件**
- 新規世界でダッシュボードが崩れない

---

EOF_ISSUE_0201
)
create_issue "$title_ISSUE_0201" "$labels_ISSUE_0201" "$body_ISSUE_0201"

title_ISSUE_0202='ISSUE-0202: 世界ダッシュボードAPI'
labels_ISSUE_0202='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0202=$(cat <<'EOF_ISSUE_0202'
# ISSUE-0202: 世界ダッシュボードAPI

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
ダッシュボード表示用データを返す

**作業**
- `GET /api/worlds/{worldId}`
- Era
- crisis_scores
- featured NPC
- rumors
- main event

**完了条件**
- ダッシュボードに必要なJSONが返る

---

EOF_ISSUE_0202
)
create_issue "$title_ISSUE_0202" "$labels_ISSUE_0202" "$body_ISSUE_0202"

title_ISSUE_0203='ISSUE-0203: 世界ダッシュボード画面'
labels_ISSUE_0203='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0203=$(cat <<'EOF_ISSUE_0203'
# ISSUE-0203: 世界ダッシュボード画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
中核画面を作る

**作業**
- `/worlds/[worldId]`
- 世界概要
- Era表示
- 危機スコア表示
- MAINイベント枠
- 注目NPC
- 最近の噂

**完了条件**
- 世界の状態が一覧できる

---

## Epic 3: 行動システム

EOF_ISSUE_0203
)
create_issue "$title_ISSUE_0203" "$labels_ISSUE_0203" "$body_ISSUE_0203"

title_ISSUE_0301='ISSUE-0301: 行動候補API'
labels_ISSUE_0301='`P1`, `backend`, `api`, `game-logic`, `todo`'
body_ISSUE_0301=$(cat <<'EOF_ISSUE_0301'
# ISSUE-0301: 行動候補API

Labels: `P1`, `backend`, `api`, `game-logic`, `todo`

**Labels:** `P1`, `backend`, `api`, `game-logic`, `todo`

**目的**  
現在地で取れる行動を返す

**作業**
- `GET /api/worlds/{worldId}/actions`
- 行動候補生成
- 周辺NPC
- 周辺イベント

**完了条件**
- 行動リストが返る

---

EOF_ISSUE_0301
)
create_issue "$title_ISSUE_0301" "$labels_ISSUE_0301" "$body_ISSUE_0301"

title_ISSUE_0302='ISSUE-0302: 行動実行API'
labels_ISSUE_0302='`P1`, `backend`, `api`, `game-logic`, `todo`'
body_ISSUE_0302=$(cat <<'EOF_ISSUE_0302'
# ISSUE-0302: 行動実行API

Labels: `P1`, `backend`, `api`, `game-logic`, `todo`

**Labels:** `P1`, `backend`, `api`, `game-logic`, `todo`

**目的**  
1回の行動を実行し、結果を返す

**作業**
- `POST /api/worlds/{worldId}/actions/execute`
- talk / inspect / move / rest の最低限
- ログ生成
- 必要ならイベント生成

**完了条件**
- 行動結果が返り、ログが残る

---

EOF_ISSUE_0302
)
create_issue "$title_ISSUE_0302" "$labels_ISSUE_0302" "$body_ISSUE_0302"

title_ISSUE_0303='ISSUE-0303: 行動画面'
labels_ISSUE_0303='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0303=$(cat <<'EOF_ISSUE_0303'
# ISSUE-0303: 行動画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
通常時の行動選択UI

**作業**
- `/worlds/[worldId]/action`
- 行動ボタン
- 自由入力欄
- 周辺NPC表示

**完了条件**
- 行動実行できる

---

EOF_ISSUE_0303
)
create_issue "$title_ISSUE_0303" "$labels_ISSUE_0303" "$body_ISSUE_0303"

title_ISSUE_0304='ISSUE-0304: 行動結果画面 or インライン結果表示'
labels_ISSUE_0304='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0304=$(cat <<'EOF_ISSUE_0304'
# ISSUE-0304: 行動結果画面 or インライン結果表示

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
何が起きたかを見せる

**作業**
- 要約
- 新規イベント
- 関係値変化
- ログ詳細導線

**完了条件**
- 行動結果が読める

---

## Epic 4: イベント / クエスト

EOF_ISSUE_0304
)
create_issue "$title_ISSUE_0304" "$labels_ISSUE_0304" "$body_ISSUE_0304"

title_ISSUE_0401='ISSUE-0401: world_event読み出し基盤'
labels_ISSUE_0401='`P1`, `backend`, `db`, `game-logic`, `todo`'
body_ISSUE_0401=$(cat <<'EOF_ISSUE_0401'
# ISSUE-0401: world_event読み出し基盤

Labels: `P1`, `backend`, `db`, `game-logic`, `todo`

**Labels:** `P1`, `backend`, `db`, `game-logic`, `todo`

**目的**  
イベント一覧と詳細を取得できるようにする

**作業**
- repo/service作成
- tier/state/eraTag で検索

**完了条件**
- イベント一覧取得可能

---

EOF_ISSUE_0401
)
create_issue "$title_ISSUE_0401" "$labels_ISSUE_0401" "$body_ISSUE_0401"

title_ISSUE_0402='ISSUE-0402: イベント一覧API'
labels_ISSUE_0402='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0402=$(cat <<'EOF_ISSUE_0402'
# ISSUE-0402: イベント一覧API

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
SUB / LINE / MAIN を見せる

**作業**
- `GET /api/worlds/{worldId}/events`
- query filter対応

**完了条件**
- 絞り込み付き一覧取得成功

---

EOF_ISSUE_0402
)
create_issue "$title_ISSUE_0402" "$labels_ISSUE_0402" "$body_ISSUE_0402"

title_ISSUE_0403='ISSUE-0403: イベント詳細API'
labels_ISSUE_0403='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0403=$(cat <<'EOF_ISSUE_0403'
# ISSUE-0403: イベント詳細API

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
イベント本文と関連情報を返す

**作業**
- `GET /api/worlds/{worldId}/events/{eventId}`
- factions / importantNpcs / rewards 返却

**完了条件**
- 詳細画面用データが返る

---

EOF_ISSUE_0403
)
create_issue "$title_ISSUE_0403" "$labels_ISSUE_0403" "$body_ISSUE_0403"

title_ISSUE_0404='ISSUE-0404: イベント一覧画面'
labels_ISSUE_0404='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0404=$(cat <<'EOF_ISSUE_0404'
# ISSUE-0404: イベント一覧画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
クエスト一覧を表示する

**作業**
- `/worlds/[worldId]/events`
- tier別表示
- 状態表示
- canSummon表示

**完了条件**
- 一覧から詳細へ遷移できる

---

EOF_ISSUE_0404
)
create_issue "$title_ISSUE_0404" "$labels_ISSUE_0404" "$body_ISSUE_0404"

title_ISSUE_0405='ISSUE-0405: イベント詳細画面'
labels_ISSUE_0405='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0405=$(cat <<'EOF_ISSUE_0405'
# ISSUE-0405: イベント詳細画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
受注・進行前の詳細確認

**作業**
- `/worlds/[worldId]/events/[eventId]`
- 導入文
- 関連派閥
- 重要NPC
- 進めるボタン

**完了条件**
- イベントを読む・進める導線がある

---

## Epic 5: ログ / リプレイ

EOF_ISSUE_0405
)
create_issue "$title_ISSUE_0405" "$labels_ISSUE_0405" "$body_ISSUE_0405"

title_ISSUE_0501='ISSUE-0501: ログ一覧API'
labels_ISSUE_0501='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0501=$(cat <<'EOF_ISSUE_0501'
# ISSUE-0501: ログ一覧API

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
ログを時系列に返す

**作業**
- `GET /api/worlds/{worldId}/logs`
- type filter対応

**完了条件**
- ログ一覧取得成功

---

EOF_ISSUE_0501
)
create_issue "$title_ISSUE_0501" "$labels_ISSUE_0501" "$body_ISSUE_0501"

title_ISSUE_0502='ISSUE-0502: ログ詳細API'
labels_ISSUE_0502='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0502=$(cat <<'EOF_ISSUE_0502'
# ISSUE-0502: ログ詳細API

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
シーンごとの本文を返す

**作業**
- `GET /api/worlds/{worldId}/logs/{logId}`
- body
- relationChanges
- linkedEvents

**完了条件**
- 詳細本文を返せる

---

EOF_ISSUE_0502
)
create_issue "$title_ISSUE_0502" "$labels_ISSUE_0502" "$body_ISSUE_0502"

title_ISSUE_0503='ISSUE-0503: ログ一覧画面'
labels_ISSUE_0503='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0503=$(cat <<'EOF_ISSUE_0503'
# ISSUE-0503: ログ一覧画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
物語の履歴を追えるようにする

**作業**
- `/worlds/[worldId]/logs`
- 種別タブ
- 日付順表示

**完了条件**
- ログ一覧が見られる

---

EOF_ISSUE_0503
)
create_issue "$title_ISSUE_0503" "$labels_ISSUE_0503" "$body_ISSUE_0503"

title_ISSUE_0504='ISSUE-0504: ログ詳細画面'
labels_ISSUE_0504='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0504=$(cat <<'EOF_ISSUE_0504'
# ISSUE-0504: ログ詳細画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
読み物として成立させる

**作業**
- `/worlds/[worldId]/logs/[logId]`
- シーン見出し
- 本文
- 関係変化欄

**完了条件**
- ログが読める

---

## Epic 6: 主人公画面

EOF_ISSUE_0504
)
create_issue "$title_ISSUE_0504" "$labels_ISSUE_0504" "$body_ISSUE_0504"

title_ISSUE_0601='ISSUE-0601: 主人公API'
labels_ISSUE_0601='`P1`, `backend`, `api`, `todo`'
body_ISSUE_0601=$(cat <<'EOF_ISSUE_0601'
# ISSUE-0601: 主人公API

Labels: `P1`, `backend`, `api`, `todo`

**Labels:** `P1`, `backend`, `api`, `todo`

**目的**  
主人公の現在状態を返す

**作業**
- `GET /api/worlds/{worldId}/character`
- stats
- cheat
- equipment
- titles

**完了条件**
- キャラ情報が返る

---

EOF_ISSUE_0601
)
create_issue "$title_ISSUE_0601" "$labels_ISSUE_0601" "$body_ISSUE_0601"

title_ISSUE_0602='ISSUE-0602: 主人公画面'
labels_ISSUE_0602='`P1`, `frontend`, `ui`, `todo`'
body_ISSUE_0602=$(cat <<'EOF_ISSUE_0602'
# ISSUE-0602: 主人公画面

Labels: `P1`, `frontend`, `ui`, `todo`

**Labels:** `P1`, `frontend`, `ui`, `todo`

**目的**  
プレイヤー自身の情報を見る

**作業**
- `/worlds/[worldId]/character`
- ステータス表示
- チート表示
- 装備欄
- 称号欄

**完了条件**
- 自分の成長要素が確認できる

---

## MVP後の次点チケット

EOF_ISSUE_0602
)
create_issue "$title_ISSUE_0602" "$labels_ISSUE_0602" "$body_ISSUE_0602"

title_ISSUE_0701='ISSUE-0701: NPC図鑑一覧'
labels_ISSUE_0701='`P2`, `frontend`, `backend`, `ui`, `api`, `todo`'
body_ISSUE_0701=$(cat <<'EOF_ISSUE_0701'
# ISSUE-0701: NPC図鑑一覧

Labels: `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

**Labels:** `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

EOF_ISSUE_0701
)
create_issue "$title_ISSUE_0701" "$labels_ISSUE_0701" "$body_ISSUE_0701"

title_ISSUE_0702='ISSUE-0702: NPC詳細'
labels_ISSUE_0702='`P2`, `frontend`, `backend`, `ui`, `api`, `todo`'
body_ISSUE_0702=$(cat <<'EOF_ISSUE_0702'
# ISSUE-0702: NPC詳細

Labels: `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

**Labels:** `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

EOF_ISSUE_0702
)
create_issue "$title_ISSUE_0702" "$labels_ISSUE_0702" "$body_ISSUE_0702"

title_ISSUE_0703='ISSUE-0703: NPC中心相関図API'
labels_ISSUE_0703='`P2`, `backend`, `api`, `game-logic`, `todo`'
body_ISSUE_0703=$(cat <<'EOF_ISSUE_0703'
# ISSUE-0703: NPC中心相関図API

Labels: `P2`, `backend`, `api`, `game-logic`, `todo`

**Labels:** `P2`, `backend`, `api`, `game-logic`, `todo`

EOF_ISSUE_0703
)
create_issue "$title_ISSUE_0703" "$labels_ISSUE_0703" "$body_ISSUE_0703"

title_ISSUE_0704='ISSUE-0704: 相関図画面'
labels_ISSUE_0704='`P2`, `frontend`, `ui`, `todo`'
body_ISSUE_0704=$(cat <<'EOF_ISSUE_0704'
# ISSUE-0704: 相関図画面

Labels: `P2`, `frontend`, `ui`, `todo`

**Labels:** `P2`, `frontend`, `ui`, `todo`

EOF_ISSUE_0704
)
create_issue "$title_ISSUE_0704" "$labels_ISSUE_0704" "$body_ISSUE_0704"

title_ISSUE_0801='ISSUE-0801: 英雄遺産一覧'
labels_ISSUE_0801='`P2`, `frontend`, `backend`, `ui`, `api`, `todo`'
body_ISSUE_0801=$(cat <<'EOF_ISSUE_0801'
# ISSUE-0801: 英雄遺産一覧

Labels: `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

**Labels:** `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

EOF_ISSUE_0801
)
create_issue "$title_ISSUE_0801" "$labels_ISSUE_0801" "$body_ISSUE_0801"

title_ISSUE_0802='ISSUE-0802: 前主人公詳細'
labels_ISSUE_0802='`P2`, `frontend`, `backend`, `ui`, `api`, `todo`'
body_ISSUE_0802=$(cat <<'EOF_ISSUE_0802'
# ISSUE-0802: 前主人公詳細

Labels: `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

**Labels:** `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

EOF_ISSUE_0802
)
create_issue "$title_ISSUE_0802" "$labels_ISSUE_0802" "$body_ISSUE_0802"

title_ISSUE_0901='ISSUE-0901: 召霊招待API'
labels_ISSUE_0901='`P2`, `backend`, `api`, `game-logic`, `todo`'
body_ISSUE_0901=$(cat <<'EOF_ISSUE_0901'
# ISSUE-0901: 召霊招待API

Labels: `P2`, `backend`, `api`, `game-logic`, `todo`

**Labels:** `P2`, `backend`, `api`, `game-logic`, `todo`

EOF_ISSUE_0901
)
create_issue "$title_ISSUE_0901" "$labels_ISSUE_0901" "$body_ISSUE_0901"

title_ISSUE_0902='ISSUE-0902: 召霊導入画面'
labels_ISSUE_0902='`P2`, `frontend`, `ui`, `todo`'
body_ISSUE_0902=$(cat <<'EOF_ISSUE_0902'
# ISSUE-0902: 召霊導入画面

Labels: `P2`, `frontend`, `ui`, `todo`

**Labels:** `P2`, `frontend`, `ui`, `todo`

EOF_ISSUE_0902
)
create_issue "$title_ISSUE_0902" "$labels_ISSUE_0902" "$body_ISSUE_0902"

title_ISSUE_0903='ISSUE-0903: 共闘イベント画面'
labels_ISSUE_0903='`P2`, `frontend`, `backend`, `ui`, `api`, `todo`'
body_ISSUE_0903=$(cat <<'EOF_ISSUE_0903'
# ISSUE-0903: 共闘イベント画面

Labels: `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

**Labels:** `P2`, `frontend`, `backend`, `ui`, `api`, `todo`

---

## スプリント例

### Sprint 1
- ISSUE-0001
- ISSUE-0002
- ISSUE-0003
- ISSUE-0004
- ISSUE-0005
- ISSUE-0101
- ISSUE-0102
- ISSUE-0103
- ISSUE-0104
- ISSUE-0105
- ISSUE-0106
- ISSUE-0107

### Sprint 2
- ISSUE-0201
- ISSUE-0202
- ISSUE-0203
- ISSUE-0301
- ISSUE-0302
- ISSUE-0303
- ISSUE-0304

### Sprint 3
- ISSUE-0401
- ISSUE-0402
- ISSUE-0403
- ISSUE-0404
- ISSUE-0405
- ISSUE-0501
- ISSUE-0502
- ISSUE-0503
- ISSUE-0504
- ISSUE-0601
- ISSUE-0602

EOF_ISSUE_0903
)
create_issue "$title_ISSUE_0903" "$labels_ISSUE_0903" "$body_ISSUE_0903"
