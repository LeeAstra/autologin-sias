import pyautogui
import time
import subprocess
import os
from dotenv import load_dotenv

# ================= 账号配置 =================
load_dotenv()
USERNAME = os.getenv("WLAN_USER")
PASSWORD = os.getenv("WLAN_PWD")

# 如果没配置环境变量，则手动输入
if not USERNAME or not PASSWORD:
    print(">>> ⚠️ 未检测到 .env，请手动输入账号密码")
    if not USERNAME: USERNAME = input("账号: ")
    if not PASSWORD: PASSWORD = input("密码: ")
# ===========================================

# ================= 核心配置 =================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 【关键】直接使用那个能进入蓝色页面的长链接
# 如果这个链接以后失效了，请替换成新的
DIRECT_LOGIN_URL = "http://2.2.2.3"

# 图片素材
IMG_USER  = "target_user.png"
IMG_PWD   = "target_login.png" 
IMG_AGREE = "target_agree.png"
# ===========================================

def get_asset_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def click_image(image_name, retry=5):
    """通用识图点击"""
    full_path = get_asset_path(image_name)
    print(f">>> 寻找: {image_name} ...")
    for i in range(retry):
        try:
            # 这里的 confidence 稍微调低一点点以适应渲染差异
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    Found! {location}")
                pyautogui.click(location)
                return True
        except: pass
        time.sleep(0.5)
    return False

def auto_login():
    if not os.path.exists(CHROME_PATH):
        print("❌ 找不到 Chrome")
        return

    # 检查图片是否存在
    for img in [IMG_USER, IMG_PWD, IMG_AGREE]:
        if not os.path.exists(get_asset_path(img)):
            print(f"❌ 缺少图片: {img}")
            return

    print(">>> 🚀 直连登录脚本启动！")
    time.sleep(2)

    # 1. 直接打开目标长链接
    print(">>> 正在打开认证页面...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", DIRECT_LOGIN_URL])
    
    # 根据你的电脑速度调整等待时间
    print(">>> 等待页面加载 (6秒)...")
    time.sleep(6)
    
    # 激活窗口（防止焦点不在浏览器上）
    w, h = pyautogui.size()
    pyautogui.click(w/2, h/2)
    time.sleep(0.5)

    # 2. 寻找并输入账号
    # 优先识图，识图失败则盲按 Tab
    if click_image(IMG_USER):
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(USERNAME, interval=0.1)
    else:
        print("⚠️ 未找到账号框，尝试盲操作...")
        pyautogui.press('tab')
        pyautogui.write(USERNAME, interval=0.1)

    # 3. 输入密码
    print(">>> 输入密码...")
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.1)

    # 4. 【必须】勾选免责条款
    print(">>> 寻找条款勾选框...")
    if not click_image(IMG_AGREE):
        print("⚠️ 未找到勾选框，尝试盲按 Tab...")
        # 根据经验，通常输入密码后按 2 次 Tab 是勾选框
        pyautogui.press('tab')
        time.sleep(0.2)
        pyautogui.press('tab')
        time.sleep(0.2)
        pyautogui.press('space')

    # 5. 点击登录
    print(">>> 点击登录...")
    if not click_image(IMG_PWD):
        print("⚠️ 未找到登录按钮，尝试回车...")
        pyautogui.press('enter')

    print(">>> ✅ 登录动作完成")

if __name__ == "__main__":
    auto_login()