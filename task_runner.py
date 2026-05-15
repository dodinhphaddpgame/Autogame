import time

import screenshot
import winapiclickandswipe


def sleep(sec=0.5):
    time.sleep(sec)


def get_screen_image(idx):
    return screenshot.screenshot(idx)


def press_back(idx):
    winapiclickandswipe.press_esc(idx)
    print("[RUN] press_back")


def click_xy(idx, x, y):
    if hasattr(winapiclickandswipe, "click2"):
        winapiclickandswipe.click2(idx, x, y)
        return True

    print("[RUN] ERROR: winapiclickandswipe.click2 not found")
    return False


def run_task_by_action_type(idx, task):
    """
    Chạy 1 task duy nhất.

    task dạng:
    {
        "card_no": 1,
        "template": "...",
        "action_type": "1_play_match"
    }
    """

    action_type = task["action_type"]
    card_no = task["card_no"]

    print("")
    print("========== RUN ONE TASK ==========")
    print(f"[RUN] card_no={card_no}")
    print(f"[RUN] action_type={action_type}")
    print(f"[RUN] template={task['template']}")

    if action_type == "1_play_match":
        return run_play_match_task(idx)

    if action_type == "2_store":
        return run_store_task(idx)

    if action_type == "3_train_player":
        return run_train_player_task(idx)

    print(f"[RUN] unknown action_type: {action_type}")
    return False


def run_play_match_task(idx):
    """
    Xử lý nhiệm vụ loại 1_play_match.

    Flow tạm:
    1. Đóng bảng nhiệm vụ
    2. TODO: vào trận
    3. TODO: chờ trận xong
    4. TODO: quay về home
    """

    print("[RUN] start 1_play_match")

    # Đóng bảng nhiệm vụ để quay ra home/game screen
    press_back(idx)
    sleep(1)

    # TODO: viết flow vào trận ở đây
    # Ví dụ sau này:
    # ok = start_match(idx)
    # if not ok:
    #     return False
    #
    # ok = wait_match_finished(idx, timeout=180)
    # if not ok:
    #     return False
    #
    # ok = return_home_after_match(idx)
    # if not ok:
    #     return False

    print("[RUN] TODO play match flow")
    return True


def run_store_task(idx):
    """
    Xử lý nhiệm vụ loại 2_store.

    Ví dụ:
    - đóng bảng nhiệm vụ
    - vào store
    - nhận free pack / mua item / mở tab cần thiết
    - quay lại home
    """

    print("[RUN] start 2_store")

    press_back(idx)
    sleep(1)

    # TODO: viết flow store ở đây

    print("[RUN] TODO store flow")
    return True


def run_train_player_task(idx):
    """
    Xử lý nhiệm vụ loại 3_train_player.

    Ví dụ:
    - đóng bảng nhiệm vụ
    - vào mục player / team
    - chọn cầu thủ
    - train
    - quay lại home
    """

    print("[RUN] start 3_train_player")

    press_back(idx)
    sleep(1)

    # TODO: viết flow train player ở đây

    print("[RUN] TODO train player flow")
    return True