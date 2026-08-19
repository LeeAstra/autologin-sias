import pyautogui
import time
import subprocess
import os
import sys
from dotenv import load_dotenv

# ================= 账号配置 =================
# 注意：.env 文件通常不建议打包进去，因为方便别人改密码
# 依然优先读取同目录下的 .env，没有则手动输入
load_dotenv()
USERNAME = os.getenv("WLAN_USER")
PASSWORD = os.getenv("WLAN_PWD")
# ===========================================

# ================= 核心配置 =================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DIRECT_LOGIN_URL = "http://2.2.2.3"

IMG_USER  = "target_user.png"
IMG_PWD   = "target_login.png" 
IMG_AGREE = "target_agree.png"
# ===========================================

def is_connected():
    """检查网络"""
    try:
        return os.system('ping -n 1 -w 2000 www.baidu.com > nul') == 0
    except:
        return False

def get_asset_path(filename):
    """
    【核心修改】资源路径获取
    既能适应 Python 直接运行，也能适应打包后的 Exe 运行
    """
    if hasattr(sys, '_MEIPASS'):
        # 如果是打包后的 exe，图片会被解压到 sys._MEIPASS 这个临时目录
        base_path = sys._MEIPASS
    else:
        # 如果是普通脚本运行，就在当前脚本所在目录找
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, filename)

def smart_click(image_name, max_wait=15, click_offset_x=0, click_offset_y=0):
    full_path = get_asset_path(image_name)
    print(f">>> 寻找: {image_name}")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    ✅ Found!")
                pyautogui.click(location.x + click_offset_x, location.y + click_offset_y)
                return True
        except:
            pass
        time.sleep(0.5)
    
    print(f"❌ 未找到: {image_name}")
    return False

def auto_login():
    if is_connected():
        return # 有网直接退出

    if not os.path.exists(CHROME_PATH):
        print("❌ 找不到 Chrome")
        # 如果没有 .env 且需要手动输入，这里应该先处理账号逻辑，再启动
        # 但为了简化，这里假设如果没有env，控制台会提示
        return

    # 处理账号输入 (如果没有 .env)
    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        # 如果打包成无窗口模式(-w)，这里的 input 会报错，所以建议先不加 -w 或者是确保有 .env
        print(">>> ⚠️ 未检测到 .env 配置，请输入账号密码：")
        if not USERNAME: USERNAME = input("账号: ")
        if not PASSWORD: PASSWORD = input("密码: ")

    print(">>> 🌐 开始自动登录...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--start-maximized", DIRECT_LOGIN_URL])
    time.sleep(3) 
    
    w, h = pyautogui.size()
    pyautogui.click(w/2, h/2)

    # 识图流程
    if smart_click(IMG_USER, max_wait=20):
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(USERNAME, interval=0.1)
    else:
        pyautogui.press('tab')
        pyautogui.write(USERNAME, interval=0.1)

    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.1)

    if not smart_click(IMG_AGREE, max_wait=3):
        pyautogui.press('tab')
        time.sleep(0.1)
        pyautogui.press('tab')
        time.sleep(0.1)
        pyautogui.press('space')

    if not smart_click(IMG_PWD, max_wait=5):
        pyautogui.press('enter')

if __name__ == "__main__":
    auto_login()