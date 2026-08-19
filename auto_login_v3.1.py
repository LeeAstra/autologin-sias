import pyautogui
import time
import subprocess
import os
import sys
from dotenv import load_dotenv

# ================= 账号配置 =================
load_dotenv()
USERNAME = os.getenv("WLAN_USER")
PASSWORD = os.getenv("WLAN_PWD")
# ===========================================

# ================= 核心配置 =================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# 直连长链接 (蓝色登录页)
DIRECT_LOGIN_URL = "http://2.2.2.3"

# 图片素材
IMG_USER  = "target_user.png"
IMG_PWD   = "target_login.png" 
IMG_AGREE = "target_agree.png"
# ===========================================

def is_connected():
    """检查网络是否连通"""
    try:
        # ping 百度，超时时间 2秒
        # -n 1 (Windows) 表示发1个包
        exit_code = os.system('ping -n 1 -w 2000 www.baidu.com > nul')
        return exit_code == 0
    except:
        return False

def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        # 如果是被打包成 exe 运行
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def smart_click(image_name, max_wait=15, click_offset_x=0, click_offset_y=0):
    """智能等待并点击：不用死等，找到立刻点"""
    full_path = get_asset_path(image_name)
    print(f">>> 正在寻找: {image_name} ...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    ✅ 找到了！({int(time.time() - start_time)}秒)")
                pyautogui.click(location.x + click_offset_x, location.y + click_offset_y)
                return True
        except:
            pass
        time.sleep(0.5) # 每0.5秒看一眼
    
    print(f"❌ 超时未找到: {image_name}")
    return False

def auto_login():
    # --- 1. 智能检测：有网就不跑 ---
    print(">>> 正在检测网络状态...")
    if is_connected():
        print(">>> ✅ 网络已通畅，无需登录！脚本退出。")
        return

    # --- 2. 启动浏览器 ---
    if not os.path.exists(CHROME_PATH):
        print("❌ 找不到 Chrome")
        return

    print(">>> 🌐 网络未连接，开始自动登录流程...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--start-maximized", DIRECT_LOGIN_URL])
    
    # 稍微等一下浏览器窗口弹出来，然后就开始高频扫描
    time.sleep(3) 
    
    # 激活窗口
    w, h = pyautogui.size()
    pyautogui.click(w/2, h/2)

    # --- 3. 智能识图流程 ---
    
    # 寻找账号框 (最多等 20 秒)
    if smart_click(IMG_USER, max_wait=20):
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(USERNAME, interval=0.1)
    else:
        print("⚠️ 账号框识别超时，尝试盲操...")
        pyautogui.press('tab')
        pyautogui.write(USERNAME, interval=0.1)

    # 密码
    print(">>> 填写密码...")
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.1)

    # 勾选 (这里用 Tab 盲打比较快且稳，如果非要识图也可以)
    print(">>> 勾选条款...")
    # 智能判断一下，如果能找到图就点图，找不到就盲按
    if not smart_click(IMG_AGREE, max_wait=3):
        pyautogui.press('tab')
        time.sleep(0.1)
        pyautogui.press('tab')
        time.sleep(0.1)
        pyautogui.press('space')

    # 登录按钮
    print(">>> 点击登录...")
    if not smart_click(IMG_PWD, max_wait=5):
        pyautogui.press('enter')

    print(">>> 🎉 流程结束")
    # 可选：登录成功后自动关闭浏览器（如果你想的话）
    # pyautogui.hotkey('alt', 'f4') 

if __name__ == "__main__":
    auto_login()