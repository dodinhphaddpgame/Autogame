import os
import time
from datetime import datetime

import cv2
import numpy as np

import screenshot
import winapiclickandswipe


# ============================================================
# CONFIG
# ============================================================

IDX = 3

DEFAULT_THRESHOLD = 0.90
TASK_MATCH_THRESHOLD = 0.88
UNKNOWN_MATCH_THRESHOLD = 0.94
COMPLETED_TICK_THRESHOLD = 0.85
REFRESH_BUTTON_THRESHOLD = 0.82

MAX_REFRESH_ROUNDS = 30
WAIT_AFTER_REFRESH = 2

SAVE_UNKNOWN_TASKS = True


# ============================================================
# FOLDERS
# ============================================================

TASK_TEMPLATE_DIRS = {
    "DOABLE": "templates/7_task_types/doable",
    "NOT_DOABLE": "templates/7_task_types/not_doable",
    "UNKNOWN": "templates/7_task_types/unknown",
}


# ============================================================
# COMMON TEMPLATES
# ============================================================

TEMPLATES = {
    "task_completed_tick": "templates/6_trangthainhiemvu/task_completed_tick.png",
    "task_refresh_button": "templates/6_trangthainhiemvu/task_refresh_button.png",
    "refresh_confirm_button": "templates/6_trangthainhiemvu/refresh_confirm_button.png",

}


# ============================================================
# REGIONS - theo ảnh 1280x720
# Format: (x, y, w, h)
# ============================================================

TASK_CARD_REGIONS = [
    (109, 176, 196, 317),   # card 1
    (318, 176, 196, 317),   # card 2
    (527, 176, 196, 317),   # card 3
    (737, 176, 196, 317),   # card 4
]

# Vùng tên nhiệm vụ trong card.
TASK_NAME_REGION_IN_CARD = (12, 48, 172, 55)

# Vùng nút đổi nhiệm vụ ở góc phải trên card.
REFRESH_BUTTON_REGION_IN_CARD = (162, 3, 32, 32)

# Vùng tick khi nhiệm vụ đã hoàn thành.
COMPLETED_TICK_REGION_IN_CARD = (45, 245, 110, 70)

# Popup xác nhận đổi nhiệm vụ
REFRESH_CONFIRM_BUTTON_REGION = (482, 331, 282, 42)

# ============================================================
# BASIC HELPERS
# ============================================================

def sleep(sec=0.5):
    time.sleep(sec)


def get_screen_image(idx):
    return screenshot.screenshot(idx)


def ensure_dirs():
    for folder in TASK_TEMPLATE_DIRS.values():
        os.makedirs(folder, exist_ok=True)


def file_exists(path):
    return os.path.exists(path) and os.path.isfile(path)


def list_template_files(folder):
    os.makedirs(folder, exist_ok=True)

    files = []

    for filename in os.listdir(folder):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            files.append(os.path.join(folder, filename))

    return files


def region_abs(parent_region, child_region):
    """
    Chuyển vùng con trong card thành vùng tuyệt đối trên màn hình.
    """
    px, py, _, _ = parent_region
    cx, cy, cw, ch = child_region

    return (px + cx, py + cy, cw, ch)


def image_to_bgr(img):
    """
    Chuẩn hóa ảnh về OpenCV BGR.
    Hỗ trợ PIL Image và numpy array.
    """
    if img is None:
        return None

    if hasattr(img, "convert"):
        return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

    if isinstance(img, np.ndarray):
        if len(img.shape) == 2:
            return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        if len(img.shape) == 3:
            return img

    return img


def crop_region(img, region):
    """
    Crop ảnh theo vùng (x, y, w, h).
    Hỗ trợ PIL Image và OpenCV/numpy image.
    """
    x, y, w, h = region

    if hasattr(img, "crop"):
        return img.crop((x, y, x + w, y + h))

    return img[y:y + h, x:x + w]


