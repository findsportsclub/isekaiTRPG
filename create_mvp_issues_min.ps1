param(
    [Parameter(Mandatory=$true)]
    [string]$Repo
)

$ErrorActionPreference = "Stop"

function New-IssueSafe {
    param(
        [string]$Title,
        [string[]]$Labels,
        [string]$Body
    )

    $tmp = Join-Path $env:TEMP (([System.Guid]::NewGuid().ToString()) + ".md")
    Set-Content -Path $tmp -Value $Body -Encoding UTF8

    $url = gh issue create --repo $Repo --title $Title --body-file $tmp
    Remove-Item $tmp -Force

    Write-Host $url

    $issueNumber = ($url -split "/")[-1]

    foreach ($label in $Labels) {
        gh issue edit $issueNumber --repo $Repo --add-label $label | Out-Null
        Write-Host "added label: $label -> #$issueNumber"
    }
}

New-IssueSafe `
  -Title "ISSUE-0001: monorepo初期化" `
  -Labels @("P0","infra","docs","todo") `
  -Body @"
# ISSUE-0001: monorepo初期化

Labels: P0, infra, docs, todo

**目的**  
frontend / backend / docs の基本構成を作る

**作業**
- frontend/ 作成
- backend/ 作成
- docs/ 作成
- ルートREADME作成

**完了条件**
- ディレクトリ構成が揃っている
"@

New-IssueSafe `
  -Title "ISSUE-0002: Next.js初期化" `
  -Labels @("P0","frontend","ui","todo") `
  -Body @"
# ISSUE-0002: Next.js初期化

Labels: P0, frontend, ui, todo

**目的**  
フロントエンド起動確認

**作業**
- Next.js + TypeScript 初期化
- Tailwind導入
- App Router構成作成

**完了条件**
- frontend で開発サーバー起動成功
"@

New-IssueSafe `
  -Title "ISSUE-0003: FastAPI初期化" `
  -Labels @("P0","backend","api","todo") `
  -Body @"
# ISSUE-0003: FastAPI初期化

Labels: P0, backend, api, todo

**目的**  
バックエンド起動確認

**作業**
- FastAPIプロジェクト作成
- /health エンドポイント作成
- Uvicorn起動確認

**完了条件**
- /health が 200 を返す
"@

New-IssueSafe `
  -Title "ISSUE-0004: SQLite接続基盤" `
  -Labels @("P0","backend","db","todo") `
  -Body @"
# ISSUE-0004: SQLite接続基盤

Labels: P0, backend, db, todo

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
"@

New-IssueSafe `
  -Title "ISSUE-0104: 世界一覧API" `
  -Labels @("P1","backend","api","todo") `
  -Body @"
# ISSUE-0104: 世界一覧API

Labels: P1, backend, api, todo

**目的**  
自分の世界一覧を返す

**作業**
- GET /api/worlds
- world一覧取得
- owner紐付け

**完了条件**
- 世界カード用データが返る
"@

New-IssueSafe `
  -Title "ISSUE-0105: 世界一覧画面" `
  -Labels @("P1","frontend","ui","todo") `
  -Body @"
# ISSUE-0105: 世界一覧画面

Labels: P1, frontend, ui, todo

**目的**  
作成済み世界を選べるようにする

**作業**
- /worlds
- 世界カード表示
- 新規作成ボタン
- 未読/召霊通知枠

**完了条件**
- 世界一覧が表示される
"@

New-IssueSafe `
  -Title "ISSUE-0106: 世界作成API" `
  -Labels @("P1","backend","api","game-logic","todo") `
  -Body @"
# ISSUE-0106: 世界作成API

Labels: P1, backend, api, game-logic, todo

**目的**  
新規世界を作る

**作業**
- POST /api/worlds
- world レコード作成
- 初期主人公作成
- 初期world_state作成

**完了条件**
- 世界作成後に worldId を返す
"@

New-IssueSafe `
  -Title "ISSUE-0107: 世界作成画面" `
  -Labels @("P1","frontend","ui","todo") `
  -Body @"
# ISSUE-0107: 世界作成画面

Labels: P1, frontend, ui, todo

**目的**  
UIから世界を新規作成する

**作業**
- /worlds/new
- 世界名
- 主人公名
- 種族
- 初期チート
- seed設定

**完了条件**
- 作成後に世界ダッシュボードへ遷移
"@

New-IssueSafe `
  -Title "ISSUE-0202: 世界ダッシュボードAPI" `
  -Labels @("P1","backend","api","todo") `
  -Body @"
# ISSUE-0202: 世界ダッシュボードAPI

Labels: P1, backend, api, todo

**目的**  
ダッシュボード表示用データを返す

**作業**
- GET /api/worlds/{worldId}
- Era
- crisis_scores
- featured NPC
- rumors
- main event

**完了条件**
- ダッシュボードに必要なJSONが返る
"@

New-IssueSafe `
  -Title "ISSUE-0203: 世界ダッシュボード画面" `
  -Labels @("P1","frontend","ui","todo") `
  -Body @"
# ISSUE-0203: 世界ダッシュボード画面

Labels: P1, frontend, ui, todo

**目的**  
中核画面を作る

**作業**
- /worlds/[worldId]
- 世界概要
- Era表示
- 危機スコア表示
- MAINイベント枠
- 注目NPC
- 最近の噂

**完了条件**
- 世界の状態が一覧できる
"@