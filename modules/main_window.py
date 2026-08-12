import os
import re
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

import config_manager
import operations
from help_dialog import HelpDialog
from settings_dialog import SettingsDialog
from workers import ScriptWorker, SubprocessWorker, LabelImgWorker


class LabelListDialog(QDialog):
    """4.3 ラベル一覧確認ダイアログ (train/val識別表示 & Excel出力)"""

    def __init__(self, dataset_dir: str, parent=None):
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self.setWindowTitle("アノテーション・ラベル一覧確認 (train/val)")
        self.setMinimumSize(800, 500)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info_lbl = QLabel(f"対象データセット: {self.dataset_dir}")
        info_lbl.setStyleSheet("font-weight: bold; color: #82aaff;")
        layout.addWidget(info_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["データ種別", "画像ファイル名", "アノテーション", "ラベル数", "検出クラス"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()

        excel_btn = QPushButton("  Excel ファイルを出力")
        excel_btn.clicked.connect(self._export_excel)
        btn_row.addWidget(excel_btn)

        btn_row.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.setProperty("accent", True)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _export_excel(self):
        try:
            xlsx_path = operations.export_label_list_excel(str(self.dataset_dir))
            QMessageBox.information(
                self,
                "Excel出力完了",
                f"dataset フォルダ内にラベル一覧を出力しました:\n\n{xlsx_path}",
            )
            os.startfile(xlsx_path)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"Excel出力に失敗しました: {e}")

    def _load_data(self):
        if not self.dataset_dir.exists():
            return

        classes_map = {}
        cls_file = self.dataset_dir / "classes.txt"
        if cls_file.exists():
            lines = cls_file.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines):
                if line.strip():
                    classes_map[idx] = line.strip()

        rows = []
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")

        for split in ["train", "val"]:
            split_dir = self.dataset_dir / split
            if not split_dir.exists():
                continue

            images = [p for p in split_dir.iterdir() if p.suffix.lower() in exts]
            for img in images:
                txt_file = split_dir / (img.stem + ".txt")
                has_txt = "あり" if txt_file.exists() else "なし"
                count = 0
                detected_classes = []

                if txt_file.exists():
                    txt_lines = txt_file.read_text(encoding="utf-8").splitlines()
                    for line in txt_lines:
                        parts = line.strip().split()
                        if parts:
                            count += 1
                            try:
                                c_id = int(parts[0])
                                c_name = classes_map.get(c_id, f"ID:{c_id}")
                                if c_name not in detected_classes:
                                    detected_classes.append(c_name)
                            except ValueError:
                                pass

                cls_str = ", ".join(detected_classes) if detected_classes else "-"
                rows.append((split, img.name, has_txt, str(count), cls_str))

        self.table.setRowCount(len(rows))
        for row_idx, data in enumerate(rows):
            for col_idx, text in enumerate(data):
                item = QTableWidgetItem(text)
                if col_idx == 0:
                    if text == "train":
                        item.setForeground(Qt.GlobalColor.cyan)
                    else:
                        item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(row_idx, col_idx, item)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = config_manager.load()
        self._worker = None
        self._last_log_was_progress = False
        self.setWindowTitle("YOLO Manager")
        self.setMinimumSize(1020, 640)
        self.resize(1100, 750)
        self._build_ui()

    # ==================================================================
    # UI 構築
    # ==================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---------- 左パネル ----------
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        title = QLabel("YOLO Manager")
        title.setObjectName("headerLabel")
        left_layout.addWidget(title)

        # 設定 + ヘルプ ボタン行
        top_row = QHBoxLayout()
        settings_btn = QPushButton("  設定")
        settings_btn.clicked.connect(self._open_settings)
        top_row.addWidget(settings_btn)
        help_btn = QPushButton("  ヘルプ")
        help_btn.clicked.connect(self._open_help)
        top_row.addWidget(help_btn)
        left_layout.addLayout(top_row)

        # --- ステップボタン群 ---
        steps_group = QGroupBox("操作ステップ")
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(5)

        self.step_buttons = []
        step_defs = [
            ("1. データセット準備 (フォルダ作成 & 画像コピー)", self._step_prepare_dataset),
            ("2. クラス名設定",                self._step_set_labels),
            ("3. 自動アノテーション (モデルがある場合のみ)", self._step_auto_label),
        ]
        for text, slot in step_defs:
            btn = QPushButton(f"  {text}")
            btn.setProperty("step", True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            steps_layout.addWidget(btn)
            self.step_buttons.append(btn)

        # 4. アノテーション (Train/Val/一覧 横並び)
        anno_label = QLabel("  4. アノテーション & 確認")
        anno_label.setStyleSheet("margin-top: 5px; font-weight: bold;")
        steps_layout.addWidget(anno_label)
        
        anno_row = QHBoxLayout()
        train_btn = QPushButton("4.1 学習用")
        train_btn.setProperty("step", True)
        train_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        train_btn.clicked.connect(self._step_annotate_train)
        anno_row.addWidget(train_btn)
        
        val_btn = QPushButton("4.2 検証用")
        val_btn.setProperty("step", True)
        val_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        val_btn.clicked.connect(self._step_annotate_val)
        anno_row.addWidget(val_btn)

        list_btn = QPushButton("4.3 ラベル一覧")
        list_btn.setProperty("step", True)
        list_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        list_btn.clicked.connect(self._step_show_label_list)
        anno_row.addWidget(list_btn)
        
        steps_layout.addLayout(anno_row)
        self.step_buttons.extend([train_btn, val_btn, list_btn])

        # 残りのステップ
        rest_defs = [
            ("5. 学習実行",                    self._step_train),
            ("6. 推論",                        self._step_inference_excel),
        ]
        for text, slot in rest_defs:
            btn = QPushButton(f"  {text}")
            btn.setProperty("step", True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            steps_layout.addWidget(btn)
            self.step_buttons.append(btn)

        steps_group.setLayout(steps_layout)
        left_layout.addWidget(steps_group)

        # プログレスバー
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        left_layout.addWidget(self.progress)

        left_layout.addStretch()

        # ---------- 右パネル (ログ) ----------
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        log_label = QLabel("ログ")
        log_label.setObjectName("sectionLabel")
        right_layout.addWidget(log_label)

        self.log_area = QTextEdit()
        self.log_area.setObjectName("logArea")
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)

        clear_btn = QPushButton("ログクリア")
        clear_btn.clicked.connect(self.log_area.clear)
        right_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)

    # ==================================================================
    # ログ
    # ==================================================================
    def _log(self, text: str):
        clean_text = text.rstrip("\r\n")
        if not clean_text:
            return

        # ANSI エスケープコード (エクスポート時のカラー制御文字等) を除去
        clean_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', clean_text)
        clean_text = re.sub(r'\[[0-9]+;?[0-9]*m', '', clean_text)

        # NCNN / PNNX エクスポート等のデバッグ・ノイズログをフィルタリング
        ncnn_ignore_keywords = [
            "inline module", "pnnx", "ncnnparam", "ncnnbin", "ncnnpy",
            "fp16 =", "optlevel =", "device =", "inputshape", "customop =",
            "moduleop =", "#############", "----------------", "Predict:",
            "Validate:", "Visualize:", "get inputshape", "Ultralytics",
            "summary (fused)", "PyTorch:", "NCNN:", "Export complete",
            "Results saved to", "NCNNモデルへ変換中", "NCNNモデルの変換が完了しました"
        ]
        if any(kw in clean_text for kw in ncnn_ignore_keywords):
            return

        # 完了メッセージ・要約ログ・エラーログ・ヘッダーなどは絶対に進捗表示とみなさない
        non_progress_keywords = [
            "Excel", "結果画像", "処理画像数", "Saved", "Total", "[OK]", "[NG]",
            "[CMD]", "[SCRIPT]", "完了", "モデル", "対象", "結果ファイル", "保存先",
            "=", "枚を処理中", "完了しました", "アノテーション"
        ]

        if any(kw in clean_text for kw in non_progress_keywords):
            is_progress = False
        else:
            progress_keywords = ["%", "it/s", "s/it", "Epoch", "Inference", "推論進捗", "train:", "val:", "Predicting"]
            is_progress = any(kw in clean_text for kw in progress_keywords)

        cursor = self.log_area.textCursor()

        # 直前行が進捗ログで今回も進捗ログの場合のみ、最末尾の1行ブロックを選択して置き換え
        if is_progress and self._last_log_was_progress:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(clean_text)
        else:
            self.log_area.append(clean_text)

        self._last_log_was_progress = is_progress

        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _log_header(self, step_name: str):
        self._last_log_was_progress = False
        self._log(f"\n{'='*40}")
        self._log(f"  {step_name}")
        self._log(f"{'='*40}")

    def _log_ok(self, msg: str):
        self._last_log_was_progress = False
        self._log(f"  [OK] {msg}")

    def _log_err(self, msg: str):
        self._last_log_was_progress = False
        self._log(f"  [NG] {msg}")

    def _log_info(self, msg: str):
        self._last_log_was_progress = False
        self._log(f"  {msg}")

    # ==================================================================
    # 設定 / ヘルプ
    # ==================================================================
    def _open_settings(self):
        dlg = SettingsDialog(self.config, log_callback=self._log, parent=self)
        if dlg.exec():
            self.config = config_manager.load()
            self._log_ok("設定を保存しました")

    def _open_help(self):
        dlg = HelpDialog(parent=self)
        dlg.exec()

    # ==================================================================
    # パス検証
    # ==================================================================
    def _require(self, *keys) -> bool:
        labels = {
            "python_path": "Python 実行パス (設定画面)",
            "dataset_dir": "データセット保存先 (設定画面)",
            "inference_model_path": "推論用モデル .pt (設定画面)",
            "autolabel_model_path": "自動アノテーション用モデル .pt (設定画面)",
        }
        missing = []
        for k in keys:
            val = self.config.get(k, "")
            if not val:
                missing.append(labels.get(k, k))
        if missing:
            QMessageBox.warning(
                self, "パス未設定",
                "以下の設定が必要です:\n" + "\n".join(f"  - {m}" for m in missing)
                + "\n\n設定画面で指定してください。",
            )
            return False
        return True

    # ==================================================================
    # ワーカー管理
    # ==================================================================
    def _set_busy(self, busy: bool):
        self.progress.setVisible(busy)
        if busy:
            self.progress.setValue(0)
        for btn in self.step_buttons:
            btn.setEnabled(not busy)

    def _start_worker(self, worker):
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "実行中", "別の処理が実行中です。完了をお待ちください。")
            return
        self._worker = worker
        worker.log_signal.connect(self._log)
        worker.progress_signal.connect(self.progress.setValue)
        worker.finished_signal.connect(self._on_worker_done)
        self._set_busy(True)
        worker.start()

    def _on_worker_done(self, success: bool, message: str):
        self._set_busy(False)
        if success:
            self._log_ok(message)
        else:
            self._log_err(message)

    # ==================================================================
    # YAML 自動生成ヘルパー
    # ==================================================================
    def _auto_create_yaml(self):
        class_text = self.config.get("class_names", "")
        if not class_text:
            return
        names = [n.strip() for n in class_text.split(",") if n.strip()]
        if names:
            path = operations.create_yaml(self.config["dataset_dir"], names)
            self._log_info(f"data.yaml 自動生成: {path}")

    # ==================================================================
    # Step 1: データセット準備
    # ==================================================================
    def _step_prepare_dataset(self):
        if not self._require("dataset_dir"):
            return
        
        self._log_header("データセット準備")
        
        # 1. フォルダ生成
        try:
            created = operations.generate_folders(self.config["dataset_dir"])
            self._log_ok(f"フォルダ作成完了 ({len(created)} フォルダ: train, val)")
        except Exception as e:
            self._log_err(f"フォルダ作成に失敗しました: {e}")
            return

        # 2. 画像フォルダ選択ダイアログ (キャンセルでフォルダ作成のみ)
        source_dir = QFileDialog.getExistingDirectory(
            self,
            "コピー元の元画像フォルダを選択してください (キャンセルでフォルダ作成のみ)",
            self.config.get("dataset_dir", "")
        )

        if not source_dir:
            self._log_info("画像フォルダの選択がキャンセルされたため、フォルダ作成のみ完了しました。")
            return

        # 画像コピー処理
        self._log_info(f"元画像フォルダ: {source_dir}")
        self._log_info("画像を分割コピー中...")
        try:
            copied = operations.split_copy(
                source_dir,
                self.config["dataset_dir"],
                self.config.get("train_count", 80),
                self.config.get("val_count", 20),
            )
            self._log_ok(f"計 {copied['total']} 枚のコピーが完了しました (学習:{copied['train']}, 検証:{copied['val']})")
        except Exception as e:
            self._log_err(f"コピー失敗: {e}")
            return

        self._log_ok("準備完了！ 次に「2. クラス名設定」を行ってください。")

    # ==================================================================
    # Step 2: クラス名設定
    # ==================================================================
    def _step_set_labels(self):
        if not self._require("dataset_dir"):
            return
        self._log_header("クラス名設定")

        try:
            current = self.config.get("class_names", "")
            if current:
                initial_text = "\n".join(n.strip() for n in current.split(",") if n.strip())
            else:
                cls_file = Path(self.config["dataset_dir"]) / "classes.txt"
                initial_text = operations.read_text_safe(cls_file).strip()

            dlg = _MultiLineInputDialog(
                title="クラス名設定",
                label="クラス名を1行に1つずつ入力 (classes.txt 形式):",
                text=initial_text,
                parent=self,
            )
            if dlg.exec():
                text = dlg.get_text().strip()
                if text:
                    names = [n.strip() for n in text.splitlines() if n.strip()]
                    path = operations.save_classes(self.config["dataset_dir"], names)
                    self.config["class_names"] = ",".join(names)
                    config_manager.save(self.config)
                    self._log_ok(f"{len(names)} クラスを保存 → classes.txt (ルート / train / val)")
                    for i, n in enumerate(names):
                        self._log_info(f"  {i}: {n}")
                else:
                    self._log_info("入力が空です")
            else:
                self._log_info("キャンセルされました")
        except Exception as e:
            self._log_err(f"クラス名設定処理中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"クラス名設定処理でエラーが発生しました:\n{e}")

    # ==================================================================
    # Step 4: アノテーション (Train / Val)
    # ==================================================================
    def _step_annotate_train(self):
        self._launch_labelimg("train")

    def _step_annotate_val(self):
        self._launch_labelimg("val")

    def _step_show_label_list(self):
        """4.3 ラベル一覧確認 (ダイアログ表示 & dataset フォルダへの Excel 出力)"""
        if not self._require("dataset_dir"):
            return
        self._log_header("ラベル一覧確認")
        dataset_dir = self.config["dataset_dir"]

        try:
            xlsx_path = operations.export_label_list_excel(dataset_dir)
            self._log_ok(f"dataset フォルダ内にラベル一覧を出力しました: {xlsx_path}")
        except Exception as e:
            self._log_err(f"Excel出力失敗: {e}")

        dlg = LabelListDialog(dataset_dir, parent=self)
        dlg.exec()

    def _launch_labelimg(self, split: str):
        if not self._require("python_path", "dataset_dir"):
            return
        self._log_header(f"アノテーション ({split})")

        dataset = Path(self.config["dataset_dir"])
        image_dir = dataset / split
        classes_file = dataset / "classes.txt"

        if not image_dir.exists():
            self._log_err(f"{split} フォルダが見つかりません: {image_dir}")
            return
        if not classes_file.exists():
            self._log_err("classes.txt が見つかりません。先に「クラス名設定」を実行してください。")
            return

        # labelImg は PyQt5 を使用しているため、PyQt6 の main.py とは
        # 別プロセスとして直接 labelImg.py を実行する必要がある。
        # 同一プロセス内で両方のバインディングをロードするとクラッシュする。
        labelimg_script = Path(__file__).parent / "labelimg_src" / "labelImg.py"
        py_exe = self.config.get("python_path") or sys.executable
        cmd = [
            str(py_exe),
            str(labelimg_script),
            str(image_dir),
            str(classes_file),
            str(image_dir),
        ]
        self._log_info(f"  対象フォルダ: {image_dir}")
        self._log_info(f"  クラスファイル: {classes_file}")
        try:
            # labelImg は GUI アプリなので stdout_log=False, CREATE_NO_WINDOW は使わない
            self.worker = LabelImgWorker(cmd)
            self.worker.finished_signal.connect(
                lambda ok, msg: self._on_labelimg_done(ok, msg, split)
            )
            self.worker.start()
        except Exception as e:
            self._log_err(f"labelImg 起動失敗: {e}")

    def _on_labelimg_done(self, success: bool, msg: str, split: str):
        if success:
            self._log_ok(f"labelImg を終了しました [{split}]")
        else:
            self._log_err(f"labelImg が異常終了しました: {msg}")
            self._log_info("  対処法: エラーログを確認してください。")

    # ==================================================================
    # Step 3: 自動アノテーション
    # ==================================================================
    def _step_auto_label(self):
        if not self._require("python_path", "dataset_dir", "autolabel_model_path"):
            return

        # 事前確認ダイアログの表示
        reply = QMessageBox.question(
            self,
            "ラベルクリアの確認",
            "既存のアノテーションラベル (.txt ファイル) をクリアして自動アノテーションを実行しますか？\n\n"
            "※ train / val フォルダ内の既存のアノテーションデータが全消去されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            self._log_header("自動アノテーション")
            self._log_info("自動アノテーションがキャンセルされました。")
            return

        self._log_header("自動アノテーション")

        # 既存ラベルのクリア実行
        cleared_count = operations.clear_annotation_labels(self.config["dataset_dir"])
        self._log_ok(f"既存のアノテーションラベル ({cleared_count} 件) をクリアしました")

        model_path = self.config["autolabel_model_path"]
        self._log_info(f"モデル: {model_path}")
        self._log_info(f"対象 : {self.config['dataset_dir']}")
        self._log_info(f"Conf : {self.config.get('conf_threshold', 0.25)}")
        self._log_info("処理開始...")

        class_text = self.config.get("class_names", "")
        class_names = [n.strip() for n in class_text.split(",") if n.strip()] if class_text else []

        script = operations.build_autolabel_script(
            model_path,
            self.config["dataset_dir"],
            self.config.get("conf_threshold", 0.25),
            class_names,
        )
        worker = ScriptWorker(self.config["python_path"], script, parent=self)
        worker.finished_signal.connect(self._on_autolabel_done)
        self._start_worker(worker)

    def _on_autolabel_done(self, success: bool, message: str):
        if success:
            xlsx_path = Path(self.config["dataset_dir"]) / "autolabel_result.xlsx"
            if xlsx_path.exists():
                self._log_info(f"結果ファイルを開きます: {xlsx_path}")
                os.startfile(str(xlsx_path))

    # ==================================================================
    # Step 5: 学習実行
    # ==================================================================
    def _step_train(self):
        if not self._require("python_path", "dataset_dir"):
            return
        self._log_header("学習実行")

        # 学習直前に YAML を自動生成・更新
        self._auto_create_yaml()

        data_yaml = Path(self.config["dataset_dir"]) / "data.yaml"
        if not data_yaml.exists():
            self._log_err("data.yaml が見つかりません。アノテーションまたは自動アノテーションを先に実行してください。")
            return

        # キャッシュ削除
        deleted = operations.delete_cache_files(self.config["dataset_dir"])
        if deleted > 0:
            self._log_info(f"キャッシュファイルを {deleted} 件削除しました")

        self._log_info(f"data.yaml : {data_yaml}")
        base_model = self.config.get('base_model', 'n')
        yolo_ver = self.config.get('yolo_version', '11')
        model_pfx = "yolo11" if yolo_ver == "11" else "yolov8"
        
        self._log_info(f"model     : {model_pfx}{base_model}.pt")
        self._log_info("学習開始...")

        script = operations.build_train_script(
            str(data_yaml),
            self.config.get("epochs", 100),
            self.config.get("batch", 4),
            self.config.get("imgsz", 640),
            self.config.get("workers", 4),
            base_model,
            yolo_ver,
            aug_params=self.config,
        )
        worker = ScriptWorker(self.config["python_path"], script, parent=self)
        worker.finished_signal.connect(self._on_train_done)
        self._start_worker(worker)

    def _on_train_done(self, success: bool, message: str):
        if not success:
            return

        runs_dir = Path.cwd() / "runs" / "detect"
        if not runs_dir.exists():
            return

        sub = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not sub:
            return

        latest_run = sub[0]
        self._log_info(f"結果フォルダ: {latest_run}")

        # best.pt を探す
        best_pt = latest_run / "weights" / "best.pt"
        if best_pt.exists():
            best_path = str(best_pt).replace("\\", "/")
            self.config["inference_model_path"] = best_path
            config_manager.save(self.config)
            self._log_ok(f"「推論用モデル」を自動更新しました: {best_path}")

            # NCNN モデルの自動変換を開始
            self._log_header("NCNNモデル自動生成")
            self._log_info(f"対象モデル: {best_path}")
            self._log_info("変換処理中...")

            ncnn_script = operations.build_ncnn_export_script(
                best_path,
                self.config.get("imgsz", 640),
            )
            worker = ScriptWorker(self.config["python_path"], ncnn_script, parent=self)
            worker.finished_signal.connect(
                lambda ok, msg: self._on_auto_ncnn_done(ok, msg, latest_run)
            )
            self._start_worker(worker)
        else:
            os.startfile(str(latest_run))

    def _on_auto_ncnn_done(self, success: bool, message: str, latest_run: Path):
        if success:
            self._log_ok("NCNNモデル（ラズパイ向け軽量化モデル）の自動生成が完了しました")
        else:
            self._log_err(f"NCNNモデルの自動生成に失敗しました: {message}")
        os.startfile(str(latest_run))

    # ==================================================================
    # Step 6: 推論
    # ==================================================================
    def _step_inference_excel(self):
        if not self._require("python_path", "inference_model_path"):
            return
        self._log_header("推論 (Excel出力付き)")

        model_path = self.config["inference_model_path"]
        image_dir = QFileDialog.getExistingDirectory(self, "推論対象の画像フォルダを選択")
        if not image_dir:
            self._log_info("キャンセルされました")
            return

        date_str = datetime.now().strftime("%Y%m%d")
        output_xlsx = str(Path(image_dir) / f"推論結果_{date_str}.xlsx")

        self._log_info(f"モデル : {model_path}")
        self._log_info(f"画像   : {image_dir}")
        self._log_info(f"出力   : {output_xlsx}")
        self._log_info("推論開始...")

        script = operations.build_inference_script(
            model_path,
            image_dir,
            self.config.get("conf_threshold", 0.25),
            output_xlsx,
        )
        worker = ScriptWorker(self.config["python_path"], script, parent=self)
        worker.finished_signal.connect(
            lambda ok, msg: self._on_inference_done(ok, msg, output_xlsx)
        )
        self._start_worker(worker)

    def _on_inference_done(self, success: bool, message: str, xlsx_path: str):
        if success:
            self._log_info(f"結果ファイル: {xlsx_path}")
            folder = str(Path(xlsx_path).parent)
            os.startfile(folder)


# ======================================================================
# 複数行テキスト入力ダイアログ
# ======================================================================
class _MultiLineInputDialog(QDialog):
    """classes.txt 形式 (1行1クラス) の入力ダイアログ"""

    def __init__(self, title: str, label: str, text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 320)
        layout = QVBoxLayout(self)

        lbl = QLabel(label)
        layout.addWidget(lbl)

        self._edit = QPlainTextEdit()
        self._edit.setPlainText(text)
        layout.addWidget(self._edit)

        hint = QLabel("(classes.txt をそのままコピペできます)")
        hint.setStyleSheet("color: #888888;")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setProperty("accent", True)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def get_text(self) -> str:
        return self._edit.toPlainText()