def save_image(img, path):
    """
    Lưu ảnh, hỗ trợ PIL và OpenCV/numpy.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if hasattr(img, "save"):
        img.save(path)
        return

    cv2.imwrite(path, img)


# ============================================================
# CLICK HELPER
# ============================================================

def click_xy(idx, x, y):
    """
    Click theo tọa độ client-relative của cửa sổ LDPlayer.

    Quan trọng:
    - winapiclickandswipe.click(target_hwnd, x, y) dùng target_hwnd
    - winapiclickandswipe.click2(idx, x, y) dùng idx
    Vì vậy ở đây phải dùng click2.
    """

    if hasattr(winapiclickandswipe, "click2"):
        winapiclickandswipe.click2(idx, x, y)
        return True

    print("[ERROR] Không tìm thấy winapiclickandswipe.click2(idx, x, y)")
    return False


# ============================================================
# TEMPLATE MATCHING
# ============================================================

def find_template_location_in_region(img, template_path, region, threshold=DEFAULT_THRESHOLD):
    """
    Tìm template trong region.

    Nếu thấy:
        return {
            "score": score,
            "x": screen_x,
            "y": screen_y,
            "w": template_w,
            "h": template_h
        }

    Nếu không thấy:
        return None
    """

    if not file_exists(template_path):
        print(f"[WARN] template not found: {template_path}")
        return None

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)

    if template is None:
        print(f"[WARN] cannot read template: {template_path}")
        return None

    cropped = crop_region(img, region)
    cropped_bgr = image_to_bgr(cropped)

    if cropped_bgr is None:
        return None

    if cropped_bgr.shape[0] < template.shape[0] or cropped_bgr.shape[1] < template.shape[1]:
        return None

    result = cv2.matchTemplate(cropped_bgr, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    rx, ry, _, _ = region
    tx, ty = max_loc
    th, tw = template.shape[:2]

    return {
        "score": float(max_val),
        "x": rx + tx,
        "y": ry + ty,
        "w": tw,
        "h": th,
    }


def find_template_in_region(img, template_path, region, threshold=DEFAULT_THRESHOLD):
    match = find_template_location_in_region(
        img=img,
        template_path=template_path,
        region=region,
        threshold=threshold
    )

    return match is not None


def click_template_in_region(idx, img, template_path, region, threshold=DEFAULT_THRESHOLD):
    """
    Tìm template trong region.
    Nếu thấy thì click vào tâm template.
    """

    match = find_template_location_in_region(
        img=img,
        template_path=template_path,
        region=region,
        threshold=threshold
    )

    if match is None:
        return False

    click_x = match["x"] + match["w"] // 2
    click_y = match["y"] + match["h"] // 2

    ok = click_xy(idx, click_x, click_y)

    if ok:
        print(
            f"[CLICK] {template_path} "
            f"at ({click_x}, {click_y}), score={match['score']:.3f}"
        )

    return ok


# ============================================================
# TASK DETECTION
# ============================================================

def task_card_completed(img, card_region):
    """
    Check card đã có tick hoàn thành chưa.
    """
    tick_region = region_abs(card_region, COMPLETED_TICK_REGION_IN_CARD)

    return find_template_in_region(
        img=img,
        template_path=TEMPLATES["task_completed_tick"],
        region=tick_region,
        threshold=COMPLETED_TICK_THRESHOLD
    )


def detect_task_from_folder(img, card_region, folder, threshold=TASK_MATCH_THRESHOLD):
    """
    So vùng tên nhiệm vụ trong card với toàn bộ template trong folder.

    Folder rỗng:
        return None

    Có match:
        return template_path
    """

    task_name_region = region_abs(card_region, TASK_NAME_REGION_IN_CARD)
    template_files = list_template_files(folder)

    if not template_files:
        return None

    for template_path in template_files:
        if find_template_in_region(
            img=img,
            template_path=template_path,
            region=task_name_region,
            threshold=threshold
        ):
            return template_path

    return None


def unknown_task_already_saved(img, card_region):
    """
    Kiểm tra nhiệm vụ hiện tại đã có trong unknown/ chưa.
    """

    return detect_task_from_folder(
        img=img,
        card_region=card_region,
        folder=TASK_TEMPLATE_DIRS["UNKNOWN"],
        threshold=UNKNOWN_MATCH_THRESHOLD
    )


def save_unknown_task(img, card_region, card_no):
    """
    Lưu vùng tên nhiệm vụ chưa nhận diện vào unknown/.
    Có chống lưu trùng.
    """

    if not SAVE_UNKNOWN_TASKS:
        print(f"[TASK] card {card_no}: save unknown disabled")
        return None

    existed = unknown_task_already_saved(img, card_region)

    if existed:
        print(f"[TASK] card {card_no}: unknown already exists => {existed}")
        return existed

    unknown_folder = TASK_TEMPLATE_DIRS["UNKNOWN"]
    os.makedirs(unknown_folder, exist_ok=True)

    task_name_region = region_abs(card_region, TASK_NAME_REGION_IN_CARD)
    cropped = crop_region(img, task_name_region)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"unknown_{timestamp}_card{card_no}.png"
    path = os.path.join(unknown_folder, filename)

    save_image(cropped, path)

    print(f"[TASK] card {card_no}: saved new unknown task => {path}")
    return path


def classify_task_card(img, card_region, card_no):
    """
    Phân loại 1 card nhiệm vụ.

    Status:
    - COMPLETED
    - DOABLE
    - NOT_DOABLE
    - UNKNOWN_EXISTED
    - UNKNOWN_SAVED
    """

    if task_card_completed(img, card_region):
        print(f"[TASK] card {card_no}: COMPLETED")
        return {
            "status": "COMPLETED",
            "template": None,
        }

    doable_match = detect_task_from_folder(
        img=img,
        card_region=card_region,
        folder=TASK_TEMPLATE_DIRS["DOABLE"],
        threshold=TASK_MATCH_THRESHOLD
    )

    if doable_match:
        print(f"[TASK] card {card_no}: DOABLE => {doable_match}")
        return {
            "status": "DOABLE",
            "template": doable_match,
        }

    not_doable_match = detect_task_from_folder(
        img=img,
        card_region=card_region,
        folder=TASK_TEMPLATE_DIRS["NOT_DOABLE"],
        threshold=TASK_MATCH_THRESHOLD
    )

    if not_doable_match:
        print(f"[TASK] card {card_no}: NOT_DOABLE => {not_doable_match}")
        return {
            "status": "NOT_DOABLE",
            "template": not_doable_match,
        }

    unknown_match = unknown_task_already_saved(
        img=img,
        card_region=card_region
    )

    if unknown_match:
        print(f"[TASK] card {card_no}: UNKNOWN_EXISTED => {unknown_match}")
        return {
            "status": "UNKNOWN_EXISTED",
            "template": unknown_match,
        }

    saved_path = save_unknown_task(
        img=img,
        card_region=card_region,
        card_no=card_no
    )

    return {
        "status": "UNKNOWN_SAVED",
        "template": saved_path,
    }


# ============================================================
# REFRESH TASK
# ============================================================

def click_refresh_confirm_button(idx, img):
    """
    Bấm nút xác nhận đổi nhiệm vụ trong popup REFRESH TASKS.
    Nút xanh có giá 10 kim cương.
    """

    ok = click_template_in_region(
        idx=idx,
        img=img,
        template_path=TEMPLATES["refresh_confirm_button"],
        region=REFRESH_CONFIRM_BUTTON_REGION,
        threshold=0.82
    )

    if ok:
        print("[TASK] clicked refresh confirm button")
        return True

    print("[TASK] refresh confirm button not found by template, fallback click center")

    # Fallback click thẳng tâm nút xanh
    x, y, w, h = REFRESH_CONFIRM_BUTTON_REGION
    click_x = x + w // 2
    click_y = y + h // 2

    return click_xy(idx, click_x, click_y)


def click_refresh_button_in_card(idx, img, card_region, card_no):
    """
    Bấm icon refresh của card.
    Sau đó bấm nút xác nhận 10 kim cương trong popup.
    """

    refresh_region = region_abs(card_region, REFRESH_BUTTON_REGION_IN_CARD)

    ok = click_template_in_region(
        idx=idx,
        img=img,
        template_path=TEMPLATES["task_refresh_button"],
        region=refresh_region,
        threshold=REFRESH_BUTTON_THRESHOLD
    )

    if not ok:
        print(f"[TASK] card {card_no}: refresh button not found")
        return False

    print(f"[TASK] card {card_no}: clicked refresh icon")

    # Chờ popup hiện
    sleep(2)

    # Chụp lại màn hình sau khi popup xuất hiện
    popup_img = get_screen_image(idx)

    confirmed = click_refresh_confirm_button(idx, popup_img)

    if confirmed:
        print(f"[TASK] card {card_no}: confirmed refresh task")
        sleep(1.0)
        return True

    print(f"[TASK] card {card_no}: cannot confirm refresh popup")
    return False


def should_refresh_status(status):
    """
    Các trạng thái cần bấm đổi.

    UNKNOWN vẫn phải đổi vì bạn chưa phân loại nó.
    """
    return status in (
        "NOT_DOABLE",
        "UNKNOWN_SAVED",
        "UNKNOWN_EXISTED",
    )


def normalize_task_list(idx, max_refresh_rounds=MAX_REFRESH_ROUNDS):
    """
    Đổi nhiệm vụ cho đến khi cả 4 card đều:
    - COMPLETED, hoặc
    - DOABLE

    UNKNOWN luôn phải đổi.
    Sau khi đổi 1 nhiệm vụ, chụp lại màn hình và scan lại từ card 1.
    """

    ensure_dirs()

    for round_no in range(1, max_refresh_rounds + 1):
        print("")
        print(f"========== NORMALIZE ROUND {round_no}/{max_refresh_rounds} ==========")

        img = get_screen_image(idx)

        all_cards_ok = True

        for card_index, card_region in enumerate(TASK_CARD_REGIONS):
            card_no = card_index + 1

            result = classify_task_card(
                img=img,
                card_region=card_region,
                card_no=card_no
            )

            status = result["status"]

            if status in ("COMPLETED", "DOABLE"):
                continue

            if should_refresh_status(status):
                print(f"[TASK] card {card_no}: refresh because status={status}")

                clicked = click_refresh_button_in_card(
                    idx=idx,
                    img=img,
                    card_region=card_region,
                    card_no=card_no
                )

                if not clicked:
                    print(f"[TASK] card {card_no}: cannot refresh, stop normalize")
                    return False

                all_cards_ok = False
                sleep(WAIT_AFTER_REFRESH)

                # Sau khi đổi 1 nhiệm vụ, ảnh cũ không còn đúng.
                # Chụp lại màn hình mới và scan lại từ card 1.
                break

            print(f"[TASK] card {card_no}: unsupported status={status}")
            return False

        if all_cards_ok:
            print("")
            print("[TASK] SUCCESS: all 4 tasks are COMPLETED or DOABLE")
            return True

    print("")
    print("[TASK] FAILED: too many refresh rounds")
    return False


# ============================================================
# DEBUG TOOLS
# ============================================================

def print_current_task_status(idx):
    img = get_screen_image(idx)

    print("")
    print("========== CURRENT TASK STATUS ==========")

    for card_index, card_region in enumerate(TASK_CARD_REGIONS):
        card_no = card_index + 1

        result = classify_task_card(
            img=img,
            card_region=card_region,
            card_no=card_no
        )

        print(f"[TASK] card {card_no}: {result}")


def save_debug_card_regions(idx):
    """
    Lưu ảnh crop để kiểm tra tọa độ đúng chưa.

    Output:
    debug_task_regions/
    - card_1.png
    - card_1_name.png
    - card_1_refresh.png
    - card_1_tick.png
    """

    img = get_screen_image(idx)

    debug_dir = "debug_task_regions"
    os.makedirs(debug_dir, exist_ok=True)

    for card_index, card_region in enumerate(TASK_CARD_REGIONS):
        card_no = card_index + 1

        card_crop = crop_region(img, card_region)
        save_image(card_crop, os.path.join(debug_dir, f"card_{card_no}.png"))

        task_name_region = region_abs(card_region, TASK_NAME_REGION_IN_CARD)
        name_crop = crop_region(img, task_name_region)
        save_image(name_crop, os.path.join(debug_dir, f"card_{card_no}_name.png"))

        refresh_region = region_abs(card_region, REFRESH_BUTTON_REGION_IN_CARD)
        refresh_crop = crop_region(img, refresh_region)
        save_image(refresh_crop, os.path.join(debug_dir, f"card_{card_no}_refresh.png"))

        tick_region = region_abs(card_region, COMPLETED_TICK_REGION_IN_CARD)
        tick_crop = crop_region(img, tick_region)
        save_image(tick_crop, os.path.join(debug_dir, f"card_{card_no}_tick.png"))

    print(f"[DEBUG] saved card regions to: {debug_dir}")


def print_config():
    print("")
    print("========== CONFIG ==========")
    print(f"IDX = {IDX}")
    print(f"SAVE_UNKNOWN_TASKS = {SAVE_UNKNOWN_TASKS}")
    print(f"TASK_MATCH_THRESHOLD = {TASK_MATCH_THRESHOLD}")
    print(f"UNKNOWN_MATCH_THRESHOLD = {UNKNOWN_MATCH_THRESHOLD}")
    print(f"MAX_REFRESH_ROUNDS = {MAX_REFRESH_ROUNDS}")
    print("")


# ============================================================
# MAIN TEST
# ============================================================

def main():
    print("[TEST] Daily Tasks refresh test")
    print("[TEST] Hãy mở sẵn bảng Daily Tasks trước khi chạy file này.")

    print_config()
    ensure_dirs()

    save_debug_card_regions(IDX)
    print_current_task_status(IDX)

    ok = normalize_task_list(IDX)

    if ok:
        print("")
        print("[TEST] DONE: 4 nhiệm vụ hiện tại đều làm được hoặc đã hoàn thành.")
    else:
        print("")
        print("[TEST] STOPPED/FAILED.")
        print("[TEST] Kiểm tra các thư mục:")
        print(f"[TEST] unknown     = {TASK_TEMPLATE_DIRS['UNKNOWN']}")
        print(f"[TEST] doable      = {TASK_TEMPLATE_DIRS['DOABLE']}")
        print(f"[TEST] not_doable  = {TASK_TEMPLATE_DIRS['NOT_DOABLE']}")


if __name__ == "__main__":
    main()