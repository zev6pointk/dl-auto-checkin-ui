import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class SeatStatusHandler:
    """处理座位状态识别和相关操作的类"""
    
    def __init__(self, driver, callback=None):
        self.driver = driver
        self.callback = callback or (lambda msg: None)
        
    def log(self, message):
        """记录日志并通过回调通知"""
        self.callback(message)
        logging.info(message)
        
    def detect_seat_status(self, seat_xpath):
        """
        检测座位状态
        
        返回:
            0: 未找到座位
            1: 座位可预约（蓝色，active）
            2: 座位已被自己预约（绿色+黄色边框，myBooked）
            3: 座位已被他人预约（绿色，booked）
        """
        try:
            # 当前问题：seat_xpath是指向p元素而不是外层div的
            # 我们需要找到包含该p元素的外层div
            
            # 1. 首先确认元素存在
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, seat_xpath))
            )
            
            # 2. 获取父元素div（包含类信息的容器）
            # 假设seat_xpath指向的是p.grid-cell-info元素
            container_xpath = f"({seat_xpath})/ancestor::div[contains(@class, 'grid-cell-container')]"
            
            container_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, container_xpath))
            )
            
            # 获取class属性来判断状态
            class_attr = container_element.get_attribute("class")
            
            self.log(f"座位容器class: {class_attr}")
            
            if "myBooked" in class_attr:
                self.log("检测到座位已被自己预约")
                return 2
            elif "booked" in class_attr:
                self.log("检测到座位已被他人预约")
                return 3
            elif "active" in class_attr:
                self.log("检测到座位可预约")
                return 1
            else:
                self.log(f"未能识别座位状态: {class_attr}")
                return 0
                
        except TimeoutException:
            self.log("等待座位元素超时，未找到座位")
            return 0     
    def find_alternative_seat(self, preferred_seat_xpath):
        """
        当首选座位不可用时，寻找替代座位
        
        返回:
            替代座位的xpath或None
        """
        try:
            # 尝试获取所有可预约的座位
            available_seats = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'grid-cell-container active')]")
            
            if not available_seats:
                self.log("没有找到可用的替代座位")
                return None
                
            self.log(f"找到 {len(available_seats)} 个可用替代座位")
            
            # 返回第一个可用座位
            first_seat = available_seats[0]
            
            # 获取座位编号
            try:
                seat_info = first_seat.find_element(By.XPATH, ".//p[@class='grid-cell-info']").text
                self.log(f"选择替代座位: {seat_info}")
            except:
                self.log("找到替代座位但无法获取座位编号")
            
            # 直接返回这个座位元素的XPath
            seat_id = first_seat.get_attribute("data-id")
            alternative_xpath = f"//div[contains(@class, 'grid-cell-container') and @data-id='{seat_id}']"
            
            return alternative_xpath
            
        except Exception as e:
            self.log(f"寻找替代座位时出错: {e}")
            return None
            
    def handle_seat_selection(self, preferred_seat_xpath, try_alternatives=True, max_retries=3):
        """
        处理座位选择，包括状态检测和处理
        
        参数:
            preferred_seat_xpath: 首选座位XPath
            try_alternatives: 是否尝试寻找替代座位
            max_retries: 最大重试次数
            
        返回:
            (成功标志, 座位状态码, 使用的座位XPath)
        """
        retry_count = 0
        
        while retry_count < max_retries:
            # 等待页面加载完成
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except:
                self.log("等待页面加载超时，继续尝试...")
            
            # 短暂等待确保JS渲染完成
            time.sleep(2)
            
            # 检测首选座位状态
            seat_status = self.detect_seat_status(preferred_seat_xpath)
            
            if seat_status == 1:  # 座位可预约
                try:
                    # 确保点击的是容器而不是内部元素
                    container_xpath = f"({preferred_seat_xpath})/ancestor::div[contains(@class, 'grid-cell-container')]"
                    
                    seat = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, container_xpath))
                    )
                    seat.click()
                    time.sleep(1)  # 等待点击效果
                    
                    self.log("成功选择首选座位")
                    return True, seat_status, preferred_seat_xpath
                    
                except Exception as e:
                    self.log(f"点击首选座位时出错: {e}")
                    retry_count += 1
                    
            elif seat_status == 2:  # 座位已被自己预约
                self.log("该座位已被您预约，无需再次预约")
                return True, seat_status, preferred_seat_xpath
                
            elif seat_status == 3:  # 座位已被他人预约
                self.log("该座位已被他人预约")
                
                if try_alternatives:
                    self.log("正在寻找替代座位...")
                    alternative_seat = self.find_alternative_seat(preferred_seat_xpath)
                    
                    if alternative_seat:
                        self.log(f"尝试使用替代座位: {alternative_seat}")
                        try:
                            # 点击替代座位
                            alt_seat = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, alternative_seat))
                            )
                            alt_seat.click()
                            time.sleep(1)  # 等待点击效果
                            
                            self.log("成功选择替代座位")
                            return True, 1, alternative_seat  # 返回状态为可预约
                            
                        except Exception as e:
                            self.log(f"点击替代座位时出错: {e}")
                            retry_count += 1
                    else:
                        self.log("未找到可用的替代座位")
                        return False, seat_status, preferred_seat_xpath
                else:
                    self.log("不尝试替代座位，返回失败")
                    return False, seat_status, preferred_seat_xpath
                    
            else:  # 未找到座位或其他问题
                self.log("座位状态未知或无法识别，尝试重新加载页面")
                
                # 尝试刷新页面
                try:
                    self.driver.refresh()
                    time.sleep(3)  # 等待刷新完成
                except:
                    pass
                    
                retry_count += 1
            
            if retry_count < max_retries:
                self.log(f"将进行第 {retry_count+1} 次座位选择尝试...")
                time.sleep(2)  # 短暂等待后重试
        
        self.log(f"座位选择失败，已尝试 {max_retries} 次")
        return False, 0, preferred_seat_xpath