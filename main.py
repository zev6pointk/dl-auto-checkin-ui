import json
import os
import sys
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, font
from tkinter import messagebox

from auth import Authentication
from checkin import LibraryCheckin
from reserve import LibraryReserve

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("library_automation.log"),
        logging.StreamHandler()
    ]
)

class LibraryAutomationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("图书馆座位自动化工具")
        self.root.geometry("800x600")
        
        # 设置更清晰的字体
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Microsoft YaHei", size=10)
        self.root.option_add("*Font", self.default_font)
        
        # 用户列表排序记录
        self.user_last_used = {}
        
        # 无头模式设置
        self.headless_var = tk.BooleanVar(value=False)
        self.load_settings()
        
        # 创建UI组件
        self.create_widgets()
        
        # 尝试加载配置文件 - 确保在创建UI组件后加载配置
        self.config = self.load_config()
        
        # 初始化状态变量
        self.current_operation = None
        self.automation_thread = None
        self.current_handler = None
        self.has_error = False
        
        # 更新用户列表
        self.update_user_list()
        
        # 设置窗口最小化时的行为
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    @staticmethod
    def resource_path(relative_path):
        """ 获取资源绝对路径 """
        if hasattr(sys, '_MEIPASS'):
            # 打包后路径（临时解压目录）
            return os.path.join(sys._MEIPASS, relative_path)
        # 未打包时的开发路径
        return os.path.join(os.path.abspath("."), relative_path)

    def load_settings(self):
        """加载应用设置"""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 加载无头模式设置
                    if 'headless' in settings:
                        self.headless_var.set(settings['headless'])
                    # 加载用户使用记录
                    if 'user_last_used' in settings:
                        self.user_last_used = settings['user_last_used']
                    self.log("已加载应用设置")
            else:
                self.log("未找到设置文件，将使用默认设置")
        except Exception as e:
            self.log(f"加载设置失败: {e}")

    def save_settings(self):
        """保存应用设置"""
        try:
            settings = {
                'headless': self.headless_var.get(),
                'user_last_used': self.user_last_used
            }
            settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.json")
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log("已保存应用设置")
        except Exception as e:
            self.log(f"保存设置失败: {e}")

    def update_user_last_used(self, user):
        """更新用户最后使用时间"""
        if user:
            self.user_last_used[user] = time.time()
            self.save_settings()

    def on_close(self):
        """关闭窗口时的处理"""
        self.save_settings()
        self.root.destroy()

    def load_config(self):
        """加载配置文件（兼容打包后路径）"""
        config = {}
        
        # 加载签到配置
        try:
            checkin_path = self.resource_path('checkinConfig.json')
            if os.path.exists(checkin_path):
                with open(checkin_path, 'r', encoding='utf-8') as f:
                    config['checkin'] = json.load(f)
                self.log(f"成功加载签到配置文件: {checkin_path}")
            else:
                self.log(f"⚠️ 配置文件未找到: {checkin_path}")
        except Exception as e:
            error_msg = f"签到配置加载失败: {str(e)}"
            self.log(error_msg)
            logging.error(error_msg)
        
        # 加载预约配置
        try:
            reserve_path = self.resource_path('reserveConfig.json')
            if os.path.exists(reserve_path):
                with open(reserve_path, 'r', encoding='utf-8') as f:
                    config['reserve'] = json.load(f)
                self.log(f"成功加载预约配置文件: {reserve_path}")
            else:
                self.log(f"⚠️ 配置文件未找到: {reserve_path}")
        except Exception as e:
            error_msg = f"预约配置加载失败: {str(e)}"
            self.log(error_msg)
            logging.error(error_msg)
        
        return config
    
    def update_user_list(self):
        """更新用户列表"""
        # 从配置中获取用户列表
        self.users = []
        if 'checkin' in self.config:
            self.users.extend(list(self.config['checkin'].keys()))
        if 'reserve' in self.config:
            if 'reserveUrl' in self.config['reserve']:
                self.users.extend(list(self.config['reserve']['reserveUrl'].keys()))
        
        # 去重
        self.users = list(set([u for u in self.users if u not in ['url', 'login_url', 'sender_email', 'sender_email_password']]))
        
        # 根据最后使用时间排序
        def get_last_used_time(user):
            return self.user_last_used.get(user, 0)
        
        self.users.sort(key=get_last_used_time, reverse=True)
        
        # 更新下拉框
        if self.users:
            self.user_combo['values'] = self.users
            self.user_var.set(self.users[0])
        else:
            self.log("警告: 未找到有效用户配置")
    
    def create_widgets(self):
        """创建UI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部控制区域
        self.control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        self.control_frame.pack(fill=tk.X, pady=5)
        
        # 用户选择下拉框
        user_frame = ttk.Frame(self.control_frame)
        user_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(user_frame, text="选择用户:").pack(side=tk.LEFT, padx=5)
        
        # 用户下拉框（初始为空，稍后填充）
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(user_frame, textvariable=self.user_var)
        self.user_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 在用户选择框下方添加无头模式复选框
        headless_frame = ttk.Frame(self.control_frame)
        headless_frame.pack(fill=tk.X, pady=5)
        
        self.headless_checkbox = ttk.Checkbutton(
            headless_frame, 
            text="无头模式 (不显示浏览器窗口)", 
            variable=self.headless_var,
            command=self.save_settings
        )
        self.headless_checkbox.pack(side=tk.LEFT, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(self.control_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.checkin_button = ttk.Button(button_frame, text="签到", command=self.start_checkin)
        self.checkin_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.reserve_button = ttk.Button(button_frame, text="预约", command=self.start_reserve)
        self.reserve_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.retry_button = ttk.Button(button_frame, text="重试", command=self.retry_operation, state=tk.DISABLED)
        self.retry_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # 验证码输入区域
        self.verification_frame = ttk.LabelFrame(main_frame, text="多因子验证", padding=10)
        # 默认隐藏
        # self.verification_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.verification_frame, text="验证码:").pack(side=tk.LEFT, padx=5)
        
        self.verification_var = tk.StringVar()
        self.verification_entry = ttk.Entry(self.verification_frame, textvariable=self.verification_var, width=20, font=("Microsoft YaHei", 12))
        self.verification_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.submit_button = ttk.Button(self.verification_frame, text="提交", command=self.submit_verification)
        self.submit_button.pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        self.verification_entry.bind("<Return>", lambda event: self.submit_verification())
        
        # 状态显示区域
        self.status_frame = ttk.LabelFrame(main_frame, text="当前状态", padding=10)
        self.status_frame.pack(fill=tk.X, pady=5)
        
        # 进度步骤
        self.steps = ["登录", "多因子验证", "主操作", "完成"]
        self.step_vars = []
        self.step_labels = []
        
        for step in self.steps:
            var = tk.StringVar(value="○ " + step)
            label = ttk.Label(self.status_frame, textvariable=var, font=("Microsoft YaHei", 10))
            label.pack(anchor=tk.W, pady=2)
            self.step_vars.append(var)
            self.step_labels.append(label)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 初始日志
        self.log("应用已启动，请选择用户并开始操作")

        # 在用户选择框下方添加无头模式复选框
        headless_frame = ttk.Frame(self.control_frame)
        headless_frame.pack(fill=tk.X, pady=5)
        
        self.headless_checkbox = ttk.Checkbutton(
            headless_frame, 
            text="无头模式 (不显示浏览器窗口)", 
            variable=self.headless_var,
            command=self.save_settings
        )
        self.headless_checkbox.pack(side=tk.LEFT, padx=5)
    
    def log(self, message):
        """添加日志信息"""
        # 确保log_text已初始化
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        # 无论UI是否准备好，都记录到系统日志
        logging.info(message)
    
    def update_step(self, step_index, status):
        """更新步骤状态"""
        if step_index < 0 or step_index >= len(self.steps):
            return
        
        # 更新步骤显示
        step = self.steps[step_index]
        if status == "active":
            self.step_vars[step_index].set("● " + step)
            self.step_labels[step_index].config(foreground="#0078D7")  # 蓝色
        elif status == "completed":
            self.step_vars[step_index].set("✓ " + step)
            self.step_labels[step_index].config(foreground="#107C10")  # 绿色
        elif status == "error":
            self.step_vars[step_index].set("✗ " + step)
            self.step_labels[step_index].config(foreground="#E81123")  # 红色
            self.has_error = True
            self.root.after(0, lambda: self.retry_button.config(state=tk.NORMAL))
        else:
            self.step_vars[step_index].set("○ " + step)
            self.step_labels[step_index].config(foreground="#000000")  # 黑色
    
    def reset_steps(self):
        """重置所有步骤状态"""
        for i in range(len(self.steps)):
            self.update_step(i, "inactive")
        self.has_error = False
        self.retry_button.config(state=tk.DISABLED)

    def callback_handler(self, message):
        """统一回调处理"""
        # 在UI主线程中更新UI
        self.root.after(0, lambda: self.log(message))
        
        # 根据消息内容更新步骤状态
        lower_message = message.lower()
        
        if "登录" in lower_message:
            if "成功" in lower_message:
                self.root.after(0, lambda: self.update_step(0, "completed"))
            elif "失败" in lower_message or "错误" in lower_message:
                self.root.after(0, lambda: self.update_step(0, "error"))
            else:
                self.root.after(0, lambda: self.update_step(0, "active"))
        
        elif "验证码" in lower_message or "多因子" in lower_message:
            if "成功" in lower_message:
                self.root.after(0, lambda: self.update_step(1, "completed"))
                # 隐藏验证码输入框
                self.root.after(0, lambda: self.verification_frame.pack_forget())
            elif "失败" in lower_message or "错误" in lower_message:
                self.root.after(0, lambda: self.update_step(1, "error"))
            elif "需要" in lower_message or "等待" in lower_message:
                self.root.after(0, lambda: self.update_step(1, "active"))
                # 显示验证码输入框并确保窗口可见
                self.root.after(0, self.root.deiconify)
                self.root.after(0, lambda: self.verification_frame.pack(fill=tk.X, pady=5, after=self.control_frame))
                # 聚焦到验证码输入框
                self.root.after(100, lambda: self.verification_entry.focus_set())
                
        elif any(op in lower_message for op in ["签到", "预约"]):
            if "成功" in lower_message or "完成" in lower_message:
                if "所有" in lower_message or "流程完成" in lower_message:
                    self.root.after(0, lambda: self.update_step(2, "completed"))
                    self.root.after(0, lambda: self.update_step(3, "completed"))
                else:
                    self.root.after(0, lambda: self.update_step(2, "active"))
            elif "失败" in lower_message or "错误" in lower_message:
                self.root.after(0, lambda: self.update_step(2, "error"))
            else:
                self.root.after(0, lambda: self.update_step(2, "active"))

    def retry_operation(self):
        """重试当前操作"""
        if not self.current_operation:
            messagebox.showinfo("提示", "没有可重试的操作")
            return
        
        self.log(f"正在重试 {self.current_operation} 操作...")
        
        # 重置步骤状态
        self.reset_steps()
        
        # 检查是否已登录
        is_logged_in = False
        if self.current_handler and hasattr(self.current_handler.auth, "is_logged_in"):
            is_logged_in = self.current_handler.auth.is_logged_in
        
        # 根据当前操作类型重试
        if self.current_operation == "checkin":
            if is_logged_in:
                # 如果已登录，直接执行签到步骤
                self.log("检测到已登录状态，直接执行签到步骤")
                self.update_step(0, "completed")
                self.update_step(1, "completed")
                self.update_step(2, "active")
                
                # 在新线程中执行签到
                def run_direct_checkin():
                    try:
                        if self.current_handler:
                            # 直接执行签到操作
                            self.current_handler.driver.get(self.current_handler.checkin_url)
                            self.current_handler.auth.wait_for_page_load()
                            result = self.current_handler.perform_check_in()
                            
                            if result:
                                self.log("签到流程成功完成")
                                self.update_step(3, "completed")
                            else:
                                self.log("签到流程失败")
                                self.update_step(2, "error")
                    except Exception as e:
                        self.log(f"签到过程中出错: {e}")
                        self.update_step(2, "error")
                    finally:
                        # 重新启用按钮
                        self.root.after(0, lambda: self.checkin_button.config(state=tk.NORMAL))
                        self.root.after(0, lambda: self.reserve_button.config(state=tk.NORMAL))
                
                # 禁用按钮
                self.checkin_button.config(state=tk.DISABLED)
                self.reserve_button.config(state=tk.DISABLED)
                self.retry_button.config(state=tk.DISABLED)
                
                checkin_thread = threading.Thread(target=run_direct_checkin)
                checkin_thread.daemon = True
                checkin_thread.start()
            else:
                # 如果未登录，重新执行完整流程
                self.start_checkin(is_retry=True)
        elif self.current_operation == "reserve":
            if is_logged_in:
                # 如果已登录，直接执行预约步骤
                self.log("检测到已登录状态，直接执行预约步骤")
                self.update_step(0, "completed")
                self.update_step(1, "completed")
                self.update_step(2, "active")
                
                # 在新线程中执行预约
                def run_direct_reserve():
                    try:
                        if self.current_handler:
                            # 依次预约每个时间段
                            success_count = 0
                            for i in range(1, 8):
                                try:
                                    if self.current_handler.reserve_single_time_slot(i):
                                        success_count += 1
                                    else:
                                        self.log(f"第{i}个时段预约失败，将继续尝试下一个时段")
                                except Exception as e:
                                    self.log(f"预约第{i}个时段时发生异常: {e}，将继续尝试下一个时段")
                            
                            # 汇报结果
                            if success_count == 7:
                                self.log("所有时段预约成功")
                                self.update_step(3, "completed")
                            else:
                                self.log(f"共预约成功{success_count}个时段，{7-success_count}个时段失败")
                                if success_count > 0:
                                    self.update_step(3, "completed")
                                else:
                                    self.update_step(2, "error")
                    except Exception as e:
                        self.log(f"预约过程中出错: {e}")
                        self.update_step(2, "error")
                    finally:
                        # 重新启用按钮
                        self.root.after(0, lambda: self.checkin_button.config(state=tk.NORMAL))
                        self.root.after(0, lambda: self.reserve_button.config(state=tk.NORMAL))
                
                # 禁用按钮
                self.checkin_button.config(state=tk.DISABLED)
                self.reserve_button.config(state=tk.DISABLED)
                self.retry_button.config(state=tk.DISABLED)
                
                reserve_thread = threading.Thread(target=run_direct_reserve)
                reserve_thread.daemon = True
                reserve_thread.start()
            else:
                # 如果未登录，重新执行完整流程
                self.start_reserve(is_retry=True)
    
    def start_checkin(self, is_retry=False):
        """开始签到流程"""
        if self.current_operation and not is_retry:
            messagebox.showwarning("警告", "当前有操作正在进行，请等待完成")
            return
        
        selected_user = self.user_var.get()
        if not selected_user:
            messagebox.showerror("错误", "请选择用户")
            return
        
        # 更新用户使用记录
        self.update_user_last_used(selected_user)
        
        self.log(f"开始签到流程，用户: {selected_user}")
        self.current_operation = "checkin"
        self.reset_steps()
        self.update_step(0, "active")
        
        # 禁用按钮
        self.checkin_button.config(state=tk.DISABLED)
        self.reserve_button.config(state=tk.DISABLED)
        self.retry_button.config(state=tk.DISABLED)
        
        # 如果不是无头模式，最小化窗口
        # if not self.headless_var.get():
            # self.root.iconify()
        self.root.iconify()
        
        # 在新线程中执行签到
        def run_checkin():
            try:
                # 如果是重试且有现有实例，先关闭
                if is_retry and self.current_handler:
                    try:
                        self.current_handler.close()
                    except:
                        pass
                
                checkin = LibraryCheckin(
                    user_key=selected_user,
                    callback=self.callback_handler,
                    headless=self.headless_var.get()
                )
                self.current_handler = checkin
                
                result = checkin.run()
                
                if result == "MFA_REQUIRED":
                    # 如果需要多因子验证，显示窗口
                    self.root.after(0, self.root.deiconify)
                    # 等待用户输入验证码，不关闭
                elif result:
                    self.log("签到流程成功完成")
                    self.update_step(3, "completed")
                    checkin.close()
                    self.current_handler = None
                    self.current_operation = None
                    # 操作完成，显示窗口
                    self.root.after(0, self.root.deiconify)
                else:
                    self.log("签到流程失败")
                    # 失败时显示窗口
                    self.root.after(0, self.root.deiconify)
                    # 不关闭，允许重试
            except Exception as e:
                self.log(f"签到过程中出错: {e}")
                self.update_step(2, "error")
                # 出错时显示窗口
                self.root.after(0, self.root.deiconify)
            finally:
                # 重新启用按钮
                self.root.after(0, lambda: self.checkin_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.reserve_button.config(state=tk.NORMAL))
        
        self.automation_thread = threading.Thread(target=run_checkin)
        self.automation_thread.daemon = True
        self.automation_thread.start()
        
    def start_reserve(self, is_retry=False):
        """开始预约流程"""
        if self.current_operation and not is_retry:
            messagebox.showwarning("警告", "当前有操作正在进行，请等待完成")
            return
        
        selected_user = self.user_var.get()
        if not selected_user:
            messagebox.showerror("错误", "请选择用户")
            return
        
        # 更新用户使用记录
        self.update_user_last_used(selected_user)
        
        self.log(f"开始预约流程，用户: {selected_user}")
        self.current_operation = "reserve"
        self.reset_steps()
        self.update_step(0, "active")
        
        # 禁用按钮
        self.checkin_button.config(state=tk.DISABLED)
        self.reserve_button.config(state=tk.DISABLED)
        self.retry_button.config(state=tk.DISABLED)
        
        # 如果不是无头模式，最小化窗口
        if not self.headless_var.get():
            self.root.iconify()
        
        # 在新线程中执行预约
        def run_reserve():
            try:
                # 如果是重试且有现有实例，先关闭
                if is_retry and self.current_handler:
                    try:
                        self.current_handler.close()
                    except:
                        pass
                
                reserver = LibraryReserve(
                    user_key=selected_user,
                    callback=self.callback_handler,
                    headless=self.headless_var.get()
                )
                self.current_handler = reserver
                
                result = reserver.run()
                
                if result == "MFA_REQUIRED":
                    # 如果需要多因子验证，显示窗口
                    self.root.after(0, self.root.deiconify)
                    # 等待用户输入验证码，不关闭
                    pass
                elif result:
                    self.log("预约流程成功完成")
                    self.update_step(3, "completed")
                    reserver.close()
                    self.current_handler = None
                    self.current_operation = None
                    # 操作完成，显示窗口
                    self.root.after(0, self.root.deiconify)
                else:
                    self.log("预约流程失败")
                    # 失败时显示窗口
                    self.root.after(0, self.root.deiconify)
                    # 不关闭，允许重试
                    # self.current_handler = None
                    # self.current_operation = None
            except Exception as e:
                self.log(f"预约过程中出错: {e}")
                self.update_step(2, "error")
                # 出错时显示窗口
                self.root.after(0, self.root.deiconify)
                # 不关闭，允许重试
                # if self.current_handler:
                #     self.current_handler.close()
                # self.current_handler = None
                # self.current_operation = None
            finally:
                # 重新启用按钮
                self.root.after(0, lambda: self.checkin_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.reserve_button.config(state=tk.NORMAL))
        
        self.automation_thread = threading.Thread(target=run_reserve)
        self.automation_thread.daemon = True
        self.automation_thread.start()

    def submit_verification(self):
        """提交验证码"""
        if not self.current_handler or not self.current_operation:
            messagebox.showerror("错误", "没有等待验证的操作")
            return
        
        code = self.verification_var.get().strip()
        if not code:
            messagebox.showerror("错误", "请输入验证码")
            return
        
        self.log(f"提交验证码: {code}")
        
        # 清空验证码输入框并隐藏
        self.verification_var.set("")
        self.verification_frame.pack_forget()
        
        # 在新线程中继续执行流程
        def continue_with_verification():
            try:
                result = self.current_handler.continue_with_verification(code)
                
                if result:
                    self.log(f"{self.current_operation}流程成功完成")
                    self.update_step(3, "completed")
                    self.current_handler.close()
                    self.current_handler = None
                    self.current_operation = None
                else:
                    self.log(f"{self.current_operation}流程失败")
                    # 不关闭，允许重试
                    # self.current_handler.close()
                    # self.current_handler = None
                    # self.current_operation = None
            except Exception as e:
                self.log(f"验证后流程中出错: {e}")
                self.update_step(2, "error")
                # 不关闭，允许重试
                # if self.current_handler:
                #     self.current_handler.close()
                # self.current_handler = None
                # self.current_operation = None
            finally:
                # 重新启用按钮
                self.root.after(0, lambda: self.checkin_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.reserve_button.config(state=tk.NORMAL))
        
        verify_thread = threading.Thread(target=continue_with_verification)
        verify_thread.daemon = True
        verify_thread.start()

def main():
    root = tk.Tk()
    app = LibraryAutomationUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()