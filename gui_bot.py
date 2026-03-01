import PySimpleGUI as sg
import pyautogui
import keyboard
import time
import random
from datetime import datetime
import threading

pyautogui.FAILSAFE = True

# ------------------ 颜色判定 ------------------

def is_gray_background(r, g, b):
    return abs(r-g) < 8 and abs(r-b) < 8 and abs(g-b) < 8 and 150 <= r <= 220

def is_black_text(r, g, b):
    return r < 110 and g < 110 and b < 110 and abs(r-g) < 25 and abs(r-b) < 25

def is_red_text(r, g, b):
    return r > 160 and g < 120 and b < 120 and (r - max(g, b)) > 60

def fast_color_check(region):
    left, top, width, height = region
    img = pyautogui.screenshot(region=region)

    step = max(5, min(width, height) // 40)
    has_black = False

    for x in range(0, width, step):
        for y in range(0, height, step):
            r, g, b = img.getpixel((x, y))

            if is_gray_background(r, g, b):
                continue
            if is_red_text(r, g, b):
                return "red"
            if is_black_text(r, g, b):
                has_black = True

    return "black" if has_black else "none"

# ------------------ 工具函数 ------------------

def wait_for_key(msg, window):
    window["log"].print(msg)
    while True:
        if keyboard.is_pressed('enter'):
            pos = pyautogui.position()
            window["log"].print(f"记录坐标: {pos}")
            time.sleep(0.3)
            return pos
        time.sleep(0.05)

def select_region(window):
    window["log"].print("把鼠标移到【区域左上角】，按 Enter")
    x1, y1 = wait_for_key("等待左上角...", window)

    window["log"].print("把鼠标移到【区域右下角】，按 Enter")
    x2, y2 = wait_for_key("等待右下角...", window)

    left, top = min(x1, x2), min(y1, y2)
    width, height = abs(x2 - x1), abs(y2 - y1)

    region = (left, top, width, height)
    window["log"].print(f"区域: {region}")
    return region

def refresh_action(start_pos, window):
    x, y = start_pos
    pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.mouseDown()
    pyautogui.moveTo(x + 150, y, duration=0.2)
    pyautogui.mouseUp()
    window["log"].print("刷新拖动完成")
    time.sleep(1)

def click_center(region, window):
    left, top, w, h = region
    cx = left + w // 2
    cy = top + h // 2
    pyautogui.click(cx, cy)
    window["log"].print(f"点击: {cx}, {cy}")

def popup_loaded(popup_region):
    img = pyautogui.screenshot(region=popup_region)
    width, height = img.size
    step = max(5, min(width, height) // 40)

    non_white = 0
    total = 0

    for x in range(0, width, step):
        for y in range(0, height, step):
            r, g, b = img.getpixel((x, y))
            total += 1
            if not (r > 240 and g > 240 and b > 240):
                non_white += 1

    return non_white / total > 0.2

def close_popup(window):
    pyautogui.hotkey('alt', 'f4')
    window["log"].print("关闭弹窗")
    time.sleep(1)

def handle_popup(monitor_region, popup_region, window):
    while True:
        click_center(monitor_region, window)
        window["log"].print("等待弹窗加载...")

        start = time.time()
        loaded = False

        while time.time() - start < 60:
            if popup_loaded(popup_region):
                loaded = True
                break
            time.sleep(2)

        if loaded:
            window["log"].print("弹窗加载成功，关闭")
            close_popup(window)
            break
        else:
            window["log"].print("加载失败，关闭重试")
            close_popup(window)
            time.sleep(1)

def in_peak_time():
    now = datetime.now().time()
    return ((now >= datetime.strptime("08:00", "%H:%M").time() and
             now <= datetime.strptime("10:00", "%H:%M").time()) or
            (now >= datetime.strptime("19:00", "%H:%M").time() and
             now <= datetime.strptime("21:00", "%H:%M").time()))

# ------------------ 主逻辑线程 ------------------

def run_bot(values, window):
    monitor_region = values["monitor"]
    refresh_start = values["refresh"]
    popup_region = values["popup"]

    last_refresh = 0

    window["log"].print("开始监控...")

    while True:
        if window.stop_flag:
            window["log"].print("已停止运行")
            break

        state = fast_color_check(monitor_region)
        window["log"].print(f"状态: {state} {datetime.now().strftime('%H:%M:%S')}")

        if state == "red":
            delay = random.randint(1, 30)
            window["log"].print(f"红字 → {delay} 秒后点击")
            time.sleep(delay)
            handle_popup(monitor_region, popup_region, window)

        elif state == "black":
            delay = random.randint(30, 15 * 60)
            window["log"].print(f"黑字 → {delay} 秒后点击")
            time.sleep(delay)
            handle_popup(monitor_region, popup_region, window)

        else:
            now = time.time()
            if in_peak_time():
                if now - last_refresh > random.randint(3, 8):
                    refresh_action(refresh_start, window)
                    last_refresh = now
            else:
                if now - last_refresh > random.randint(30*60, 60*60):
                    refresh_action(refresh_start, window)
                    last_refresh = now

            time.sleep(1)

# ------------------ GUI ------------------

layout = [
    [sg.Text("自动刷新监控工具", font=("微软雅黑", 16))],
    [sg.Button("选择监控区域"), sg.Text("", key="monitor")],
    [sg.Button("选择刷新起点"), sg.Text("", key="refresh")],
    [sg.Button("选择弹窗区域"), sg.Text("", key="popup")],
    [sg.Button("开始运行", button_color="green"), sg.Button("停止", button_color="red")],
    [sg.Multiline(size=(70, 20), key="log")]
]

window = sg.Window("自动刷新工具", layout, finalize=True)
window.stop_flag = False

monitor_region = None
refresh_start = None
popup_region = None

while True:
    event, values = window.read()

    if event == sg.WINDOW_CLOSED:
        break

    if event == "选择监控区域":
        monitor_region = select_region(window)
        window["monitor"].update(str(monitor_region))

    if event == "选择刷新起点":
        refresh_start = wait_for_key("把鼠标移到刷新起点，按 Enter", window)
        window["refresh"].update(str(refresh_start))

    if event == "选择弹窗区域":
        popup_region = select_region(window)
        window["popup"].update(str(popup_region))

    if event == "开始运行":
        if not monitor_region or not refresh_start or not popup_region:
            window["log"].print("请先选择所有区域！")
            continue

        window.stop_flag = False
        threading.Thread(target=run_bot, args=(
            {"monitor": monitor_region, "refresh": refresh_start, "popup": popup_region},
            window
        ), daemon=True).start()

    if event == "停止":
        window.stop_flag = True

window.close()
