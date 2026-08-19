import pyautogui
import time
import subprocess
import os
import sys
import traceback
import requests  # 【新增】我们需要用这个库来做真实的 HTTP 请求
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

IMG_USER  = "target_user.png"
IMG_PWD   = "target_login.png" 
IMG_AGREE = "target_agree.png"
# ===========================================

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def is_connected():
    """
    【核心修改】真实的联网检测
    不再使用 ping，而是尝试访问百度主页
    """
    try:
        # 尝试访问百度，超时设置短一点(3秒)
        # 这里的逻辑是：如果你没登录，访问 https 百度会报 SSL 错误（像你的截图那样）
        # Python 捕获到错误，就会返回 False，从而触发登录。这正是我们要的！
        response = requests.get("https://www.baidu.com", timeout=3)
        
        # 双重保险：状态码必须是 200 且 内容里真的包含 "baidu"
        # 防止网关返回 200 但内容是登录页
        if response.status_code == 200 and "baidu" in response.text.lower():
            return True
        return False
    except:
        # 只要有任何报错（超时、SSL证书错误、连接被重置），都算没网
        return False

def smart_click(image_name, max_wait=15, click_offset_x=0, click_offset_y=0):
    full_path = get_asset_path(image_name)
    print(f">>> 正在寻找素材: {image_name}")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    ✅ 找到了！")
                pyautogui.click(location.x + click_offset_x, location.y + click_offset_y)
                return True
        except:
            pass
        time.sleep(0.5)
    
    print(f"❌ 超时未找到: {image_name}")
    return False

def main_logic():
    print(">>> 正在检测真实网络状态 (HTTP请求)...")
    
    if is_connected():
        print(">>> ✅ 真·互联网已连接，无需登录！")
        return
    else:
        print(">>> 🌐 检测到无法访问互联网 (或被网关拦截)，准备登录...")

    # 检查 Chrome
    if not os.path.exists(CHROME_PATH):
        print(f"❌ 错误：找不到 Chrome 浏览器！\n{CHROME_PATH}")
        return

    # 检查账号
    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("\n>>> ⚠️ 未检测到 .env 配置文件，请输入账号密码：")
        if not USERNAME: USERNAME = input("请输入账号: ")
        if not PASSWORD: PASSWORD = input("请输入密码: ")

    print(">>> 启动浏览器...")
    # 使用 --new-window 确保弹出一个新窗口，防止被旧窗口干扰
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--new-window", DIRECT_LOGIN_URL])
    
    print(">>> 等待浏览器启动 (4秒)...")
    time.sleep(4) 
    
    # 激活屏幕中心
    w, h = pyautogui.size()
    pyautogui.click(w/2, h/2)

    # --- 流程开始 ---
    # 1. 账号
    if smart_click(IMG_USER, max_wait=20):
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(USERNAME, interval=0.1)
    else:
        print("⚠️ 转为盲操作输入账号...")
        pyautogui.press('tab')
        pyautogui.write(USERNAME, interval=0.1)

    # 2. 密码
    print(">>> 输入密码...")
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.1)

    # 3. 协议
# 优先尝试识图（最准）
    if not smart_click(IMG_AGREE, max_wait=3):
        print("⚠️ 识图失败，执行 4 次 Tab 盲操作...")
        
        # 【这里修改了】：连续按 4 次 Tab
        for i in range(4):
            pyautogui.press('tab')
            time.sleep(0.1) # 稍微停顿一下，防止按太快浏览器没反应过来
            
        # 此时光标应该刚好在方框上，按空格打勾
        pyautogui.press('space')

    # 4. 登录
    print(">>> 点击登录...")
    if not smart_click(IMG_PWD, max_wait=5):
        pyautogui.press('enter')
    
    print("\n>>> 🎉 执行结束！")

if __name__ == "__main__":
    try:
        main_logic()
    except Exception as e:
        print("\n" + "="*40)
        print("❌ 发生严重错误，程序崩溃！")
        traceback.print_exc()
        print("="*40)
    finally:
        # 如果你想打包后看报错，可以保留这行。
        # 如果想让它完全自动化（跑完就关），可以注释掉这行。
        # print("\n[程序已暂停，请按回车键关闭窗口...]")
        # input() 
        pass