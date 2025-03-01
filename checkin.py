import json
import logging
import os
import sys
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from auth import Authentication

class LibraryCheckin:
    def __init__(self, driver=None, user_key=None, config_path='checkinConfig.json', callback=None):
        """
        初始化图书馆签到类
        
        参数:
            driver: WebDriver实例，如果为None则创建新实例
            user_key: 用户配置键名
            config_path: 配置文件路径
            callback: 回调函数，用于报告状态更新
        """
        self.user_key = user_key
        self.callback = callback or (lambda msg: None)  # 默认回调为空函数
        
        # 加载配置
        try:
            with open(self.resource_path(config_path), 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.callback(f"成功加载签到配置文件")
        except Exception as e:
            error_msg = f"加载签到配置文件失败: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            self.config = {}
        
        # 初始化认证模块
        self.auth = Authentication(driver=driver, config_path=config_path, user_key=user_key)
        self.driver = self.auth.driver
        
        # 获取座位ID
        try:
            if user_key in self.config:
                self.seat_id = self.config[user_key]['seat_id']
                self.username = self.config[user_key]['username']
                self.password = self.config[user_key]['password']
                self.callback(f"成功加载用户 {user_key} 的签到配置")
            else:
                error_msg = f"错误: 在配置中找不到用户 {user_key}"
                self.callback(error_msg)
                logging.error(error_msg)
                self.seat_id = None
                self.username = None
                self.password = None
        except Exception as e:
            error_msg = f"加载用户 {user_key} 配置时出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            self.seat_id = None
            self.username = None
            self.password = None
        
        # 构建签到URL
        if self.seat_id:
            self.checkin_url = f"https://webvpn3.hebau.edu.cn/https/77726476706e69737468656265737421f5ff40902b7e60557c099ce29d51367b21a6/qljfwapp/sys/lwAppointmentPublicPlace/*default/index.do?placeId=fb9dedd807fc48a59dc19338a50ea099&seatId={self.seat_id}#/checkinBySeat"
            self.callback(f"座位ID: {self.seat_id}")
        else:
            self.checkin_url = None
            self.callback("警告: 未设置座位ID，无法构建签到URL")
    
    @staticmethod
    def resource_path(relative_path):
        """ 获取资源绝对路径 """
        if hasattr(sys, '_MEIPASS'):
            # 打包后路径（临时解压目录）
            return os.path.join(sys._MEIPASS, relative_path)
        # 未打包时的开发路径
        return os.path.join(os.path.abspath("."), relative_path)

    def perform_check_in(self):
        """执行签到操作"""
        try:
            self.callback("正在执行签到操作...")
            
            # 等待签到按钮出现
            check_in_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[2]/div/button"))
            )
            
            # 点击签到按钮
            check_in_button.click()
            self.callback("签到成功")
            
            # 等待确认
            try:
                # 查找可能的成功消息元素（根据实际页面元素调整）
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '成功') or contains(text(), '签到成功')]"))
                )
            except:
                pass  # 即使没有确认消息也继续执行
            
            return True
        except Exception as e:
            error_msg = f"签到失败: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return False
    
    def run(self):
        """执行完整的签到流程"""
        try:
            # 检查是否有签到URL
            if not self.checkin_url:
                self.callback("错误: 未设置签到URL，无法继续")
                return False
                
            # 打开签到页面
            self.callback("正在打开签到页面...")
            self.driver.get(self.checkin_url)
            self.auth.wait_for_page_load()
            
            # 检查是否需要登录
            if "login" in self.driver.current_url:
                self.callback("需要登录")
                if not self.username or not self.password:
                    self.callback("错误: 用户名或密码未设置，无法登录")
                    return False
                    
                login_result = self.auth.login(
                    username=self.username,
                    password=self.password,
                    callback=self.callback
                )
                
                # 处理多因子验证
                if login_result == "MFA_REQUIRED":
                    self.callback("等待验证码输入...")
                    return "MFA_REQUIRED"
                
                # 检查登录是否成功
                if not self.auth.is_logged_in:
                    self.callback("登录失败，无法继续签到")
                    return False
                
                # 再次打开签到页面
                self.driver.get(self.checkin_url)
                self.auth.wait_for_page_load()
            
            # 执行签到
            checkin_result = self.perform_check_in()
            
            if checkin_result:
                self.callback("签到流程完成")
                return True
            else:
                self.callback("签到失败")
                return False
            
        except Exception as e:
            error_msg = f"签到过程中出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return False
    
    def continue_with_verification(self, code):
        """提交验证码并继续签到流程"""
        try:
            # 提交验证码
            verification_result = self.auth.submit_verification_code(code, callback=self.callback)
            
            if not verification_result:
                self.callback("验证码验证失败")
                return False
            
            # 继续签到流程
            if not self.checkin_url:
                self.callback("错误: 未设置签到URL，无法继续")
                return False
                
            self.driver.get(self.checkin_url)
            self.auth.wait_for_page_load()
            
            # 执行签到
            return self.perform_check_in()
            
        except Exception as e:
            error_msg = f"验证后签到过程中出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return False
    
    def close(self):
        """关闭签到模块（清理资源）"""
        try:
            self.auth.close()
        except Exception as e:
            logging.error(f"关闭签到模块时出错: {e}")

# 如果直接运行该模块，执行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s: %(message)s')
    
    # 测试签到功能
    checker = LibraryCheckin(user_key='LZ', callback=print)
    result = checker.run()
    
    if result == "MFA_REQUIRED":
        print("请输入验证码:")
        code = input()
        checker.continue_with_verification(code)
    
    time.sleep(5)
    checker.close()