# -*- coding: utf-8 -*-
"""設定画面 (QDialog)"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import config_manager
import operations
from workers import InstallWorker, check_packages


class CollapsibleGroupBox(QWidget):
    """クリックして開閉できる折りたたみ式グループコンテナ"""

    def __init__(self, title: str, parent=None, is_expanded: bool = False):
        super().__init__(parent)
        self._is_expanded = is_expanded
        self._title_text = title

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setSpacing(0)

        # ヘッダーボタン
        self.toggle_btn = QPushButton()
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(
            "QPushButton { text-align: left; font-weight: bold; font-size: 13px; "
            "padding: 8px 12px; background-color: #2b2b2b; color: #e0e0e0; "
            "border: 1px solid #3c3c3c; border-radius: 6px; } "
            "QPushButton:hover { background-color: #383838; border-color: #555555; }"
        )
        self.toggle_btn.clicked.connect(self.toggle_expanded)
        self.main_layout.addWidget(self.toggle_btn)

        # コンテンツ表示用エリア
        self.content_area = QWidget()
        self.content_area.setObjectName("CollapsibleContent")
        self.content_area.setStyleSheet(
            "QWidget#CollapsibleContent { background-color: #1e1e1e; border: 1px solid #3c3c3c; "
            "border-top: none; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }"
        )
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 12, 12, 12)

        self.main_layout.addWidget(self.content_area)
        self._update_state()

    def toggle_expanded(self):
        self._is_expanded = not self._is_expanded
        self._update_state()

    def _update_state(self):
        arrow = "▼" if self._is_expanded else "▶"
        self.toggle_btn.setText(f"{arrow}  {self._title_text}")
        self.content_area.setVisible(self._is_expanded)
        self.updateGeometry()
        if self.parentWidget():
            self.parentWidget().updateGeometry()

    def setContentLayout(self, layout):
        container = QWidget()
        container.setLayout(layout)
        self.content_layout.addWidget(container)


class SettingsDialog(QDialog):
    """設定ダイアログ"""

    def __init__(self, config: dict, log_callback=None, parent=None):
        super().__init__(parent)
        self.config = dict(config)  # コピーして編集
        self.log_callback = log_callback
        self._install_worker = None
        self.setWindowTitle("設定")
        self.setMinimumSize(750, 800)
        self._build_ui()
        self._load_values()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # スクロールエリアの設定
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        root = QVBoxLayout(content_widget)
        root.setContentsMargins(0, 0, 0, 0)

        # --- パス設定 ---
        path_group = QGroupBox("パス設定")
        path_layout = QFormLayout()
        
        # ユーザーが頻繁に変更する順
        self.dataset_edit = self._path_row(
            path_layout, "データセット保存先:",
            tooltip="学習データ（train/val）や設定ファイルが保存される中心となるフォルダです。"
        )
        self.autolabel_model_edit = self._path_row(
            path_layout, "自動アノテーション用モデル (.pt):", 
            file_mode=True, 
            file_filter="YOLO Model (*.pt);;All (*)",
            tooltip="ステップ3の「自動アノテーション」で使用する学習済みモデルファイルです。"
        )
        self.inference_model_edit = self._path_row(
            path_layout, "推論用モデル (.pt):", 
            file_mode=True, 
            file_filter="YOLO Model (*.pt);;All (*)",
            tooltip="ステップ6の「推論」で使用するモデルファイルです。ステップ5の学習完了時に自動更新されます。"
        )
        self.python_edit = self._path_row(
            path_layout, "Python 実行パス:", 
            file_mode=True,
            tooltip="AIプログラムを動かすための設定です。仮想環境(venv)内の python.exe を指定します。"
        )
        
        path_group.setLayout(path_layout)
        root.addWidget(path_group)

        # --- データ分割 ---
        split_group = QGroupBox("データ分割")
        split_layout = QFormLayout()
        self.train_spin = QSpinBox()
        self.train_spin.setRange(1, 99999)
        self.train_spin.setToolTip("学習用(train)としてコピーする画像の枚数です。")
        split_layout.addRow("学習用枚数:", self.train_spin)
        
        self.val_spin = QSpinBox()
        self.val_spin.setRange(1, 99999)
        self.val_spin.setToolTip("検証用(val)としてコピーする画像の枚数です。通常は全体の20%程度にします。")
        split_layout.addRow("検証用枚数:", self.val_spin)
        split_group.setLayout(split_layout)
        root.addWidget(split_group)

        # --- ハイパーパラメータ ---
        hp_group = QGroupBox("ハイパーパラメータ")
        hp_layout = QFormLayout()
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 9999)
        self.epochs_spin.setToolTip("学習を何回繰り返すか指定します。回数が多いほど賢くなりますが時間がかかります。")
        hp_layout.addRow("学習回数 (Epochs):", self.epochs_spin)
        
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(32, 4096)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setToolTip("学習・推論時の画像サイズ。通常は 640 を使用します。")
        hp_layout.addRow("画像サイズ (Image Size):", self.imgsz_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, 32)
        self.workers_spin.setToolTip("データ読み込みの並列処理ワーカー数。0〜8が推奨です（RTX 5060等の環境でimgsz=640なら4、800なら2、1024なら0を推奨）。")
        hp_layout.addRow("並列数 (workers):", self.workers_spin)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["n", "s", "m", "l", "x", "n-p2", "s-p2", "m-p2", "l-p2", "x-p2"])
        self.model_combo.setToolTip("学習のベースにするモデルサイズ。P2ヘッダー付きモデル(n-p2〜x-p2)も選択可能です。")
        hp_layout.addRow("ベースモデル:", self.model_combo)

        self.yolo_version_combo = QComboBox()
        self.yolo_version_combo.addItems(["8", "11"])
        self.yolo_version_combo.setToolTip("使用する YOLO のバージョンを選択します。")
        hp_layout.addRow("YOLO バージョン:", self.yolo_version_combo)

        hp_group.setLayout(hp_layout)
        root.addWidget(hp_group)

        # --- オーギュメント設定 [折りたたみコンテナ] ---
        aug_group = CollapsibleGroupBox("オーギュメント設定", is_expanded=False)
        aug_layout = QFormLayout()

        # HSV-H
        self.hsv_h_spin = QDoubleSpinBox()
        self.hsv_h_spin.setRange(0.0, 1.0)
        self.hsv_h_spin.setSingleStep(0.005)
        self.hsv_h_spin.setDecimals(3)
        self.hsv_h_spin.setToolTip("画像の色相(Hue)のランダム変化量 (0.0〜1.0)")
        aug_layout.addRow("色相変化 (hsv_h):", self.hsv_h_spin)

        # HSV-S
        self.hsv_s_spin = QDoubleSpinBox()
        self.hsv_s_spin.setRange(0.0, 1.0)
        self.hsv_s_spin.setSingleStep(0.05)
        self.hsv_s_spin.setDecimals(2)
        self.hsv_s_spin.setToolTip("画像の彩度(Saturation)のランダム変化量 (0.0〜1.0)")
        aug_layout.addRow("彩度変化 (hsv_s):", self.hsv_s_spin)

        # HSV-V
        self.hsv_v_spin = QDoubleSpinBox()
        self.hsv_v_spin.setRange(0.0, 1.0)
        self.hsv_v_spin.setSingleStep(0.05)
        self.hsv_v_spin.setDecimals(2)
        self.hsv_v_spin.setToolTip("画像の明度(Value)のランダム変化量 (0.0〜1.0)")
        aug_layout.addRow("明度変化 (hsv_v):", self.hsv_v_spin)

        # 回転 (degrees)
        self.degrees_spin = QDoubleSpinBox()
        self.degrees_spin.setRange(0.0, 180.0)
        self.degrees_spin.setSingleStep(1.0)
        self.degrees_spin.setDecimals(1)
        self.degrees_spin.setToolTip("ランダム回転の最大角度 (±度)")
        aug_layout.addRow("回転 (degrees):", self.degrees_spin)

        # 平行移動 (translate)
        self.translate_spin = QDoubleSpinBox()
        self.translate_spin.setRange(0.0, 1.0)
        self.translate_spin.setSingleStep(0.05)
        self.translate_spin.setDecimals(2)
        self.translate_spin.setToolTip("画像のランダム平行移動比率 (0.0〜1.0)")
        aug_layout.addRow("平行移動 (translate):", self.translate_spin)

        # 拡大縮小 (scale)
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.0, 1.0)
        self.scale_spin.setSingleStep(0.05)
        self.scale_spin.setDecimals(2)
        self.scale_spin.setToolTip("画像のランダム拡大縮小倍率ゲイン (0.0〜1.0)")
        aug_layout.addRow("拡大縮小 (scale):", self.scale_spin)

        # シアー / せん断 (shear)
        self.shear_spin = QDoubleSpinBox()
        self.shear_spin.setRange(0.0, 180.0)
        self.shear_spin.setSingleStep(1.0)
        self.shear_spin.setDecimals(1)
        self.shear_spin.setToolTip("ランダムせん断変形の最大角度 (±度)")
        aug_layout.addRow("せん断 (shear):", self.shear_spin)

        # 遠近法 (perspective)
        self.perspective_spin = QDoubleSpinBox()
        self.perspective_spin.setRange(0.0, 0.001)
        self.perspective_spin.setSingleStep(0.0001)
        self.perspective_spin.setDecimals(5)
        self.perspective_spin.setToolTip("ランダム遠近法変形の度合い (0.0〜0.001)")
        aug_layout.addRow("遠近法 (perspective):", self.perspective_spin)

        # 上下反転 (flipud)
        self.flipud_spin = QDoubleSpinBox()
        self.flipud_spin.setRange(0.0, 1.0)
        self.flipud_spin.setSingleStep(0.05)
        self.flipud_spin.setDecimals(2)
        self.flipud_spin.setToolTip("上下反転の適用確率 (0.0〜1.0)")
        aug_layout.addRow("上下反転 (flipud):", self.flipud_spin)

        # 左右反転 (fliplr)
        self.fliplr_spin = QDoubleSpinBox()
        self.fliplr_spin.setRange(0.0, 1.0)
        self.fliplr_spin.setSingleStep(0.05)
        self.fliplr_spin.setDecimals(2)
        self.fliplr_spin.setToolTip("左右反転の適用確率 (0.0〜1.0)")
        aug_layout.addRow("左右反転 (fliplr):", self.fliplr_spin)

        aug_group.setContentLayout(aug_layout)
        root.addWidget(aug_group)

        # --- 推論設定 ---
        inf_group = QGroupBox("推論・自動アノテーション設定")
        inf_layout = QHBoxLayout()
        inf_label = QLabel("信頼度閾値 (Conf):")
        inf_label.setToolTip("AIが「それ」であると確信する度合いの最低ラインです。高いほど誤検知が減ります。")
        inf_layout.addWidget(inf_label)
        
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(1, 100)  # 0.01 ~ 1.00
        self.conf_slider.setTickInterval(5)
        self.conf_slider.setToolTip("0.01(甘い) 〜 1.00(非常に厳しい) の間で調整します。")
        self.conf_label = QLabel("0.4")
        self.conf_label.setMinimumWidth(40)
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f"{v / 100:.2f}")
        )
        inf_layout.addWidget(self.conf_slider)
        inf_layout.addWidget(self.conf_label)
        inf_group.setLayout(inf_layout)
        root.addWidget(inf_group)
        
        root.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # --- ボタン行 ---
        btn_row = QHBoxLayout()

        check_btn = QPushButton("パッケージ確認")
        check_btn.clicked.connect(self._check_packages)
        btn_row.addWidget(check_btn)

        reset_btn = QPushButton("パラメータリセット")
        reset_btn.clicked.connect(self._reset_params)
        btn_row.addWidget(reset_btn)

        shortcut_btn = QPushButton("ショートカット作成")
        shortcut_btn.setToolTip("デスクトップにアプリ起動用ショートカット（YOLOマネージャー）を作成します。")
        shortcut_btn.clicked.connect(self._create_shortcut)
        btn_row.addWidget(shortcut_btn)

        help_btn = QPushButton("ヘルプ")
        help_btn.clicked.connect(self._show_settings_help)
        btn_row.addWidget(help_btn)

        btn_row.addStretch()

        save_btn = QPushButton("保存して閉じる")
        save_btn.setProperty("accent", True)
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(save_btn)

        main_layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # ヘルパー: パス入力行
    # ------------------------------------------------------------------
    def _path_row(self, form_layout, label: str,
                  file_mode: bool = False,
                  file_filter: str = "Python (python.exe);;All (*)",
                  tooltip: str = "") -> QLineEdit:
        row = QHBoxLayout()
        edit = QLineEdit()
        if tooltip:
            edit.setToolTip(tooltip)
        
        browse = QPushButton("参照")
        browse.setFixedWidth(80)  # ボタンの幅を固定

        def on_browse():
            if file_mode:
                path, _ = QFileDialog.getOpenFileName(self, label, "", file_filter)
            else:
                path = QFileDialog.getExistingDirectory(self, label)
            if path:
                edit.setText(path)

        browse.clicked.connect(on_browse)
        row.addWidget(edit, 1)  # 入力欄を伸ばす
        row.addWidget(browse)
        wrapper = QWidget()
        wrapper.setLayout(row)
        form_layout.addRow(label, wrapper)
        return edit

    # ------------------------------------------------------------------
    # 値の読み書き
    # ------------------------------------------------------------------
    def _load_values(self):
        self.python_edit.setText(self.config.get("python_path", ""))
        self.dataset_edit.setText(self.config.get("dataset_dir", ""))
        
        # 移行中などの考慮、互換性
        inf_path = self.config.get("inference_model_path", "") or self.config.get("model_path", "")
        auto_path = self.config.get("autolabel_model_path", "") or self.config.get("model_path", "")
        self.inference_model_edit.setText(inf_path)
        self.autolabel_model_edit.setText(auto_path)

        self.train_spin.setValue(self.config.get("train_count", 80))
        self.val_spin.setValue(self.config.get("val_count", 20))
        self.epochs_spin.setValue(self.config.get("epochs", 100))
        self.imgsz_spin.setValue(self.config.get("imgsz", 640))
        self.workers_spin.setValue(self.config.get("workers", 4))
        model = self.config.get("base_model", "n")
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)

        yolo_ver = str(self.config.get("yolo_version", "11"))
        v_idx = self.yolo_version_combo.findText(yolo_ver)
        if v_idx >= 0:
            self.yolo_version_combo.setCurrentIndex(v_idx)

        conf_int = int(self.config.get("conf_threshold", 0.4) * 100)
        self.conf_slider.setValue(max(1, min(100, conf_int)))
        self.conf_label.setText(f"{conf_int / 100:.2f}")

        # オーギュメントパラメータ
        self.hsv_h_spin.setValue(float(self.config.get("hsv_h", 0.015)))
        self.hsv_s_spin.setValue(float(self.config.get("hsv_s", 0.7)))
        self.hsv_v_spin.setValue(float(self.config.get("hsv_v", 0.4)))
        self.degrees_spin.setValue(float(self.config.get("degrees", 0.0)))
        self.translate_spin.setValue(float(self.config.get("translate", 0.1)))
        self.scale_spin.setValue(float(self.config.get("scale", 0.5)))
        self.shear_spin.setValue(float(self.config.get("shear", 0.0)))
        self.perspective_spin.setValue(float(self.config.get("perspective", 0.0)))
        self.flipud_spin.setValue(float(self.config.get("flipud", 0.0)))
        self.fliplr_spin.setValue(float(self.config.get("fliplr", 0.5)))

    def _collect_values(self) -> dict:
        imgsz_val = self.imgsz_spin.value()
        return {
            "python_path": self.python_edit.text().strip(),
            "dataset_dir": self.dataset_edit.text().strip(),
            "inference_model_path": self.inference_model_edit.text().strip(),
            "autolabel_model_path": self.autolabel_model_edit.text().strip(),
            "train_count": self.train_spin.value(),
            "val_count": self.val_spin.value(),
            "epochs": self.epochs_spin.value(),
            "batch": -1,
            "imgsz": imgsz_val,
            "workers": self.workers_spin.value(),
            "base_model": self.model_combo.currentText(),
            "yolo_version": self.yolo_version_combo.currentText(),
            "conf_threshold": self.conf_slider.value() / 100.0,
            "class_names": self.config.get("class_names", ""),
            "hsv_h": self.hsv_h_spin.value(),
            "hsv_s": self.hsv_s_spin.value(),
            "hsv_v": self.hsv_v_spin.value(),
            "degrees": self.degrees_spin.value(),
            "translate": self.translate_spin.value(),
            "scale": self.scale_spin.value(),
            "shear": self.shear_spin.value(),
            "perspective": self.perspective_spin.value(),
            "flipud": self.flipud_spin.value(),
            "fliplr": self.fliplr_spin.value(),
        }

    # ------------------------------------------------------------------
    # アクション
    # ------------------------------------------------------------------
    def _save_and_close(self):
        self.config = self._collect_values()
        config_manager.save(self.config)
        self.accept()

    def _reset_params(self):
        self.config = config_manager.reset_params(self._collect_values())
        self._load_values()

    def _check_packages(self):
        python_path = self.python_edit.text().strip()
        if not python_path or not Path(python_path).exists():
            QMessageBox.warning(self, "警告", "有効な Python パスを指定してください。")
            return

        required = ["ultralytics", "pandas", "openpyxl", "labelImg", "PyQt6", "PyYAML", "onnx", "ncnn"]
        missing = check_packages(python_path, required)

        if not missing:
            QMessageBox.information(self, "確認", "全パッケージがインストール済みです。")
            return

        msg = "以下のパッケージが不足しています:\n" + ", ".join(missing)
        msg += "\n\n自動インストールしますか?"
        reply = QMessageBox.question(
            self, "パッケージ不足", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_install(python_path, missing)

    def _run_install(self, python_path: str, packages: list):
        self._install_worker = InstallWorker(python_path, packages, parent=self)
        if self.log_callback:
            self._install_worker.log_signal.connect(self.log_callback)
        self._install_worker.finished_signal.connect(self._on_install_done)
        self._install_worker.start()

    def _on_install_done(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "完了", message)
        else:
            QMessageBox.warning(self, "エラー", message)

    def _show_settings_help(self):
        """設定項目の詳しい解説ダイアログを表示"""
        help_msg = """
