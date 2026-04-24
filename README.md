# 安徽理工大学(AUST)校园网自动登录

> 专供安徽理工大学校园网使用 | 支持联通/电信/移动全运营商

## 功能特性

- 专为本校校园网定制（网关：`10.255.0.19`）
- 支持联通、电信、移动全运营商
- 开机自动检测网络状态
- Windows 平台通知提醒
- 配置文件分离，账号信息不外泄

## 项目结构

```
campus-login/
├── AutoLogin.py      # 主脚本
├── config.yml        # 配置文件（自行填写，不上传）
├── config.yml.example # 配置模板
├── requirements.txt  # Python 依赖
└── 运行.bat          # Windows 一键启动
```

## 快速开始

### 1. 安装依赖

双击运行 `安装依赖.bat`，或手动执行：
```bash
pip install requests pyyaml
```

### 2. 配置账号

复制 `config.yml.example` 为 `config.yml`，填入你的信息：

```yaml
url: "http://10.255.0.19/drcom/login"
username: "你的学号"
password: "你的密码"
isp: "unicom"  # 运营商：unicom / telecom / mobile
```

### 3. 运行

双击 `运行.bat` 即可自动登录。

### 4. 开机自启动

1. 按 `Win + R`，输入 `shell:startup`
2. 创建快捷方式，指向 `运行.bat`

## 运营商支持

| ISP 值 | 运营商 | 后缀 |
|--------|--------|------|
| unicom | 中国联通 | @unicom |
| telecom | 中国电信 | @telecom |
| mobile | 中国移动 | @mobile |

## 隐私说明

- `config.yml` 包含真实账号，**不会**上传到 GitHub
- `.gitignore` 已屏蔽配置文件

## 免责声明

本项目仅供安徽理工大学(AUST)在校师生学习交流使用，请遵守学校相关规定。
