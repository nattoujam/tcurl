# tcurl - TUI HTTP Client 仕様書

## 1. プロジェクト概要

### 1.1 プロジェクト名
**tcurl** (Terminal cURL)

### 1.2 概要
HTTPリクエストを管理・実行できるターミナルUIアプリケーション。リクエスト設定をYAMLファイルで永続化し、変数を使った柔軟なリクエスト送信が可能。Textualフレームワークを使用した高機能なTUIを提供。

### 1.3 技術スタック
- **言語**: Python 3.9+
- **パッケージ管理**: Poetry
- **TUIライブラリ**: Textual
- **CLIライブラリ**: Click
- **HTTPクライアント**: httpx
- **データ永続化**: YAML

---

## 2. ディレクトリ構造

```
tcurl/
├── pyproject.toml
├── README.md
├── tcurl/
│   ├── __init__.py
│   ├── cli.py              # Clickエントリーポイント
│   ├── app.py              # Textualアプリケーションクラス
│   ├── models.py           # データモデル（RequestSet等）
│   ├── storage.py          # YAML永続化処理
│   ├── http_client.py      # HTTPリクエスト実行
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── request_list.py    # リクエスト一覧ウィジェット
│   │   ├── detail_panel.py    # 詳細表示ウィジェット
│   │   ├── response_panel.py  # レスポンス表示ウィジェット
│   │   └── input_dialog.py    # 入力ダイアログウィジェット
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── main_screen.py     # メイン画面
│   │   └── help_screen.py     # ヘルプ画面
│   └── utils/
│       ├── __init__.py
│       ├── editor.py       # エディタ起動処理
│       └── clipboard.py    # クリップボード操作
└── tests/
```

---

## 3. 設定ファイル

### 3.1 保存場所
```
~/.config/nattoujam/tcurl/
├── config.yaml          # アプリケーション設定
└── requests/            # リクエストセット保存ディレクトリ
    ├── example1.yaml
    ├── example2.yaml
    └── ...
```

### 3.2 config.yaml（アプリケーション設定）
```yaml
# HTTPリクエスト設定
http:
  timeout: 10  # タイムアウト秒数（デフォルト: 10）

# エディタ設定（環境変数 EDITOR を優先）
editor: vim  # フォールバック用

# UI設定
ui:
  theme: default  # 将来的な拡張用
```

### 3.3 リクエストセットファイル (requests/*.yaml)
```yaml
name: "ユーザー作成API"
description: "新規ユーザーを作成するPOSTリクエスト"
method: POST  # GET or POST
url: "https://api.example.com/users"
headers:
  Content-Type: "application/json"
  Authorization: "Bearer your-token-here"
body: |
  {
    "name": "$1",
    "email": "$2",
    "age": $3
  }
variables:
  - name: "ユーザー名"
    placeholder: "例: John Doe"
  - name: "メールアドレス"
    placeholder: "例: john@example.com"
  - name: "年齢"
    placeholder: "例: 25"
```

**変数の仕様**:
- `$1`, `$2`, `$3` ... のプレースホルダーをbody内に記述
- リクエスト実行時にスペース区切りで入力: `John Doe john@example.com 25`
- 入力値が順番に `$1`, `$2`, `$3` に置換される

---

## 4. UIレイアウト

### 4.1 画面構成（lazygitライク）