<h1 style="color:#82aaff;">設定項目の解説</h1>

<h3 style="color:#c3e88d;">パス設定</h3>
<p><b>■ データセット保存先:</b><br>
学習用データや成果物が保存されるメインフォルダです。新プロジェクトごとに空のフォルダを作るのが推奨です。</p>
<p><b>■ 自動アノテーション用モデル:</b><br>
AIに自動ラベル付けをさせたい時に使用する既存のモデル（.pt）を指定します。</p>
<p><b>■ 推論用モデル:</b><br>
テスト（推論）に使用するモデルを指定します。ステップ5の学習が成功すると、生成された best.pt に自動でパスが更新されます。</p>
<p><b>■ Python 実行パス:</b><br>
AIを動かすためのエンジンの場所を指定します。基本的には初期設定のままで問題ありません。</p>

<h3 style="color:#c3e88d;">データ分割</h3>
<p><b>■ 学習用枚数 / 検証用枚数:</b><br>
元画像から何枚を「学習用」と「検証用」に割り振るかを決めます。ステップ1で指定した枚数分、ランダムにコピーを行います。<br>
一般的に 8(練習):2(テスト) 程度の比率が良いとされています。</p>

<h3 style="color:#c3e88d;">ハイパーパラメータ</h3>
<p><b>■ 学習回数 (Epochs):</b><br>
データを何回繰り返し学習させるかです。50〜200 程度が目安です。</p>
<p><b>■ 画像サイズ (Image Size):</b><br>
AIが画像を読み込む解像度です。通常は 640 です。高いと精度が上がりますが動作は遅くなります。</p>
<p>※バッチサイズは自動バッチ(-1)、並列数は画像サイズに応じて最適な値が自動設定されます。</p>
<p><b>■ ベースモデル:</b><br>
学習の土台となるモデルの「規模」です。n(最速) < s < m < l < x(最高精度) の順で、右ほど賢いですが重くなります。</p>
<p><b>■ YOLO バージョン:</b><br>
使用するAIの世代です。最新の 11 が最もお勧めです。</p>

