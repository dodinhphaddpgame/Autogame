import ctypes
import os
import json
import win32gui, win32ui, win32con
import numpy as np
import cv2
from typing import Optional
import log_message
import winapiclickandswipe

# Make process DPI aware (optional)
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

_user32 = ctypes.windll.user32
_PrintWindow = _user32.PrintWindow
_IsIconic = _user32.IsIconic

def screenshot_window_by_hwnd(hwnd: int,
                           use_printwindow_fallback: bool = True,
                           prefer_client_area: bool = False) -> Optional[np.ndarray]:
    """
    Capture window by hwnd and return BGR numpy array (HxWx3) or None on failure.
    - hwnd: window handle (int)
    - use_printwindow_fallback: if True, try PrintWindow when BitBlt yields invalid data
    - prefer_client_area: if True capture client area (no title bar); else full window rect
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None

    # If minimized => usually nothing reliable
    try:
        if _IsIconic(hwnd):
            return None
    except Exception:
        pass

    # choose rect
    try:
        if prefer_client_area:
            l, t, r, b = win32gui.GetClientRect(hwnd)
            l, t = win32gui.ClientToScreen(hwnd, (l, t))
            r, b = win32gui.ClientToScreen(hwnd, (r, b))
        else:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
    except Exception:
        return None

    w = r - l
    h = b - t
    if w <= 0 or h <= 0:
        return None

    hwndDC = mfcDC = saveDC = bmp = None
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(bmp)

        # BitBlt from window DC
        saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

        # read raw bits
        bmp_bits = bmp.GetBitmapBits(True)
        arr = np.frombuffer(bmp_bits, dtype=np.uint8)

        expected = w * h * 4
        if arr.size != expected and use_printwindow_fallback:
            # try PrintWindow once
            try:
                res = _PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)  # 2 ~ PW_RENDERFULLCONTENT
                if res != 0:
                    bmp_bits = bmp.GetBitmapBits(True)
                    arr = np.frombuffer(bmp_bits, dtype=np.uint8)
            except Exception:
                pass

        if arr.size != expected:
            return None

        arr.shape = (h, w, 4)
        img_bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        return img_bgr

    except Exception:
        return None

    finally:
        # cleanup
        try:
            if bmp:
                win32gui.DeleteObject(bmp.GetHandle())
        except Exception:
            pass
        try:
            if saveDC:
                saveDC.DeleteDC()
        except Exception:
            pass
        try:
            if mfcDC:
                mfcDC.DeleteDC()
        except Exception:
            pass
        try:
            if hwndDC:
                win32gui.ReleaseDC(hwnd, hwndDC)
        except Exception:
            pass

def gethwnd(window_title, target="child"):
    """
    window_title: substring của title (ví dụ "LDPlayer-4")
    target: "child" để gửi tới RenderWindow (mặc định), "parent" để gửi tới cửa sổ cha
    """
    parent_hwnd = None
    child_hwnd = None

    # tìm parent window (top-level) chứa window_title
    def enum_windows_proc(hwnd, _):
        nonlocal parent_hwnd, child_hwnd
        try:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd) or ""
                if window_title.lower() in title.lower():
                    parent_hwnd = hwnd

                    # tìm child RenderWindow bên trong parent
                    def enum_child_proc(chwnd, _2):
                        nonlocal child_hwnd
                        try:
                            cls = (win32gui.GetClassName(chwnd) or "").lower()
                            if "renderwindow" in cls:
                                child_hwnd = chwnd
                        except Exception:
                            pass

                    win32gui.EnumChildWindows(hwnd, enum_child_proc, None)
        except Exception:
            pass

    win32gui.EnumWindows(enum_windows_proc, None)

    if not parent_hwnd and not child_hwnd:
        raise Exception(f"Không tìm thấy cửa sổ chứa: '{window_title}'")

    # chọn target theo mode
    if target == "child":
        if not child_hwnd:
            raise Exception(f"Không tìm thấy RenderWindow trong cửa sổ chứa: '{window_title}'")
        return child_hwnd
    else:  # target == "parent"
        if not parent_hwnd:
            raise Exception(f"Không tìm thấy parent window chứa: '{window_title}'")
        return parent_hwnd

def screenshot(idx):
    # image = screenshot_window_by_hwnd(a)
    # image = screenshot_window_by_hwnd(gethwnd(window_title=window_title, target=target))  # img is BGR numpy array or None
    return screenshot_window_by_hwnd(gethwnd(window_title=f"LDPlayer-{idx}", target="child"))

def screenshot2(idx):
    # image = screenshot_window_by_hwnd(a)
    # image = screenshot_window_by_hwnd(gethwnd(window_title=window_title, target=target))  # img is BGR numpy array or None
    return screenshot_window_by_hwnd(gethwnd(window_title=f"LDPlayer-{idx}", target="parent"))


def find_template_on_screen(image, template_path, threshold=0.99, search_region=None):
    """
    Chụp màn từ LDPlayer idx, tìm template_path.
    Trả về (found, max_val, rect) where rect=(x1,y1,x2,y2) in screen coords.
    """
    if image is None:
        log_message.logg("Không chụp được ảnh để dò template.")
        return (False, 0.0, None)

    search_img = image
    offset_x = offset_y = 0
    if search_region:
        x1, y1, x2, y2 = map(int, search_region)
        # clamp
        x1 = max(0, min(search_img.shape[1]-1, x1))
        x2 = max(0, min(search_img.shape[1], x2))
        y1 = max(0, min(search_img.shape[0]-1, y1))
        y2 = max(0, min(search_img.shape[0], y2))
        if x2 <= x1 or y2 <= y1:
            log_message.logg("search_region không hợp lệ: {search_region}")
            return (False, 0.0, None)
        search_img = image[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1

    tpl = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if tpl is None:
        log_message.logg(f"Không đọc được template: {template_path}")
        return (False, 0.0, None)

    if tpl.shape[0] > search_img.shape[0] or tpl.shape[1] > search_img.shape[1]:
        # template to hơn vùng tìm -> skip
        return (False, 0.0, None)

    try:
        res = cv2.matchTemplate(search_img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        top_left = max_loc
        h, w = tpl.shape[:2]
        x1m = int(top_left[0] + offset_x)
        y1m = int(top_left[1] + offset_y)
        x2m = x1m + w
        y2m = y1m + h
        found = (max_val >= threshold)
        return (found, float(max_val), (x1m, y1m, x2m, y2m))
    except Exception as e:
        log_message.logg(f"Lỗi khi match template {os.path.basename(template_path)}: {e}")
        return (False, 0.0, None)

def expand_region(roi, pad, img_shape):
    x1, y1, x2, y2 = roi
    h, w = img_shape[:2]

    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)

    return (x1, y1, x2, y2)

def find_template_on_screen_with_region(image, template_path, threshold=0.99):
    """
    Chụp màn từ LDPlayer idx, tìm template_path.
    Trả về (found, max_val, rect) where rect=(x1,y1,x2,y2) in screen coords.
    """

    json_path = os.path.splitext(template_path)[0] + ".json"
    roi_json = json.load(open(json_path))
    roi = (roi_json["x1"], roi_json["y1"],
           roi_json["x2"], roi_json["y2"])
    region = expand_region(roi, pad=5, img_shape=image.shape)

    if image is None:
        log_message.logg("Không chụp được ảnh để dò template.")
        return (False, 0.0, None)

    search_img = image
    offset_x = offset_y = 0
    if region:
        x1, y1, x2, y2 = map(int, region)
        # clamp
        x1 = max(0, min(search_img.shape[1]-1, x1))
        x2 = max(0, min(search_img.shape[1], x2))
        y1 = max(0, min(search_img.shape[0]-1, y1))
        y2 = max(0, min(search_img.shape[0], y2))
        if x2 <= x1 or y2 <= y1:
            log_message.logg("search_region không hợp lệ: {search_region}")
            return (False, 0.0, None)
        search_img = image[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1

    tpl = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if tpl is None:
        log_message.logg(f"Không đọc được template: {template_path}")
        return (False, 0.0, None)

    if tpl.shape[0] > search_img.shape[0] or tpl.shape[1] > search_img.shape[1]:
        # template to hơn vùng tìm -> skip
        return (False, 0.0, None)

    try:
        res = cv2.matchTemplate(search_img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        top_left = max_loc
        h, w = tpl.shape[:2]
        x1m = int(top_left[0] + offset_x)
        y1m = int(top_left[1] + offset_y)
        x2m = x1m + w
        y2m = y1m + h
        found = (max_val >= threshold)
        return (found, float(max_val), (x1m, y1m, x2m, y2m))
    except Exception as e:
        log_message.logg(f"Lỗi khi match template {os.path.basename(template_path)}: {e}")
        return (False, 0.0, None)

def found_image_with_region(idx, img, template_path, threshold=0.99):
    found, score, rect = find_template_on_screen_with_region(img, template_path, threshold)
    if not found:
        log_message.logg(f"[LD {idx}] Không tìm thấy {template_path} (score={score:.3f})")
    return found

def found_image(image, template_path, threshold=0.99, search_region=None):
    found, score, rect = find_template_on_screen(image, template_path, threshold, search_region)
    return found

def click_if_found(idx, img, template_path, target_hwnd, threshold=0.99, search_region=None):
    """
    Nếu template xuất hiện thì tap vào giữa template đó.
    """
    found, score, rect = find_template_on_screen(img, template_path, threshold, search_region)
    if found and rect:
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        try:
            # abc = winapiclickandswipe.LdPlayerHelperWinMsg(f"LDPlayer-{idx}", target="child")
            # abc.click(cx,cy)
            winapiclickandswipe.click(target_hwnd ,cx,cy)
            return True
        except Exception as e:
            log_message.logg(f"[LD {idx}] Lỗi khi click: {e}")
    else:
        log_message.logg(f"[LD {idx}] Không tìm thấy {template_path} (score={score:.3f})")
    return False

def click_if_found_with_region(idx, img, template_path, threshold=0.99):
    """
    Nếu template xuất hiện thì tap vào giữa template đó.
    """
    target_hwnd = gethwnd(window_title = f"LDPlayer-{idx}", target = "child")

    found, score, rect = find_template_on_screen_with_region(img, template_path, threshold)
    if found and rect:
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        try:
            # abc = winapiclickandswipe.LdPlayerHelperWinMsg(f"LDPlayer-{idx}", target="child")
            # abc.click(cx,cy)
            winapiclickandswipe.click(target_hwnd ,cx,cy)
            return True
        except Exception as e:
            log_message.logg(f"[LD {idx}] Lỗi khi click: {e}")
    else:
        log_message.logg(f"[LD {idx}] Không tìm thấy {template_path} (score={score:.3f})")
    return False

if __name__ == "__main__":
    abcd = gethwnd(window_title="LDPlayer-3", target = "child")
    # img = screenshot_window_by_hwnd(abcd)  # img is BGR numpy array or None
    # winapiclickandswipe.press_esc(abcd)
    # found, score, rect = find_template_on_screen(img, "templates/start_game/tpl_20251010_080251game.png")
    # print(found)
    # print(score)
    # print(rect)
    x = 0
    y = 0
    while True:
        img = screenshot_window_by_hwnd(abcd)  # img is BGR numpy array or None
        found, score, rect = find_template_on_screen(img, "templates/autotrongcay/tpl_20251010_091551tang1.png")
        x = x+1

        if found:
            y = y+1
        print(f"{x}, {y}, {score}")
    # click_if_found("1", img, "templates/start_game/tpl_20251007_151509.png", abcd)
    # if img is not None:
    #     # xử lý với OpenCV
    #     cv2.imshow("snap", img);
    #     cv2.waitKey(10000)
    # else:
    #     print("Không chụp được (minimized/không hỗ trợ).")