```
┌─────────────────────────────────────────────────────────────────┐
│ tcurl - TUI HTTP Client                            [?] Help     │
├──────────────────┬──────────────────────────────────────────────┤
│ Requests         │ Request Details                              │
│                  │                                              │
│ > example1       │ Name: ユーザー作成API                         │
│   example2       │ Method: POST                                 │
│   api-test       │ URL: https://api.example.com/users           │
│                  │                                              │
│                  │ [Headers] [Body] [Response]                  │
│                  │                                              │
│                  │ {                                            │
│                  │   "name": "$1",                              │
│                  │   "email": "$2",                             │
│                  │   "age": $3                                  │
│                  │ }                                            │
│                  │                                              │
│                  │                                              │
├──────────────────┴──────────────────────────────────────────────┤
│ [n]ew [e]dit [d]elete [Enter]execute [q]uit                    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 パネル構成

#### 左パネル: リクエストセット一覧
- リクエストセット名を一覧表示
- 上下キー (`↑`, `↓`, `j`, `k`) で選択
- 選択中の項目をハイライト表示

#### 右パネル: 詳細・実行結果
- **3つのタブで切り替え**:
  1. **Headers**: リクエストヘッダー表示
  2. **Body**: リクエストボディ表示
  3. **Response**: レスポンス表示（実行後）

- タブ切り替え: `Tab`キーまたは`1`, `2`, `3`キー

#### 下部: ステータスバー
- 現在の操作可能なキーバインディングを表示

---

## 5. キーバインディング

### 5.1 グローバル
| キー | 動作 |
|------|------|
| `q` | アプリケーション終了 |
| `?` | ヘルプ表示 |
| `↑`, `k` | 上へ移動 |
| `↓`, `j` | 下へ移動 |

### 5.2 リクエストセット操作
| キー | 動作 |
|------|------|
| `n` | 新規リクエストセット作成 |
| `e` | 選択中のリクエストセットを編集 |
| `d` | 選択中のリクエストセットを削除（確認ダイアログ表示） |
| `Enter` | 選択中のリクエストセットを実行 |

### 5.3 詳細パネル操作
| キー | 動作 |
|------|------|
| `Tab`, `1`, `2`, `3` | タブ切り替え（Headers/Body/Response） |
| `y` | レスポンス内容をクリップボードにコピー |
| `s` | レスポンスをファイルに保存（将来的な拡張） |

---

## 6. 機能詳細

### 6.1 リクエストセット管理

#### 新規作成 (`n`キー)
1. デフォルトのYAMLテンプレートを生成
2. `$EDITOR`（未設定時は`config.yaml`のeditor設定）でファイルを開く
3. 保存後、一覧に追加

**テンプレート例**:
```yaml
name: "新規リクエスト"
description: ""
method: GET
url: "https://api.example.com"
headers:
  Content-Type: "application/json"
body: ""
variables: []
```

#### 編集 (`e`キー)
1. 選択中のYAMLファイルをエディタで開く
2. 保存後、変更を反映

#### 削除 (`d`キー)
1. 確認ダイアログを表示: `"[name]を削除しますか？ (y/n)"`
2. `y`で削除実行、`n`でキャンセル

### 6.2 リクエスト実行

#### 実行フロー
1. `Enter`キーでリクエスト実行を開始
2. **変数がある場合**:
   - 入力プロンプト表示: `変数を入力してください (スペース区切り):`
   - 各変数のプレースホルダーをヒント表示
   - 例: `ユーザー名(例: John Doe) メールアドレス(例: john@example.com) 年齢(例: 25)`
3. 入力値を`$1`, `$2`, `$3`...に置換
4. HTTPリクエスト送信（タイムアウト: config設定値）
5. レスポンスを右パネルのResponseタブに表示

#### レスポンス表示
```
Status: 200 OK
Time: 245ms

[Headers] [Body]

--- Headers ---
Content-Type: application/json
Content-Length: 156

--- Body ---
{
  "id": 12345,
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2025-12-28T10:30:00Z"
}
```

- JSON形式の場合は自動整形（indent=2）
- ステータスコードは色分け:
  - 2xx: 緑
  - 4xx: 黄
  - 5xx: 赤

#### エラー処理
- 接続エラー、タイムアウト時もResponseタブに表示:
```
Status: ERROR
Time: 10000ms (timeout)

Error: Connection timeout
Details: httpx.TimeoutException: ...
```

### 6.3 クリップボードコピー

- Responseタブで`y`キー押下
- レスポンスボディ全体をクリップボードにコピー
- ステータスバーに `"Copied to clipboard!"` と表示
- 使用ライブラリ: `pyperclip`

---

## 7. データモデル

### 7.1 RequestSet
```python
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class Variable:
    name: str
    placeholder: str

