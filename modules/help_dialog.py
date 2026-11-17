# -*- coding: utf-8 -*-
"""ヘルプ画面"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


HELP_TEXT = """
<h2 style="color:#82aaff;">YOLO Manager 初心者ガイド</h2>

<p>このツールは、AI（YOLO）を使って画像の中から特定の物体を見つけるための「学習」と「推論」を簡単に行うためのものです。<br>
プログラミングの知識がなくても、以下のステップに従うことで独自の検知モデルを作成できます。</p>

<h3 style="color:#c3e88d;">準備：設定画面での入力</h3>
<p>まず最初に<b>「設定」</b>ボタンで以下の項目を準備しましょう：</p>
<ul>
  <li><b>データセット保存先</b>：学習に必要なデータ一式を保存するフォルダを指定します。
    <br><span style="color:#82aaff;">※フォルダ直下に <code>classes.txt</code> が存在する場合は、クラス名が自動で読み込まれます。</span></li>
  <li><b>モデルパス</b>：AIの「脳」となるファイル（.pt）を指定します。初回は空でOK、二回目以降は自分で作った <code>best.pt</code> を指定します。</li>
  <li><b>Python 実行パス</b>：AIを動かすためのエンジンの場所を指定します。通常は変更不要です（デフォルト: <code>/usr/bin/python</code>）。</li>
  <li><b>推論・自動アノテーション設定</b>：信頼度閾値（Conf）に加え、検出枠の重複除去を行う<b>重なり判定閾値（IoU）</b>をスライダーで直感的に調整できます。</li>
  <li><b>SAHI / タイル分割設定（折りたたみ）</b>：高解像度画像や微小物体を高精度に学習・推論したい場合に展開して設定します。</li>
  <li><b>ショートカット作成ボタン</b>：設定画面下部のボタンを押すと、デスクトップに起動用ファイル（Windows: .bat / Linux・ラズパイ: .sh）を自動生成できます。</li>
</ul>

<hr>

<h3 style="color:#c3e88d;">目的別の操作パターン</h3>

<h4>パターンA：モデル初回作成の場合</h4>
<p>いちからAIの「脳」を作る基本のコースです。<br>
<b>手順:</b> 設定画面で「データセット保存先」と「元画像フォルダ」を指定 ➔ [1. データセット準備] ➔ [2. クラス名設定] ➔ [4. アノテーション] ➔ [5. 学習実行]</p>

<h4>パターンB：データセット作成済の場合</h4>
<p>先に作成しておいたデータセット（画像とラベル付けデータ）を使って、学習を行うコースです。<br>
データセットの構成は以下の通りとしてください。<br>
<code>
    dataset/<br>
    ├── train/<br>
    │   └── 学習用画像 + ラベル (.txt)<br>
    ├── val/<br>
    │   └── 検証用画像 + ラベル (.txt)<br>
    ├── classes.txt<br>
    └── data.yaml (学習時自動作成されるのでなくても可)<br>
</code>
<b>手順:</b> 設定画面でデータセットのフォルダを指定（classes.txt があれば自動反映） ➔ [5. 学習実行]</p>

<h4>パターンC：すでに作成したモデルの精度を上げたい場合</h4>
<p>一度作ったモデル（best.pt）をベースに、さらに新しい画像を学習させて賢くするコースです。<br>
<b>手順:</b> 設定画面で「データセット保存先」、「元画像フォルダ」を指定し、「モデルパス」で過去の <code>best.pt</code> を指定 ➔ [1. データセット準備] ➔ [3. 自動アノテーション] ➔ 出力されたExcelで結果を確認 ➔ [4. アノテーション] (ラベル結果の修正) ➔ [5. 学習実行]</p>

<h4>パターンD：作成したモデルの精度を確かめたい場合</h4>
<p>学習が完了したモデルを使って、実際に画像の中から正しく検知できるかテストするコースです。<br>
<b>手順:</b> 設定画面の「推論用モデル」でテストしたい <code>best.pt</code> を指定 ➔ [6. 推論]<br>
[6. 推論] ボタンを押すと対象フォルダの選択画面が開きます。推論結果は Excel ファイルにまとめられ、画像は検出個数別フォルダに保存されます。</p>

<h4>パターンE：高解像度画像や極小・微小物体を高精度に検出したい場合（SAHI / タイル分割）</h4>
<p>画像全体に対して物体が非常に小さい場合、通常の学習や推論では縮小されて見落とされがちになります。<br>
<b>手順:</b> 設定画面の「SAHI / タイル分割設定」を開き、
<ul>
  <li><b>学習時</b>: 「タイル分割学習を適用する」にチェック ➔ 高解像度画像をタイル状（例: 640×640）にスライスして学習を行います（元画像はそのまま保持され、一時データは学習完了後に自動削除されます）。</li>
  <li><b>推論・自動アノテーション時</b>: 「推論・自動アノテーションでSAHIスライス推論を使用する」にチェック ➔ 画像をスライスしながら細かく検知し、最後に結合して検出します。</li>
