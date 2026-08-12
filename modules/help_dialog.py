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
  <li><b>データセット保存先</b>：学習に必要なデータ一式を保存するフォルダを指定します。</li>
  <li><b>モデルパス</b>：AIの「脳」となるファイル（.pt）を指定します。初回は空でOK、二回目以降は自分で作った <code>best.pt</code> を指定します。</li>
  <li><b>Python 実行パス</b>：AIを動かすためのエンジンの場所を指定します。開発者向けなので通常は変更しなくてよいです。</li>
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
    │   └── 学習用画像<br>
    │   └── 学習用ラベル<br>
    ├── val/<br>
    │   ├── 検証用画像<br>
    │   └── 検証用ラベル<br>
    ├── classes.txt<br>
    └── data.yaml(学習時自動作成されるのでなくても可)<br>
</code>
<b>手順:</b> 設定画面でデータセットのフォルダを指定 ➔ [5. 学習実行]</p>

<h4>パターンC：すでに作成したモデルの精度を上げたい場合</h4>
<p>一度作ったモデル（best.pt）をベースに、さらに新しい画像を学習させて賢くするコースです。（※学習枚数を増やすことも有効です）<br>
自動アノテーションは旧モデルが間違える可能性があるので、誤りがあれば手動で修正してください。<br>
<b>手順:</b> 設定画面で「データセット保存先」、「元画像フォルダ」を指定し、「モデルパス」で過去の <code>best.pt</code> を指定 ➔ [1. データセット準備] ➔ [3. 自動アノテーション] ➔　出力されたExcelで結果を確認 ➔ [4. アノテーション] (ラベル結果の修正) ➔ [5. 学習実行]</p>

<h4>パターンD：作成したモデルの精度を確かめたい場合</h4>
<p>学習が完了したモデル（best.pt）を使って、実際に画像の中から正しく検知できるかテストするコースです。<br>
<b>手順:</b> 設定画面の「推論用モデル」でテストしたい <code>best.pt</code> 等を指定 ➔ [6. 推論]<br>
[6. 推論]ボタンを押すと推論対象の画像フォルダを指定する画面が立ち上がります。推論が完了すると、推論結果はExcelファイルに保存され、画像は検出個数別に分けて保存されます。</p>

<h4>パターンE：作成したモデルをラズパイ等の小型デバイスで動かしたい場合</h4>
<p>学習（ステップ5）が完了すると、自動的にラズパイ等の小型デバイスで高速動作する軽量モデル（NCNN形式）も併せて作成されます。<br>
生成された <code>best_ncnn_model</code> フォルダをラズパイ側にコピーして使用できます。</p>

<hr>

<h3 style="color:#c3e88d;">操作の流れ（ステップ別解説）</h3>

<h4>1. データセット準備</h4>
<p>「データセット準備」ボタンを押すと、フォルダ作成と画像のコピーが自動で行われます。</p>

<h4>2. クラス名設定</h4>
<p>AIに覚えさせたい物体の名前（例：apple）を登録します。1行につき1つ入力してください。</p>

<h4>3. 自動アノテーション</h4>
<p>すでに学習済みのモデル(.pt)を持っている場合に使えます。AIが自動で画像の内容を判断し、下書きのアノテーションを作成します。</p>

<h4>4. アノテーション</h4>
<p>手動で新規にアノテーションをしたり、AIが作成した下書きを修正したりします。<br>
「4.1 学習用」で練習用画像、「4.2 検証用」で確認用画像を修正します。「4.3 ラベル一覧」でアノテーション状況を確認・Excel出力できます。</p>

<h4>5. 学習実行</h4>
<p>作成したデータを使ってAIに新しい知識を覚えさせます。完了すると独自のモデル（.pt）およびラズパイ向け軽量モデル（NCNN形式）が自動生成されます。</p>

<h4>6. 推論（任意）</h4>
<p>完成したAIを使って、実際の判定テストを行います。結果は Excel にまとめられ、個数別に整理保存されます。</p>

<hr>
<h3 style="color:#c3e88d;">困ったときは</h3>
<ul>
  <li><b>設定画面が開かない</b>：Pythonのパスが正しいか、ライブラリが揃っているか確認してください。</li>
  <li><b>ボタンが押せない</b>：前のステップが完了しているか、設定が保存されているか確認してください。</li>
  <li><b>判定精度が低い</b>：学習画像の枚数を増やす、設定画面でデータ拡張（回転や色の変化等）を調整する、ラベルごとの枚数をそろえるなどを試してください。</li>
</ul>
"""


class HelpDialog(QDialog):
    """ヘルプ画面ダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ヘルプ - 使い方ガイド")
        self.setMinimumSize(580, 500)
        self.resize(620, 560)

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
