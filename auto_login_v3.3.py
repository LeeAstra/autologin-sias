import pyautogui
import time
import subprocess
import os
import sys
import traceback  # 用于打印详细错误
from dotenv import load_dotenv

# ================= 配置区域 =================
# 尝试加载 .env
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
    """获取资源路径（兼容打包环境）"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

def is_connected():
    """检查网络"""
    try:
        return os.system('ping -n 1 -w 2000 www.baidu.com > nul') == 0
    except:
        return False

def smart_click(image_name, max_wait=15, click_offset_x=0, click_offset_y=0):
    full_path = get_asset_path(image_name)
    print(f">>> 正在寻找素材: {image_name}")
    # 打印一下完整路径，方便调试
    # print(f"    (路径: {full_path})") 
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    ✅ 找到了！")
                pyautogui.click(location.x + click_offset_x, location.y + click_offset_y)
                return True
        except Exception as e:
            # 这里的错通常是 opencv 没装好或者图片读不到，但不影响循环
            pass
        time.sleep(0.5)
    
    print(f"❌ 超时未找到: {image_name}")
    return False

def main_logic():
    """主逻辑函数"""
    print(">>> 正在检测网络状态...")
    if is_connected():
        print(">>> ✅ 网络已通畅，无需登录！")
        return

    # 检查 Chrome
    if not os.path.exists(CHROME_PATH):
        print(f"❌ 错误：找不到 Chrome 浏览器！\n请确认路径是否正确: {CHROME_PATH}")
        return

    # 检查账号
    global USERNAME, PASSWORD
    if not USERNAME or not PASSWORD:
        print("\n>>> ⚠️ 未检测到 .env 配置文件，请输入账号密码：")
        if not USERNAME: USERNAME = input("请输入账号: ")
        if not PASSWORD: PASSWORD = input("请输入密码: ")

    print(">>> 🌐 启动浏览器...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", "--start-maximized", DIRECT_LOGIN_URL])
    
    print(">>> 等待浏览器启动 (3秒)...")
    time.sleep(3) 
    
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
    print(">>> 勾选协议...")
    if not smart_click(IMG_AGREE, max_wait=3):
        # 盲操备选
        pyautogui.press('tab')
        time.sleep(0.1)
        pyautogui.press('tab')
        time.sleep(0.1)
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
        # === 捕获所有未知错误 ===
        print("\n" + "="*40)
        print("❌ 发生严重错误，程序崩溃！")
        print("错误信息如下：")
        print("-" * 20)
        traceback.print_exc()  # 打印具体的报错位置
        print("="*40)
    finally:
        # === 无论成功还是失败，都暂停在这里 ===
        print("\n[程序已暂停，请按回车键关闭窗口...]")
        input()