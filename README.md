# 图书馆座位自动化工具文档

## 项目概述
本工具实现图书馆座位预约与签到的全流程自动化，包含以下核心功能：
- 支持多因子验证的登录系统
- 一键预约未来两天7个时间段座位
- 定时自动签到功能
- 可视化UI界面实时监控流程
- 完整的日志记录系统

## 项目结构
```
.
├── auth.py            # 认证模块（登录/MFA）
├── checkin.py         # 签到功能模块
├── reserve.py         # 预约功能模块
├── main.py            # 主界面程序
├── checkinConfig.json # 签到配置文件
├── reserveConfig.json # 预约配置文件
└── library_automation.log # 运行日志
```

## 功能模块说明

### 1. 认证模块 (auth.py)
- **功能**：
  - 自动化登录校园系统
  - 多因子验证(MFA)处理
  - WebDriver管理
  - 页面加载等待优化

- **关键技术**：
  ```python
  WebDriverWait(driver, 10).until(EC.presence_of_element_located(...))  # 显式等待替代sleep
  execute_script('return document.readyState') == 'complete'  # 页面加载检测
  ```

### 2. 预约模块 (reserve.py)
- **功能**：
  - 自动预约未来两天7个时间段（08:00-22:00）
  - 智能重试机制
  - 多时段并行预约

- **配置示例**：
  ```json
  {
    "reserveUrl": {
      "LZ": {
        "username": "学号",
        "password": "密码",
        "real_name": "姓名",
        "phone_number": "手机号",
        "seat_xpath": "//div[@seat-id='A101']"
      }
    },
    "selectArea": "//区域选择XPath",
    "eastC": "//东C区XPath",
    "confirmButton": "//确认按钮XPath"
  }
  ```

### 3. 签到模块 (checkin.py)
- **功能**：
  - 自动检测签到状态
  - 异常状态重试
  - 智能URL构建

- **签到流程**：
  ```
  打开签到页 → 登录检测 → MFA验证 → 点击签到 → 结果确认
  ```

### 4. UI界面 (main.py)
- **功能组件**：
  - 用户选择下拉框
  - 签到/预约双功能按钮
  - 动态验证码输入框
  - 四步状态指示器
  - 实时日志面板

### 配置说明
**checkinConfig.json**：
```json
{
  "LZ": {
    "username": "学号",
    "password": "密码",
    "seat_id": "座位ID"
  }
}
```

**reserveConfig.json**：
```json
{
  "reserveUrl": {
    "LZ": {
      "username": "学号",
      "password": "密码",
      "real_name": "姓名",
      "phone_number": "手机号",
      "seat_xpath": "//div[@seat-id='A101']"
    }
  },
  "selectArea": "//区域选择XPath",
  "eastC": "//东C区XPath",
  "confirmButton": "//确认按钮XPath"
}
```

