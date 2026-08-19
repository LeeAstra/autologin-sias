import pyautogui
import time
import subprocess
import os
from dotenv import load_dotenv # 引入读取环境变量的库

# ================= 账号获取逻辑 (核心修改) =================
# 1. 尝试加载当前目录下的 .env 文件
load_dotenv()

# 2. 读取环境变量
USERNAME = os.getenv("WLAN_USER")
PASSWORD = os.getenv("WLAN_PWD")

# 3. 如果没读取到（说明没创建 .env 文件，或者发给了别人），则转为手动输入
if not USERNAME or not PASSWORD:
    print(">>> ⚠️ 未检测到 .env 配置文件，或配置不完整。")
    print(">>> (如果你想自动登录，请在同级目录下创建 .env 文件并写入 WLAN_USER 和 WLAN_PWD)")
    print(">>> 现在请手动输入：")
    
    if not USERNAME:
        USERNAME = input("请输入账号: ")
    if not PASSWORD:
        PASSWORD = input("请输入密码: ")
else:
    print(">>> ✅ 已从 .env 文件加载账号配置")

# ================= 配置区域 =================
# Chrome 路径
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 网址
LOGIN_URL = "http://2.2.2.3"

# 图片文件名
IMG_USER = "target_user.png"
IMG_PWD  = "target_login.png" 
IMG_AGREE = "target_agree.png"
# ===========================================

def get_asset_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def click_image(image_name, retry=5, click_offset_x=0, click_offset_y=0):
    full_path = get_asset_path(image_name)
    print(f">>> 正在寻找: {image_name} ...")
    
    for i in range(retry):
        try:
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    Found! 坐标: {location}")
                pyautogui.click(location.x + click_offset_x, location.y + click_offset_y)
                return True
        except Exception:
            pass 
        time.sleep(1)
    
    print(f"❌ 未找到图片: {image_name}")
    return False

def auto_login():
    if not os.path.exists(CHROME_PATH):
        print("❌ 找不到 Chrome，请检查路径。")
        return
    
    # 检查图片
    for img in [IMG_USER, IMG_PWD, IMG_AGREE]:
        if not os.path.exists(get_asset_path(img)):
            print(f"❌ 错误：找不到图片文件 {img}")
            return

    print(">>> 🚀 脚本启动！3秒后接管鼠标...")
    time.sleep(3)

    print(">>> 启动 Chrome...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", LOGIN_URL])
    
    print(">>> 等待页面加载 (10秒)...")
    time.sleep(10)
    
    # 激活窗口
    w, h = pyautogui.size()
    pyautogui.click(w/2, h/2) 
    time.sleep(1)

    # 输入账号
    if click_image(IMG_USER):
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        print(">>> 输入账号...")
        pyautogui.write(USERNAME, interval=0.1)
    else:
        print("⚠️ 盲按 Tab 输入账号...")
        pyautogui.press('tab')
        pyautogui.write(USERNAME, interval=0.1)

    # 输入密码
    print(">>> 切换并输入密码...")
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.1)

    # 勾选条款
    print(">>> 寻找条款勾选框...")
    if not click_image(IMG_AGREE):
        print("⚠️ 盲按 Tab 勾选...")
        pyautogui.press('tab') 
        time.sleep(0.2)
        pyautogui.press('tab')
        time.sleep(0.2)
        pyautogui.press('space')

    # 点击登录
    print(">>> 寻找登录按钮...")
    if not click_image(IMG_PWD):
        print("⚠️ 尝试回车登录...")
        pyautogui.press('enter')

    print(">>> ✅ 流程结束！")

if __name__ == "__main__":
    auto_login()