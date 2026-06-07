#!/usr/bin/env python3
"""
安徽理工大学(AUST)校园网自动登录
- 修复：门户 302 不再误判为已联网
- 支持 Dr.COM 门户状态检测 + 外网连通性双重校验
"""

from __future__ import annotations

import argparse
import json
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


def bj_now() -> str:
    utc = datetime.now(timezone.utc)
    bj = utc.astimezone(timezone(timedelta(hours=8)))
    return bj.strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str, *, also_print: bool = True) -> None:
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
    import subprocess

    log(f"执行 post_login_cmd: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=False, cwd=str(ROOT))
    except Exception as e:
        log(f"post_login_cmd 失败: {e}")


def run_once(config: dict[str, Any], *, force: bool = False) -> int:
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
    parser = argparse.ArgumentParser(description="AUST 校园网自动登录")
    parser.add_argument("--once", action="store_true", help="单次检测（供任务计划程序调用）")
    parser.add_argument("--watch", action="store_true", help="循环守护模式")
    parser.add_argument("--force", action="store_true", help="忽略在线检测，强制登录")
    parser.add_argument("--check", action="store_true", help="仅检测状态，不登录")
    args = parser.parse_args()

    config = get_config()

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

    # 默认 & --once：单次运行
    sys.exit(run_once(config, force=args.force))


if __name__ == "__main__":
    main()
