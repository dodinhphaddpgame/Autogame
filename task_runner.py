import os
import time

import screenshot
import winapiclickandswipe


PLAY_MATCH_TEMPLATES = {
    # Ảnh 1: nút PLAY ở màn hình home
    "home_play": "templates/8_play_match/home_play.png",

    # Ảnh 2: thẻ VS ATTACK trong màn PLAY
    "vs_attack": "templates/8_play_match/vs_attack.png",

    # Ảnh 3: nút PLAY trong màn VS ATTACK
    "vs_attack_play": "templates/8_play_match/vs_attack_play.png",

    # Ảnh 4: nút READY trước khi vào trận. Không bắt buộc, nhưng bấm được thì vào nhanh hơn.
    "ready": "templates/8_play_match/ready.png",

    # Ảnh 7: nút CONTINUE sau khi trận kết thúc
    "continue": "templates/8_play_match/continue.png",
}


STORE_TEMPLATES = {
    # Bước 2: nút STORE ở màn hình home
    "store": "templates/9_store/store.png",

    # Bước 3: nút/tab EXCHANGES trong Store
    "exchanges": "templates/9_store/exchanges.png",

    # Bước 4: nút TTPOINT trong Exchanges
    "ttpoint": "templates/9_store/ttpoint.png",

    # Bước 5: gói 30K
    "30k": "templates/9_store/30k.png",
}


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


def template_exists(templates_dict, name):
    if name not in templates_dict:
        print(f"[RUN] template name not found: {name}")
        return False

    path = templates_dict[name]
    json_path = os.path.splitext(path)[0] + ".json"

    if not os.path.exists(path):
        print(f"[RUN] missing template image: {path}")
        return False

    if not os.path.exists(json_path):
        print(f"[RUN] missing template json: {json_path}")
        return False

    return True


def see_template(img, templates_dict, name, threshold=0.84):
    if not template_exists(templates_dict, name):
        return False

    found, score, rect = screenshot.find_template_on_screen_with_region(
        img,
        templates_dict[name],
        threshold,
    )
    print(f"[RUN] see {name}: found={found} score={score:.3f} rect={rect}")
    return found


def click_template(idx, img, templates_dict, name, threshold=0.84):
    if not template_exists(templates_dict, name):
        return False

    ok = screenshot.click_if_found_with_region(
        idx,
        img,
        templates_dict[name],
        threshold,
    )
    print(f"[RUN] click {name}: {ok}")
    return ok


def wait_template_disappeared(
    idx,
    templates_dict,
    name,
    timeout=8,
    interval=0.8,
    threshold=0.84,
    stable_misses=2,
):
    """
    Sau khi click, chờ template vừa click biến mất ổn định.
    Nếu biến mất liên tiếp stable_misses lần thì coi như đã chuyển cảnh.
    """
    deadline = time.time() + timeout
    miss_count = 0

    while time.time() < deadline:
        img = get_screen_image(idx)
        if img is None:
            sleep(interval)
            continue

        found = see_template(img, templates_dict, name, threshold=threshold)

        if not found:
            miss_count += 1
            print(f"[RUN] {name} disappeared miss_count={miss_count}/{stable_misses}")

            if miss_count >= stable_misses:
                return True
        else:
            miss_count = 0

        sleep(interval)

    print(f"[RUN] disappear timeout: {name}")
    return False


