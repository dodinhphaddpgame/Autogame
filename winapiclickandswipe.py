import time
import win32gui
import win32con
import win32api

class LdPlayerHelperWinMsg:
    def __init__(self, window_title, target="child"):
        """
        window_title: substring của title (ví dụ "LDPlayer-4")
        target: "child" để gửi tới RenderWindow (mặc định), "parent" để gửi tới cửa sổ cha
        """
        self.window_title = window_title
        self.target_mode = target  # "child" hoặc "parent"
        self.parent_hwnd = None
        self.child_hwnd = None
        self.target_hwnd = None

        # tìm parent window (top-level) chứa window_title
        def enum_windows_proc(hwnd, _):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd) or ""
                    if window_title.lower() in title.lower():
                        self.parent_hwnd = hwnd
                        # tìm child RenderWindow bên trong parent
                        def enum_child_proc(chwnd, _2):
                            try:
                                cls = (win32gui.GetClassName(chwnd) or "").lower()
                                if "renderwindow" in cls:
                                    self.child_hwnd = chwnd
                            except Exception:
                                pass
                        win32gui.EnumChildWindows(hwnd, enum_child_proc, None)
                        # nếu đã tìm parent thì ta vẫn tiếp tục enum để có thể bắt parent khác nếu có nhiều
            except Exception:
                pass

        win32gui.EnumWindows(enum_windows_proc, None)

        if not self.parent_hwnd and not self.child_hwnd:
            raise Exception(f"Không tìm thấy cửa sổ chứa: '{window_title}'")

        # chọn target theo mode
        if self.target_mode == "child":
            if not self.child_hwnd:
                raise Exception(f"Không tìm thấy RenderWindow trong cửa sổ chứa: '{window_title}'")
            self.target_hwnd = self.child_hwnd
        else:  # target == "parent"
            if not self.parent_hwnd:
                raise Exception(f"Không tìm thấy parent window chứa: '{window_title}'")
            self.target_hwnd = self.parent_hwnd

    def _lparam(self, x, y):
        return win32api.MAKELONG(int(x), int(y))

    def info(self):
        print("Parent HWND:", self.parent_hwnd, "Title:", win32gui.GetWindowText(self.parent_hwnd) if self.parent_hwnd else None)
        print("Child  HWND:", self.child_hwnd, "Class:", win32gui.GetClassName(self.child_hwnd) if self.child_hwnd else None)
        print("Target HWND:", self.target_hwnd, "Mode:", self.target_mode)

    def click(self, x, y):
        """
        Click gửi tới self.target_hwnd.
        Lưu ý: x,y phải là client-coords **relative tới target_hwnd** (không phải screen coords).
        """
        if not self.target_hwnd:
            raise RuntimeError("target_hwnd chưa set")
        lparam = self._lparam(x, y)
        win32gui.SendMessage(self.target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.02)
        win32gui.SendMessage(self.target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam)
        time.sleep(0.02)
        win32gui.SendMessage(self.target_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def swipe(self, x1, y1, x2, y2, duration=400, step=20):
        if not self.target_hwnd:
            raise RuntimeError("target_hwnd chưa set")
        dx = (x2 - x1) / step
        dy = (y2 - y1) / step
        delay = max(0.001, duration / step / 1000.0)
        lparam = self._lparam(x1, y1)
        win32gui.SendMessage(self.target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.005)
        for i in range(1, step + 1):
            xi = int(x1 + dx * i)
            yi = int(y1 + dy * i)
            lparam = self._lparam(xi, yi)
            win32gui.SendMessage(self.target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam)
            time.sleep(delay)
        lparam = self._lparam(x2, y2)
        win32gui.SendMessage(self.target_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def swipe_multi(self, points, duration=800, step=20):
        if not self.target_hwnd:
            raise RuntimeError("target_hwnd chưa set")
        if not points or len(points) < 2:
            print("[WARN] swipe_multi cần >= 2 điểm")
            return
        total_segments = len(points) - 1
        delay = max(0.001, duration / (step * total_segments) / 1000.0)
        x0, y0 = points[0]
        win32gui.SendMessage(self.target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, self._lparam(x0, y0))
        time.sleep(0.005)
        for seg in range(total_segments):
            x1, y1 = points[seg]
            x2, y2 = points[seg + 1]
            dx = (x2 - x1) / step
            dy = (y2 - y1) / step
            for i in range(1, step + 1):
                xi = int(x1 + dx * i); yi = int(y1 + dy * i)
                win32gui.SendMessage(self.target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, self._lparam(xi, yi))
                time.sleep(delay)
        x_end, y_end = points[-1]
        win32gui.SendMessage(self.target_hwnd, win32con.WM_LBUTTONUP, 0, self._lparam(x_end, y_end))

    # helper: lấy client size của target (trả (w,h))
    def get_client_size(self):
        if not self.target_hwnd:
            return None
        left, top, right, bottom = win32gui.GetClientRect(self.target_hwnd)
        return (right - left, bottom - top)

    # helper: convert screen -> client coords của target
    def screen_to_client(self, sx, sy):
        if not self.target_hwnd:
            return None
        return win32gui.ScreenToClient(self.target_hwnd, (int(sx), int(sy)))


def _lparam(x, y):
    return win32api.MAKELONG(int(x), int(y))

def click(target_hwnd, x, y):
    """
    Click gửi tới self.target_hwnd.
    Lưu ý: x,y phải là client-coords **relative tới target_hwnd** (không phải screen coords).
    """
    if not target_hwnd:
        raise RuntimeError("target_hwnd chưa set")
    lparam = _lparam(x, y)
    win32gui.SendMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.02)
    win32gui.SendMessage(target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam)
    time.sleep(0.02)
    win32gui.SendMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def click2(idx, x, y):
    target_hwnd = gethwnd(window_title = f"LDPlayer-{idx}", target = "child")
    if not target_hwnd:
        raise RuntimeError("target_hwnd chưa set")
    lparam = _lparam(x, y)
    win32gui.SendMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.02)
    win32gui.SendMessage(target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam)
    time.sleep(0.02)
    win32gui.SendMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

