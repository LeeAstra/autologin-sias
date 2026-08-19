import pyautogui
import time
import subprocess
import os
import ctypes
import urllib.request # 【替换】用原生库代替 requests
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
        if "Chrome" in title or "2.2.2.3" in title:
            return True
        time.sleep(0.1)
    return False

def is_connected():
    """使用原生库检测网络 (不依赖 requests，减小体积)"""
    try:
        # 尝试访问百度，超时2秒
        response = urllib.request.urlopen('https://www.baidu.com', timeout=2)
        # 如果能打开且状态码是200
        if response.getcode() == 200:
            return True
    except:
        pass
    return False

def main_logic():
    print(">>> ⚡ 正在检测网络...")
    if is_connected():
        print(">>> ✅ 网络通畅，退出！")
        return

    if not os.path.exists(CHROME_PATH):
        print(f"❌ 找不到 Chrome")
        return

    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("\n>>> ⚠️ 未检测到 .env，请输入账号密码：")
        if not USERNAME: USERNAME = input("请输入账号: ")
        if not PASSWORD: PASSWORD = input("请输入密码: ")

    print(">>> 🚀 启动浏览器...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--new-window", DIRECT_LOGIN_URL])
    
    if wait_for_chrome_active(timeout=10):
        print(">>> ⏳ 等待页面渲染 (1.5秒)...")
        time.sleep(1.5) 
    else:
        time.sleep(3)

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

    print("\n>>> 🎉 完成！")

if __name__ == "__main__":
    try:
        main_logic()
    except Exception:
        pass