# RTX Config

RTX830の設定をGitで管理し、変更を簡単に適用するためのツールです。SSH公開鍵認証を使用した安全な接続を提供します。

## 🚀 特徴

- **SSH公開鍵認証**: セキュアな接続でパスワードレス運用
- **設定のバージョン管理**: Gitと連携した設定履歴管理
- **自動バックアップ**: 設定変更前の自動バックアップ作成
- **設定差分表示**: 現在の設定との差分を視覚的に確認
- **設定検証**: 適用前の設定ファイル構文チェック
- **リッチUI**: colorfulなCLIインターフェース
- **古いバックアップの自動削除**: 保持期間による自動クリーンアップ

## 📋 必要な環境

- Python 3.9以上
- [uv](https://docs.astral.sh/uv/) (Pythonパッケージマネージャー)
- SSH公開鍵認証が設定済みのRTX830

## 🛠️ インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd rtxconfig

# 依存パッケージをインストール
uv sync
```

## ⚙️ 初期設定

### 1. 設定ファイルの作成

```bash
uv run rtx init-config config.yaml
```

### 2. 設定ファイルの編集

作成された`config.yaml`を編集してRTX830の接続情報を設定：

```yaml
rtx_connection:
  host: "192.168.100.1"      # RTX830のIPアドレス
  username: "admin"           # SSHユーザー名
  key_file: "~/.ssh/id_ed25519"  # SSH秘密鍵ファイルのパス
  port: 22
  timeout: 30

backup:
  directory: "./backups"     # バックアップ保存先
  keep_days: 30             # バックアップ保持日数

logging:
  level: "INFO"
  file: "./logs/rtxconfig.log"
```

### 3. 接続テスト

```bash
uv run rtx connect
```

## 📖 使用方法

### 基本的なワークフロー

1. **現在の設定をバックアップ**
   ```bash
   uv run rtx backup
   ```

2. **設定ファイルを作成・編集**
   ```bash
   # テンプレートをコピーして編集
   cp templates/basic_rtx830.txt my_config.txt
   # お好みのエディタで編集
   ```

3. **設定内容を検証**
   ```bash
   uv run rtx validate my_config.txt
   ```

4. **差分を確認**
   ```bash
   uv run rtx diff my_config.txt
   ```

5. **設定を適用**
   ```bash
   uv run rtx apply my_config.txt
   ```

### コマンド一覧

| コマンド | 説明 | 例 |
|----------|------|-----|
| `init-config` | 設定ファイルのテンプレートを作成 | `uv run rtx init-config config.yaml` |
| `connect` | RTX830への接続をテスト | `uv run rtx connect` |
| `backup` | 現在の設定をバックアップ | `uv run rtx backup` |
| `apply` | 設定ファイルを適用 | `uv run rtx apply config.txt` |
| `diff` | 設定の差分を表示 | `uv run rtx diff config.txt` |
| `restore` | バックアップから復元 | `uv run rtx restore backup.txt` |
| `backups` | バックアップファイルの一覧・管理 | `uv run rtx backups` |
| `validate` | 設定ファイルの検証 | `uv run rtx validate config.txt` |

### オプション

- `--config, -c`: 設定ファイルのパスを指定
- `--verbose, -v`: 詳細ログを表示

```bash
# カスタム設定ファイルを使用
uv run rtx --config /path/to/config.yaml connect

# 詳細ログ付きで実行
uv run rtx --verbose backup
```

## 📝 設定ファイル形式

RTX830の設定ファイルは通常のコマンド形式で記述します：

```text
# RTX830 Basic Configuration
console character ascii
console prompt RTX830

# Network settings
ip lan1 address 192.168.100.1/24
ip pp enable

# SSH settings
ssh host key generate
ssh server host key enable

# Save configuration
save
```

### 記述ルール

- `#`で始まる行はコメント（無視されます）
- 空行は無視されます
- 各行は1つのRTX830コマンドとして扱われます
- 長いコマンドは複数行に分けることができます

## 🔒 セキュリティ

### SSH鍵の設定

RTX830でSSH公開鍵認証を有効にする必要があります：

```bash
# RTX830での設定例
ssh server host key enable
ssh user <username> key <public-key-content>
```

### セキュリティのベストプラクティス

- SSH秘密鍵ファイルは適切な権限（600）で保護
- 設定ファイルに機密情報を含めない
- バックアップファイルのアクセス権限に注意
- 定期的なSSH鍵の更新

```bash
# SSH鍵の権限確認・設定
chmod 600 ~/.ssh/id_ed25519
```

## 📁 ディレクトリ構成

```
rtxconfig/
├── rtxconfig/              # メインパッケージ
│   ├── __init__.py
│   ├── cli.py             # CLIインターフェース
│   ├── config.py          # 設定管理
│   ├── connection.py      # SSH接続管理
│   └── manager.py         # 設定操作管理
├── configs/               # 設定ファイル
│   └── config.example.yaml
├── templates/             # 設定テンプレート
│   └── basic_rtx830.txt
├── docs/                  # ドキュメント
│   └── usage.md
├── backups/               # バックアップファイル（自動作成）
├── logs/                  # ログファイル（自動作成）
├── config.yaml            # メイン設定ファイル
├── pyproject.toml         # プロジェクト設定
└── README.md
```

## 🔧 開発・カスタマイズ

### 開発環境のセットアップ

```bash
# 開発モードでインストール
uv sync --dev

# コードの品質チェック
uv run ruff check .
uv run mypy rtxconfig

# テスト実行
uv run pytest
```

### カスタムテンプレートの作成

`templates/`ディレクトリに新しいテンプレートファイルを追加できます：

```bash
# カスタムテンプレートを作成
cp templates/basic_rtx830.txt templates/my_custom.txt
# 編集してカスタマイズ
```

## 🐛 トラブルシューティング

### よくある問題

1. **接続に失敗する**
   ```
   解決方法：
   - SSH鍵のパスと権限を確認
   - RTX830のSSH設定を確認
   - ネットワーク接続を確認
   ```

2. **設定適用が失敗する**
   ```
   解決方法：
   - 設定ファイルの構文をvalidateコマンドで確認
   - RTX830の現在状態を確認
   - バックアップから復元してリトライ
   ```

3. **バックアップが作成されない**
   ```
   解決方法：
   - backupディレクトリの書き込み権限を確認
   - ディスク容量を確認
   ```

### ログの確認

```bash
# ログファイルの確認
tail -f logs/rtxconfig.log

# 詳細ログでの実行
uv run rtx --verbose <command>
```

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

バグ報告、機能要望、プルリクエストを歓迎します！

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📞 サポート

- GitHub Issues: バグ報告・機能要望
- Documentation: `docs/usage.md`

---

**RTX Config** - RTX830設定管理を簡単に 🚀