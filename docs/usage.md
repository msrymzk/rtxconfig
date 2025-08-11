# RTX Config 使用方法

## 基本的なワークフロー

1. **設定ファイル作成**
   ```bash
   uv run rtx init-config config.yaml
   ```

2. **RTX830接続情報設定**
   - config.yamlを編集
   - SSH秘密鍵の設定

3. **接続テスト**
   ```bash
   uv run rtx connect
   ```

4. **現在の設定をバックアップ**
   ```bash
   uv run rtx backup
   ```

5. **設定ファイル作成・編集**
   - テキストエディタで設定ファイルを作成
   - RTX830のコマンド形式で記述

6. **設定差分確認**
   ```bash
   uv run rtx diff new_config.txt
   ```

7. **設定適用**
   ```bash
   uv run rtx apply new_config.txt
   ```

## コマンド詳細

### connect
RTX830への接続をテストします。

```bash
uv run rtx connect
```

### backup
現在のRTX830設定をバックアップします。

```bash
# 自動的にタイムスタンプ付きファイルを作成
uv run rtx backup

# 指定したファイルに保存
uv run rtx backup -o config_backup.txt
```

### apply
設定ファイルをRTX830に適用します。

```bash
# 通常の適用（事前にバックアップを作成）
uv run rtx apply config.txt

# バックアップを作成せずに適用
uv run rtx apply --no-backup config.txt

# ドライラン（実際には適用しない）
uv run rtx apply --dry-run config.txt
```

### diff
現在の設定と指定ファイルの差分を表示します。

```bash
uv run rtx diff config.txt
```

### restore
バックアップファイルから設定を復元します。

```bash
uv run rtx restore backups/rtx830_config_20240101_123456.txt
```

### backups
バックアップファイルの管理を行います。

```bash
# バックアップファイル一覧
uv run rtx backups

# 古いバックアップの削除
uv run rtx backups --cleanup
```

### validate
設定ファイルの構文をチェックします。

```bash
uv run rtx validate config.txt
```

### init-config
設定ファイルのテンプレートを作成します。

```bash
uv run rtx init-config config.yaml
```

## グローバルオプション

すべてのコマンドで使用可能なオプション：

- `--config, -c`: 設定ファイルパスを指定
- `--verbose, -v`: 詳細ログを有効化

例：
```bash
uv run rtx --config /path/to/config.yaml --verbose connect
```