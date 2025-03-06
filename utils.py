import os
import sys
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait

def resource_path(relative_path):
    """获取资源绝对路径（支持打包后的路径）"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后路径：使用 exe 所在目录而非临时目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 未打包时的开发路径
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

def wait_for_page_load(driver, timeout=30):
    """等待页面完全加载"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        # 额外等待确保JS渲染完成
        time.sleep(1)
        return True
    except Exception as e:
        logging.warning(f"页面加载超时: {e}")
        return False

def safe_click(element, wait_time=1):
    """安全点击元素并等待"""
    try:
        element.click()
        time.sleep(wait_time)  # 等待点击效果
        return True
    except Exception as e:
        logging.error(f"点击元素时出错: {e}")
        return False
    