def wait_and_click_template(
    idx,
    templates_dict,
    name,
    timeout=20,
    interval=1.0,
    threshold=0.84,
    optional=False,
    stable_hits=2,
    pre_click_delay=0.8,
    confirm_disappeared=True,
    disappear_timeout=8,
    disappear_interval=0.8,
    disappear_stable_misses=2,
    max_click_retries=3,
):
    """
    Chờ template xuất hiện ổn định rồi click.

    Logic:
    1. Chờ thấy template stable_hits lần.
    2. Đợi thêm pre_click_delay để UI hết animation.
    3. Chụp ảnh mới nhất rồi click.
    4. Nếu confirm_disappeared=True:
       - Chờ template vừa click biến mất.
       - Nếu chưa biến mất thì retry click.
    """
    deadline = time.time() + timeout
    hit_count = 0
    click_try = 0

    while time.time() < deadline:
        img = get_screen_image(idx)
        if img is None:
            sleep(interval)
            continue

        found = see_template(img, templates_dict, name, threshold=threshold)

        if found:
            hit_count += 1
            print(f"[RUN] stable hit {name}: {hit_count}/{stable_hits}")
        else:
            hit_count = 0

        if hit_count >= stable_hits:
            sleep(pre_click_delay)

            latest_img = get_screen_image(idx)
            if latest_img is None:
                sleep(interval)
                continue

            if click_template(idx, latest_img, templates_dict, name, threshold=threshold):
                sleep(1.0)

                if not confirm_disappeared:
                    return True

                if wait_template_disappeared(
                    idx,
                    templates_dict,
                    name,
                    timeout=disappear_timeout,
                    interval=disappear_interval,
                    threshold=threshold,
                    stable_misses=disappear_stable_misses,
                ):
                    return True

                click_try += 1
                print(f"[RUN] click confirmed failed for {name}, retry {click_try}/{max_click_retries}")
                hit_count = 0

                if click_try >= max_click_retries:
                    break

        sleep(interval)

    if optional:
        print(f"[RUN] optional template timeout: {name}")
        return True

    print(f"[RUN] template timeout: {name}")
    return False


def wait_template(idx, templates_dict, name, timeout=20, interval=1.0, threshold=0.84):
    deadline = time.time() + timeout

    while time.time() < deadline:
        img = get_screen_image(idx)
        if img is not None and see_template(img, templates_dict, name, threshold=threshold):
            return True
        sleep(interval)

    print(f"[RUN] wait template timeout: {name}")
    return False


