import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Authentication:
    def __init__(self, driver=None, config_path=None, user_key=None):
        """
        初始化认证模块
        
        参数:
            driver: WebDriver实例，如果为None则创建新实例
            config_path: 配置文件路径
            user_key: 用户配置键名
        """
        self.driver = driver
        self.user_key = user_key
        self.is_logged_in = False
        self.config = None
        
        # 加载配置
        if config_path:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        
        # 创建新WebDriver如果未提供
        if self.driver is None:
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            self.driver = webdriver.Chrome(options=options)
            self.should_quit_driver = True
        else:
            self.should_quit_driver = False
        
        # 设置WebDriverWait
        self.wait = WebDriverWait(self.driver, 10)
    
    def wait_for_page_load(self, timeout=30):
        """等待页面加载完成"""
        wait = WebDriverWait(self.driver, timeout)
        try:
            wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            logging.warning(f"页面加载超时: {e}")
    
    def login(self, username=None, password=None, url=None, callback=None):
        """
        执行登录操作
        
        参数:
            username: 用户名，如果为None则从配置中获取
            password: 密码，如果为None则从配置中获取
            url: 登录URL，如果为None则从配置中获取
            callback: 回调函数，用于报告状态更新
        
        返回:
            bool: 登录是否成功
        """
        try:
            # 从配置中获取参数（如果未提供）
            if username is None and self.config and self.user_key:
                username = self.config['reserveUrl'][self.user_key]['username']
            
            if password is None and self.config and self.user_key:
                password = self.config['reserveUrl'][self.user_key]['password']
            
            if url is None and self.config:
                url = self.config['url']
            
            # 打开登录页面
            if callback: callback("正在打开登录页面...")
            self.driver.get(url)
            self.wait_for_page_load()
            
            # 等待用户名输入框出现
            if callback: callback("正在登录...")
            username_input = self.wait.until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            
            # 输入用户名和密码
            username_input.clear()
            username_input.send_keys(username)
            
            password_input = self.driver.find_element(By.ID, 'password')
            password_input.clear()
            password_input.send_keys(password)
            
            # 点击登录按钮
            login_button = self.driver.find_element(By.ID, 'login_submit')
            login_button.click()
            
            # 等待页面加载
            time.sleep(3)  # 短暂等待，让登录过程开始
            self.wait_for_page_load()
            
            # 检查是否需要多因子验证
            if self.check_for_mfa():
                if callback: callback("需要多因子验证")
                return "MFA_REQUIRED"
            
            # 验证登录是否成功
            if "login" not in self.driver.current_url:
                self.is_logged_in = True
                if callback: callback("登录成功")
                return True
            else:
                if callback: callback("登录失败")
                return False
            
        except Exception as e:
            if callback: callback(f"登录过程中出错: {str(e)}")
            logging.error(f"登录失败: {e}")
            return False
    
    def check_for_mfa(self):
        """
        检查是否需要多因子验证
        
        返回:
            bool: 是否需要多因子验证
        """
        try:
            # 检查是否存在多因子验证的元素
            # 注意：这里需要根据实际网站的多因子验证页面元素来调整
            mfa_elements = self.driver.find_elements(By.XPATH, "//div[contains(text(), '验证码')]")
            
            if len(mfa_elements) > 0:
                # 找到发送验证码按钮并点击
                send_button = self.driver.find_element(By.XPATH, "//button[contains(text(), '发送验证码')]")
                send_button.click()
                return True
            
            return False
        except Exception as e:
            logging.error(f"检查多因子验证时出错: {e}")
            return False
    
    def submit_verification_code(self, code, callback=None):
        """
        提交多因子验证码
        
        参数:
            code: 验证码
            callback: 回调函数，用于报告状态更新
        
        返回:
            bool: 验证是否成功
        """
        try:
            if callback: callback(f"正在提交验证码: {code}")
            
            # 找到验证码输入框
            code_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='验证码']"))
            )
            
            # 输入验证码
            code_input.clear()
            code_input.send_keys(code)
            
            # 点击提交按钮
            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), '确认') or contains(text(), '提交')]")
            submit_button.click()
            
            # 等待页面加载
            time.sleep(2)
            self.wait_for_page_load()
            
            # 检查是否验证成功
            if "login" not in self.driver.current_url:
                self.is_logged_in = True
                if callback: callback("验证成功")
                return True
            else:
                if callback: callback("验证失败")
                return False
                
        except Exception as e:
            if callback: callback(f"提交验证码时出错: {str(e)}")
            logging.error(f"验证码提交失败: {e}")
            return False
    
    def logout(self):
        """登出当前账号"""
        try:
            # 找到并点击退出按钮（根据实际页面元素调整）
            logout_button = self.driver.find_element(By.XPATH, "//a[contains(text(), '退出')]")
            logout_button.click()
            self.is_logged_in = False
            self.wait_for_page_load()
            return True
        except Exception as e:
            logging.error(f"登出失败: {e}")
            return False
    
    def close(self):
        """关闭WebDriver"""
        if self.should_quit_driver and self.driver:
            self.driver.quit()

# 如果直接运行该模块，执行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s: %(message)s')
    
    # 测试登录功能
    auth = Authentication(config_path='reserveConfig.json', user_key='LZ')
    result = auth.login(callback=print)
    
    if result == "MFA_REQUIRED":
        print("请输入验证码:")
        code = input()
        auth.submit_verification_code(code, callback=print)
    
    time.sleep(5)
    auth.close()