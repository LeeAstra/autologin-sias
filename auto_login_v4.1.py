import pyautogui
import time
import subprocess
import os
import requests
import ctypes  # 【新增】用于调用 Windows 系统 API 获取窗口标题
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
# 蓝色登录页长链接
DIRECT_LOGIN_URL = "http://2.2.2.3"
# ===========================================

def get_active_window_title():
    """
    【核心黑科技】获取当前电脑最前端（活动）窗口的标题
    """
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    except:
        return ""

def wait_for_chrome_active(timeout=10):
    """
    循环检测，直到 Chrome 变成活动窗口
    """
    print(">>> 👁️ 正在等待浏览器窗口弹出...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        title = get_active_window_title()
        # 只要当前窗口标题包含 "Chrome" 或 "2.2.2.3"，就说明弹出来了
        if "Chrome" in title or "2.2.2.3" in title:
            print(f">>> ✅ 检测到浏览器窗口: [{title}]")
            return True
        time.sleep(0.1) # 极速轮询，每0.1秒看一眼
    return False

def is_connected():
    try:
        response = requests.get("https://www.baidu.com", timeout=2)
        if response.status_code == 200 and "baidu" in response.text.lower():
            return True
        return False
    except:
        return False

def main_logic():
    print(">>> ⚡ 正在极速检测网络...")
    if is_connected():
        print(">>> ✅ 网络通畅，秒退！")
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
    # 启动浏览器
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--new-window", DIRECT_LOGIN_URL])
    
    # === 核心优化：智能等待 ===
    # 1. 先等待窗口弹出来（最长等10秒，但通常只需0.5秒）
    if wait_for_chrome_active(timeout=10):
        # 2. 窗口弹出来了，但网页内容（输入框）渲染还需要一点点时间
        #    虽然这里还是 sleep，但只需要给 1.5秒 就足够页面加载 DOM 了
        #    比之前的死等 6秒 节省了 4.5秒！
        print(">>> ⏳ 窗口已就绪，等待页面渲染 (1.5秒)...")
        time.sleep(1.5) 
    else:
        print(">>> ⚠️ 窗口检测超时，强制等待 3 秒保底...")
        time.sleep(3)

    # 再次强制激活一下，防止刚才那1.5秒你点别的地方去了
    pyautogui.press('shift') 

    # --- 1. 输入账号 ---
    print(">>> 输入账号...")
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(USERNAME, interval=0.05)

    # --- 2. 输入密码 ---
    print(">>> 切换到密码...")
    pyautogui.press('tab') 
    time.sleep(0.2) # 稍微快一点
    pyautogui.write(PASSWORD, interval=0.05)

    # --- 3. 勾选协议 (Tab x 4) ---
    print(">>> 切换到协议...")
    for i in range(4):
        pyautogui.press('tab')
        # 这里的间隔不能太短，否则浏览器反应不过来
        time.sleep(0.05) 
    
    print(">>> 勾选 & 登录...")
    pyautogui.press('space')
    time.sleep(0.2)
    pyautogui.press('enter')

    print("\n>>> 🎉 完成！")

if __name__ == "__main__":
    try:
        main_logic()
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        pass