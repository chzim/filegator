# Agent 开发规范（FileGator 部署）

> 本文件是 AI 辅助开发的强制行为规范。任何代码生成任务都必须遵守本文约定。
> 项目背景：FileGator 是开源 PHP 文件管理系统（上游 `github.com/filegator/filegator`，PHP 8.3 + Apache + Vue 2 前端）。
> 本仓库为内部分叉（当前工作分支 `xzic`），目标分两阶段：
> - **一阶段（现行）**：通过 Portainer（swarm-o 集群）部署官方镜像，先跑通业务；
> - **二阶段（暂缓）**：GitLab CI 多架构构建 + 部署 K8s 集群（等待 runner 宿主内核 seccomp 问题解决后启用，规范见「六、二阶段」）。

## 一、核心工作循环（强制）

每次代码生成/修改后，必须按以下顺序执行，不得跳步：

```
理解需求 → 与用户确认修改方案 → 本地验证 → 修改代码 → 同步更新相关说明文档 → 运行测试 → 测试全绿 → 汇报结果 →（用户确认后）git commit
```

**规则：**

1. **修改代码前必须先与用户确认修改内容**：向用户说明将要修改哪些文件、改什么、为什么改，得到用户确认后才能动手修改。
2. **修改代码时必须同步更新并对齐相关说明文档**：凡改动涉及部署方式、CI 流程、K8s 资源、CI/CD 变量等，必须在同一次改动中同步更新 `AGENT.MD` 与 `.local/部署环境.md` 等对应文档；文档与现状不一致视为未完成。
3. **修改代码前先本地验证**：能用 curl/docker 本地验证的先验证（如 `docker compose config` 校验 stack 文件、Portainer API 调用验证），确认符合预期后再落地；验证结论一并向用户汇报。
4. **临时脚本与本地敏感内容目录约定**：本地验证、调试用的临时脚本统一放在项目根目录 `.tmp/` 下；Portainer 凭据、GitLab API 配置、K8s 集群配置、CSRF 密钥等敏感内容统一放在项目根目录 `.local/` 下，仅限本地使用；两个目录均不提交到版本库，密钥等敏感值不得写入代码、日志或 commit。
5. **未通过测试的代码禁止提交**；每次 commit 对应一个完整、可运行的状态。
6. 修改多个不相关的功能时，拆成多次独立的「修改→测试→提交」循环。
7. 向用户汇报时必须包含：改了什么、验证结果、测试结果；已提交时附 commit hash。

## 二、原始文件保护原则（本项目特有，强制）

**原则上不修改项目原始文件**（上游 FileGator 代码：`backend/`、`frontend/`、`dist/`、`index.php`、`configuration_sample.php`、原 `Dockerfile` / `Dockerfile.dev` / `Dockerfile.multiarch`、`composer.*`、`package*.json`、`.github/` 等）。

- 全部部署能力通过**新增文件**实现，目录约定见「三、项目结构」。
- 唯一例外：`.gitignore` 末尾追加本地目录排除项（`.local/`、`.tmp/`），防止敏感信息误提交；除此之外不得改动原始文件。
- 确有必要改动原始文件时（如上游 bug 导致无法构建），必须先向用户说明原因并得到确认。

## 三、项目结构（新增文件）

```
AGENT.MD                    本规范文件
.gitlab-ci.yml              GitLab CI 总入口（一阶段仅 deploy 阶段, 参照 cip 模式）
docker-stack.yml            Portainer Stack 定义（一阶段部署源）
portainer_deploy.py         Portainer API 部署脚本（参照 cip 项目模式）
.local/                     本地敏感信息（不提交）
  部署环境.md               部署环境与首次部署步骤记录
  gitlab-config             GitLab API 访问配置（二阶段用）
  k8s-config                K8s 集群访问配置（二阶段用）
  env.sh                    FILEGATOR_CSRF_KEY 等本地敏感值（二阶段用）
.tmp/                       临时脚本与调试产物（不提交）
```

二阶段启用时新增（当前不在仓库）：`VERSION`、`.gitlab-ci.yml`、`.ci/`、`deploy/k8s/`、`scripts/build.sh`。

## 四、一阶段：Portainer 部署（现行）

**目标**：swarm-o 集群（x86 架构）上以官方 amd64 镜像跑通 FileGator 业务。

**前置（一次性）**：

1. Harbor 项目 `filegator` 已创建；官方镜像 `harbor.xzic.com/filegator/filegator:v7.16.5`（Docker Hub `filegator/filegator` 的 amd64 版，适配 x86 集群）已经由 transfer 节点（172.29.10.61，`/root/transfer-images/direct.sh`）同步入 Harbor。升级版本时重新同步对应 tag。
2. Portainer（`https://portainer.swarm-o.xzic.com`）UI 手工创建 Stack：名称 `filegator`，端点 `swarm-o`（`portainer_deploy.py` 只按名称查找并更新已存在的 Stack，不自动创建）。

