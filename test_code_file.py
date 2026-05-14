import time
import screenshot
import winapiclickandswipe
import ztest_refresh_tasks

TEMPLATES = {
    # Check game / home
    "login_screen_1": "templates/2_home/1.png",
    "login_screen_2": "templates/2_home/2.png",
    "login_screen_3": "templates/2_home/3.png",

    # Start game
    "startgame1": "templates/1_startgame/1.png",
    "startgame2": "templates/1_startgame/2.png",

    # Open quest panel
    "openbangnhiemvu1": "templates/3_openbangnhiemvu/1.png",
    "openbangnhiemvu2": "templates/3_openbangnhiemvu/2.png",
    "openbangnhiemvu3": "templates/3_openbangnhiemvu/3.png",
    "openbangnhiemvu4": "templates/3_openbangnhiemvu/4.png",

    # Quest status / reward
    "daily_all_done": "templates/6_trangthainhiemvu/7.png",
    "daily_reward_popup": "templates/6_trangthainhiemvu/5.png",
    "daily_reward_claim_button": "templates/6_trangthainhiemvu/8.png",
    "quest_claim_button": "templates/5_nhanquanhiemvu/1.png",

    # Reward pack after quest claim
    "item_pack_tap_to_open": "templates/5_nhanquanhiemvu/5.png",
    "item_pack_reveal_all": "templates/5_nhanquanhiemvu/6.png",
    "item_pack_continue": "templates/5_nhanquanhiemvu/7.png",
}

DEFAULT_THRESHOLD = 0.81


# =========================
# Primitive
# =========================

def get_screen_image(idx):
    return screenshot.screenshot(idx)


def get_screen_image2(idx):
    return screenshot.screenshot2(idx)


def see(idx, img, name, threshold=DEFAULT_THRESHOLD):
    template_path = TEMPLATES[name]
    return screenshot.found_image_with_region(idx, img, template_path, threshold)


def click(idx, img, name, threshold=DEFAULT_THRESHOLD):
    template_path = TEMPLATES[name]
    return screenshot.click_if_found_with_region(idx, img, template_path, threshold)


def press_back(idx):
    winapiclickandswipe.press_esc(idx)
    print("[ACTION] press_back")


def press_f1(idx):
    winapiclickandswipe.press_f1(idx)
    print("[ACTION] press_f1")


def sleep(sec=0.5):
    time.sleep(sec)


# =========================
# Check functions
# =========================

def game_is_running(idx, img):
    return see(idx, img, "startgame2")


def in_home(idx, img):
    return (
        see(idx, img, "login_screen_1")
        and see(idx, img, "login_screen_2")
        and see(idx, img, "login_screen_3")
    )


def quest_panel_open(idx, img):
    return see(idx, img, "openbangnhiemvu4")


def daily_all_done(idx, img):
    return see(idx, img, "daily_all_done", threshold=0.90)


def daily_reward_popup_open(idx, img):
    return see(idx, img, "daily_reward_popup", threshold=0.90)


# =========================
# Ensure functions
# =========================

def ensure_game_running(idx, img):
    if game_is_running(idx, img):
        return True

    press_f1(idx)
    sleep(2)

    img = get_screen_image(idx)

    if see(idx, img, "startgame1"):
        print("[FLOW] click start game")
        click(idx, img, "startgame1")
        sleep(3)

    img = get_screen_image2(idx)
    return game_is_running(idx, img)


def ensure_in_home(idx, img):
    if in_home(idx, img):
        return True

    press_back(idx)
    sleep(1)
    return False


def ensure_quest_panel_open(idx, img):
    if quest_panel_open(idx, img):
        return True

    while True:
        img = get_screen_image(idx)

        if click(idx, img, "openbangnhiemvu2"):
            sleep(1)

        if click(idx, img, "openbangnhiemvu3"):
            sleep(1)

        if click(idx, img, "openbangnhiemvu1"):
            sleep(1)

            img = get_screen_image(idx)
            if quest_panel_open(idx, img):
                print("[FLOW] quest panel opened")
                return True

            print("[FLOW] clicked quest icon but panel not confirmed")
            return False

        sleep(1)


# =========================
# Quest reward functions
# =========================

def claim_daily_reward_popup(idx, img):
    if not daily_reward_popup_open(idx, img):
        return False

    if click(idx, img, "daily_reward_claim_button", threshold=0.90):
        print("[QUEST] claimed daily reward popup")
        sleep(1)
        return True

    print("[QUEST] daily reward popup found but claim button not available")
    return False

def handle_item_pack_after_claim(idx, max_steps=8):
    """
    Xử lý các màn thưởng sau khi claim task:
    - TAP TO OPEN
    - REVEAL ALL
    - CONTINUE

    Return True nếu đã xử lý xong hoặc đã quay lại DAILY TASKS.
    """

    for step in range(max_steps):
        img = get_screen_image(idx)

        # Nếu đã quay lại bảng nhiệm vụ thì xong
        if quest_panel_open(idx, img):
            print("[REWARD] back to quest panel")
            return True

        # Màn có nút TAP TO OPEN
        if click(idx, img, "item_pack_tap_to_open", threshold=0.88):
            print("[REWARD] click TAP TO OPEN")
            sleep(1)
            continue

        # Màn có nút REVEAL ALL
        if click(idx, img, "item_pack_reveal_all", threshold=0.88):
            print("[REWARD] click REVEAL ALL")
            sleep(1)
            continue

        # Màn có nút CONTINUE
        if click(idx, img, "item_pack_continue", threshold=0.88):
            print("[REWARD] click CONTINUE")
            sleep(1)
            continue

        print(f"[REWARD] no reward button found, step={step}")
        sleep(1.5)

    print("[REWARD] item pack flow timeout")
    return False