<h3 style="color:#c3e88d;">オーギュメント設定</h3>
<p>画像枚数が少ない場合や、実際の撮影環境の変動に対応させるためのリアルタイム画像加工パラメータです。ヘッダーをクリックすると詳細が展開されます。</p>
<p><b>■ 色相変化 (hsv_h: 0.0〜1.0):</b><br>
画像の色合いをランダムに変化させます。照明の色変化に対する耐性を高めます。（初期値: 0.015）</p>
<p><b>■ 彩度変化 (hsv_s: 0.0〜1.0):</b><br>
画像の鮮やかさをランダムに変えます。影や光の反射に対する耐性を高めます。（初期値: 0.7）</p>
<p><b>■ 明度変化 (hsv_v: 0.0〜1.0):</b><br>
画像の明るさをランダムに変えます。明暗の強弱に対応させます。（初期値: 0.4）</p>
<p><b>■ 回転 (degrees: 0〜180度):</b><br>
画像を左右へ指定角度の範囲で回転させます。向きが様々な物体に効果的です。（初期値: 0.0）</p>
<p><b>■ 平行移動 (translate: 0.0〜1.0):</b><br>
画面内での物体の位置を前後にずらします。（初期値: 0.1）</p>
<p><b>■ 拡大縮小 (scale: 0.0〜1.0):</b><br>
物体の撮影距離による大小の違いに対応させます。（初期値: 0.5）</p>
<p><b>■ せん断 (shear: 0〜180度):</b><br>
画像を斜めにひがませます。カメラ角度の歪みに効果的です。（初期値: 0.0）</p>
<p><b>■ 遠近法 (perspective: 0.0〜0.001):</b><br>
3次元的な奥ゆきの歪みを疑似再現します。（初期値: 0.0）</p>
<p><b>■ 上下反転 (flipud: 0.0〜1.0):</b><br>
上下をひっくり返す確率です。文字や正横向きが決まっている物体の場合は 0 にしてください。（初期値: 0.0）</p>
<p><b>■ 左右反転 (fliplr: 0.0〜1.0):</b><br>
左右を反転させる確率です。鏡映しでも同じ対象の場合は 0.5 程度が有効です。（初期値: 0.5）</p>

