import pyautogui
import time
import subprocess
import os
import requests
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
DIRECT_LOGIN_URL = "http://2.2.2.3/ac_portal/20210120210326/pc.html?template=20210120210326&tabs=pwd&vlanid=0&_ID_=0&switch_url=&url=http://2.2.2.3/"
# ===========================================

def is_connected():
    """真实联网检测"""
    try:
        response = requests.get("https://www.baidu.com", timeout=3)
        if response.status_code == 200 and "baidu" in response.text.lower():
            return True
        return False
    except:
        return False

def main_logic():
    print(">>> 正在检测网络状态...")
    if is_connected():
        print(">>> ✅ 互联网已连接，无需登录！")
        return

    if not os.path.exists(CHROME_PATH):
        print(f"❌ 找不到 Chrome: {CHROME_PATH}")
        return

    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("\n>>> ⚠️ 未检测到 .env，请输入账号密码：")
        if not USERNAME: USERNAME = input("请输入账号: ")
        if not PASSWORD: PASSWORD = input("请输入密码: ")

    print(">>> 启动浏览器...")
    # 启动浏览器
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--new-window", DIRECT_LOGIN_URL])
    
    print(">>> 等待页面加载 (6秒)...")
    # 因为没有图片识别了，这里的时间要给够，防止网页没开就开始打字
    time.sleep(6) 
    
    # 注意：既然光标自动聚焦，我们就不点击屏幕中间了，防止点歪了把焦点弄丢
    # 如果为了保险，可以按一下 Shift 键唤醒窗口但不影响输入
    pyautogui.press('shift') 

    # --- 1. 输入账号 ---
    print(">>> 输入账号...")
    # 为了保险，先全选删除（万一浏览器记住了上次的账号）
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(USERNAME, interval=0.05)

    # --- 2. 输入密码 ---
    print(">>> 切换到密码...")
    pyautogui.press('tab') # 按1次 Tab
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.05)

    # --- 3. 勾选协议 (Tab x 4) ---
    print(">>> 切换到协议 (Tab x4)...")
    for i in range(4):
        pyautogui.press('tab')
        time.sleep(0.1) # 稍微给点间隔，更稳
    
    print(">>> 勾选协议 (Space)...")
    pyautogui.press('space')

    # --- 4. 登录 ---
    print(">>> 提交登录 (Enter)...")
    # 通常勾选完协议，焦点还在协议框上，直接回车可能不行
    # 如果回车能提交就用回车，如果不能，通常再按 1-2 次 Tab 能到登录按钮
    # 这里我们先试直接回车，因为很多网页表单支持全局回车提交
    time.sleep(0.5)
    pyautogui.press('enter')
    
    # 如果上面的回车没反应，可以尝试把下面这两行注释打开（再按一次 Tab 到登录按钮）
    # pyautogui.press('tab')
    # pyautogui.press('enter')

    print("\n>>> 🎉 流程结束！")

if __name__ == "__main__":
    try:
        main_logic()
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        # input("按回车退出...")
        pass