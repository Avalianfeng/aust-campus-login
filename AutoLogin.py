#!/usr/bin/env python3
"""
Campus Network Auto Login Script
安徽理工大学(AUST)校园网自动登录脚本
"""

import requests
import yaml
import os
import sys
import time
import hashlib
import base64
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.yml"


def get_config():
    """读取配置文件"""
    if not CONFIG_FILE.exists():
        print(f"错误：配置文件 {CONFIG_FILE} 不存在")
        print("请复制 config.yml.example 为 config.yml 并填入账号信息")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_network(url="http://www.baidu.com", timeout=5):
    """检查网络是否已连接"""
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=False)
        return response.status_code == 200 or response.status_code == 301 or response.status_code == 302
    except:
        return False


def generate_encrypted_password(password):
    """
    生成加密密码（示例：简单的MD5+Base64）
    实际加密方式根据学校认证服务器要求可能不同
    """
    m = hashlib.md5()
    m.update(password.encode('utf-8'))
    return base64.b64encode(m.hexdigest().encode()).decode()


def login(config):
    """执行登录"""
    url = config['url']
    username = config['username']
    password = config['password']
    isp = config.get('isp', 'unicom')
    
    # 拼接完整用户名（学号@运营商后缀）
    if '@' not in username:
        suffix_map = {
            'unicom': '@unicom',
            'telecom': '@telecom', 
            'mobile': '@mobile'
        }
        username_full = username + suffix_map.get(isp, '@unicom')
    else:
        username_full = username
    
    # 构造登录请求（根据各学校实际抓包结果调整）
    data = {
        'username': username_full,
        'password': password,
        'secret': 'true',
        'action': 'login',
        'ac_id': '1',
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"登录响应: {response.status_code}")
        print(response.text[:200])
        return True
    except requests.exceptions.Timeout:
        print("错误：登录请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("错误：无法连接到认证服务器")
        return False
    except Exception as e:
        print(f"错误：{e}")
        return False


def main():
    print("=" * 40)
    print("安徽理工大学(AUST)校园网自动登录")
    print("=" * 40)
    
    # 检查网络
    print("\n检查网络状态...")
    if check_network():
        print("网络已连接，无需登录")
        return
    
    print("网络未连接，开始登录...")
    
    # 读取配置
    config = get_config()
    
    # 执行登录
    success = login(config)
    
    if success:
        # 等待后验证
        time.sleep(2)
        if check_network():
            print("\n登录成功！")
        else:
            print("\n登录响应异常，请检查配置")
    else:
        print("\n登录失败，请检查网络和配置")


if __name__ == '__main__':
    main()