@dataclass
class RequestSet:
    name: str
    method: str  # "GET" or "POST"
    url: str
    headers: Dict[str, str]
    body: Optional[str]
    description: Optional[str] = ""
    variables: List[Variable] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []
```

### 7.2 Response
```python
@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    body: str
    elapsed_ms: float
    error: Optional[str] = None
```

---

## 8. 依存パッケージ

### pyproject.toml
```toml
[tool.poetry]
name = "tcurl"
version = "0.1.0"
description = "TUI HTTP Client with request management"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
textual = "^0.47.0"
click = "^8.1.7"
httpx = "^0.27.0"
pyyaml = "^6.0.1"
pyperclip = "^1.8.2"

[tool.poetry.scripts]
tcurl = "tcurl.cli:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## 9. 実装優先順位

### Phase 1: 基本機能
1. ✅ プロジェクト構造作成
2. ✅ YAML読み込み・書き込み機能
3. ✅ 基本的なTUI（左パネル一覧表示）
4. ✅ リクエスト実行（GET/POST）
5. ✅ レスポンス表示

### Phase 2: リクエスト管理
6. ✅ 新規作成（エディタ起動）
7. ✅ 編集機能
8. ✅ 削除機能（確認ダイアログ）

### Phase 3: 高度な機能
9. ✅ 変数機能（$1, $2, $3）
10. ✅ タブ切り替え（Headers/Body/Response）
11. ✅ クリップボードコピー
12. ✅ タイムアウト設定

### Phase 4: 改善・最適化
13. エラーハンドリング強化
14. UIの洗練（色、アニメーション）
15. ヘルプ画面の実装

---

## 10. テストケース

### 10.1 単体テスト
- YAML読み込み・書き込み
- 変数置換処理（$1, $2, $3）
- HTTPリクエスト実行（モック）

### 10.2 統合テスト
- エディタ起動→保存→反映
- リクエスト実行→レスポンス表示
- クリップボードコピー

---

## 11. 将来的な拡張案

- 環境変数の切り替え（dev/staging/prod）
- リクエスト履歴の保存・表示
- curlコマンドへのエクスポート
- レスポンスの差分表示
- PUT/DELETE/PATCHメソッド対応
- 認証フロー（OAuth2等）のサポート
- ダークモード/ライトモードの切り替え

---

## 12. Textual固有の実装ポイント

### 12.1 アプリケーション構造
```python
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, ListView, TabbedContent

class TcurlApp(App):
    CSS_PATH = "tcurl.css"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_request", "New"),
        ("e", "edit_request", "Edit"),
        ("d", "delete_request", "Delete"),
        ("?", "help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                RequestListWidget(id="request-list"),
                DetailPanelWidget(id="detail-panel"),
            )
        )
        yield Footer()
```

### 12.2 レイアウト（CSS）
Textualは独自のCSSライクなスタイリングシステムを使用:
```css
#request-list {
    width: 30%;
    border: solid green;
}

#detail-panel {
    width: 70%;
    border: solid blue;
}

TabbedContent {
    height: 100%;
}
```

### 12.3 リアクティブな状態管理
Textualのreactive属性を活用:
```python
from textual.reactive import reactive

class RequestListWidget(ListView):
    selected_request = reactive(None)
    
    def watch_selected_request(self, request):
        # 選択が変わった時の処理
        self.app.query_one("#detail-panel").update(request)
```

---

## 13. 参考資料

- [Textual Documentation](https://textual.textualize.io/)
- [Click Documentation](https://click.palletsprojects.com/)
- [httpx Documentation](https://www.python-httpx.org/)
- [lazygit UI Reference](https://github.com/jesseduffield/lazygit)

---

**仕様書バージョン**: 1.0  
**最終更新**: 2025-12-28