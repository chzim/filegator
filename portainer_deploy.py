#!/usr/bin/env python3
# FileGator Portainer 部署脚本 (参照 cip 项目模式)
#
# 用法:
#   export PORTAINER_PASS='***'
#   export STACK_NAME=filegator
#   ./portainer_deploy.py
#
# 环境变量:
#   PORTAINER_URL   默认 https://portainer.swarm-o.xzic.com
#   PORTAINER_USER  默认 admin (仅密码模式)
#   PORTAINER_API_KEY  优先: 直接 Bearer 认证 (xzic 组级变量)
#   PORTAINER_PASS  回退: 用户名密码登录
#   STACK_NAME      必填, Portainer 中预先创建的 Stack 名称
#   TZ / FILEGATOR_IMAGE_TAG   可选, 随 Stack 下发的环境变量
import os
import requests
import sys

requests.packages.urllib3.disable_warnings()

PORTAINER_URL = os.environ.get('PORTAINER_URL', 'https://portainer.swarm-o.xzic.com')
PORTAINER_USER = os.environ.get("PORTAINER_USER", 'admin')
PORTAINER_API_KEY = os.environ.get("PORTAINER_API_KEY")
PORTAINER_PASS = os.environ.get("PORTAINER_PASS")
STACK_NAME = os.environ.get('STACK_NAME')

if not STACK_NAME:
    print("错误: 需设置 STACK_NAME 环境变量")
    sys.exit(1)

if PORTAINER_API_KEY:
    headers = {"Authorization": "Bearer " + PORTAINER_API_KEY}
    print("使用 API Key 认证")
else:
    if not PORTAINER_PASS:
        print("错误: 需设置 PORTAINER_API_KEY 或 PORTAINER_PASS 环境变量")
        sys.exit(1)
    auth_url = PORTAINER_URL + "/api/auth"
    r = requests.post(auth_url, json={"username": PORTAINER_USER, "password": PORTAINER_PASS}, verify=False)
    r.raise_for_status()
    jwt = r.json()["jwt"]
    print("Portainer 登录成功")
    headers = {"Authorization": "Bearer " + jwt}

r = requests.get(PORTAINER_URL + "/api/stacks", headers=headers, verify=False)
r.raise_for_status()

stack = next((s for s in r.json() if s["Name"] == STACK_NAME), None)
if not stack:
    print("未找到 Stack: " + STACK_NAME + " (请先在 Portainer UI 创建, 端点选择 swarm-o)")
    sys.exit(1)

stack_id = stack["Id"]
endpoint_id = stack["EndpointId"]
print("Stack ID: " + str(stack_id))
print("Stack EndpointId: " + str(endpoint_id))

with open("docker-stack.yml") as f:
    compose_content = f.read()

url = PORTAINER_URL + "/api/stacks/" + str(stack_id) + "?endpointId=" + str(endpoint_id)
print("更新 URL: " + url)

env_vars = []

env_mappings = [
    'TZ',
    'FILEGATOR_IMAGE_TAG',
]

for env_name in env_mappings:
    env_value = os.environ.get(env_name)
    if env_value:
        env_vars.append({"name": env_name, "value": env_value})

print("环境变量数量: " + str(len(env_vars)))

data = {
    "Name": STACK_NAME,
    "stackFileContent": compose_content,
    "env": env_vars
}

print("发送数据...")
r = requests.put(url, headers=headers, json=data, verify=False)
print("状态码: " + str(r.status_code))
print("响应: " + r.text[:500])

r.raise_for_status()
print("\nStack " + STACK_NAME + " 更新成功!")
