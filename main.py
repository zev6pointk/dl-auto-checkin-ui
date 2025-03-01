import json
import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
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
        
        # 尝试加载配置文件
        self.config = self.load_config()
        
        # 创建UI组件
        self.create_widgets()
        
        # 初始化状态变量
        self.current_operation = None
        self.automation_thread = None
        self.current_handler = None
    
    def load_config(self):
        """加载配置文件"""
        config = {}
        try:
            # 尝试加载签到配置
            if os.path.exists('checkinConfig.json'):
                with open('checkinConfig.json', 'r', encoding='utf-8') as f:
                    config['checkin'] = json.load(f)
            
            # 尝试加载预约配置
            if os.path.exists('reserveConfig.json'):
                with open('reserveConfig.json', 'r', encoding='utf-8') as f:
                    config['reserve'] = json.load(f)
            
            return config
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return {}
    
    def create_widgets(self):
        """创建UI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部控制区域
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=5)
        
        # 用户选择下拉框
        user_frame = ttk.Frame(control_frame)
        user_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(user_frame, text="选择用户:").pack(side=tk.LEFT, padx=5)
        
        # 从配置中获取用户列表
        self.users = []
        if 'checkin' in self.config:
            self.users.extend(list(self.config['checkin'].keys()))
        if 'reserve' in self.config:
            if 'reserveUrl' in self.config['reserve']:
                self.users.extend(list(self.config['reserve']['reserveUrl'].keys()))
        
        # 去重
        self.users = list(set([u for u in self.users if u not in ['url', 'sender_email', 'sender_email_password']]))
        
        # 用户下拉框
        self.user_var = tk.StringVar()
        if self.users:
            self.user_var.set(self.users[0])
        
        self.user_combo = ttk.Combobox(user_frame, textvariable=self.user_var, values=self.users)
        self.user_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.checkin_button = ttk.Button(button_frame, text="签到", command=self.start_checkin)
        self.checkin_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.reserve_button = ttk.Button(button_frame, text="预约", command=self.start_reserve)
        self.reserve_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # 验证码输入区域
        self.verification_frame = ttk.LabelFrame(main_frame, text="多因子验证", padding=10)
        # 默认隐藏
        # self.verification_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.verification_frame, text="验证码:").pack(side=tk.LEFT, padx=5)
        
        self.verification_var = tk.StringVar()
        self.verification_entry = ttk.Entry(self.verification_frame, textvariable=self.verification_var, width=20)
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
            label = ttk.Label(self.status_frame, textvariable=var)
            label.pack(anchor=tk.W, pady=2)
            self.step_vars.append(var)
            self.step_labels.append(label)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 初始日志
        self.log("应用已启动，请选择用户并开始操作")
    
    def log(self, message):
        """添加日志信息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        logging.info(message)
    
    def update_step(self, step_index, status):
        """更新步骤状态"""
        if step_index < 0 or step_index >= len(self.steps):
            return
        
        # 更新步骤显示
        step = self.steps[step_index]
        if status == "active":
            self.step_vars[step_index].set("● " + step)
            self.step_labels[step_index].config(foreground="blue")
        elif status == "completed":
            self.step_vars[step_index].set("✓ " + step)
            self.step_labels[step_index].config(foreground="green")
        elif status == "error":
            self.step_vars[step_index].set("✗ " + step)
            self.step_labels[step_index].config(foreground="red")
        else:
            self.step_vars[step_index].set("○ " + step)
            self.step_labels[step_index].config(foreground="black")
    
    def reset_steps(self):
        """重置所有步骤状态"""
        for i in range(len(self.steps)):
            self.update_step(i, "inactive")
    
    def callback_handler(self, message):
        """统一回调处理"""
        # 在UI主线程中更新UI
        self.root.after(0, lambda: self.log(message))
        
        # 根据消息内容更新步骤状态
        lower_message = message.lower()
        
        if "登录" in lower_message:
            if "成功" in lower_message:
                self.root.after(0, lambda: self.update_step(0, "completed"))
            elif "失败" in lower_message:
                self.root.after(0, lambda: self.update_step(0, "error"))
            else:
                self.root.after(0, lambda: self.update_step(0, "active"))
        
        elif "验证码" in lower_message or "多因子" in lower_message:
            if "成功" in lower_message:
                self.root.after(0, lambda: self.update_step(1, "completed"))
                # 隐藏验证码输入框
                self.root.after(0, lambda: self.verification_frame.pack_forget())
            elif "失败" in lower_message:
                self.root.after(0, lambda: self.update_step(1, "error"))
            elif "需要" in lower_message or "等待" in lower_message:
                self.root.after(0, lambda: self.update_step(1, "active"))
                # 显示验证码输入框
                self.root.after(0, lambda: self.verification_frame.pack(fill=tk.X, pady=5, after=self.control_frame))
            
        elif any(op in lower_message for op in ["签到", "预约"]):
            if "成功" in lower_message or "完成" in lower_message:
                if "所有" in lower_message or "流程完成" in lower_message:
                    self.root.after(0, lambda: self.update_step(2, "completed"))
                    self.root.after(0, lambda: self.update_step(3, "completed"))
                else:
                    self.root.after(0, lambda: self.update_step(2, "active"))
            elif "失败" in lower_message:
                self.root.after(0, lambda: self.update_step(2, "error"))
            else:
                self.root.after(0, lambda: self.update_step(2, "active"))
    
    def start_checkin(self):
        """开始签到流程"""
        if self.current_operation:
            messagebox.showwarning("警告", "当前有操作正在进行，请等待完成")
            return
        
        selected_user = self.user_var.get()
        if not selected_user:
            messagebox.showerror("错误", "请选择用户")
            return
        
        self.log(f"开始签到流程，用户: {selected_user}")
        self.current_operation = "checkin"
        self.reset_steps()
        self.update_step(0, "active")
        
        # 禁用按钮
        self.checkin_button.config(state=tk.DISABLED)
        self.reserve_button.config(state=tk.DISABLED)
        
        # 在新线程中执行签到
        def run_checkin():
            try:
                checkin = LibraryCheckin(
                    user_key=selected_user,
                    callback=self.callback_handler
                )
                self.current_handler = checkin
                
                result = checkin.run()
                
                if result == "MFA_REQUIRED":
                    # 等待用户输入验证码，不关闭
                    pass
                elif result:
                    self.log("签到流程成功完成")
                    self.update_step(3, "completed")
                    checkin.close()
                    self.current_handler = None
                    self.current_operation = None
                else:
                    self.log("签到流程失败")
                    checkin.close()
                    self.current_handler = None
                    self.current_operation = None
            except Exception as e:
                self.log(f"签到过程中出错: {e}")
                if self.current_handler:
                    self.current_handler.close()
                self.current_handler = None
                self.current_operation = None
            finally:
                # 重新启用按钮
                self.root.after(0, lambda: self.checkin_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.reserve_button.config(state=tk.NORMAL))
        
        self.automation_thread = threading.Thread(target=run_checkin)
        self.automation_thread.daemon = True
        self.automation_thread.start()
    
    def start_reserve(self):
        """开始预约流程"""
        if self.current_operation:
            messagebox.showwarning("警告", "当前有操作正在进行，请等待完成")
            return
        
        selected_user = self.user_var.get()
        if not selected_user:
            messagebox.showerror("错误", "请选择用户")
            return
        
        self.log(f"开始预约流程，用户: {selected_user}")
        self.current_operation = "reserve"
        self.reset_steps()
        self.update_step(0, "active")
        
        # 禁用按钮
        self.checkin_button.config(state=tk.DISABLED)
        self.reserve_button.config(state=tk.DISABLED)
        
        # 在新线程中执行预约
        def run_reserve():
            try:
                reserver = LibraryReserve(
                    user_key=selected_user,
                    callback=self.callback_handler
                )
                self.current_handler = reserver
                
                result = reserver.run()
                
                if result == "MFA_REQUIRED":
                    # 等待用户输入验证码，不关闭
                    pass
                elif result:
                    self.log("预约流程成功完成")
                    self.update_step(3, "completed")
                    reserver.close()
                    self.current_handler = None
                    self.current_operation = None
                else:
                    self.log("预约流程失败")
                    reserver.close()
                    self.current_handler = None
                    self.current_operation = None
            except Exception as e:
                self.log(f"预约过程中出错: {e}")
                if self.current_handler:
                    self.current_handler.close()
                self.current_handler = None
                self.current_operation = None
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
                else:
                    self.log(f"{self.current_operation}流程失败")
                
                self.current_handler.close()
                self.current_handler = None
                self.current_operation = None
            except Exception as e:
                self.log(f"验证后流程中出错: {e}")
                if self.current_handler:
                    self.current_handler.close()
                self.current_handler = None
                self.current_operation = None
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