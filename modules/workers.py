# -*- coding: utf-8 -*-
"""QThread ワーカー群 - 重い処理をバックグラウンドで実行"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


def _read_process_output_realtime(read_pipe, process, log_signal, is_cancelled_fn, encoding="utf-8"):
    """\\r (tqdm 進捗など) と \\n の両方に対応したバイナリリアルタイム読み込みルーチン"""
    if not read_pipe:
        return
    buffer = bytearray()
    while True:
        if is_cancelled_fn():
            return
        b = read_pipe.read(1)
        if not b:
            if process.poll() is not None:
                break
            continue
        if b in (b'\r', b'\n'):
            if buffer:
                try:
                    line = buffer.decode(encoding, errors="replace").strip()
                except Exception:
                    line = buffer.decode("cp932", errors="replace").strip()
                buffer.clear()
                if line:
                    log_signal.emit(line)
        else:
            buffer.extend(b)
            if len(buffer) > 2048:
                try:
                    line = buffer.decode(encoding, errors="replace").strip()
                except Exception:
                    line = buffer.decode("cp932", errors="replace").strip()
                buffer.clear()
                if line:
                    log_signal.emit(line)

    if buffer:
        try:
            line = buffer.decode(encoding, errors="replace").strip()
        except Exception:
            line = buffer.decode("cp932", errors="replace").strip()
        if line:
            log_signal.emit(line)


class SubprocessWorker(QThread):
    """任意のコマンドを subprocess で実行し、stdout/stderr をリアルタイム配信。"""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # (成功フラグ, メッセージ)
    progress_signal = pyqtSignal(int)  # 0-100

    def __init__(self, command: list, cwd: str = None, parent=None, stdout_log: bool = True):
        super().__init__(parent)
        self.command = command
        self.cwd = cwd
        self.stdout_log = stdout_log
        self._is_cancelled = False

    def run(self):
        try:
            if self.stdout_log:
                self.log_signal.emit(f"[CMD] {' '.join(self.command)}")
            self.progress_signal.emit(0)
            encoding = "utf-8"
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"

            if self.stdout_log:
                stdout_target = subprocess.PIPE
                stderr_target = subprocess.STDOUT  # 統合
            else:
                stdout_target = subprocess.DEVNULL # 標準出力は捨てる
                stderr_target = subprocess.PIPE    # エラー出力のみ

            self._process = subprocess.Popen(
                self.command,
                stdout=stdout_target,
                stderr=stderr_target,
                cwd=self.cwd,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            
            # 出力読み取りルーチン (\\r と \\n 両対応のバイナリ即時配信)
            read_pipe = self._process.stdout if self.stdout_log else self._process.stderr
            _read_process_output_realtime(read_pipe, self._process, self.log_signal, lambda: self._is_cancelled, encoding=encoding)
                    
            self._process.wait()
            if self._is_cancelled:
                self.finished_signal.emit(False, "キャンセルされました")
            elif self._process.returncode == 0:
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, "正常に完了しました")
            else:
                self.finished_signal.emit(False, f"終了コード: {self._process.returncode}")
        except Exception as e:
            self.finished_signal.emit(False, f"エラー: {e}")

    def cancel(self):
        self._is_cancelled = True
        if hasattr(self, "_process") and self._process and self._process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._process.terminate()
            except Exception:
                pass



class LabelImgWorker(QThread):
    """labelImg (PyQt5 GUI) を独立プロセスとして起動し終了を監視するワーカー。
    CREATE_NO_WINDOW を使わずウィンドウが正常に表示されるようにする。
    """

    finished_signal = pyqtSignal(bool, str)  # (成功フラグ, メッセージ)

    def __init__(self, command: list, parent=None):
        super().__init__(parent)
        self.command = command
        self._process = None

    def run(self):
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            # labelImg は PyQt5 ベースの GUI アプリのため、CREATE_NO_WINDOW を
            # 指定してはいけない（ウィンドウが非表示になり 0xC0000409 クラッシュが発生）
            self._process = subprocess.Popen(
                self.command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            self._process.wait()
            rc = self._process.returncode
            if rc == 0:
                self.finished_signal.emit(True, "正常に完了しました")
            else:
                self.finished_signal.emit(False, f"終了コード: {rc}")
        except Exception as e:
            self.finished_signal.emit(False, f"エラー: {e}")

    def cancel(self):
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass


class ScriptWorker(QThread):
    """Python スクリプト文字列を仮想環境で実行するワーカー。
    operations.py の build_*_script() と連携する。"""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)

    def __init__(self, python_path: str, script_text: str, parent=None):
        super().__init__(parent)
        self.python_path = python_path
        self.script_text = script_text
        self._is_cancelled = False

    def run(self):
        tmp_file = None
        try:
            # 一時ファイルにスクリプトを書き出して実行
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            )
            tmp_file.write(self.script_text)
            tmp_file.close()

            self.progress_signal.emit(0)

            encoding = "utf-8"
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"

            self._process = subprocess.Popen(
                [self.python_path, "-u", tmp_file.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            _read_process_output_realtime(self._process.stdout, self._process, self.log_signal, lambda: self._is_cancelled, encoding=encoding)
            self._process.wait()
            if self._is_cancelled:
                self.finished_signal.emit(False, "キャンセルされました")
            elif self._process.returncode == 0:
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, "正常に完了しました")
            else:
                self.finished_signal.emit(False, f"終了コード: {self._process.returncode}")
        except Exception as e:
            self.finished_signal.emit(False, f"エラー: {e}")
        finally:
            if tmp_file:
                try:
                    Path(tmp_file.name).unlink(missing_ok=True)
                except OSError:
                    pass

    def cancel(self):
        self._is_cancelled = True
        if hasattr(self, "_process") and self._process and self._process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._process.terminate()
            except Exception:
                pass


class InstallWorker(QThread):
    """不足パッケージを pip install するワーカー。"""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)

    def __init__(self, python_path: str, packages: list, parent=None):
        super().__init__(parent)
        self.python_path = python_path
        self.packages = packages

    def run(self):
        total = len(self.packages)
        for i, pkg in enumerate(self.packages):
            self.log_signal.emit(f"[INSTALL] {pkg} をインストール中... ({i+1}/{total})")
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                process = subprocess.Popen(
                    [self.python_path, "-m", "pip", "install", pkg],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                for line in iter(process.stdout.readline, ""):
                    self.log_signal.emit(line.rstrip())
                process.wait()
                if process.returncode != 0:
                    self.finished_signal.emit(False, f"{pkg} のインストールに失敗しました")
                    return
            except Exception as e:
                self.finished_signal.emit(False, f"エラー: {e}")
                return
            self.progress_signal.emit(int((i + 1) / total * 100))
        self.finished_signal.emit(True, "全パッケージのインストールが完了しました")


def check_packages(python_path: str, packages: list) -> list:
    """指定された Python 環境でのパッケージ有無をチェック。
    不足しているパッケージ名のリストを返す。"""
    missing = []
    for pkg in packages:
        import_name = pkg
        # パッケージ名とインポート名の対応
        name_map = {
            "ultralytics": "ultralytics",
            "pandas": "pandas",
            "openpyxl": "openpyxl",
            "labelImg": "labelImg",
            "PyQt6": "PyQt6",
            "PyYAML": "yaml",
        }
        imp = name_map.get(pkg, pkg)
        try:
            result = subprocess.run(
                [python_path, "-c", f"import {imp}"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if result.returncode != 0:
                missing.append(pkg)
        except Exception:
            missing.append(pkg)
    return missing


class CopyWorker(QThread):
    """画像分割コピーをバックグラウンド実行し進捗を通知するワーカー"""

    progress_signal = pyqtSignal(int, int, str)  # (copied_count, total_count, filename)
    finished_signal = pyqtSignal(bool, dict, str)  # (success, result_dict, error_msg)

    def __init__(self, source_dir: str, dataset_dir: str, train_count: int, val_count: int, parent=None):
        super().__init__(parent)
        self.source_dir = source_dir
        self.dataset_dir = dataset_dir
        self.train_count = train_count
        self.val_count = val_count
        self._is_cancelled = False

    def run(self):
        try:
            import operations

            def on_progress(current, total, filename):
                self.progress_signal.emit(current, total, filename)

            def is_cancel():
                return self._is_cancelled

            result = operations.split_copy(
                self.source_dir,
                self.dataset_dir,
                self.train_count,
                self.val_count,
                progress_callback=on_progress,
                cancel_check=is_cancel,
            )
            if self._is_cancelled:
                self.finished_signal.emit(False, {}, "キャンセルされました")
            else:
                self.finished_signal.emit(True, result, "")
        except Exception as e:
            self.finished_signal.emit(False, {}, str(e))

    def cancel(self):
        self._is_cancelled = True
