# -*- coding: utf-8 -*-
"""YOLO Manager v2.0 - エントリーポイント"""
# EXE化する場合は、直下の `build_app.bat` を実行してください。

import sys
import traceback
from pathlib import Path

# アプリフォルダをモジュール検索パスに追加
sys.path.insert(0, str(Path(__file__).parent))

import argparse
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

DEBUG_LOG = Path(__file__).parent.parent / "yolo_manager_trace.log"

def _trace(msg: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass

from main_window import MainWindow
from styles import DARK_THEME_QSS


def main():
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    _trace("main:start")
    parser = argparse.ArgumentParser(description="YOLOv8 Manager")
    parser.add_argument("--labelImg", action="store_true", help="Launch bundled labelImg")
    args, unknown = parser.parse_known_args()
    _trace(f"main:parsed args={args} unknown={unknown}")

    if args.labelImg:
        import importlib.util
        # Directly load the script file to avoid conflict with the 'labelImg' directory
        script_path = Path(__file__).parent / "labelimg_src" / "labelImg.py"
        
        # Add labelimg_src to sys.path so its internal imports (like from labelimg_libs) work
        sys.path.insert(0, str(script_path.parent))
        
        spec = importlib.util.spec_from_file_location("labelImg_mod", str(script_path))
        if spec is None or spec.loader is None:
            print(f"Error: Could not load labelImg from {script_path}")
            sys.exit(1)
            
        labelImg_mod = importlib.util.module_from_spec(spec)
        
        # labelImg uses sys.argv for its own argument parsing.
        # We need to remove the --labelImg flag from sys.argv.
        sys.argv = [sys.argv[0]] + unknown
        
        spec.loader.exec_module(labelImg_mod)
        sys.exit(labelImg_mod.main())

    app = QApplication(sys.argv)
    _trace("main:created QApplication")
    app.setStyleSheet(DARK_THEME_QSS)
    app.setApplicationName("YOLO Manager")

    window = MainWindow()
    _trace("main:created MainWindow")
    window.show()
    _trace("main:window shown")
    try:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geom = screen.availableGeometry()
            frame = window.frameGeometry()
            frame.moveCenter(geom.center())
            window.move(frame.topLeft())
        window.raise_()
        window.activateWindow()
    except Exception:
        pass

    exit_code = app.exec()
    _trace(f"main:app.exec returned {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error_log = Path(__file__).parent.parent / "yolo_manager_error.log"
        with open(error_log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"YOLO Manager の起動に失敗しました。\nログ: {error_log}",
                "YOLO Manager",
                0x10,
            )
        except Exception:
            pass
        sys.exit(1)
