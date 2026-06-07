# 安徽理工大学(AUST)校园网自动登录

专供安理工 Dr.COM Web 认证，支持联通 / 电信 / 移动 / 教职工。

## 修复说明（相比原版）

原脚本用 `http://www.baidu.com` 且把 **302 当成已联网**。未认证时访问外网会被门户 **302 到 10.255.0.19**，因此断网也显示「无需登录」。

现改为：

1. **外网探测**：`generate_204` / `msftconnecttest`，只有真连通才算在线  
2. **门户检测**：读取 `10.255.0.19` 页面中的 `Dr.COMWebLoginID_1`（已登录）/ `_0`（未登录）  
3. **登录方式**：改为 Dr.COM 标准 GET + JSON 回调（与 [iPanda92/AutoLogin](https://github.com/iPanda92/AutoLogin) 一致）  
4. **运营商后缀**：电信为 `@aust`（不是 `@telecom`）

## 快速开始

```powershell
cd D:\wifi\aust-campus-login
pip install -r requirements.txt
copy config.yml.example config.yml   # 首次
# 编辑 config.yml 填入学号密码
```

### 手动运行

| 方式 | 命令 |
|------|------|
| 双击 | `运行.bat` |
| 仅检测 | `python AutoLogin.py --check` |
| 单次登录 | `python AutoLogin.py --once` |
| 守护循环 | `python AutoLogin.py --watch` 或 `守护模式.bat` |

### 定时任务（推荐）

以管理员打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\wifi\aust-campus-login\安装定时任务.ps1"
```

将创建 **每 5 分钟** 运行一次的 `AUST-Campus-Login-Watchdog` 任务（无弹窗、写日志）。

日志位置：

- `logs/campus-login.log` — 主日志  
- `logs/task.log` — 计划任务 stdout

### 登录成功后重启 Cloudflare Tunnel（可选）

在 `config.yml` 中取消注释：

```yaml
post_login_cmd: "pm2 restart cloudflared"
```

## 运营商对照

| isp 值 | 后缀 |
|--------|------|
| unicom | @unicom |
| telecom | @aust |
| mobile | @cmcc |
| jzg | @jzg |

## 删除定时任务

```powershell
Unregister-ScheduledTask -TaskName "AUST-Campus-Login-Watchdog" -Confirm:$false
```

## 免责声明

仅供安理工在校师生学习交流，请遵守学校相关规定。
