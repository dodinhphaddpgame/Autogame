# log_message.py
import threading
from datetime import datetime

_text_widget_callback = None
_lock = threading.Lock()

def register_text_widget_callback(fn):
    """
    Đăng ký fn(msg:str). GUI sẽ truyền 1 hàm an toàn với thread
    (ví dụ dùng text_box.after để cập nhật UI).
    """
    global _text_widget_callback
    _text_widget_callback = fn

def _call_callback(msg):
    try:
        if _text_widget_callback:
            _text_widget_callback(msg)
    except Exception as e:
        # không để logging phá chương trình chính
        print(f"[log_message] callback error: {e}")

def logg(message):
    """
    Ghi log: in ra console và gọi callback (nếu GUI đã đăng ký).
    Tên 'logg' giữ tương thích với code hiện tại của bạn.
    """
    now = datetime.now().strftime("%H:%M:%S")
    out = f"[{now}] {message}"
    with _lock:
        print(out)
    # Gọi callback (không block)
    try:
        _call_callback(out)
    except Exception:
        pass
