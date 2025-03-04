import json
import os
import sys
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Authentication:
    def __init__(self, driver=None, config_path=None, user_key=None, headless=False):
        """
        初始化认证模块
        
        参数:
            driver: WebDriver实例，如果为None则创建新实例
            config_path: 配置文件路径
            user_key: 用户配置键名
            headless: 是否以无头模式运行
        """
        self.driver = driver
        self.user_key = user_key
        self.is_logged_in = False
        self.config = None
        
        # 加载配置
        if config_path:
            with open(self.resource_path(config_path), 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        
        # 创建新WebDriver如果未提供
        if self.driver is None:
            options = Options()
            
            if headless:
                options.add_argument("--headless")
                
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            self.driver = webdriver.Chrome(options=options)
            self.should_quit_driver = True
        else:
            self.should_quit_driver = False
        
        # 设置WebDriverWait
        self.wait = WebDriverWait(self.driver, 10)
    
    @staticmethod
    def resource_path(relative_path):
        """ 获取资源绝对路径 """
        if hasattr(sys, '_MEIPASS'):
            # 打包后路径（临时解压目录）
            return os.path.join(sys._MEIPASS, relative_path)
        # 未打包时的开发路径
        return os.path.join(os.path.abspath("."), relative_path)

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
                try:
                    # 尝试不同的配置路径
                    if 'reserveUrl' in self.config and self.user_key in self.config['reserveUrl']:
                        username = self.config['reserveUrl'][self.user_key]['username']
                    elif self.user_key in self.config:
                        username = self.config[self.user_key]['username']
                    else:
                        if callback: callback(f"错误: 无法找到用户名配置")
                        return False
                except Exception as e:
                    if callback: callback(f"获取用户名配置时出错: {str(e)}")
                    return False
            
            if password is None and self.config and self.user_key:
                try:
                    # 尝试不同的配置路径
                    if 'reserveUrl' in self.config and self.user_key in self.config['reserveUrl']:
                        password = self.config['reserveUrl'][self.user_key]['password']
                    elif self.user_key in self.config:
                        password = self.config[self.user_key]['password']
                    else:
                        if callback: callback(f"错误: 无法找到密码配置")
                        return False
                except Exception as e:
                    if callback: callback(f"获取密码配置时出错: {str(e)}")
                    return False
            
            # 使用默认URL或从配置中获取
            if url is None:
                # 默认登录URL
                url = "https://webvpn3.hebau.edu.cn/https/77726476706e69737468656265737421f5ff40902b7e60557c099ce29d51367b21a6/qljfwapp/sys/lwAppointmentPublicPlace/*default/index.do"
                
                # 尝试从配置中获取URL
                if self.config and 'url' in self.config:
                    url = self.config['url']
                elif self.config and 'login_url' in self.config:
                    url = self.config['login_url']
                
                if callback: callback(f"使用URL: {url}")
            
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
            if self.check_for_mfa(callback):
                if callback: callback("需要多因子验证")
                return "MFA_REQUIRED"
            
            # 验证登录是否成功
            if "login" not in self.driver.current_url:
                self.is_logged_in = True
                if callback: callback("登录成功")
                return True
            else:
                if callback: callback("登录失败，请检查用户名和密码")
                return False
            
        except Exception as e:
            if callback: callback(f"登录过程中出错: {str(e)}")
            logging.error(f"登录失败: {e}")
            return False
    
    def check_for_mfa(self, callback=None):
        """
        检查是否需要多因子验证
        
        参数:
            callback: 回调函数，用于报告状态更新
        
        返回:
            bool: 是否需要多因子验证
        """
        try:
            # 检查页面标题或内容是否包含多因子验证相关文字
            if "多因子认证" in self.driver.page_source:
                if callback: callback("检测到多因子认证页面")
                
                # 尝试点击获取验证码按钮
                try:
                    # 等待获取验证码按钮出现
                    get_code_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, 'getDynamicCode'))
                    )
                    if callback: callback("点击获取验证码按钮")
                    get_code_button.click()
                    return True
                except Exception as e:
                    if callback: callback(f"点击获取验证码按钮失败: {e}")
                    logging.error(f"点击获取验证码按钮失败: {e}")
                    # 尝试其他可能的按钮
                    try:
                        # 尝试通过文本内容找到获取验证码按钮
                        buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '获取验证码') or contains(text(), '获取')]")
                        if buttons:
                            if callback: callback("找到替代的获取验证码按钮")
                            buttons[0].click()
                            return True
                    except Exception as e2:
                        if callback: callback(f"尝试替代按钮也失败: {e2}")
                        logging.error(f"尝试替代按钮也失败: {e2}")
            
            # 检查是否有其他多因子验证的元素（适配不同的多因子页面）
            
            # 检查方法1: 通过ID检查验证码输入框
            try:
                code_input = self.driver.find_element(By.ID, 'dynamicCode')
                if code_input.is_displayed():
                    if callback: callback("找到验证码输入框")
                    # 找到获取验证码按钮并点击
                    get_code_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '获取')]")
                    if get_code_buttons:
                        get_code_buttons[0].click()
                        if callback: callback("点击获取验证码按钮")
                    return True
            except:
                pass
            
            # 检查方法2: 通过页面标题或内容
            if "验证码" in self.driver.page_source and "登录" in self.driver.page_source:
                if callback: callback("页面包含验证码和登录字样，可能是多因子认证页面")
                # 尝试找到并点击获取验证码按钮
                buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '获取')]")
                if buttons:
                    buttons[0].click()
                    if callback: callback("点击获取验证码按钮")
                    return True
            
            return False
        except Exception as e:
            if callback: callback(f"检查多因子验证时出错: {e}")
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
            
            # 先尝试通过ID找到验证码输入框
            try:
                code_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, 'dynamicCode'))
                )
                if callback: callback("找到验证码输入框(通过ID)")
            except:
                if callback: callback("未通过ID找到验证码输入框，尝试其他方法")
                # 尝试通过placeholder找到验证码输入框
                code_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入' or @placeholder='请输入验证码' or contains(@placeholder, '验证码')]"))
                )
                if callback: callback("找到验证码输入框(通过placeholder)")
            
            # 输入验证码
            code_input.clear()
            code_input.send_keys(code)
            
            # 点击登录/提交按钮
            # 先尝试通过ID找到按钮
            try:
                submit_button = self.driver.find_element(By.ID, 'reAuthSubmitBtn')
                if callback: callback("找到提交按钮(通过ID)")
            except:
                if callback: callback("未通过ID找到提交按钮，尝试其他方法")
                # 尝试通过文本内容找到按钮
                submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), '登录') or contains(text(), '提交') or contains(text(), '确认')]")
                if callback: callback("找到提交按钮(通过文本)")
            
            submit_button.click()
            if callback: callback("已点击提交按钮")
            
            # 等待页面加载
            time.sleep(2)
            self.wait_for_page_load()
            
            # 尝试找到并点击"信任此设备"按钮
            try:
                # 尝试多种方式找到信任此设备按钮
                trust_buttons = []
                try:
                    # 通过class查找
                    trust_buttons = self.driver.find_elements(By.CLASS_NAME, 'trust-device-button')
                except:
                    pass
                
                if not trust_buttons:
                    try:
                        # 通过文本内容查找
                        trust_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., '信任此设备')]")
                    except:
                        pass
                
                if not trust_buttons:
                    try:
                        # 通过完整XPath查找
                        trust_buttons = self.driver.find_elements(By.XPATH, "//button[@class='trust-device-button trust-device-sub-btn']")
                    except:
                        pass
                
                if trust_buttons:
                    if callback: callback("找到'信任此设备'按钮，点击中...")
                    trust_buttons[0].click()
                    time.sleep(1)  # 等待按钮点击效果
                    if callback: callback("已点击'信任此设备'按钮")
                else:
                    if callback: callback("未找到'信任此设备'按钮，继续验证流程")
            except Exception as e:
                if callback: callback(f"处理'信任此设备'按钮时出错: {e}")
                logging.warning(f"处理'信任此设备'按钮时出错: {e}")
                # 继续流程，不要因为这个错误而中断
            
            # 等待页面加载
            time.sleep(1)
            self.wait_for_page_load()
            
            # 检查是否验证成功
            if "login" not in self.driver.current_url and "多因子" not in self.driver.page_source:
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