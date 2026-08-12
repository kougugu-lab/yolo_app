# -*- coding: utf-8 -*-
"""config.json の読み書き・デフォルト値管理"""

import sys
import json
from pathlib import Path

# CONFIG_PATH の決定
if getattr(sys, 'frozen', False):
    # PyInstaller でビルドされた実行ファイル (.exe) の場合
    # 実行ファイル本体と同じフォルダに config.json を置く
    CONFIG_PATH = Path(sys.executable).parent / "config.json"
else:
    # 通常のスクリプト実行の場合
    # スクリプトの親フォルダ（modules/）に置く
    CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULTS = {
    # パス設定
    "python_path": "",
    "dataset_dir": "",
    "inference_model_path": "", # 推論 / NCNN 変換用モデル (.pt)
    "autolabel_model_path": "", # オートラベル用モデル (.pt)
    # データ分割
    "train_count": 80,
    "val_count": 20,
    # ハイパーパラメータ
    "epochs": 100,
    "batch": -1,
    "imgsz": 640,
    "workers": 4,
    "base_model": "n",          # n / s / m / l / x
    "yolo_version": "11",       # 8 / 11
    # 推論設定
    "conf_threshold": 0.25,
    # クラス名 (カンマ区切りで保存)
    "class_names": "",
    # オーギュメント (データ拡張) 設定
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "degrees": 0.0,
    "translate": 0.1,
    "scale": 0.5,
    "shear": 0.0,
    "perspective": 0.0,
    "flipud": 0.0,
    "fliplr": 0.5,
}


def load() -> dict:
    """config.json から設定を読み込む。存在しなければデフォルトを返す。"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = {**DEFAULTS, **saved}
            return merged
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULTS)
    return dict(DEFAULTS)


def save(config: dict) -> None:
    """設定を config.json に保存する。"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def reset_params(config: dict) -> dict:
    """パス以外のパラメータのみデフォルトに戻す。"""
    path_keys = ("python_path", "dataset_dir", "inference_model_path", "autolabel_model_path")
    reset = dict(DEFAULTS)
    for k in path_keys:
        reset[k] = config.get(k, "")
    reset["class_names"] = config.get("class_names", "")
    return reset
