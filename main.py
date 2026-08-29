# -*- coding: utf-8 -*-
"""YOLO Manager v2.0 - エントリーポイント"""
# EXE化する場合は、直下の `build_app.bat` を実行してください。

import sys
import traceback
from pathlib import Path

# modules フォルダをモジュール検索パスに追加
MODULES_DIR = Path(__file__).parent / "modules"
sys.path.insert(0, str(MODULES_DIR))

import argparse
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

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

    parser = argparse.ArgumentParser(description="YOLO Manager")
    parser.add_argument("--labelImg", action="store_true", help="Launch bundled labelImg")
    args, unknown = parser.parse_known_args()

    if args.labelImg:
        import importlib.util
        # Directly load the script file to avoid conflict with the 'labelImg' directory
        script_path = MODULES_DIR / "labelimg_src" / "labelImg.py"
        
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
    app.setStyleSheet(DARK_THEME_QSS)
    app.setApplicationName("YOLO Manager")

    window = MainWindow()
    window.show()
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
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error_log = Path(__file__).parent / "yolo_manager_error.log"
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
