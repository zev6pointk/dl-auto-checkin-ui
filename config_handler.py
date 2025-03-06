import json
import os
import logging
from utils import resource_path

class ConfigHandler:
    """处理配置文件读取和管理"""
    
    def __init__(self, callback=None):
        self.callback = callback or (lambda msg: None)
        self.checkin_config = None
        self.reserve_config = None
        self.app_settings = None
        
    def log(self, message):
        """记录日志并通过回调通知"""
        self.callback(message)
        logging.info(message)
        
    def load_checkin_config(self, path='checkinConfig.json'):
        """加载签到配置文件"""
        try:
            config_path = resource_path(path)
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.checkin_config = json.load(f)
                self.log(f"成功加载签到配置文件: {path}")
                return self.checkin_config
            else:
                self.log(f"⚠️ 签到配置文件未找到: {path}")
                return None
        except Exception as e:
            self.log(f"加载签到配置文件失败: {e}")
            return None
            
    def load_reserve_config(self, path='reserveConfig.json'):
        """加载预约配置文件"""
        try:
            config_path = resource_path(path)
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.reserve_config = json.load(f)
                self.log(f"成功加载预约配置文件: {path}")
                return self.reserve_config
            else:
                self.log(f"⚠️ 预约配置文件未找到: {path}")
                return None
        except Exception as e:
            self.log(f"加载预约配置文件失败: {e}")
            return None
            
    def load_app_settings(self, path='app_settings.json'):
        """加载应用设置文件"""
        try:
            settings_path = resource_path(path)
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    self.app_settings = json.load(f)
                self.log("已加载应用设置")
                return self.app_settings
            else:
                self.log("未找到设置文件，将使用默认设置")
                self.app_settings = {
                    'headless': False,
                    'user_last_used': {}
                }
                return self.app_settings
        except Exception as e:
            self.log(f"加载设置失败: {e}")
            self.app_settings = {
                'headless': False,
                'user_last_used': {}
            }
            return self.app_settings
            
    def save_app_settings(self, settings, path='app_settings.json'):
        """保存应用设置"""
        try:
            settings_path = resource_path(path)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log("已保存应用设置")
            return True
        except Exception as e:
            self.log(f"保存设置失败: {e}")
            return False
            
    def get_user_config(self, config_type, user_key):
        """获取特定用户的配置"""
        try:
            if config_type == 'checkin':
                if not self.checkin_config:
                    self.load_checkin_config()
                if self.checkin_config and user_key in self.checkin_config:
                    return self.checkin_config[user_key]
            elif config_type == 'reserve':
                if not self.reserve_config:
                    self.load_reserve_config()
                if self.reserve_config and 'reserveUrl' in self.reserve_config:
                    if user_key in self.reserve_config['reserveUrl']:
                        return self.reserve_config['reserveUrl'][user_key]
            
            self.log(f"未找到用户 {user_key} 的 {config_type} 配置")
            return None
        except Exception as e:
            self.log(f"获取用户配置时出错: {e}")
            return None
