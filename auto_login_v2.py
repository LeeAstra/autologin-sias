import pyautogui
import time
import subprocess
import os
import pyperclip  # 需要安装: pip install pyperclip (用于粘贴长网址)

# ================= 配置区域 =================
# 1. Chrome 路径
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 2. 入口网址 (先去这里拿 Cookie)
BASE_URL = "http://2.2.2.3"

# 3. 【关键】真正的蓝色页面长链接 (请替换为你自己的！)
REAL_LOGIN_URL = "http://2.2.2.3/ac_portal/20210120210326/pc.html?template=20210120210326&tabs=pwd&vlanid=0&_ID_=0&switch_url=&url=http://2.2.2.3/homepage/index.html&controller_type=&mac=XX-XX-XX-XX-XX-XX"

# 4. 账号密码
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"

# 5. 图片文件名
IMG_USER = "target_user.png"
IMG_PWD  = "target_login.png" 
IMG_AGREE = "target_agree.png"
# ===========================================

def get_asset_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def click_image(image_name, retry=5):
    full_path = get_asset_path(image_name)
    print(f">>> 寻找: {image_name} ...")
    for i in range(retry):
        try:
            location = pyautogui.locateCenterOnScreen(full_path, confidence=0.8, grayscale=True)
            if location:
                print(f"    Found! {location}")
                pyautogui.click(location)
                return True
        except: pass
        time.sleep(1)
    return False

def auto_login():
    if not os.path.exists(CHROME_PATH):
        print("❌ 找不到 Chrome")
        return

    print(">>> 🚀 脚本启动！")
    time.sleep(2)

    # === 1. 第一阶段：访问首页“骗”Cookie ===
    print(">>> 1. 启动浏览器访问首页 (获取Cookie)...")
    subprocess.Popen([CHROME_PATH, "--ignore-certificate-errors", BASE_URL])
    
    # 给它一点时间加载绿色页面
    print(">>> 等待绿色页面加载 (8秒)...")
    time.sleep(8)
    
    # === 2. 第二阶段：强制跳转到蓝色页面 ===
    print(">>> 2. 正在跳转至蓝色认证页面...")
    
    # 点击一次屏幕中间，激活窗口
    w, h = pyautogui.size()
    pyautogui.click(w/2, h/2)
    time.sleep(0.5)

    # 快捷键 Ctrl+L 选中地址栏
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.5)
    
    # 使用剪贴板粘贴长链接 (防止输入法干扰)
    pyperclip.copy(REAL_LOGIN_URL)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print(">>> 等待蓝色页面跳转 (5秒)...")
    time.sleep(5)

    # === 3. 第三阶段：图像识别登录 ===
    # 输入账号
    if click_image(IMG_USER):
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(USERNAME, interval=0.1)
    else:
        print("⚠️ 没找到账号框，尝试盲按 Tab...")
        pyautogui.press('tab')
        pyautogui.write(USERNAME, interval=0.1)

    # 输入密码
    print(">>> 切换密码框...")
    pyautogui.press('tab')
    time.sleep(0.5)
    pyautogui.write(PASSWORD, interval=0.1)

    # 勾选条款
    print(">>> 勾选条款...")
    if not click_image(IMG_AGREE):
        print("⚠️ 盲按 Tab 勾选...")
        pyautogui.press('tab') 
        time.sleep(0.2)
        pyautogui.press('tab')
        time.sleep(0.2)
        pyautogui.press('space')

    # 点击登录
    print(">>> 点击登录...")
    if not click_image(IMG_PWD):
        print("⚠️ 回车登录...")
        pyautogui.press('enter')

    print(">>> ✅ 完成！")

if __name__ == "__main__":
    auto_login()