**部署**（CI 或手工，二者等价）：

- **CI（默认路径）**：push 任意分支 → `deploy` job（`docker` 标签 runner）→ `python3 portainer_deploy.py`，以 `FILEGATOR_IMAGE_TAG`（CI 变量，默认 `v7.16.5`）更新 Stack；tag 推送（`v*`）→ 以 tag 名作为镜像 tag 部署（须先用 transfer 节点同步进 Harbor）。
- **手工**：
```bash
export PORTAINER_PASS='***'   # 不入库, 仅本机 shell
export STACK_NAME=filegator
# 可选: export FILEGATOR_IMAGE_TAG=v7.16.5
./portainer_deploy.py
```

**GitLab CI/CD Variables（一阶段）**：

| 变量 | 类型 | 说明 |
|---|---|---|
| `PORTAINER_API_KEY` | Masked | 优先认证方式（**xzic 组级已配置**，直接 Bearer，不受密码/2FA 影响） |
| `PORTAINER_PASS` | Masked | 回退：admin 用户名密码登录（组级已配置；2026-10 已观察到 422 被拒，疑似过期） |

其余（`PORTAINER_URL`/`STACK_NAME`/`FILEGATOR_IMAGE_TAG`）内置于 `.gitlab-ci.yml` variables。

**约定**：

1. `docker-stack.yml` 是唯一部署源；服务名 `filegator`，单副本，接入集群现有 traefik（外部 `proxy` 网络），域名 `filegator.swarm-o.xzic.com`（web 80 + websec 443），监听容器 8080 端口。
2. 数据持久化（NFS 共享）：stack 文件中卷 `filegator-repository`（用户文件）与 `filegator-private`（users.json / sessions / logs）以 `driver_opts`（`type: nfs`，`addr=172.29.10.99`）声明式挂载 NFS 服务器（172.29.10.99）的 `/data/nfs/filegator_data/{repository,private}`（参照 nightingale 的 Volume 约定，NFS 目录属主 uid 33 = 容器内 www-data）；6 个 swarm 节点（172.29.10.101-106）的卷目录 `/opt/docker/volumes/filegator_filegator-{repository,private}/_data` 已手动挂同一 NFS 路径作双保险（与 nightingale 节点现状一致；节点重启后需按 `.local/部署环境.md` 重挂）。单副本 + `restart_policy: on-failure`。
3. 用户体系：官方镜像使用默认 `configuration.php`（首个登录用户自动成为管理员，FileGator 原生行为）；一阶段不注入自定义 CSRF key（CSRF 注入随二阶段自构建/ConfigMap 方案落地）。
4. 回滚/换版本：修改 `FILEGATOR_IMAGE_TAG` 环境变量重跑 `portainer_deploy.py` 即可（镜像须已同步入 Harbor）。

## 五、Git 提交规范

**Commit message 格式**（中文描述，类型用英文）：

```
<type>: <简述>

<正文：为什么改、改了什么，可选>
```

type 取值：`feat` / `fix` / `test` / `docs` / `refactor` / `chore`。

**提交红线**：

1. 暂存文件按文件名明确 `git add <file>`，不要 `git add -A`。
2. **禁止提交**：密钥、证书私钥、`.env`、`configuration.php`、`.local/`、`.tmp/`。
3. **禁止自动 commit / push**：只在用户明确要求时才创建 commit 与 push。

## 六、二阶段：CI 构建 + K8s 部署（暂缓）

> 启用条件：runner 宿主机内核支持 seccomp（当前 `ci-runner-amd64` 内核不支持，trixie 系镜像内 xz 5.4+ 解包报 `xz: Failed to enable the sandbox`，`--security-opt seccomp=unconfined` 亦无效；需运维修内核或换 bookworm 基础镜像）。启用时按以下规范重建 `VERSION` / `.gitlab-ci.yml` / `.ci/` / `deploy/k8s/` / `scripts/build.sh`。

**流程**：`transfer-base-images`（同步基础镜像到 Harbor）→ `php-test`（单元测试）→ `build-filegator-amd64` + `build-filegator-arm64`（并行构建）→ `manifest-filegator`（合并多架构 manifest，推 `:latest`）→ `deploy-k8s`（部署到 K8s）。

**命名与分支规则（强制）**：

1. CI stage/job 名用 `-`（连字符），shell 变量用 `_`（下划线），Docker 镜像名与 K8s 资源名用 `-`。
2. 主分支（`master`/`main`）：镜像 tag = `VERSION` 文件内容，K8s 命名空间/前缀 = `filegator`，Ingress 域名 `filegator.xzbdc.cn`。
3. 其它分支：镜像 tag = `<分支名>-<VERSION>`，K8s 命名空间/前缀 = `filegator-<分支名>`，Ingress 域名 `filegator-<分支名>.k8s-arm.xzic.com`（每分支独立命名空间隔离部署）。
4. Tag 发布（`v*`）：始终构建 + 部署。
5. 部署前校验版本镜像必须存在于 Harbor（Harbor API），不存在即失败，**禁止使用 `:latest` 部署**。