def ensure_home_by_main(idx, timeout=20):
    """
    Về màn home bằng ensure_in_home của main.py.
    main.ensure_in_home có thể chỉ bấm back 1 lần rồi return False,
    nên task_runner gọi lặp lại cho tới khi thật sự ở home.
    """
    import main

    deadline = time.time() + timeout

    while time.time() < deadline:
        img = get_screen_image(idx)
        if img is not None and main.ensure_in_home(idx, img):
            print("[RUN] confirmed home")
            return True

        sleep(1)

    print("[RUN] ensure home timeout")
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

    Flow:
    1. Về màn hình chính game bằng main.ensure_in_home
    2. Click PLAY ở home
    3. Click VS ATTACK
    4. Click PLAY trong VS ATTACK
    5. Click READY nếu thấy
    6. Chờ trận chạy xong tới màn kết quả
    7. Click CONTINUE
    8. Về lại home bằng main.ensure_in_home
    """

    print("[RUN] start 1_play_match")

    # 1. Về home. Khi đang ở bảng nhiệm vụ, ensure_in_home sẽ tự bấm ESC/back.
    if not ensure_home_by_main(idx, timeout=25):
        return False

    # 2. Home -> PLAY
    if not wait_and_click_template(
        idx,
        PLAY_MATCH_TEMPLATES,
        "home_play",
        timeout=15,
        threshold=0.84,
        stable_hits=2,
        pre_click_delay=1.0,
        disappear_timeout=8,
    ):
        return False

    # 3. PLAY screen -> VS ATTACK
    if not wait_and_click_template(
        idx,
        PLAY_MATCH_TEMPLATES,
        "vs_attack",
        timeout=20,
        threshold=0.82,
        stable_hits=2,
        pre_click_delay=1.0,
        disappear_timeout=8,
    ):
        return False

    # 4. VS ATTACK -> PLAY
    if not wait_and_click_template(
        idx,
        PLAY_MATCH_TEMPLATES,
        "vs_attack_play",
        timeout=20,
        threshold=0.82,
        stable_hits=2,
        pre_click_delay=1.2,
        disappear_timeout=8,
    ):
        return False

    # 5. READY. Có trường hợp game tự bắt đầu, nên coi READY là optional.
    wait_and_click_template(
        idx,
        PLAY_MATCH_TEMPLATES,
        "ready",
        timeout=25,
        threshold=0.82,
        optional=True,
        stable_hits=2,
        pre_click_delay=1.0,
        disappear_timeout=8,
    )

    # 6-7. Chờ màn kết quả rồi bấm CONTINUE.
    # VS Attack thường cần vài phút gồm matching/loading/trận/kết quả.
    if not wait_and_click_template(
        idx,
        PLAY_MATCH_TEMPLATES,
        "continue",
        timeout=360,
        interval=2.0,
        threshold=0.82,
        stable_hits=2,
        pre_click_delay=1.5,
        disappear_timeout=15,
    ):
        return False

    # Có thể hiện thêm CONTINUE/transition lần nữa, thử bấm thêm nếu xuất hiện nhanh.
    wait_and_click_template(
        idx,
        PLAY_MATCH_TEMPLATES,
        "continue",
        timeout=8,
        interval=1.0,
        threshold=0.82,
        optional=True,
        stable_hits=1,
        pre_click_delay=1.0,
        disappear_timeout=10,
    )

    # 8. Về home để main loop tiếp tục mở nhiệm vụ và nhận thưởng.
    if not ensure_home_by_main(idx, timeout=35):
        return False

    print("[RUN] 1_play_match finished")
    return True


def run_store_buy_once(idx, round_no=1):
    """
    Chạy 1 vòng mua trong store:
    ensure home -> store -> exchanges -> ttpoint -> 30k -> ensure home
    """

    print(f"[RUN] start 2_store round {round_no}/2")

    # 1. Về home. Khi đang ở bảng nhiệm vụ, ensure_in_home sẽ tự bấm ESC/back.
    if not ensure_home_by_main(idx, timeout=25):
        return False

    # 2. Home -> STORE
    if not wait_and_click_template(
        idx,
        STORE_TEMPLATES,
        "store",
        timeout=15,
        threshold=0.84,
        stable_hits=2,
        pre_click_delay=1.0,
        disappear_timeout=8,
    ):
        return False

    # 3. STORE -> EXCHANGES
    if not wait_and_click_template(
        idx,
        STORE_TEMPLATES,
        "exchanges",
        timeout=20,
        threshold=0.82,
        stable_hits=2,
        pre_click_delay=1.0,
        disappear_timeout=8,
    ):
        return False

    # 4. EXCHANGES -> TTPOINT
    if not wait_and_click_template(
        idx,
        STORE_TEMPLATES,
        "ttpoint",
        timeout=20,
        threshold=0.82,
        stable_hits=2,
        pre_click_delay=1.0,
        disappear_timeout=8,
    ):
        return False

    # 5. Click 30K
    if not wait_and_click_template(
        idx,
        STORE_TEMPLATES,
        "30k",
        timeout=20,
        threshold=0.82,
        stable_hits=2,
        pre_click_delay=1.2,
        disappear_timeout=10,
    ):
        return False

    sleep(1.5)

    # 6. Về home để vòng sau đi lại từ đầu cho chắc.
    if not ensure_home_by_main(idx, timeout=35):
        return False

    print(f"[RUN] 2_store round {round_no}/2 finished")
    return True


def run_store_task(idx):
    """
    Xử lý nhiệm vụ loại 2_store.

    Nhiệm vụ yêu cầu vào shop mua 2 lần, nên chạy đủ 2 vòng:
    1. Về màn hình chính game bằng main.ensure_in_home
    2. Click STORE
    3. Click EXCHANGES
    4. Click TTPOINT
    5. Click 30K
    6. Về lại home bằng main.ensure_in_home
    7. Lặp lại thêm 1 lần nữa
    """

    print("[RUN] start 2_store")

    for round_no in range(1, 3):
        if not run_store_buy_once(idx, round_no=round_no):
            print(f"[RUN] 2_store failed at round {round_no}/2")
            return False

        # Nghỉ nhẹ giữa 2 vòng để UI/game cập nhật nhiệm vụ.
        if round_no < 2:
            sleep(2.0)

    print("[RUN] 2_store finished 2 rounds")
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


def main():
    print("[TEST] task_runner test")

    # Test play match:
    # run_play_match_task(3)

    # Test store:
    run_store_task(3)


if __name__ == "__main__":
    main()
