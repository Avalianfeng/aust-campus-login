#!/usr/bin/env python3
"""
安徽理工大学(AUST)校园网自动登录
- 修复：门户 302 不再误判为已联网
- 支持 Dr.COM 门户状态检测 + 外网连通性双重校验
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml

ROOT = Path(__file__).parent
CONFIG_FILE = ROOT / "config.yml"
LOG_FILE = ROOT / "logs" / "campus-login.log"
TASK_PS1 = ROOT / "_task.ps1"
LOG_DIR = ROOT / "logs"

PORTAL_BASE = "http://10.255.0.19"
PORTAL_PAGE = f"{PORTAL_BASE}/"
LOGIN_URL = f"{PORTAL_BASE}/drcom/login"

# Dr.COM 门户 HTML 标记：1=已登录，0=未登录
PORTAL_LOGGED_IN = "Dr.COMWebLoginID_1"
PORTAL_LOGGED_OUT = "Dr.COMWebLoginID_0"

# 外网探测（204/固定正文 = 真联网；302 到 10.x = 门户拦截）
PROBE_URLS = (
    ("http://connectivitycheck.gstatic.com/generate_204", {204}),
    ("http://www.msftconnecttest.com/connecttest.txt", {200}),
)

ISP_SUFFIX = {
    "unicom": "@unicom",
    "telecom": "@aust",
    "mobile": "@cmcc",
    "jzg": "@jzg",
    "staff": "@jzg",
    # 兼容旧配置误写
    "aust": "@aust",
    "cmcc": "@cmcc",
}

_QUIET = False


def bj_now() -> str:
    utc = datetime.now(timezone.utc)
    bj = utc.astimezone(timezone(timedelta(hours=8)))
    return bj.strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str, *, also_print: bool | None = None) -> None:
    if also_print is None:
        also_print = not _QUIET
    line = f"{bj_now()} {msg}"
    if also_print:
        print(line)
        sys.stdout.flush()
    LOG_DIR.mkdir(exist_ok=True)
    with open(LOG_DIR / "campus-login.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        log(f"错误：配置文件不存在 {CONFIG_FILE}")
        log("请复制 config.yml.example 为 config.yml 并填入账号信息")
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def is_keepalive_enabled(config: dict[str, Any]) -> bool:
    """后台计划任务是否应执行检测（由 config.yml 的 auto_keepalive 控制）。"""
    return bool(config.get("auto_keepalive", False))


def set_keepalive_enabled(enabled: bool) -> None:
    """写入 config.yml 的 auto_keepalive 开关。"""
    config = get_config()
    config["auto_keepalive"] = enabled
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def call_task_ps1(action: str) -> tuple[bool, str]:
    """调用 _task.ps1，返回 (成功, 消息)。"""
    if not TASK_PS1.exists():
        return False, f"找不到 {TASK_PS1}"
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(TASK_PS1),
                "-Action",
                action,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
        )
    except OSError as e:
        return False, str(e)

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        return False, err or f"任务操作失败 (exit {result.returncode})"
    return True, (result.stdout or "").strip()


def get_task_status() -> dict[str, Any]:
    """读取计划任务状态。"""
    ok, output = call_task_ps1("status")
    if not ok:
        return {"exists": False, "enabled": False, "state": "Unknown", "error": output}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"exists": False, "enabled": False, "state": "Unknown", "error": output}


def enable_keepalive() -> tuple[bool, str]:
    set_keepalive_enabled(True)
    ok, msg = call_task_ps1("enable")
    if ok:
        return True, "已开启后台保活（静默，每 5 分钟检测）"
    return False, (
        f"配置已更新，但计划任务启用失败：{msg}\n"
        "请右键「管理.bat」→ 以管理员身份运行后重试。"
    )


def disable_keepalive() -> tuple[bool, str]:
    set_keepalive_enabled(False)
    ok, msg = call_task_ps1("disable")
    if ok:
        return True, "已关闭后台保活（计划任务已暂停）"
    return False, f"配置已更新，但计划任务暂停失败：{msg}"


def read_last_log_lines(count: int = 10) -> list[str]:
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return lines[-count:] if lines else []


def portal_status_label(portal: str | None) -> str:
    return {
        "online": "已认证",
        "offline": "未认证",
        None: "不可达",
    }.get(portal, str(portal))


def task_status_label(task: dict[str, Any]) -> str:
    if task.get("error"):
        return "查询失败"
    if not task.get("exists"):
        return "未安装"
    if task.get("enabled"):
        return "已启用"
    return "已暂停"


def get_keepalive_status() -> dict[str, Any]:
    """汇总保活与任务状态（供菜单显示）。"""
    config = get_config()
    task = get_task_status()
    last_lines = read_last_log_lines(1)
    return {
        "config_on": is_keepalive_enabled(config),
        "task_exists": task.get("exists", False),
        "task_enabled": task.get("enabled", False),
        "task_state": task.get("state", "Unknown"),
        "last_log_line": last_lines[-1] if last_lines else "（暂无）",
    }


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def run_menu() -> None:
    """交互式管理菜单。"""
    while True:
        config = get_config()
        timeout = float(config.get("timeout", 5))
        online = is_online(config)
        portal = check_portal_status(timeout)
        status = get_keepalive_status()

        clear_screen()
        print("========== AUST 校园网 ==========")
        print(f"网络状态 : {'在线' if online else '离线'}")
        print(f"门户状态 : {portal_status_label(portal)}")
        print(f"自动保活 : {'开启' if status['config_on'] else '关闭'}")
        print(f"计划任务 : {task_status_label(status)}")
        print(f"最近日志 : {status['last_log_line']}")
        print("================================")
        print("[1] 立即检测并登录（单次）")
        print("[2] 开启后台保活（静默，每5分钟）")
        print("[3] 关闭后台保活")
        print("[4] 前台守护（本窗口循环，自动暂停计划任务）")
        print("[5] 查看最近 10 条日志")
        print("[0] 退出")
        print()

        choice = input("请选择: ").strip()

        if choice == "0":
            print("再见。")
            return
        if choice == "1":
            run_once(config)
        elif choice == "2":
            ok, msg = enable_keepalive()
            print(msg)
        elif choice == "3":
            ok, msg = disable_keepalive()
            print(msg)
        elif choice == "4":
            task = get_task_status()
            if task.get("enabled"):
                ok, msg = call_task_ps1("disable")
                if ok:
                    print("已暂停计划任务（避免与守护模式重复检测）")
                else:
                    print(f"暂停计划任务失败：{msg}")
            print("进入前台守护模式（Ctrl+C 退出）...")
            input("按回车开始...")
            run_watch(config)
            return
        elif choice == "5":
            lines = read_last_log_lines(10)
            clear_screen()
            print("========== 最近日志 ==========")
            if lines:
                print("\n".join(lines))
            else:
                print("（暂无日志）")
            print("==============================")
        else:
            print("无效选项，请重试。")

        input("\n按回车继续...")


def is_portal_redirect(location: str) -> bool:
    if not location:
        return False
    loc = location.lower()
    if "drcom" in loc:
        return True
    try:
        host = urlparse(location).hostname or ""
    except Exception:
        host = location
    return host.startswith("10.") or host.startswith("192.168.")


def probe_internet(timeout: float) -> bool:
    """外网探测：仅 status 符合预期且无门户重定向时视为在线。"""
    for url, ok_codes in PROBE_URLS:
        try:
            r = requests.get(url, timeout=timeout, allow_redirects=False)
            if r.status_code in ok_codes:
                if url.endswith("connecttest.txt") and "Microsoft Connect Test" not in r.text:
                    continue
                return True
            if r.status_code in (301, 302, 303, 307, 308):
                if is_portal_redirect(r.headers.get("Location", "")):
                    return False
        except requests.RequestException:
            continue
    return False


def check_portal_status(timeout: float) -> str | None:
    """
    读取 Dr.COM 门户页状态。
    返回 'online' | 'offline' | None（无法访问门户，可能物理断网）
    """
    try:
        r = requests.get(PORTAL_PAGE, timeout=timeout, allow_redirects=True)
        body = r.text
        if PORTAL_LOGGED_IN in body:
            return "online"
        if PORTAL_LOGGED_OUT in body:
            return "offline"
        # 部分版本只有 login 表单
        if "drcom" in body.lower() and ("upass" in body.lower() or "login" in body.lower()):
            return "offline"
    except requests.RequestException:
        return None
    return None


def is_online(config: dict[str, Any]) -> bool:
    timeout = float(config.get("timeout", 5))
    if probe_internet(timeout):
        return True
    portal = check_portal_status(timeout)
    if portal == "online":
        return True
    if portal == "offline":
        return False
    # 门户不可达且外网不通 → 离线
    return False


def build_username(config: dict[str, Any]) -> str:
    username = str(config.get("username", "")).strip()
    if "@" in username:
        return username
    isp = str(config.get("isp", "telecom")).strip().lower()
    suffix = ISP_SUFFIX.get(isp)
    if not suffix:
        log(f"警告：未知 isp={isp}，默认使用 @aust")
        suffix = "@aust"
    return username + suffix


def login(config: dict[str, Any]) -> bool:
    username = build_username(config)
    password = str(config.get("password", ""))
    mk_key = str(config.get("mk_key", "123456"))
    timeout = float(config.get("timeout", 10))

    params = {
        "callback": "dr1003",
        "DDDDD": username,
        "upass": password,
        "0MKKey": mk_key,
    }

    try:
        r = requests.get(LOGIN_URL, params=params, timeout=timeout)
        log(f"登录请求 HTTP {r.status_code}")
        text = r.text.strip()
        if text.startswith("dr1003(") and text.endswith(")"):
            payload = json.loads(text[7:-1])
            result = payload.get("result")
            msg = payload.get("msga") or payload.get("msg") or str(payload)
            log(f"登录响应 result={result} msg={msg}")
            return result == 1
        log(f"登录响应（非 JSON）: {text[:200]}")
        return False
    except requests.Timeout:
        log("错误：登录请求超时")
        return False
    except requests.ConnectionError:
        log("错误：无法连接认证服务器 10.255.0.19")
        return False
    except Exception as e:
        log(f"错误：{e}")
        return False


def run_post_login(config: dict[str, Any]) -> None:
    cmd = config.get("post_login_cmd")
    if not cmd:
        return

    log(f"执行 post_login_cmd: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=False, cwd=str(ROOT))
    except Exception as e:
        log(f"post_login_cmd 失败: {e}")


def run_once(
    config: dict[str, Any], *, force: bool = False, scheduled: bool = False
) -> int:
    if scheduled and not force and not is_keepalive_enabled(config):
        log("自动保活已关闭，跳过检测")
        return 0

    log("检查网络状态...")
    online = is_online(config)

    if online and not force:
        log("网络已连接，无需登录")
        return 0

    if not online:
        log("网络未连接或门户未认证，开始登录...")
    else:
        log("强制登录模式...")

    if not login(config):
        log("登录失败")
        return 1

    time.sleep(float(config.get("verify_delay", 2)))
    if is_online(config):
        log("登录成功，外网已恢复")
        run_post_login(config)
        return 0

    log("登录后仍未连通，请检查账号/运营商/密码")
    return 2


def run_watch(config: dict[str, Any]) -> None:
    task = get_task_status()
    if task.get("enabled"):
        ok, msg = call_task_ps1("disable")
        if ok:
            log("已暂停计划任务（避免与守护模式重复检测）")
        else:
            log(f"暂停计划任务失败: {msg}")

    interval = int(config.get("watch_interval", 300))
    log(f"守护模式启动，每 {interval} 秒检测一次（Ctrl+C 退出）")
    while True:
        try:
            run_once(config)
        except KeyboardInterrupt:
            log("守护模式已停止")
            break
        except Exception as e:
            log(f"守护循环异常: {e}")
        time.sleep(interval)


def main() -> None:
    global _QUIET

    parser = argparse.ArgumentParser(description="AUST 校园网自动登录")
    parser.add_argument("--once", action="store_true", help="单次检测")
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="计划任务调用；auto_keepalive 为 false 时直接跳过",
    )
    parser.add_argument("--watch", action="store_true", help="循环守护模式")
    parser.add_argument("--force", action="store_true", help="忽略在线检测，强制登录")
    parser.add_argument("--check", action="store_true", help="仅检测状态，不登录")
    parser.add_argument(
        "--quiet", action="store_true", help="不输出到控制台（计划任务静默运行）"
    )
    parser.add_argument("--menu", action="store_true", help="交互式管理菜单")
    args = parser.parse_args()

    if args.quiet:
        _QUIET = True

    config = get_config()

    if args.menu:
        run_menu()
        return

    if args.check:
        online = is_online(config)
        portal = check_portal_status(float(config.get("timeout", 5)))
        log(f"外网探测={'通过' if probe_internet(float(config.get('timeout', 5))) else '失败'}")
        log(f"门户状态={portal or '不可达'}")
        log(f"综合判定={'在线' if online else '离线'}")
        sys.exit(0 if online else 1)

    if args.watch:
        run_watch(config)
        return

    # 默认 & --once：单次运行（手动运行不受 auto_keepalive 限制）
    sys.exit(run_once(config, force=args.force, scheduled=args.scheduled))


if __name__ == "__main__":
    main()
