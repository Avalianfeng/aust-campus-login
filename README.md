# 安徽理工大学(AUST)校园网自动登录

专供安理工 Dr.COM Web 认证，支持联通 / 电信 / 移动 / 教职工。

## 快速开始

```powershell
cd D:\wifi\aust-campus-login
pip install -r requirements.txt
copy config.yml.example config.yml   # 首次
# 编辑 config.yml 填入学号密码
```

**双击 [`管理.bat`](管理.bat)** 打开交互菜单，所有操作都在里面完成。

## 交互菜单

```
========== AUST 校园网 ==========
网络状态 / 门户状态 / 自动保活 / 计划任务 / 最近日志
================================
[1] 立即检测并登录（单次）
[2] 开启后台保活（静默，每5分钟）
[3] 关闭后台保活
[4] 前台守护（本窗口循环）
[5] 查看最近 10 条日志
[0] 退出
```

## 使用场景

| 场景 | 操作 |
|------|------|
| 手动登录一次 | 菜单 `[1]`，或双击 `运行.bat` |
| 晚上 / 挂机静默保活 | 菜单 `[2]`（需管理员权限注册计划任务） |
| 白天 / 不想后台跑 | 菜单 `[3]` |
| 前台调试循环检测 | 菜单 `[4]` 或 `守护模式.bat`（会自动暂停计划任务） |

## 命令行（可选）

| 命令 | 说明 |
|------|------|
| `python AutoLogin.py --menu` | 交互菜单 |
| `python AutoLogin.py --once` | 单次检测并登录 |
| `python AutoLogin.py --check` | 仅检测状态 |
| `python AutoLogin.py --watch` | 前台守护循环 |

计划任务静默执行：`pythonw AutoLogin.py --once --scheduled --quiet`

日志：`logs/campus-login.log`

## 检测原理

1. **外网探测**：`generate_204` / `msftconnecttest`，只有真连通才算在线  
2. **门户检测**：读取 `10.255.0.19` 页面中的 `Dr.COMWebLoginID_1` / `_0`  
3. **登录方式**：Dr.COM 标准 GET + JSON 回调  

## 运营商对照

| isp 值 | 后缀 |
|--------|------|
| unicom | @unicom |
| telecom | @aust |
| mobile | @cmcc |
| jzg | @jzg |

## 可选：登录成功后执行命令

在 `config.yml` 中设置：

```yaml
post_login_cmd: "pm2 restart cloudflared"
```

## 彻底删除计划任务

```powershell
Unregister-ScheduledTask -TaskName "AUST-Campus-Login-Watchdog" -Confirm:$false
```

## 免责声明

仅供安理工在校师生学习交流，请遵守学校相关规定。