</ul>
</p>

<h4>パターンF：作成したモデルをラズパイ等の小型デバイスで動かしたい場合</h4>
<p>学習（ステップ5）が完了すると、自動的にラズパイ等の小型デバイスで高速動作する軽量モデル（NCNN形式）も併せて作成されます。<br>
生成された <code>best_ncnn_model</code> フォルダをラズパイ側にコピーして使用できます。<br>
<span style="color:#ffcb6b;">※注意: Raspberry Pi 環境上ではスペック・保護のため「5. 学習実行」はクリック不可に制限されています。学習はGPU搭載PCで行ってください。</span></p>

<hr>

<h3 style="color:#c3e88d;">操作の流れ（ステップ別解説）</h3>

<h4>1. データセット準備</h4>
<p>「データセット準備」ボタンを押すと、フォルダ作成と画像のコピー（学習用・検証用への分割）が自動で行われます。</p>

<h4>2. クラス名設定</h4>
<p>AIに覚えさせたい物体の名前（例：apple）を登録します。1行につき1つ入力してください。データセット直下に <code>classes.txt</code> があれば自動で読み込まれます。</p>

<h4>3. 自動アノテーション</h4>
<p>すでに学習済みのモデル(.pt)を持っている場合に使えます。AIが自動で画像の内容を判断し、下書きのアノテーションを作成します。SAHI推論をONにすると微小物体も検出できます。</p>

<h4>4. アノテーション</h4>
<p>手動で新規にアノテーションをしたり、AIが作成した下書きを修正したりします。<br>
「4.1 学習用」で練習用画像、「4.2 検証用」で確認用画像を修正します。「4.3 ラベル一覧」でアノテーション状況を確認・Excel出力できます。</p>

<h4>5. 学習実行</h4>
<p>作成したデータを使ってAIに新しい知識を覚えさせます（YOLO26 / YOLO11 / YOLOv8 に対応）。未アノテーション画像には空ラベルが自動補填されます。<br>
タイル分割学習をONにしている場合は、高解像度画像をスライスした一時データセットで学習が行われます。<br>
完了すると独自のモデル（.pt）およびラズパイ向け軽量モデル（NCNN形式）が自動生成されます。<br>
<span style="color:#ffcb6b;">※Raspberry Pi 環境では本ボタンは安全のため無効化されています。</span></p>

<h4>6. 推論（任意）</h4>
<p>完成したAIを使って、実際の判定テストを行います。SAHIスライス推論をONにすることで微小物体も見逃さずに検出可能です。結果は Excel にまとめられ、個数別に整理保存されます。<br>
※Excelビューアがない環境（ラズパイ等）では自動オープンを安全にスキップし、ファイルの生成・保存のみを行います。</p>

<hr>
<h3 style="color:#c3e88d;">困ったときは</h3>
<ul>
  <li><b>設定画面が開かない</b>：Pythonのパスが正しいか、必要なパッケージ（ultralytics, sahi, PyQt6 など）が揃っているか確認してください。</li>
  <li><b>ラズパイで「学習実行」が押せない</b>：Raspberry Pi 上での学習は安全・性能上の理由で制限されています。PC等で学習を行ってください。</li>
  <li><b>Excelファイルが自動で開かない</b>：LibreOffice などの閲覧アプリがない環境（Raspberry Piなど）では、安全のため自動オープンを中止し、ファイル作成のみ行われます。ファイル自体は正常に出力されています。</li>
  <li><b>小さい物体・遠くの物体が検知されない</b>：設定画面で「SAHI / タイル分割設定」を開き、タイル分割学習やSAHIスライス推論を有効にしてみてください。</li>
  <li><b>判定精度が低い</b>：学習画像の枚数を増やす、設定画面でデータ拡張（オーギュメント）を調整する、ラベルごとの枚数をそろえるなどを試してください。</li>
</ul>
"""


class HelpDialog(QDialog):
    """ヘルプ画面ダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ヘルプ - 使い方ガイド")
        self.setMinimumSize(600, 520)
        self.resize(660, 620)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QLabel(HELP_TEXT)
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setContentsMargins(16, 8, 16, 8)
        scroll.setWidget(content)

        layout.addWidget(scroll)

        close_btn = QPushButton("閉じる")
        close_btn.setProperty("accent", True)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
