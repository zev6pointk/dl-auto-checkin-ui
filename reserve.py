import json
import datetime
import os
import sys
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seat_status import SeatStatusHandler
from auth import Authentication

class LibraryReserve:
    def __init__(self, driver=None, user_key=None, config_path='reserveConfig.json', callback=None, headless=False):
        """
        初始化图书馆预约类
        
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
            self.callback(f"成功加载预约配置文件")
        except Exception as e:
            error_msg = f"加载预约配置文件失败: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            self.config = {}
        
        # 初始化认证模块
        self.auth = Authentication(driver=driver, config_path=config_path, user_key=user_key, headless=headless)
        self.driver = self.auth.driver
        
        # 检查用户配置
        try:
            if 'reserveUrl' in self.config and user_key in self.config['reserveUrl']:
                self.user_config = self.config['reserveUrl'][user_key]
                self.callback(f"成功加载用户 {user_key} 的预约配置")
            else:
                error_msg = f"错误: 在配置中找不到用户 {user_key} 的预约配置"
                self.callback(error_msg)
                logging.error(error_msg)
                self.user_config = None
        except Exception as e:
            error_msg = f"加载用户 {user_key} 预约配置时出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            self.user_config = None
        
        # 预约时间段设置
        self.index_arr = [
            [],
            [["08", "00"], ["09", "59"]],
            [["10", "00"], ["11", "59"]],
            [["12", "30"], ["14", "29"]],
            [["14", "30"], ["16", "19"]],
            [["16", "20"], ["18", "19"]],
            [["18", "20"], ["20", "19"]],
            [["20", "20"], ["22", "00"]]
        ]
        
        self.should_stop = False
    
    def stop_operation(self):
        """终止当前操作"""
        self.should_stop = True
        self.callback("已接收终止指令，将在完成当前步骤后停止")


    @staticmethod
    def resource_path(relative_path):
        """ 获取资源绝对路径（支持外部文件）"""
        if hasattr(sys, '_MEIPASS'):
            # 打包后路径：改用 exe 所在目录而非临时目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 未打包时的开发路径
            base_path = os.path.abspath(".")
            
        return os.path.join(base_path, relative_path)

    def build_reservation_url(self, time_index):
        """
        构建预约URL
        
        参数:
            time_index: 时间段索引 (1-7)
        
        返回:
            str: 预约URL
        """
        try:
            # 检查用户配置
            if not self.user_config:
                self.callback("错误: 缺少用户配置，无法构建预约URL")
                return None
                
            # 获取两天后的日期
            two_days_later = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
            
            # 获取时间段
            if time_index < 1 or time_index > 7:
                self.callback(f"错误: 无效的时间段索引 {time_index}，有效范围是1-7")
                return None
                
            time_slot = self.index_arr[time_index]
            start_hour, start_min = time_slot[0]
            end_hour, end_min = time_slot[1]
            
            # 构建URL
            base_url = "https://webvpn3.hebau.edu.cn/https/77726476706e69737468656265737421f5ff40902b7e60557c099ce29d51367b21a6/qljfwapp/sys/lwAppointmentPublicPlace/*default/index.do"
            
            url = f"{base_url}#/seatdetail?USER_ID={self.user_config['username']}&USER_NAME={self.user_config['real_name']}&DEPT_CODE=423&DEPT_NAME=%E4%BF%A1%E6%81%AF%E7%A7%91%E5%AD%A6%E4%B8%8E%E6%8A%80%E6%9C%AF%E5%AD%A6%E9%99%A2&PHONE_NUMBER={self.user_config['phone_number']}&PALCE_ID=fb9dedd807fc48a59dc19338a50ea099"
            url += f"&BEGINNING_DATE={two_days_later}%20{start_hour}%3A{start_min}&ENDING_DATE={two_days_later}%20{end_hour}%3A{end_min}"
            url += f"&SCHOOL_DISTRICT_CODE=1&SCHOOL_DISTRICT=%E4%B8%9C%E6%A0%A1%E5%8C%BA&LOCATION=%E4%BA%8C%E5%B1%82%E3%80%81%E4%B8%89%E5%B1%82&PLACE_NAME=%E4%B8%9C%E6%A0%A1%E5%8C%BA%E6%95%B0%E5%AD%97%E5%8C%96%E5%9B%BE%E4%B9%A6%E9%A6%86"
            url += f"&IS_CANCELLED=0&APPLY_DATE={two_days_later}&APPLY_TIME_AREA={start_hour}%3A{start_min}-{end_hour}%3A{end_min}"
            
            self.callback(f"构建了预约URL，时间段: {start_hour}:{start_min}-{end_hour}:{end_min}")
            return url
        except Exception as e:
            error_msg = f"构建预约URL时出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return None
    
    def reserve_single_time_slot(self, time_index):
        """
        预约单个时间段
        
        参数:
            time_index: 时间段索引 (1-7)
        
        返回:
            bool: 预约是否成功
        """
        max_retries = 2  # 最大重试次数
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # 计算实际开始时间
                start_time = 6 + time_index * 2
                self.callback(f"开始预约第{time_index}个时段 ({start_time}点){' - 重试尝试' + str(retry_count) if retry_count > 0 else ''}")
                
                # 构建并打开预约URL
                reservation_url = self.build_reservation_url(time_index)
                if not reservation_url:
                    self.callback(f"无法为第{time_index}个时段生成预约URL")
                    return False
                    
                self.driver.get(reservation_url)
                # 增加等待时间，确保页面完全加载
                self.auth.wait_for_page_load(timeout=30)
                # 额外短暂等待，确保JS渲染完成
                time.sleep(2)
                
                # 选择区域
                try:
                    if 'selectArea' not in self.config:
                        self.callback("错误: 配置中缺少selectArea")
                        return False
                    
                    # 使用更稳定的等待策略
                    select_area = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, self.config['selectArea']))
                    )
                    self.callback("找到区域选择按钮")
                    select_area.click()
                    time.sleep(1)  # 短暂等待点击效果
                    self.auth.wait_for_page_load()
                    
                    # 选择东C
                    if 'eastC' not in self.config:
                        self.callback("错误: 配置中缺少eastC")
                        return False
                    
                    # 刷新元素引用，避免stale元素
                    east_c = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, self.config['eastC']))
                    )
                    self.callback("找到东C选项")
                    east_c.click()
                    time.sleep(1)  # 短暂等待点击效果
                    self.auth.wait_for_page_load()
                    
                    # 选择座位
                    if 'seat_xpath' not in self.user_config:
                        self.callback("错误: 用户配置中缺少seat_xpath")
                        return False
                    
                    preferred_seat_xpath = self.user_config['seat_xpath']
                    self.callback(f"首选座位位置: {preferred_seat_xpath}")
                    
                    # 使用座位状态处理器
                    seat_handler = SeatStatusHandler(self.driver, self.callback)
                    
                    # 获取是否允许尝试替代座位的配置
                    try_alternatives = self.user_config.get('try_alternative_seats', True)
                    
                    # 处理座位选择
                    success, status, used_seat_xpath = seat_handler.handle_seat_selection(
                        preferred_seat_xpath, 
                        try_alternatives=try_alternatives
                    )
                    
                    # 根据座位状态进行不同处理
                    if status == 2:  # 座位已被自己预约
                        self.callback(f"第{time_index}个时段座位已被您预约，视为成功")
                        return True
                        
                    elif not success:  # 座位选择失败
                        if status == 3:  # 座位已被他人预约且无法找到替代座位
                            self.callback(f"第{time_index}个时段座位已被他人预约，且无法找到替代座位")
                        else:
                            self.callback(f"第{time_index}个时段座位选择失败")
                        
                        # 记录详细原因到日志，以供后续分析
                        logging.warning(f"时间段{time_index}预约失败，座位状态码: {status}")
                        
                        retry_count += 1
                        if retry_count <= max_retries:
                            self.callback(f"将进行第{retry_count}次重试...")
                            time.sleep(2)  # 短暂等待后重试
                            continue
                        else:
                            return False
                    
                    # 点击确定
                    if 'confirmButton' not in self.config:
                        self.callback("错误: 配置中缺少confirmButton")
                        return False
                    
                    # 再次刷新元素引用
                    confirm_button = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, self.config['confirmButton']))
                    )
                    confirm_button.click()
                    
                    # 等待预约完成
                    time.sleep(2)  # 确保操作完成
                    self.auth.wait_for_page_load()
                    
                    # 验证预约是否成功
                    try:
                        # 查找可能的成功提示消息
                        success_message = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '成功') or contains(text(), '预约成功')]"))
                        )
                        self.callback(f"第{time_index}个时段预约成功 ({start_time}点)")
                        return True
                    except:
                        # 如果找不到成功消息，检查页面状态
                        if "预约成功" in self.driver.page_source:
                            self.callback(f"第{time_index}个时段预约成功 ({start_time}点)")
                            return True
                        else:
                            self.callback(f"未找到成功提示，可能预约失败")
                            
                            # 再次尝试
                            retry_count += 1
                            if retry_count <= max_retries:
                                self.callback(f"将进行第{retry_count}次重试...")
                                time.sleep(2)  # 短暂等待后重试
                                continue
                            else:
                                return False
                except Exception as e:
                    error_msg = f"预约第{time_index}个时段过程中出错: {e}"
                    self.callback(error_msg)
                    logging.error(error_msg)
                    
                    retry_count += 1
                    if retry_count <= max_retries:
                        self.callback(f"将进行第{retry_count}次重试...")
                        time.sleep(2)  # 短暂等待后重试
                        continue
                    else:
                        return False
            except Exception as e:
                error_msg = f"预约第{time_index}个时段失败: {e}"
                self.callback(error_msg)
                logging.error(error_msg)
                
                retry_count += 1
                if retry_count <= max_retries:
                    self.callback(f"将进行第{retry_count}次重试...")
                    time.sleep(2)  # 短暂等待后重试
                    continue
                else:
                    return False
        
        return False  # 所有重试都失败

    def build_reservation_url(self, time_index, days_ahead=2):
        """
        构建预约URL
        
        参数:
            time_index: 时间段索引 (1-7)
            days_ahead: 提前预约的天数，默认2天后
        
        返回:
            str: 预约URL
        """
        try:
            # 检查用户配置
            if not self.user_config:
                self.callback("错误: 缺少用户配置，无法构建预约URL")
                return None
                
            # 获取指定天数后的日期
            target_date = (datetime.datetime.now() + datetime.timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            self.callback(f"预约目标日期: {target_date} (提前{days_ahead}天)")
            
            # 获取时间段
            if time_index < 1 or time_index > 7:
                self.callback(f"错误: 无效的时间段索引 {time_index}，有效范围是1-7")
                return None
                
            time_slot = self.index_arr[time_index]
            start_hour, start_min = time_slot[0]
            end_hour, end_min = time_slot[1]
            
            # 构建URL
            base_url = "https://webvpn3.hebau.edu.cn/https/77726476706e69737468656265737421f5ff40902b7e60557c099ce29d51367b21a6/qljfwapp/sys/lwAppointmentPublicPlace/*default/index.do"
            
            url = f"{base_url}#/seatdetail?USER_ID={self.user_config['username']}&USER_NAME={self.user_config['real_name']}&DEPT_CODE=423&DEPT_NAME=%E4%BF%A1%E6%81%AF%E7%A7%91%E5%AD%A6%E4%B8%8E%E6%8A%80%E6%9C%AF%E5%AD%A6%E9%99%A2&PHONE_NUMBER={self.user_config['phone_number']}&PALCE_ID=fb9dedd807fc48a59dc19338a50ea099"
            url += f"&BEGINNING_DATE={target_date}%20{start_hour}%3A{start_min}&ENDING_DATE={target_date}%20{end_hour}%3A{end_min}"
            url += f"&SCHOOL_DISTRICT_CODE=1&SCHOOL_DISTRICT=%E4%B8%9C%E6%A0%A1%E5%8C%BA&LOCATION=%E4%BA%8C%E5%B1%82%E3%80%81%E4%B8%89%E5%B1%82&PLACE_NAME=%E4%B8%9C%E6%A0%A1%E5%8C%BA%E6%95%B0%E5%AD%97%E5%8C%96%E5%9B%BE%E4%B9%A6%E9%A6%86"
            url += f"&IS_CANCELLED=0&APPLY_DATE={target_date}&APPLY_TIME_AREA={start_hour}%3A{start_min}-{end_hour}%3A{end_min}"
            
            self.callback(f"构建了预约URL，时间段: {start_hour}:{start_min}-{end_hour}:{end_min}")
            return url
        except Exception as e:
            error_msg = f"构建预约URL时出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return None


    def run(self):
        """执行完整的预约流程"""
        try:
            self.should_stop = False
            self.callback("开始预约流程...")
            
            # 检查用户配置
            if not self.user_config:
                self.callback("错误: 用户配置缺失，无法继续预约")
                return False
            
            # 先登录
            self.callback("准备登录...")
            login_result = self.auth.login(callback=self.callback)
            
            # 处理多因子验证
            if login_result == "MFA_REQUIRED":
                self.callback("等待验证码输入...")
                return "MFA_REQUIRED"
            
            # 检查登录是否成功
            if not self.auth.is_logged_in:
                self.callback("登录失败，无法继续预约")
                return False
            
            # 依次预约每个时间段
            success_count = 0
            for i in range(1, 8):
                # 检查是否应该终止
                if self.should_stop:
                    self.callback(f"操作已终止，已成功预约{success_count}个时段")
                    return success_count > 0
                    
                try:
                    if self.reserve_single_time_slot(i):
                        success_count += 1
                    else:
                        self.callback(f"第{i}个时段预约失败，将继续尝试下一个时段")
                except Exception as e:
                    self.callback(f"预约第{i}个时段时发生异常: {e}，将继续尝试下一个时段")
            
            # 汇报结果
            if success_count == 7:
                self.callback("所有时段预约成功")
            else:
                self.callback(f"共预约成功{success_count}个时段，{7-success_count}个时段失败")
            
            return success_count > 0
            
        except Exception as e:
            error_msg = f"预约过程中出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return False


    def continue_with_verification(self, code):
        """提交验证码并继续预约流程"""
        try:
            # 提交验证码
            verification_result = self.auth.submit_verification_code(code, callback=self.callback)
            
            if not verification_result:
                self.callback("验证码验证失败")
                return False
            
            # 检查用户配置
            if not self.user_config:
                self.callback("错误: 用户配置缺失，无法继续预约")
                return False
            
            # 依次预约每个时间段
            success_count = 0
            for i in range(1, 8):
                try:
                    if self.reserve_single_time_slot(i):
                        success_count += 1
                    else:
                        self.callback(f"第{i}个时段预约失败，将继续尝试下一个时段")
                except Exception as e:
                    self.callback(f"预约第{i}个时段时发生异常: {e}，将继续尝试下一个时段")
            
            # 汇报结果
            if success_count == 7:
                self.callback("所有时段预约成功")
            else:
                self.callback(f"共预约成功{success_count}个时段，{7-success_count}个时段失败")
            
            return success_count > 0
            
        except Exception as e:
            error_msg = f"验证后预约过程中出错: {e}"
            self.callback(error_msg)
            logging.error(error_msg)
            return False
    
    def close(self):
        """关闭预约模块（清理资源）"""
        try:
            self.auth.close()
        except Exception as e:
            logging.error(f"关闭预约模块时出错: {e}")

# 如果直接运行该模块，执行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s: %(message)s')
    
    # 测试预约功能
    reserver = LibraryReserve(user_key='LZ', callback=print)
    result = reserver.run()
    
    if result == "MFA_REQUIRED":
        print("请输入验证码:")
        code = input()
        reserver.continue_with_verification(code)
    
    time.sleep(5)
    reserver.close()