<h3 style="color:#c3e88d;">推論・自動アノテーション設定</h3>
<p><b>■ 信頼度閾値 (Conf):</b><br>
AIが「自信がある」と判断する基準です。0.4〜0.5 程度が使いやすい設定です。</p>
"""
        dlg = QDialog(self)
        dlg.setWindowTitle("設定ヘルプ")
        dlg.setMinimumSize(550, 650)
        lyt = QVBoxLayout(dlg)
        
        area = QScrollArea()
        area.setWidgetResizable(True)
        lbl = QLabel(help_msg)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setContentsMargins(15, 15, 15, 15)
        area.setWidget(lbl)
        
        lyt.addWidget(area)
        btn = QPushButton("了解")
        btn.clicked.connect(dlg.accept)
        lyt.addWidget(btn)
        
        dlg.exec()

    def _create_shortcut(self):
        """デスクトップに実行ショートカット (YOLOマネージャー) を作成する"""
        py_path = self.python_edit.text().strip()
        res = operations.create_desktop_shortcut(py_path)
        if res.get("success"):
            QMessageBox.information(
                self,
                "ショートカット作成完了",
                f"{res.get('message')}\n\n作成先:\n{res.get('path')}",
            )
        else:
            QMessageBox.warning(
                self,
                "作成失敗",
                f"ショートカットの作成に失敗しました:\n{res.get('message', '')}",
            )
