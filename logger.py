import logging
import os
import time
from datetime import datetime

class Logger:
    """日志处理类"""
    
    def __init__(self, log_file='library_automation.log', level=logging.INFO, callback=None):
        self.callback = callback
        self.log_file = log_file
        
        # 配置日志
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('library_automation')
    
    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)
        if self.callback:
            self.callback(message)
            
    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(f"⚠️ {message}")
        if self.callback:
            self.callback(f"⚠️ {message}")
            
    def error(self, message):
        """记录错误日志"""
        self.logger.error(f"❌ {message}")
        if self.callback:
            self.callback(f"❌ {message}")
            
    def success(self, message):
        """记录成功日志"""
        self.logger.info(f"✅ {message}")
        if self.callback:
            self.callback(f"✅ {message}")
            
    def create_session_log(self, operation_type, user):
        """创建会话日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        session_log = os.path.join(log_dir, f"{operation_type}_{user}_{timestamp}.log")
        
        # 添加文件处理器
        file_handler = logging.FileHandler(session_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
        self.logger.addHandler(file_handler)
        
        self.info(f"创建会话日志: {session_log}")
        return file_handler
        
    def close_session_log(self, handler):
        """关闭会话日志处理器"""
        if handler:
            self.logger.removeHandler(handler)
            handler.close()