**镜像构建策略（临时 Dockerfile，强制）**：

镜像以仓库原始 `Dockerfile` 为唯一构建源：`scripts/build.sh` 构建前将其复制为 `.tmp/dockerfile.generated` 临时文件，仅在临时文件上做最小改造（原始文件保持逐字节不变）：

| 改造点 | 原始 Dockerfile | 临时文件 |
|---|---|---|
| 基础镜像 | `php:8.3-apache`（Docker Hub 官方） | `harbor.xzic.com/library/php:8.3-apache`（本地 Harbor） |
| 源码获取 | `git clone` GitHub 仓库 | `COPY . /var/www/filegator/`（本地构建上下文） |
| apt 源 | `deb.debian.org` / `security.debian.org` | `mirrors.aliyun.com`（两个 stage 均替换） |
| Node.js | `deb.nodesource.com` setup 脚本（国内不可达） | npmmirror 官方二进制包（按 `dpkg --print-architecture` 自适应 x64/arm64） |
| composer 源 | packagist 官方 | `https://repo.packagist.com`（官方国内镜像） |
| npm 源 | npmjs 官方 | `https://registry.npmmirror.com` |
| ldap 扩展 libdir | `--with-libdir=lib/x86_64-linux-gnu/`（硬编码 amd64，arm64 构建必失败） | `--with-libdir=lib/$(dpkg --print-architecture)-linux-gnu/`（架构自适应） |
| 产物清理 | 原清理行 | 追加 `.tmp`（临时文件不进镜像） |

**K8s 数据模型要点**：

1. 单体镜像（PHP + Apache，端口 8080），无数据库/Redis。
2. `configuration.php` 经 ConfigMap 挂载；`csrf_key` 经 Secret → env `FILEGATOR_CSRF_KEY` + `getenv()` 读取。
3. PVC（RWO 10Gi）挂 `repository/` 与 `private/`；**单副本 + Recreate**（PHP 原生文件 Session，多副本互斥）。
4. init 容器铺目录 + users.json（可选 `FILEGATOR_USERS_JSON` Secret）；探针 `httpGet /?r=login`。
5. Ingress TLS 用内网 CA 签发（含 SAN，secretName=host）。

**GitLab CI/CD Variables**：`HARBOR_USERNAME`/`HARBOR_PASSWORD`、`K8S_ARM64_KUBECONFIG_BASE64`、`FILEGATOR_CSRF_KEY`（Masked）；`FILEGATOR_USERS_JSON`、`PKI_CA_CERT`/`PKI_CA_KEY`（File，可选）。

**Runner 标签**：`ci-runner-amd64`（同步/测试）、`shell-x86_64` / `shell-aarch64`（amd64/arm64 构建）、`docker`（manifest + 部署）。

## 七、测试要求

| 模块 | 测试命令 | 说明 |
|---|---|---|
| docker-stack.yml（一阶段） | `docker compose config -f docker-stack.yml` | 插值后校验语法 |
| portainer_deploy.py | `python3 -m py_compile portainer_deploy.py` | 语法校验 |
| backend/（PHP，二阶段） | `composer install && vendor/bin/phpunit` | CI `php-test` job 执行 |
| deploy/k8s/（二阶段） | `kubectl apply --dry-run=client -f deploy/k8s/` | 占位符替换后校验 |

## 八、安全红线（违反即返工）

1. `PORTAINER_PASS`、`FILEGATOR_CSRF_KEY`、`users.json`（含密码哈希）、kubeconfig、Harbor/GitLab 凭据等**一律不得写入代码、日志、commit**；只经 `.local/` 或 K8s Secret 注入。
2. 管理面（用户管理、文件管理）仅限内网/指定域名访问（一阶段 `filegator.swarm-o.xzic.com`，二阶段按分支域名规则）。
3. `.local/`、`.tmp/` 目录内容仅限本机使用，禁止入库（已列入 `.gitignore`）。

## 九、沟通约定

1. 回复、代码注释、commit message 一律使用中文（type 关键字与代码标识符除外）。
2. 遇到需求模糊或有多种合理实现时，先列出选项及利弊询问用户，不要自行拍板。
3. 环境类失败（Harbor 不可达、Portainer 登录失败、Runner 未注册等）属于前置环境问题，直接向用户报告，不要"假装"环境可用。
4. 涉及密码/密钥的演示与验证，结果汇报中不粘贴任何密钥明文。
