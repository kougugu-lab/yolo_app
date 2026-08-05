# YOLO Manager を別のPCで使用するための手順です。

## 1. 事前準備 (一回のみ)

### Python のインストール
- [Python 3.10.x](https://www.python.org/downloads/windows/) をインストールしてください。
- インストール時、「Add Python to PATH」に必ずチェックを入れてください。

### フォルダのコピー
- `yolo_app` フォルダが含まれるプロジェクトディレクトリ全体をコピーして、配布先PCの任意の場所（例: `C:\YOLO_App`）に配置します。

## 2. セットアップ手順

プロジェクトディレクトリ（`requirements.txt` がある場所）でコマンドプロンプトを開き、以下のコマンドを順番に実行します。

```batch
# 仮想環境の作成
python -m venv venv

# 仮想環境のアクティベート
call venv\Scripts\activate

# ライブラリの一括インストール
pip install -r requirements.txt
```

## 3. アプリの起動

`start_app.bat` をダブルクリックするか、以下のコマンドで起動します。

```batch
venv\Scripts\python.exe yolo_app/main.py
```

## 4. 起動後の設定

1. アプリが起動したら「設定」ボタンを押します。
2. **Python 実行パス** に、先ほど作成した仮想環境内の python を指定します。
   - 例: `C:\YOLO_App\venv\Scripts\python.exe`
3. **データセット保存先** など、各フォルダパスを配布先PCの環境に合わせて設定し「保存」してください。
