import pyautogui
import time
import subprocess
import os
import ctypes
# 移除了 urllib.request，因为不再需要联网检测
from dotenv import load_dotenv

# ================= 配置区域 =================
try:
    load_dotenv()
    USERNAME = os.getenv("WLAN_USER")
    PASSWORD = os.getenv("WLAN_PWD")
except:
    USERNAME = None
    PASSWORD = None

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DIRECT_LOGIN_URL = "http://2.2.2.3"
# ===========================================

def get_active_window_title():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    except:
        return ""

def wait_for_chrome_active(timeout=10):
    print(">>> 👁️ 正在等待浏览器窗口...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        title = get_active_window_title()
        # 只要窗口标题包含 Chrome 或 IP，就认为弹出来了
        if "Chrome" in title or "2.2.2.3" in title:
            return True
        time.sleep(0.1)
    return False

def main_logic():
    # --- 删除部分：网络检测逻辑已移除 ---
    print(">>> 🚀 强制启动登录流程...")

    if not os.path.exists(CHROME_PATH):
        print(f"❌ 找不到 Chrome")
        return

    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("\n>>> ⚠️ 未检测到 .env，请输入账号密码：")
        if not USERNAME: USERNAME = input("请输入账号: ")
        if not PASSWORD: PASSWORD = input("请输入密码: ")

    print(">>> 启动浏览器...")
    # 使用 --new-window 确保每次都弹出一个新窗口，避免干扰
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--new-window", DIRECT_LOGIN_URL])
    
    # 等待窗口激活
    if wait_for_chrome_active(timeout=10):
        print(">>> ⏳ 窗口已激活，等待页面渲染 (1.5秒)...")
        time.sleep(1.5) 
    else:
        print(">>> ⚠️ 窗口检测超时，默认等待 3 秒...")
        time.sleep(3)

    # 再次确保激活焦点
    pyautogui.press('shift') 

    # 1. 账号
    print(">>> 输入账号...")
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(USERNAME, interval=0.05)

    # 2. 密码
    print(">>> 输入密码...")
    pyautogui.press('tab') 
    time.sleep(0.2)
    pyautogui.write(PASSWORD, interval=0.05)

    # 3. 协议 (Tab x 4)
    print(">>> 切换到协议...")
    for i in range(4):
        pyautogui.press('tab')
        time.sleep(0.05) 
    
    print(">>> 勾选 & 登录...")
    pyautogui.press('space')
    time.sleep(0.2)
    pyautogui.press('enter')

    print("\n>>> 🎉 执行完成！")

if __name__ == "__main__":
    try:
        main_logic()
    except Exception as e:
        print(f"Error: {e}")