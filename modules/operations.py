import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml


def safe_open_path(target_path: Union[str, Path], is_excel: bool = False) -> Tuple[bool, str]:
    """ファイルまたはフォルダをOS標準のビューア/ファイラーで安全に開く。
    開けない環境やアプリがない場合は例外を出さずに (False, 案内メッセージ) を返す。
    開けた場合は (True, 案内メッセージ) を返す。
    """
    target = Path(target_path)
    if not target.exists():
        return False, f"対象が見つかりません: {target}"

    is_xlsx = is_excel or target.suffix.lower() == ".xlsx"
    target_str = str(target)
    type_name = "Excelファイル" if is_xlsx else ("フォルダ" if target.is_dir() else "ファイル")

    if sys.platform == "win32":
        try:
            os.startfile(target_str)
            return True, f"{type_name}を開きました: {target_str}"
        except Exception:
            return False, f"{type_name}を開くことができない環境のため、オープンを中止しました（ファイルは正常に作成・保存されています: {target_str}）"
    else:
        # Linux / Raspberry Pi / macOS
        if is_xlsx:
            viewers = ["libreoffice", "localc", "gnumeric", "wps", "soffice"]
            has_viewer = any(shutil.which(cmd) for cmd in viewers)
            xdg = shutil.which("xdg-open")

            has_mime = False
            if xdg:
                try:
                    res = subprocess.run(
                        ["xdg-mime", "query", "default", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
                        capture_output=True, text=True, timeout=2
                    )
                    if res.stdout.strip():
                        has_mime = True
                except Exception:
                    pass

            if not has_viewer and not has_mime:
                return False, f"Excelファイルを開くアプリケーション（LibreOffice等）が見つからない環境のため、オープンを中止しました（ファイルは正常に作成・保存されています: {target_str}）"

            opener = xdg or next((v for v in viewers if shutil.which(v)), None)
            if not opener:
                return False, f"Excelファイルを開くアプリケーションが見つからないため、オープンを中止しました（ファイルは正常に作成・保存されています: {target_str}）"

            try:
                subprocess.Popen([opener, target_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Excelファイルを開きます: {target_str}"
            except Exception:
                return False, f"Excelファイルを開くことができなかったため、オープンを中止しました（ファイルは正常に作成・保存されています: {target_str}）"
        else:
            xdg = shutil.which("xdg-open")
            if xdg:
                try:
                    subprocess.Popen([xdg, target_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True, f"{type_name}を開きます: {target_str}"
                except Exception:
                    return False, f"{type_name}を開くことができなかったため、オープンを中止しました（保存先: {target_str}）"
            else:
                return False, f"{type_name}を開くコマンド(xdg-open)がないため、オープンを中止しました（保存先: {target_str}）"


def _safe(path: str) -> str:
    """Windows パスのバックスラッシュをスラッシュに統一。"""
    return str(path).replace("\\", "/")


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")


def get_auto_workers(imgsz: int) -> int:
    """RTX 5060 前提の imgsz に連動した並列数 (workers) 自動決定ロジック。
    - imgsz <= 640  : workers = 4
    - imgsz <= 800  : workers = 2
    - imgsz > 800   : workers = 0 (1024 など)
    """
    if imgsz <= 640:
        return 4
    elif imgsz <= 800:
        return 2
    else:
        return 0



# ---------------------------------------------------------------------------
# 1. データセットフォルダ生成
# ---------------------------------------------------------------------------
def generate_folders(dataset_dir: str) -> List[str]:
    """dataset 配下に train / val フォルダを作成する。"""
    base = Path(dataset_dir)
    folders = [base / "train", base / "val"]
    created = []
    for f in folders:
        f.mkdir(parents=True, exist_ok=True)
        created.append(str(f))
    return created


# ---------------------------------------------------------------------------
# 2. 分割コピー
# ---------------------------------------------------------------------------
def split_copy(
    source_dir: str,
    dataset_dir: str,
    train_count: int,
    val_count: int,
    progress_callback=None,
    cancel_check=None,
) -> dict:
    """元画像からランダム抽出し、train/val フォルダへコピーする。
    画像が指定枚数より少ない場合は、ある分だけ設定比率と同じ比率でコピーする。
    """
    src = Path(source_dir)
    all_images = [
        p for p in src.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not all_images:
        raise ValueError(f"コピー元のフォルダに対象となる画像ファイルが見つかりません: {source_dir}")

    # 必ず整数化（小数点や文字列が渡されても確実に安全にする）
    try:
        train_count = int(round(float(train_count)))
    except (ValueError, TypeError):
        train_count = 80
    try:
        val_count = int(round(float(val_count)))
    except (ValueError, TypeError):
        val_count = 20

    total_avail = len(all_images)
    total_needed = train_count + val_count
    original_train = train_count
    original_val = val_count
    adjusted = False

    if total_avail < total_needed:
        adjusted = True
        if total_needed > 0:
            ratio = train_count / total_needed
        else:
            ratio = 0.8
        actual_train = int(round(total_avail * ratio))
        actual_val = int(total_avail - actual_train)
        if total_avail >= 2:
            if val_count > 0 and actual_val == 0:
                actual_val = 1
                actual_train = total_avail - 1
            elif train_count > 0 and actual_train == 0:
                actual_train = 1
                actual_val = total_avail - 1
        train_count = int(actual_train)
        val_count = int(actual_val)

    random.shuffle(all_images)
    train_files = all_images[:train_count]
    val_files = all_images[train_count : train_count + val_count]

    train_dst = Path(dataset_dir) / "train"
    val_dst = Path(dataset_dir) / "val"
    train_dst.mkdir(parents=True, exist_ok=True)
    val_dst.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    total_files = len(train_files) + len(val_files)

    for f in train_files:
        if cancel_check and cancel_check():
            raise InterruptedError("処理が中断されました")
        shutil.copy2(str(f), str(train_dst / f.name))
        copied_count += 1
        if progress_callback:
            progress_callback(copied_count, total_files, f.name)

    for f in val_files:
        if cancel_check and cancel_check():
            raise InterruptedError("処理が中断されました")
        shutil.copy2(str(f), str(val_dst / f.name))
        copied_count += 1
        if progress_callback:
            progress_callback(copied_count, total_files, f.name)

    return {
        "train": len(train_files),
        "val": len(val_files),
        "total": total_files,
        "adjusted": adjusted,
        "requested_train": original_train,
        "requested_val": original_val,
    }


# ---------------------------------------------------------------------------
# 3. ラベル設定
# ---------------------------------------------------------------------------
def read_text_safe(file_path: Union[str, Path]) -> str:
    """UTF-8, UTF-8-sig, CP932(Shift-JIS) 等のマルチエンコーディング対応で安全にテキストを読み込む。"""
    path = Path(file_path)
    if not path.exists():
        return ""
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, OSError):
            continue
    try:
        return path.read_bytes().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def read_classes_from_dataset(dataset_dir: Union[str, Path]) -> List[str]:
    """dataset_dir 直下に classes.txt があれば読み込んでクラス名リストを返す。存在しない場合は空リスト。"""
    if not dataset_dir:
        return []
    cls_file = Path(dataset_dir) / "classes.txt"
    if cls_file.exists():
        raw = read_text_safe(cls_file)
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return []


def slice_yolo_dataset(
    dataset_dir: Union[str, Path],
    tile_size: int = 640,
    overlap: float = 0.2,
    bg_ratio: float = 0.5,
) -> dict:
    """dataset_dir 配下の train/ と val/ を tile_size×tile_size にスライスし、
    train_sliced/ と val_sliced/ に保存する。元データは一切変更しない。

    Args:
        dataset_dir: データセットのルートディレクトリ
        tile_size:   タイルの一辺のピクセル数
        overlap:     タイル間のオーバーラップ比率 (0.0〜1.0)
        bg_ratio:    背景タイル（アノテーションなし）の保存割合 (0.0〜1.0)

    Returns:
        dict: {
            "train_sliced": str (パス),
            "val_sliced":   str (パス),
            "sliced_yaml":  str (data_sliced.yaml のパス),
            "train_count":  int (trainタイル数),
            "val_count":    int (valタイル数),
        }
    """
    try:
        from PIL import Image as PILImage
    except ImportError:
        raise ImportError("Pillow がインストールされていません。pip install Pillow を実行してください。")

    base = Path(dataset_dir)
    stride = int(tile_size * (1.0 - overlap))
    if stride < 1:
        stride = 1

    counts = {}

    for split in ("train", "val"):
        src_dir = base / split
        dst_dir = base / f"{split}_sliced"

        # 出力先をクリア・再作成
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        dst_dir.mkdir(parents=True)

        tile_count = 0

        if not src_dir.exists():
            counts[split] = 0
            continue

        # classes.txt をコピー
        cls_src = base / "classes.txt"
        if cls_src.exists():
            shutil.copy2(cls_src, dst_dir / "classes.txt")
        else:
            # train フォルダ内の classes.txt も試みる
            cls_in_split = src_dir / "classes.txt"
            if cls_in_split.exists():
                shutil.copy2(cls_in_split, dst_dir / "classes.txt")

        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
        images = [p for p in src_dir.iterdir() if p.suffix.lower() in exts]

        for img_path in images:
            # 対応ラベルファイル読み込み
            txt_path = src_dir / (img_path.stem + ".txt")
            boxes = []  # List[List[float]]: [cls_id, cx, cy, w, h] (正規化)
            if txt_path.exists():
                raw = read_text_safe(txt_path)
                for line in raw.splitlines():
                    parts = line.strip().split()
                    if len(parts) == 5:
                        try:
                            boxes.append([float(p) for p in parts])
                        except ValueError:
                            pass

            try:
                pil_img = PILImage.open(img_path).convert("RGB")
            except Exception:
                continue

            img_w, img_h = pil_img.size

            # タイル座標リスト生成
            xs = list(range(0, max(img_w - tile_size, 0) + 1, stride))
            ys = list(range(0, max(img_h - tile_size, 0) + 1, stride))
            # 末端タイルを確実にカバー
            if not xs or xs[-1] + tile_size < img_w:
                xs.append(max(img_w - tile_size, 0))
            if not ys or ys[-1] + tile_size < img_h:
                ys.append(max(img_h - tile_size, 0))

            tile_idx = 0
            for y0 in ys:
                for x0 in xs:
                    x1 = x0 + tile_size
                    y1 = y0 + tile_size

                    # タイル内に収まるよう調整
                    tx0 = max(x0, 0)
                    ty0 = max(y0, 0)
                    tx1 = min(x1, img_w)
                    ty1 = min(y1, img_h)
                    tw = tx1 - tx0
                    th = ty1 - ty0
                    if tw <= 0 or th <= 0:
                        continue

                    # ボックスをタイル座標に変換
                    tile_boxes = []
                    for box in boxes:
                        cls_id = int(box[0])
                        # 元画像絶対座標 (ピクセル)
                        bcx = box[1] * img_w
                        bcy = box[2] * img_h
                        bw  = box[3] * img_w
                        bh  = box[4] * img_h
                        bx0 = bcx - bw / 2
                        by0 = bcy - bh / 2
                        bx1 = bcx + bw / 2
                        by1 = bcy + bh / 2

                        # タイルとの交差
                        ix0 = max(bx0, tx0)
                        iy0 = max(by0, ty0)
                        ix1 = min(bx1, tx1)
                        iy1 = min(by1, ty1)
                        if ix1 <= ix0 or iy1 <= iy0:
                            continue

                        # 交差面積 ≥ 元ボックス面積の 10% のみ保持
                        inter_area = (ix1 - ix0) * (iy1 - iy0)
                        orig_area  = bw * bh
                        if orig_area <= 0 or inter_area / orig_area < 0.10:
                            continue

                        # タイル内正規化座標
                        new_cx = (ix0 + ix1) / 2 - tx0
                        new_cy = (iy0 + iy1) / 2 - ty0
                        new_w  = ix1 - ix0
                        new_h  = iy1 - iy0
                        tile_boxes.append([
                            cls_id,
                            new_cx / tw,
                            new_cy / th,
                            new_w  / tw,
                            new_h  / th,
                        ])

                    # 保存判定
                    is_foreground = len(tile_boxes) > 0
                    if not is_foreground and random.random() > bg_ratio:
                        continue

                    # タイル画像のクロップと保存
                    cropped = pil_img.crop((tx0, ty0, tx1, ty1))
                    # タイルが tile_size より小さい場合はパディング
                    if tw < tile_size or th < tile_size:
                        padded = PILImage.new("RGB", (tile_size, tile_size), (114, 114, 114))
                        padded.paste(cropped, (0, 0))
                        cropped = padded

                    tile_name = f"{img_path.stem}_tile{tile_idx:04d}"
                    out_img = dst_dir / f"{tile_name}.jpg"
                    out_txt = dst_dir / f"{tile_name}.txt"

                    cropped.save(out_img, "JPEG", quality=95)

                    # ラベルファイル保存
                    with open(out_txt, "w", encoding="utf-8") as f:
                        for tb in tile_boxes:
                            f.write(f"{int(tb[0])} {tb[1]:.6f} {tb[2]:.6f} {tb[3]:.6f} {tb[4]:.6f}\n")

                    tile_idx += 1
                    tile_count += 1

        counts[split] = tile_count

    # data_sliced.yaml を生成
    train_sliced = str(base / "train_sliced")
    val_sliced   = str(base / "val_sliced")
    sliced_yaml  = base / "data_sliced.yaml"

    # クラス名を取得
    class_names_list = read_classes_from_dataset(base)
    nc = len(class_names_list)
    names_yaml = class_names_list if class_names_list else []

    yaml_content = (
        f"train: {train_sliced}\n"
        f"val: {val_sliced}\n"
        f"nc: {nc}\n"
        f"names: {names_yaml}\n"
    )
    sliced_yaml.write_text(yaml_content, encoding="utf-8")

    return {
        "train_sliced": train_sliced,
        "val_sliced":   val_sliced,
        "sliced_yaml":  str(sliced_yaml),
        "train_count":  counts.get("train", 0),
        "val_count":    counts.get("val", 0),
    }


def cleanup_sliced_dataset(dataset_dir: Union[str, Path]) -> None:
    """slice_yolo_dataset() が生成した一時フォルダと YAML を削除する。"""
    base = Path(dataset_dir)
    for name in ("train_sliced", "val_sliced"):
        p = base / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    yaml_p = base / "data_sliced.yaml"
    if yaml_p.exists():
        yaml_p.unlink(missing_ok=True)


def save_classes(dataset_dir: str, class_names: List[str]) -> str:
    """classes.txt をデータセット直下および train/val フォルダに保存。
    ルートのパスを返す。"""
    base = Path(dataset_dir)
    content = "\n".join(name.strip() for name in class_names) + "\n"

    # データセット直下
    root_path = base / "classes.txt"
    root_path.parent.mkdir(parents=True, exist_ok=True)
    root_path.write_text(content, encoding="utf-8")

    # train / val サブフォルダ（存在すれば更新、なければ作成）
    for split in ("train", "val"):
        split_dir = base / split
        if split_dir.exists():
            (split_dir / "classes.txt").write_text(content, encoding="utf-8")

    return str(root_path)


# ---------------------------------------------------------------------------
# 4a. labelImg 起動コマンド構築
# ---------------------------------------------------------------------------
def build_labelimg_command(
    python_path: str,
    image_dir: str,
    classes_file: str,
    save_dir: str = None,
) -> List[str]:
    """labelImg 起動用のコマンドリストを返す。"""
    if save_dir is None:
        save_dir = image_dir
    
    # python.exe の場所から labelImg.exe を探す
    py_path = Path(python_path)
    labelimg_exe = py_path.parent / "labelImg.exe"
    
    if labelimg_exe.exists():
        return [
            str(labelimg_exe),
            str(Path(image_dir)),
            str(Path(classes_file)),
            str(Path(save_dir)),
        ]
    else:
        # 見つからない場合は従来の方式を試すが、-c で確実に起動させる
        return [
            str(py_path),
            "-c",
            "import sys; from labelImg.labelImg import main; sys.exit(main())",
            str(Path(image_dir)),
            str(Path(classes_file)),
            str(Path(save_dir)),
        ]


# ---------------------------------------------------------------------------
# YAML 作成
# ---------------------------------------------------------------------------
def create_yaml(
    dataset_dir: str,
    class_names: List[str],
) -> str:
    """data.yaml をデータセット直下に作成。パスを返す。"""
    base = Path(dataset_dir)
    yaml_path = base / "data.yaml"
    names_dict = {i: name.strip() for i, name in enumerate(class_names)}
    content = {
        "path": str(base),
        "train": "train",
        "val": "val",
        "nc": len(class_names),
        "names": names_dict,
    }
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return str(yaml_path)


# ---------------------------------------------------------------------------
# キャッシュ削除
# ---------------------------------------------------------------------------
def delete_cache_files(dataset_dir: str) -> int:
    """データセットフォルダ内の .cache ファイルを全て削除。削除数を返す。"""
    base = Path(dataset_dir)
    count = 0
    for cache_file in base.rglob("*.cache"):
        cache_file.unlink()
        count += 1
    return count


# ---------------------------------------------------------------------------
# アノテーションラベル削除 (クリア)
# ---------------------------------------------------------------------------
def clear_annotation_labels(dataset_dir: str) -> int:
    """dataset_dir 配下の train / val フォルダ内の .txt ファイル (classes.txt 除く) を全削除。削除数を返す。"""
    base = Path(dataset_dir)
    count = 0
    for split in ["train", "val"]:
        split_dir = base / split
        if split_dir.exists():
            for txt_file in split_dir.glob("*.txt"):
                if txt_file.name.lower() != "classes.txt":
                    txt_file.unlink(missing_ok=True)
                    count += 1
    return count


# ---------------------------------------------------------------------------
# 5. 学習スクリプト構築
# ---------------------------------------------------------------------------
def build_train_script(
    data_yaml: str,
    epochs: int,
    batch: int,
    imgsz: int,
    workers: int,
    base_model: str,
    yolo_version: str = "11",
    aug_params: dict = None,
) -> str:
    """YOLO 学習用の Python スクリプト文字列を返す。
    freeze_support() 付きで multiprocessing エラーを防止。"""
    if str(yolo_version) == "26":
        model_name = f"yolo26{base_model}.pt"
    elif str(yolo_version) == "11":
        model_name = f"yolo11{base_model}.pt"
    else:
        model_name = f"yolov8{base_model}.pt"
    s_data = _safe(data_yaml)

    if aug_params is None:
        aug_params = {}

    hsv_h = aug_params.get("hsv_h", 0.015)
    hsv_s = aug_params.get("hsv_s", 0.7)
    hsv_v = aug_params.get("hsv_v", 0.4)
    degrees = aug_params.get("degrees", 0.0)
    translate = aug_params.get("translate", 0.1)
    scale = aug_params.get("scale", 0.5)
    shear = aug_params.get("shear", 0.0)
    perspective = aug_params.get("perspective", 0.0)
    flipud = aug_params.get("flipud", 0.0)
    fliplr = aug_params.get("fliplr", 0.5)

    return f'''# -*- coding: utf-8 -*-
import multiprocessing
import gc
import torch

multiprocessing.freeze_support()

from ultralytics import YOLO

def main():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    try:
        model = YOLO("{model_name}")
    except Exception as e:
        print(f"[ERROR] モデル '{model_name}' のロードに失敗しました: {{e}}")
        if "26" in "{model_name}".lower():
            print("[ERROR] ultralytics のバージョンが古いため、YOLO26 に対応していない可能性があります。")
            print("[HINT] 設定画面の『パッケージ確認』から ultralytics を最新バージョンに更新（アップグレード）してください。")
        raise SystemExit(1)

    try:
        results = model.train(
            data="{s_data}",
            epochs={epochs},
            batch={batch},
            imgsz={imgsz},
            workers={workers},
            hsv_h={hsv_h},
            hsv_s={hsv_s},
            hsv_v={hsv_v},
            degrees={degrees},
            translate={translate},
            scale={scale},
            shear={shear},
            perspective={perspective},
            flipud={flipud},
            fliplr={fliplr},
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "out of memory" in err_msg or "cuda" in err_msg:
            print("[WARNING] CUDA Out of Memory (VRAM不足) が発生しました。")
            print("[INFO] VRAMを完全解放し、安全バッチサイズ (batch=4) で自動リトライを開始します...")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            try:
                results = model.train(
                    data="{s_data}",
                    epochs={epochs},
                    batch=4,
                    imgsz={imgsz},
                    workers={workers},
                    hsv_h={hsv_h},
                    hsv_s={hsv_s},
                    hsv_v={hsv_v},
                    degrees={degrees},
                    translate={translate},
                    scale={scale},
                    shear={shear},
                    perspective={perspective},
                    flipud={flipud},
                    fliplr={fliplr},
                )
            except Exception as e2:
                print("[INFO] VRAMを完全解放し、極小バッチサイズ (batch=2) で最終リトライを開始します...")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
                results = model.train(
                    data="{s_data}",
                    epochs={epochs},
                    batch=2,
                    imgsz={imgsz},
                    workers=0,
                    hsv_h={hsv_h},
                    hsv_s={hsv_s},
                    hsv_v={hsv_v},
                    degrees={degrees},
                    translate={translate},
                    scale={scale},
                    shear={shear},
                    perspective={perspective},
                    flipud={flipud},
                    fliplr={fliplr},
                )
        else:
            raise e

    print("Training complete")

if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# 6. 信頼度ヒストグラム生成ヘルパー
# ---------------------------------------------------------------------------
HISTOGRAM_HELPER_CODE = '''
def generate_confidence_histogram(rows, output_path, title="信頼度分布 & 統計情報"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        import numpy as np

        # 日本語フォント設定
        jp_fonts = [
            "Yu Gothic", "Meiryo", "MS Gothic", "TakaoGothic",
            "IPAexGothic", "IPAGothic", "Noto Sans CJK JP", "VL Gothic"
        ]
        available_fonts = set(f.name for f in fm.fontManager.ttflist)
        matched_font = next((f for f in jp_fonts if f in available_fonts), None)
        if matched_font:
            plt.rcParams["font.family"] = matched_font
        plt.rcParams["axes.unicode_minus"] = False

        # クラスごとに集計 (None または信頼度0は除外)
        class_scores = {}
        for r in rows:
            cls_name = r.get("クラス名")
            conf = float(r.get("信頼度", 0))
            if not cls_name or cls_name == "None" or conf <= 0:
                continue
            if cls_name not in class_scores:
                class_scores[cls_name] = []
            class_scores[cls_name].append(conf)

        if not class_scores:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.text(0.5, 0.5, "検出されたオブジェクトはありません", ha="center", va="center", fontsize=14)
            ax.axis("off")
            plt.tight_layout()
            plt.savefig(str(output_path), dpi=120)
            plt.close(fig)
            return

        n_classes = len(class_scores)
        n_cols = min(n_classes, 4)
        n_rows = (n_classes + 3) // 4

        block_width = 4.8
        block_height = 3.2
        fig_w = max(6.0, block_width * n_cols)
        fig_h = max(3.5, block_height * n_rows)
        fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
        if title:
            fig.suptitle(title, fontsize=14, fontweight="bold")

        outer_grid = fig.add_gridspec(n_rows, n_cols)

        for idx, (cls_name, scores) in enumerate(class_scores.items()):
            row = idx // 4
            col = idx % 4

            sub_grid = outer_grid[row, col].subgridspec(1, 2, width_ratios=[1.15, 2.0], wspace=0.18)
            ax_table = fig.add_subplot(sub_grid[0, 0])
            ax_hist = fig.add_subplot(sub_grid[0, 1])

            arr = np.array(scores)
            n = len(arr)
            mean_val = float(np.mean(arr))
            median_val = float(np.median(arr))
            max_val = float(np.max(arr))
            min_val = float(np.min(arr))
            std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0

            table_data = [
                ["N", f"{n}"],
                ["平均", f"{mean_val:.3f}"],
                ["中央値", f"{median_val:.3f}"],
                ["MAX", f"{max_val:.3f}"],
                ["MIN", f"{min_val:.3f}"],
                ["標準偏差", f"{std_val:.3f}"],
            ]
            ax_table.axis("off")
            tbl = ax_table.table(
                cellText=table_data,
                colLabels=["項目", "値"],
                loc="center",
                cellLoc="center"
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(8.5)
            tbl.scale(1.0, 1.25)

            for (r_idx, c_idx), cell in tbl.get_celld().items():
                if r_idx == 0:
                    cell.set_facecolor("#2b5b84")
                    cell.set_text_props(color="white", weight="bold")
                else:
                    cell.set_facecolor("#f8f9fa" if r_idx % 2 == 1 else "#eef2f5")

            bins = np.linspace(0.0, 1.0, 21)
            ax_hist.hist(arr, bins=bins, color="#3498db", edgecolor="#21618c", alpha=0.85)
            ax_hist.set_title(f"{cls_name} (N={n})", fontsize=10, fontweight="bold", pad=4)
            ax_hist.set_xlim(0.0, 1.0)
            ax_hist.set_xlabel("信頼度 (Confidence)", fontsize=8)
            ax_hist.set_ylabel("度数 (件数)", fontsize=8)
            ax_hist.tick_params(axis="both", which="major", labelsize=8)
            ax_hist.grid(axis="y", linestyle="--", alpha=0.5)

        total_cells = n_rows * n_cols
        for empty_idx in range(n_classes, total_cells):
            row = empty_idx // 4
            col = empty_idx % 4
            ax_empty = fig.add_subplot(outer_grid[row, col])
            ax_empty.axis("off")

        plt.savefig(str(output_path), dpi=120)
        plt.close(fig)
    except Exception as e:
        print(f"ヒストグラム画像生成エラー: {e}")
'''


def generate_confidence_histogram(
    rows: List[dict],
    output_path: Union[str, Path],
    title: str = "信頼度分布 & 統計情報",
) -> bool:
    """推論・自動アノテーション結果 rows からクラス別の統計表＋ヒストグラム画像を生成して保存する。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        import numpy as np

        jp_fonts = [
            "Yu Gothic", "Meiryo", "MS Gothic", "TakaoGothic",
            "IPAexGothic", "IPAGothic", "Noto Sans CJK JP", "VL Gothic"
        ]
        available_fonts = set(f.name for f in fm.fontManager.ttflist)
        matched_font = next((f for f in jp_fonts if f in available_fonts), None)
        if matched_font:
            plt.rcParams["font.family"] = matched_font
        plt.rcParams["axes.unicode_minus"] = False

        class_scores = {}
        for r in rows:
            cls_name = r.get("クラス名")
            conf = float(r.get("信頼度", 0))
            if not cls_name or cls_name == "None" or conf <= 0:
                continue
            if cls_name not in class_scores:
                class_scores[cls_name] = []
            class_scores[cls_name].append(conf)

        if not class_scores:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.text(0.5, 0.5, "検出されたオブジェクトはありません", ha="center", va="center", fontsize=14)
            ax.axis("off")
            plt.tight_layout()
            plt.savefig(str(output_path), dpi=120)
            plt.close(fig)
            return True

        n_classes = len(class_scores)
        n_cols = min(n_classes, 4)
        n_rows = (n_classes + 3) // 4

        block_width = 4.8
        block_height = 3.2
        fig_w = max(6.0, block_width * n_cols)
        fig_h = max(3.5, block_height * n_rows)
        fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
        if title:
            fig.suptitle(title, fontsize=14, fontweight="bold")

        outer_grid = fig.add_gridspec(n_rows, n_cols)

        for idx, (cls_name, scores) in enumerate(class_scores.items()):
            row = idx // 4
            col = idx % 4

            sub_grid = outer_grid[row, col].subgridspec(1, 2, width_ratios=[1.15, 2.0], wspace=0.18)
            ax_table = fig.add_subplot(sub_grid[0, 0])
            ax_hist = fig.add_subplot(sub_grid[0, 1])

            arr = np.array(scores)
            n = len(arr)
            mean_val = float(np.mean(arr))
            median_val = float(np.median(arr))
            max_val = float(np.max(arr))
            min_val = float(np.min(arr))
            std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0

            table_data = [
                ["N", f"{n}"],
                ["平均", f"{mean_val:.3f}"],
                ["中央値", f"{median_val:.3f}"],
                ["MAX", f"{max_val:.3f}"],
                ["MIN", f"{min_val:.3f}"],
                ["標準偏差", f"{std_val:.3f}"],
            ]
            ax_table.axis("off")
            tbl = ax_table.table(
                cellText=table_data,
                colLabels=["項目", "値"],
                loc="center",
                cellLoc="center"
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(8.5)
            tbl.scale(1.0, 1.25)

            for (r_idx, c_idx), cell in tbl.get_celld().items():
                if r_idx == 0:
                    cell.set_facecolor("#2b5b84")
                    cell.set_text_props(color="white", weight="bold")
                else:
                    cell.set_facecolor("#f8f9fa" if r_idx % 2 == 1 else "#eef2f5")

            bins = np.linspace(0.0, 1.0, 21)
            ax_hist.hist(arr, bins=bins, color="#3498db", edgecolor="#21618c", alpha=0.85)
            ax_hist.set_title(f"{cls_name} (N={n})", fontsize=10, fontweight="bold", pad=4)
            ax_hist.set_xlim(0.0, 1.0)
            ax_hist.set_xlabel("信頼度 (Confidence)", fontsize=8)
            ax_hist.set_ylabel("度数 (件数)", fontsize=8)
            ax_hist.tick_params(axis="both", which="major", labelsize=8)
            ax_hist.grid(axis="y", linestyle="--", alpha=0.5)

        total_cells = n_rows * n_cols
        for empty_idx in range(n_classes, total_cells):
            row = empty_idx // 4
            col = empty_idx % 4
            ax_empty = fig.add_subplot(outer_grid[row, col])
            ax_empty.axis("off")

        plt.savefig(str(output_path), dpi=120)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"ヒストグラム生成エラー: {e}")
        return False


# ---------------------------------------------------------------------------
# 6. 推論→Excel スクリプト文字列生成
# ---------------------------------------------------------------------------
def build_inference_script(
    model_path: str,
    image_dir: str,
    conf: float,
    output_xlsx: str,
    use_sahi: bool = False,
    tile_size: int = 640,
    tile_overlap: float = 0.2,
    iou: float = 0.7,
) -> str:
    """推論 + Excel 出力を行い、結果を個数別フォルダに保存する。
    use_sahi=True の場合は SAHI タイル推論を使用する。"""
    s_model = _safe(model_path)
    s_images = _safe(image_dir)
    s_xlsx = _safe(output_xlsx)

    if use_sahi:
        return f'''# -*- coding: utf-8 -*-
import multiprocessing
multiprocessing.freeze_support()

import cv2
import numpy as np
import pandas as pd
import PIL.Image
import torch
from pathlib import Path
from tqdm import tqdm
import sys
import shutil

{HISTOGRAM_HELPER_CODE}

def main():
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    from ultralytics.utils.plotting import Annotator, colors

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    detection_model = AutoDetectionModel.from_pretrained(
        model_type="ultralytics",
        model_path="{s_model}",
        confidence_threshold={conf},
        device=device,
    )

    exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
    image_dir = Path("{s_images}")
    images = [p for p in image_dir.iterdir() if p.suffix.lower() in exts]

    # 保存用ベースフォルダ
    save_base = image_dir / "結果画像"
    if save_base.exists():
        shutil.rmtree(save_base)
    save_base.mkdir(parents=True, exist_ok=True)

    print(f"{{len(images)}} 枚を処理中... (SAHI タイル推論 tile={tile_size}, overlap={tile_overlap}, iou={iou})")
    rows = []

    for img_path in tqdm(images, desc="推論進捗", unit="img", file=sys.stdout):
        fname = img_path.name
        result = get_sliced_prediction(
            str(img_path),
            detection_model,
            slice_height={tile_size},
            slice_width={tile_size},
            overlap_height_ratio={tile_overlap},
            overlap_width_ratio={tile_overlap},
            postprocess_type="GREEDYNMM",
            postprocess_match_metric="IOU",
            postprocess_match_threshold={iou},
            verbose=0,
        )
        preds = result.object_prediction_list
        count = len(preds)

        # 個数別フォルダの作成と保存
        count_dir = save_base / str(count)
        count_dir.mkdir(parents=True, exist_ok=True)
        save_path = count_dir / fname

        # YOLOと同様の描画 (Annotator によるクラス固有色・解像度に応じたフォントサイズ)
        orig_pil = PIL.Image.open(img_path).convert("RGB")
        im_cv = cv2.cvtColor(np.array(orig_pil), cv2.COLOR_RGB2BGR)
        annotator = Annotator(im_cv)

        if count > 0:
            for pred in preds:
                cls_id = int(pred.category.id) if pred.category.id is not None else 0
                cls_name = pred.category.name
                confidence = round(pred.score.value, 4)

                box = [pred.bbox.minx, pred.bbox.miny, pred.bbox.maxx, pred.bbox.maxy]
                label_txt = f"{{cls_name}} {{confidence:.2f}}"
                annotator.box_label(box, label=label_txt, color=colors(cls_id, True))

                rows.append({{
                    "ファイル名": fname,
                    "クラス名": cls_name,
                    "信頼度": confidence,
                    "検出個数": count,
                }})
        else:
            rows.append({{"ファイル名": fname, "クラス名": "None", "信頼度": 0, "検出個数": 0}})

        # YOLOと同様にRGB変換してPILで保存 (日本語パス対応)
        res_bgr = annotator.result()
        res_rgb = cv2.cvtColor(res_bgr, cv2.COLOR_BGR2RGB)
        PIL.Image.fromarray(res_rgb).save(str(save_path), quality=95)

    df = pd.DataFrame(rows)
    df.to_excel("{s_xlsx}", index=False, engine="openpyxl")

    # オートフィルター設定
    try:
        from openpyxl import load_workbook
        wb = load_workbook("{s_xlsx}")
        ws = wb.active
        ws.auto_filter.ref = ws.dimensions
        wb.save("{s_xlsx}")
    except Exception:
        pass

    # 信頼度ヒストグラム画像の保存
    try:
        hist_png = Path("{s_xlsx}").parent / (Path("{s_xlsx}").stem + "_ヒストグラム.png")
        generate_confidence_histogram(rows, str(hist_png), title="推論結果 信頼度分布 & 統計情報")
        print(f"ヒストグラム画像保存先: {{hist_png}}")
    except Exception as e:
        print(f"ヒストグラム生成スキップ (エラー): {{e}}")

    print(f"\\nExcel出力完了: {s_xlsx}")
    print(f"結果画像保存先: {{save_base}}")
    print(f"処理画像数: {{len(images)}}枚, 検出総数: {{len(rows)}}個")

if __name__ == "__main__":
    main()
'''
    # --- 通常推論 (SAHI なし) ---
    return f'''# -*- coding: utf-8 -*-
import multiprocessing
multiprocessing.freeze_support()

import pandas as pd
from ultralytics import YOLO
from pathlib import Path
from tqdm import tqdm
import sys
import shutil

{HISTOGRAM_HELPER_CODE}

def main():
    try:
        model = YOLO("{s_model}")
    except Exception as e:
        print(f"[ERROR] モデル '{s_model}' のロードに失敗しました: {{e}}")
        if "26" in "{s_model}".lower():
            print("[ERROR] ultralytics のバージョンが古いため、YOLO26 に対応していない可能性があります。")
            print("[HINT] 設定画面の『パッケージ確認』から ultralytics を最新バージョンに更新（アップグレード）してください。")
        sys.exit(1)
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
    image_dir = Path("{s_images}")
    images = [p for p in image_dir.iterdir() if p.suffix.lower() in exts]
    
    # 保存用ベースフォルダ
    save_base = image_dir / "結果画像"
    if save_base.exists():
        shutil.rmtree(save_base)
    save_base.mkdir(parents=True, exist_ok=True)

    print(f"{{len(images)}} 枚を処理中... (conf={conf}, iou={iou})")
    results = model.predict(source="{s_images}", conf={conf}, iou={iou}, save=False,
                            stream=True, verbose=False)
    rows = []
    
    for r in tqdm(results, total=len(images), desc="推論進捗", unit="img", file=sys.stdout):
        fname = Path(r.path).name
        count = len(r.boxes)
        
        # 個数別フォルダの作成と保存
        count_dir = save_base / str(count)
        count_dir.mkdir(parents=True, exist_ok=True)
        save_path = count_dir / fname
        r.save(filename=str(save_path))

        if count > 0:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                confidence = float(box.conf[0])
                rows.append({{
                    "ファイル名": fname,
                    "クラス名": cls_name,
                    "信頼度": round(confidence, 4),
                    "検出個数": count
                }})
        else:
            rows.append({{"ファイル名": fname, "クラス名": "None", "信頼度": 0, "検出個数": 0}})

    df = pd.DataFrame(rows)
    df.to_excel("{s_xlsx}", index=False, engine="openpyxl")
    
    # オートフィルター設定
    try:
        from openpyxl import load_workbook
        wb = load_workbook("{s_xlsx}")
        ws = wb.active
        ws.auto_filter.ref = ws.dimensions
        wb.save("{s_xlsx}")
    except Exception:
        pass

    # 信頼度ヒストグラム画像の保存
    try:
        hist_png = Path("{s_xlsx}").parent / (Path("{s_xlsx}").stem + "_ヒストグラム.png")
        generate_confidence_histogram(rows, str(hist_png), title="推論結果 信頼度分布 & 統計情報")
        print(f"ヒストグラム画像保存先: {{hist_png}}")
    except Exception as e:
        print(f"ヒストグラム生成スキップ (エラー): {{e}}")

    print(f"\\nExcel出力完了: {s_xlsx}")
    print(f"結果画像保存先: {{save_base}}")
    print(f"処理画像数: {{len(images)}}枚, 検出総数: {{len(rows)}}個")

if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# 4d. ラベル一覧 Excel 出力
# ---------------------------------------------------------------------------
def export_label_list_excel(dataset_dir: str) -> str:
    """dataset フォルダ内に ラベル一覧.xlsx を出力し、その絶対パスを返す。"""
    base = Path(dataset_dir)
    xlsx_path = base / "ラベル一覧.xlsx"

    classes_map = {}
    cls_file = base / "classes.txt"
    if cls_file.exists():
        lines = cls_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            if line.strip():
                classes_map[idx] = line.strip()

    rows = []
    exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")

    for split in ["train", "val"]:
        split_dir = base / split
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
            rows.append({
                "データ種別": split,
                "画像ファイル名": img.name,
                "アノテーション": has_txt,
                "ラベル数": count,
                "検出クラス": cls_str
            })

    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_excel(str(xlsx_path), index=False, engine="openpyxl")

    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(xlsx_path))
        ws = wb.active
        ws.auto_filter.ref = ws.dimensions
        wb.save(str(xlsx_path))
    except Exception:
        pass

    return str(xlsx_path)


# ---------------------------------------------------------------------------
# 4c. 自動アノテーション用スクリプト文字列生成
#     verbose=False で個別結果を非表示、tqdm のみ進捗表示
# ---------------------------------------------------------------------------
def build_autolabel_script(
    model_path: str,
    dataset_dir: str,
    conf: float,
    class_names: List[str],
    use_sahi: bool = False,
    tile_size: int = 640,
    tile_overlap: float = 0.2,
    iou: float = 0.7,
) -> str:
    """自動アノテーション用の Python スクリプト文字列を返す。
    use_sahi=True の場合は SAHI タイル推論を使用する。"""
    s_model = _safe(model_path)
    s_dataset = _safe(dataset_dir)

    if use_sahi:
        return f'''# -*- coding: utf-8 -*-
import multiprocessing
multiprocessing.freeze_support()

import os
import sys
import torch
import pandas as pd
from pathlib import Path
from tqdm import tqdm

{HISTOGRAM_HELPER_CODE}

def main():
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    detection_model = AutoDetectionModel.from_pretrained(
        model_type="ultralytics",
        model_path="{s_model}",
        confidence_threshold={conf},
        device=device,
    )

    dataset = Path("{s_dataset}")
    splits = []
    for split in ["train", "val"]:
        d = dataset / split
        if d.exists():
            splits.append((split, d))

    if not splits:
        print("ERROR: train または val フォルダが見つかりません")
        sys.exit(1)

    # classes.txt を各フォルダに作成
    class_names = detection_model.model.names
    names_list = [class_names[i] for i in range(len(class_names))]
    for split, split_dir in splits:
        cls_file = split_dir / "classes.txt"
        with open(cls_file, "w", encoding="utf-8") as f:
            for name in names_list:
                f.write(name + "\\n")

    excel_rows = []
    total_images = 0

    for split, split_dir in splits:
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
        images = [p for p in split_dir.iterdir() if p.suffix.lower() in exts]
        total_images += len(images)
        print(f"\\n[{{split}}] {{len(images)}} 枚を処理中... (SAHI tile={tile_size}, overlap={tile_overlap}, iou={iou})")

        for img_path in tqdm(images, desc=f"  {{split}}", unit="img", file=sys.stdout):
            fname = img_path.name
            txt_path = split_dir / (img_path.stem + ".txt")

            result = get_sliced_prediction(
                str(img_path),
                detection_model,
                slice_height={tile_size},
                slice_width={tile_size},
                overlap_height_ratio={tile_overlap},
                overlap_width_ratio={tile_overlap},
                postprocess_type="GREEDYNMM",
                postprocess_match_metric="IOU",
                postprocess_match_threshold={iou},
                verbose=0,
            )
            preds = result.object_prediction_list
            count = len(preds)

            if count > 0:
                # YOLO 形式 (正規化) でラベル保存
                import PIL.Image
                img = PIL.Image.open(img_path)
                img_w, img_h = img.size
                with open(txt_path, "w", encoding="utf-8") as f:
                    for pred in preds:
                        cls_id = pred.category.id
                        cls_name = pred.category.name
                        bbox = pred.bbox  # BoundingBox: minx, miny, maxx, maxy
                        cx = (bbox.minx + bbox.maxx) / 2 / img_w
                        cy = (bbox.miny + bbox.maxy) / 2 / img_h
                        w  = (bbox.maxx - bbox.minx) / img_w
                        h  = (bbox.maxy - bbox.miny) / img_h
                        f.write(f"{{cls_id}} {{cx:.6f}} {{cy:.6f}} {{w:.6f}} {{h:.6f}}\\n")
                        conf_val = round(pred.score.value, 4)
                        excel_rows.append({{
                            "データ種別": split,
                            "画像ファイル名": fname,
                            "クラス名": cls_name,
                            "信頼度": conf_val,
                            "検出個数": count,
                        }})
            else:
                txt_path.write_text("", encoding="utf-8")
                excel_rows.append({{
                    "データ種別": split,
                    "画像ファイル名": fname,
                    "クラス名": "None",
                    "信頼度": 0,
                    "検出個数": 0,
                }})

    xlsx_path = dataset / "autolabel_result.xlsx"
    df = pd.DataFrame(excel_rows)
    df.to_excel(str(xlsx_path), index=False, engine="openpyxl")

    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(xlsx_path))
        ws = wb.active
        ws.auto_filter.ref = ws.dimensions
        wb.save(str(xlsx_path))
    except Exception:
        pass

    # 信頼度ヒストグラム画像の保存
    try:
        hist_png = dataset / "autolabel_histogram.png"
        generate_confidence_histogram(excel_rows, str(hist_png), title="自動アノテーション 信頼度分布 & 統計情報")
        print(f"ヒストグラム画像保存先: {{hist_png}}")
    except Exception as e:
        print(f"ヒストグラム生成スキップ (エラー): {{e}}")

    print(f"\\n=== オートラベリング完了 (SAHI) ===")
    print(f"  処理画像数: {{total_images}}")
    print(f"  Excel出力 : {{xlsx_path}}")

if __name__ == "__main__":
    main()
'''
    # --- 通常自動アノテーション (SAHI なし) ---
    return f'''# -*- coding: utf-8 -*-
import multiprocessing
multiprocessing.freeze_support()

import os
import sys
import yaml
import pandas as pd
from ultralytics import YOLO
from pathlib import Path
from tqdm import tqdm

{HISTOGRAM_HELPER_CODE}

def main():
    try:
        model = YOLO("{s_model}")
    except Exception as e:
        print(f"[ERROR] モデル '{s_model}' のロードに失敗しました: {{e}}")
        if "26" in "{s_model}".lower():
            print("[ERROR] ultralytics のバージョンが古いため、YOLO26 に対応していない可能性があります。")
            print("[HINT] 設定画面の『パッケージ確認』から ultralytics を最新バージョンに更新（アップグレード）してください。")
        sys.exit(1)
    dataset = Path("{s_dataset}")

    splits = []
    for split in ["train", "val"]:
        d = dataset / split
        if d.exists():
            splits.append((split, d))

    if not splits:
        print("ERROR: train または val フォルダが見つかりません")
        sys.exit(1)

    # classes.txt を各フォルダに作成
    names_list = [model.names[i] for i in range(len(model.names))]
    for split, split_dir in splits:
        cls_file = split_dir / "classes.txt"
        with open(cls_file, "w", encoding="utf-8") as f:
            for name in names_list:
                f.write(name + "\\n")

    excel_rows = []
    total_images = 0

    for split, split_dir in splits:
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
        images = [p for p in split_dir.iterdir() if p.suffix.lower() in exts]
        total_images += len(images)

        print(f"\\n[{{split}}] {{len(images)}} 枚を処理中... (conf={conf}, iou={iou})")
        results = model.predict(source=str(split_dir), conf={conf}, iou={iou},
                                save=False, stream=True, verbose=False)

        for r in tqdm(results, total=len(images), desc=f"  {{split}}",
                      unit="img", file=sys.stdout):
            img_path = Path(r.path)
            txt_path = split_dir / (img_path.stem + ".txt")
            fname = img_path.name
            count = len(r.boxes)

            if count > 0:
                # save_txt はデフォルトで上書きするが、明示的に。
                r.save_txt(str(txt_path))
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    conf_val = float(box.conf[0])
                    excel_rows.append({{
                        "データ種別": split,
                        "画像ファイル名": fname,
                        "クラス名": cls_name,
                        "信頼度": round(conf_val, 4),
                        "検出個数": count
                    }})
            else:
                # 検出なしの場合、ファイルを空（上書き）にして確実に既存ラベルを消す
                txt_path.write_text("", encoding="utf-8")
                excel_rows.append({{
                    "データ種別": split,
                    "画像ファイル名": fname,
                    "クラス名": "None",
                    "信頼度": 0,
                    "検出個数": 0
                }})

    xlsx_path = dataset / "autolabel_result.xlsx"
    df = pd.DataFrame(excel_rows)
    df.to_excel(str(xlsx_path), index=False, engine="openpyxl")

    # オートフィルター設定
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(xlsx_path))
        ws = wb.active
        ws.auto_filter.ref = ws.dimensions
        wb.save(str(xlsx_path))
    except Exception:
        pass

    # 信頼度ヒストグラム画像の保存
    try:
        hist_png = dataset / "autolabel_histogram.png"
        generate_confidence_histogram(excel_rows, str(hist_png), title="自動アノテーション 信頼度分布 & 統計情報")
        print(f"ヒストグラム画像保存先: {{hist_png}}")
    except Exception as e:
        print(f"ヒストグラム生成スキップ (エラー): {{e}}")

    print(f"\\n=== オートラベリング完了 ===")
    print(f"  処理画像数: {{total_images}}")
    print(f"  Excel出力 : {{xlsx_path}}")

if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# 7. NCNN エクスポートスクリプト
# ---------------------------------------------------------------------------
def build_ncnn_export_script(model_path: str, imgsz: int) -> str:
    """NCNN 形式にモデルをエクスポートし、作成されたフォルダの末尾に .ncnn を付与するスクリプト文字列を返す。"""
    s_model = _safe(model_path)
    return f'''# -*- coding: utf-8 -*-
import multiprocessing
multiprocessing.freeze_support()

import os
import shutil
from pathlib import Path
from ultralytics import YOLO

def main():
    model = YOLO("{s_model}")
    out = model.export(format="ncnn", imgsz={imgsz})
    if out:
        out_path = Path(out)
        if out_path.exists():
            if not out_path.name.endswith(".ncnn"):
                new_path = out_path.with_name(out_path.name + ".ncnn")
                if new_path.exists():
                    if new_path.is_dir():
                        shutil.rmtree(new_path)
                    else:
                        new_path.unlink()
                out_path.rename(new_path)
                print(f"NCNN model saved to: {{new_path}}")
            else:
                print(f"NCNN model saved to: {{out_path}}")

if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# 8. 未アノテーション画像に対する空ラベルファイルの自動作成
# ---------------------------------------------------------------------------
def create_empty_labels(dataset_dir: Union[str, Path]) -> int:
    """train / val フォルダ内の未アノテーション画像（対応する .txt が存在しない画像）に対して空の .txt ファイルを作成する。
    戻り値: 作成した空ラベルファイル数
    """
    base = Path(dataset_dir)
    if not base.exists():
        return 0

    created_count = 0
    # 通常の dataset/{train,val} または dataset/images/{train,val} の両方に対応
    target_dirs = []
    for split in ["train", "val"]:
        # 1. dataset/train, dataset/val
        d1 = base / split
        if d1.is_dir():
            target_dirs.append((d1, d1))
        # 2. dataset/images/train, dataset/labels/train
        img_d = base / "images" / split
        lbl_d = base / "labels" / split
        if img_d.is_dir():
            lbl_d.mkdir(parents=True, exist_ok=True)
            target_dirs.append((img_d, lbl_d))

    for img_dir, lbl_dir in target_dirs:
        for img_file in img_dir.iterdir():
            if img_file.is_file() and img_file.suffix.lower() in IMAGE_EXTENSIONS:
                txt_file = lbl_dir / f"{img_file.stem}.txt"
                if not txt_file.exists():
                    txt_file.touch()  # 空ファイル作成
                    created_count += 1

    return created_count


# ---------------------------------------------------------------------------
# 9. デスクトップ起動ショートカットの作成 (OS自動判定)
# ---------------------------------------------------------------------------
def create_desktop_shortcut(python_path: str = "") -> dict:
    """デスクトップ上に 'YOLOマネージャー' の起動ショートカット/スクリプトを作成する。
    - Windows: 'YOLOマネージャー.bat'
    - Linux / Raspberry Pi: 'YOLOマネージャー.sh' (chmod 0o755) & 'YOLOマネージャー.desktop'
    """
    app_dir = Path(__file__).resolve().parent.parent
    main_py = app_dir / "main.py"
    
    # 実行用 python パス
    py_exec = python_path if python_path and Path(python_path).exists() else sys.executable

    # デスクトップのパスを取得
    home = Path.home()
    desktop_dir = home / "Desktop"
    if not desktop_dir.exists():
        desktop_jp = home / "デスクトップ"
        if desktop_jp.exists():
            desktop_dir = desktop_jp
        else:
            desktop_dir.mkdir(parents=True, exist_ok=True)

    is_windows = sys.platform == "win32"

    if is_windows:
        bat_file = desktop_dir / "YOLOマネージャー.bat"
        content = (
            f"@echo off\n"
            f"chcp 65001 > nul\n"
            f"cd /d \"{app_dir}\"\n"
            f"\"{py_exec}\" \"{main_py}\"\n"
            f"if errorlevel 1 pause\n"
        )
        bat_file.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "path": str(bat_file),
            "type": "bat",
            "message": f"Windows用実行ファイル ({bat_file.name}) をデスクトップに作成しました。",
        }
    else:
        # Linux / Raspberry Pi (.sh のみ作成、ターミナルウィンドウを表示)
        sh_file = desktop_dir / "YOLOマネージャー.sh"
        sh_content = (
            f"#!/bin/bash\n"
            f"# ターミナル環境でない場合（デスクトップダブルクリックなど）はターミナルを起動して自身を実行\n"
            f"if [ ! -t 0 ] && [ -z \"$ALREADY_IN_TERMINAL\" ]; then\n"
            f"    export ALREADY_IN_TERMINAL=1\n"
            f"    for term in lxterminal x-terminal-emulator gnome-terminal xterm konsole; do\n"
            f"        if command -v $term >/dev/null 2>&1; then\n"
            f"            exec $term -e \"$0\" \"$@\"\n"
            f"        fi\n"
            f"    done\n"
            f"fi\n\n"
            f"# Wayland プラグイン未導入環境での安定動作 (Xwayland/xcb フォールバック)\n"
            f"export QT_QPA_PLATFORM=${{QT_QPA_PLATFORM:-\"xcb\"}}\n\n"
            f"cd \"{app_dir}\"\n"
            f"\"{py_exec}\" \"{main_py}\"\n\n"
            f"echo ''\n"
            f"read -p \"処理が終了しました。Enterキーを押すと閉じます...\"\n"
        )
        sh_file.write_text(sh_content, encoding="utf-8")
        try:
            sh_file.chmod(0o755)
        except Exception:
            pass

        return {
            "success": True,
            "path": str(sh_file),
            "type": "sh",
            "message": f"Linux/Raspberry Pi用実行スクリプト ({sh_file.name}) をデスクトップに作成しました。",
        }


# ---------------------------------------------------------------------------
# 10. Raspberry Pi 環境判定
# ---------------------------------------------------------------------------
def is_raspberry_pi() -> bool:
    """現在の実行環境が Raspberry Pi (または ARM SBC) かどうかを判定する。"""
    try:
        model_path = Path("/proc/device-tree/model")
        if model_path.exists():
            model_text = model_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "raspberry pi" in model_text or "rpi" in model_text:
                return True
    except Exception:
        pass

    try:
        for p in ["/etc/rpi-issue", "/etc/os-release"]:
            f = Path(p)
            if f.exists():
                content = f.read_text(encoding="utf-8", errors="ignore").lower()
                if "raspberry pi" in content or "raspbian" in content:
                    return True
    except Exception:
        pass

    if sys.platform.startswith("linux"):
        import platform
        mach = platform.machine().lower()
        if "arm" in mach or "aarch64" in mach:
            return True

    return False