def swipe_multi(target_hwnd, points, duration=800, step=20):
    if not target_hwnd:
        raise RuntimeError("target_hwnd chưa set")
    if not points or len(points) < 2:
        print("[WARN] swipe_multi cần >= 2 điểm")
        return
    total_segments = len(points) - 1
    delay = max(0.001, duration / (step * total_segments) / 1000.0)
    x0, y0 = points[0]
    win32gui.SendMessage(target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, _lparam(x0, y0))
    time.sleep(0.005)
    for seg in range(total_segments):
        x1, y1 = points[seg]
        x2, y2 = points[seg + 1]
        dx = (x2 - x1) / step
        dy = (y2 - y1) / step
        for i in range(1, step + 1):
            xi = int(x1 + dx * i); yi = int(y1 + dy * i)
            win32gui.SendMessage(target_hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON,_lparam(xi, yi))
            time.sleep(delay)
    x_end, y_end = points[-1]
    win32gui.SendMessage(target_hwnd, win32con.WM_LBUTTONUP, 0,_lparam(x_end, y_end))


def _make_key_lparams(vk):
    """
    Trả về (lparam_down, lparam_up) cho WM_KEYDOWN / WM_KEYUP
    theo virtual-key code vk.
    """
    # scan code từ virtual key
    scan = win32api.MapVirtualKey(vk, 0) & 0xFF
    # key down: repeat count = 1, scan << 16
    ldown = 1 | (scan << 16)
    # key up: set previous-state (bit 30) và transition (bit 31)
    lup = 1 | (scan << 16) | (1 << 30) | (1 << 31)
    return ldown, lup

def press_key(target_hwnd, vk_code, use_sendmessage=True, delay=0.03):
    """
    Gửi phím (VK) tới target_hwnd.
    - target_hwnd: HWND mục tiêu (client window)
    - vk_code: virtual-key code (ví dụ win32con.VK_ESCAPE)
    - use_sendmessage: nếu True sẽ dùng SendMessage (blocking), mặc định dùng PostMessage (non-blocking)
    - delay: thời gian giữa down và up (giây)
    Trả True nếu đã gửi, False nếu lỗi.
    """
    if not target_hwnd:
        raise RuntimeError("target_hwnd chưa set")

    ldown, lup = _make_key_lparams(vk_code)

    try:
        if use_sendmessage:
            # blocking
            win32gui.SendMessage(target_hwnd, win32con.WM_KEYDOWN, vk_code, ldown)
            time.sleep(delay)
            win32gui.SendMessage(target_hwnd, win32con.WM_KEYUP, vk_code, lup)
        else:
            # non-blocking
            win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, vk_code, ldown)
            time.sleep(delay)
            win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, vk_code, lup)
        return True
    except Exception as e:
        print("[ERROR] press_key failed:", e)
        return False

def press_esc(idx, use_sendmessage=True, delay=0.03):
    """Nhấn phím Esc lên target_hwnd."""
    hwnd = gethwnd(f"LDPlayer-{idx}", target="child")
    return press_key(hwnd, win32con.VK_ESCAPE, use_sendmessage=use_sendmessage, delay=delay)

def press_f1(idx, use_sendmessage=True, delay=0.03):
    """Nhấn phím Esc lên target_hwnd."""
    hwnd = gethwnd(f"LDPlayer-{idx}", target="child")
    return press_key(hwnd, win32con.VK_F1, use_sendmessage=use_sendmessage, delay=delay)

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


if __name__ == "__main__":
    test = LdPlayerHelperWinMsg("LDPlayer-1", target="child")
    test.info()
    # test.click(492,140)         # client coords của RenderWindow
    # test.click(305, 741)

    # test.swipe(635, 100, 770, 450)
    test.swipe_multi([(770,230),(770,450)])