def claim_quest_reward(idx, img):
    """
    Claim reward của task nhỏ.
    Sau khi claim có thể hiện ITEM PACK, nên phải xử lý xong pack rồi mới return.
    """

    if not click(idx, img, "quest_claim_button", threshold=0.90):
        return False

    print("[QUEST] clicked quest reward CLAIM")
    sleep(1.5)

    handle_item_pack_after_claim(idx)

    return True

def close_daily_reward_popup(idx):
    print("[QUEST] close daily reward popup by clicking empty area")

    winapiclickandswipe.click2(idx, 520, 300)
    sleep(2)

    img = get_screen_image(idx)

    if daily_reward_popup_open(idx, img):
        print("[QUEST] daily reward popup still open after click")
        return False

    print("[QUEST] daily reward popup closed")
    return True

def handle_quest_panel(idx):
    img = get_screen_image(idx)

    # 1. Nếu popup DAILY REWARDS đang mở
    if daily_reward_popup_open(idx, img):
        print("[QUEST] daily reward popup open")

        # 1.1. Nếu daily reward claim được thì claim
        if claim_daily_reward_popup(idx, img):
            return "CLAIMED_DAILY_REWARD"

        # 1.2. Nếu daily reward chưa claim được thì đóng popup
        print("[QUEST] daily reward popup not ready, close it")
        close_daily_reward_popup(idx)

        # 1.3. Đóng popup xong phải chụp lại ảnh
        img = get_screen_image(idx)

        # 1.4. Ưu tiên nhận reward của task nhỏ
        if claim_quest_reward(idx, img):
            return "CLAIMED_QUEST_REWARD"

        # 1.5. Nếu không còn task nhỏ để nhận thì mới check all done
        if daily_all_done(idx, img):
            print("[QUEST] all daily quests completed")
            return "ALL_DONE"

        # 1.6. Không có gì để nhận thì mới chuyển qua scan/refresh task
        print("[QUEST] no claim button found after closing daily reward popup")
        return "NO_CLAIM"

    # 2. Nếu không có popup, nhận reward task nhỏ trước
    if claim_quest_reward(idx, img):
        return "CLAIMED_QUEST_REWARD"

    # 3. Không còn reward nhỏ thì mới check all done
    if daily_all_done(idx, img):
        print("[QUEST] all daily quests completed")
        return "ALL_DONE"

    # 4. Không có gì để nhận -> chuyển sang ztest_refresh_tasks
    print("[QUEST] no claim button found")
    return "NO_CLAIM"


# =========================
# Main loop
# =========================

def quest_master_loop(idx):
    print("----- NEW LOOP -----")

    img = get_screen_image2(idx)

    if not ensure_game_running(idx, img):
        print("[FLOW] waiting game open")
        return "WAITING_GAME_OPEN"

    img = get_screen_image(idx)

    if not ensure_in_home(idx, img):
        print("[FLOW] returning to home")
        return "RETURNING_HOME"

    img = get_screen_image(idx)

    if not ensure_quest_panel_open(idx, img):
        print("[FLOW] opening quest panel failed")
        return "OPEN_QUEST_PANEL_FAILED"

    result = handle_quest_panel(idx)
    print(f"[FLOW] quest panel result = {result}")

    # Nếu đã xong hết nhiệm vụ ngày thì dừng
    if result == "ALL_DONE":
        return "ALL_DONE"

    # Nếu vừa nhận quà/nhiệm vụ, màn hình có thể thay đổi.
    # Cho vòng loop sau xử lý tiếp cho chắc.
    if result in ("CLAIMED_DAILY_REWARD", "CLAIMED_QUEST_REWARD"):
        return result

    # Nếu không có gì để nhận, bắt đầu phase 2:
    # phân loại nhiệm vụ và refresh task không làm được.
    if result == "NO_CLAIM":
        ok = ztest_refresh_tasks.normalize_task_list(idx)

        if ok:
            ztest_refresh_tasks.print_doable_tasks_with_action_type(idx)
            return "TASKS_NORMALIZED"

        return "TASKS_NORMALIZE_FAILED"

    return result
    
def main():
    idx = 3

    while True:
        result = quest_master_loop(idx)

        if result == "ALL_DONE":
            print("[MAIN] all daily quests completed, stop program")
            break

        if result == "TASKS_NORMALIZED":
            print("[MAIN] tasks normalized, ready to run doable tasks")
            break

        if result == "TASKS_NORMALIZE_FAILED":
            print("[MAIN] cannot normalize tasks, stop program")
            break
        break
        sleep(0.5)


if __name__ == "__main__":
    main()