import pyautogui
import time
import subprocess
import os
import ctypes
from dotenv import load_dotenv

# ================= 配置区域 =================
try:
    load_dotenv()
    USERNAME = os.getenv("WLAN_USER")
    PASSWORD = os.getenv("WLAN_PWD")
except:
    USERNAME = None
    PASSWORD = None

# 【修改点1】Edge 浏览器的默认路径
# 注意：大多数电脑上 Edge 装在 (x86) 文件夹下，如果报错找不到文件，试着去掉 " (x86)"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
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

def wait_for_edge_active(timeout=10):
    print(">>> 👁️ 正在等待 Edge 窗口...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        title = get_active_window_title()
        # 【修改点2】只要窗口标题包含 Edge 或 IP，就认为弹出来了
        if "Edge" in title or "2.2.2.3" in title or "个人" in title or "工作" in title:
            return True
        time.sleep(0.1)
    return False

def main_logic():
    print(">>> 🚀 强制启动 Edge 登录流程...")

    if not os.path.exists(EDGE_PATH):
        print(f"❌ 找不到 Edge 浏览器！\n请检查路径是否正确: {EDGE_PATH}")
        # 尝试检查另一个常见路径
        alt_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        if os.path.exists(alt_path):
            print(f"💡 在 Program Files (非x86) 找到了，请修改代码路径。")
        return

    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("\n>>> ⚠️ 未检测到 .env，请输入账号密码：")
        if not USERNAME: USERNAME = input("请输入账号: ")
        if not PASSWORD: PASSWORD = input("请输入密码: ")

    print(">>> 启动浏览器...")
    # Edge 是 Chromium 内核，参数和 Chrome 基本通用
    subprocess.Popen([EDGE_PATH, "--ignore-certificate-errors", "--new-window", DIRECT_LOGIN_URL])
    
    # 等待窗口激活
    if wait_for_edge_active(timeout=10):
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