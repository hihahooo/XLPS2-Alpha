# XLPS2-Alpha

> 本文件是 XLPS2-Alpha 项目的 **CodeBuddy 项目记忆（codebuddyMd）**，会被本地 CodeBuddy（CLI：`cbc` / `codebuddy`）自动加载为项目上下文。
> 作用：把本仓库正式「链接」到本地 CodeBuddy，让 agent 在每次进入项目时都掌握仓库背景与操作约定。

## 项目概览

- **项目名称**：XLPS2-Alpha
- **项目类型**：通用软件项目（当前为初始骨架阶段）
- **GitHub 仓库**：https://github.com/hihahooo/XLPS2-Alpha
- **默认分支**：`main`
- **认证方式**：SSH（公钥已注册到 GitHub 账户 `hihahooo`，因沙箱封锁 22 端口，强制走 `ssh.github.com:443`）

## 目录结构

```
XLPS2-Alpha/
├── src/        # 源代码主目录
├── docs/       # 文档
├── tests/      # 测试用例
├── scripts/    # 构建 / 运维脚本
├── config/     # 配置文件
├── .codebuddy/ # CodeBuddy 项目配置（settings.json）
├── .gitignore  # 忽略规则
├── CODEBUDDY.md# 本文件：CodeBuddy 项目记忆
└── README.md   # 项目说明
```

## 开发约定

- 主分支为 `main`，功能开发请在独立分支上进行，并通过 Pull Request 合入。
- 提交信息保持清晰、语义化（如 `feat:`, `fix:`, `chore:`）。
- 推送使用 SSH：`git remote` 为 `git@github.com:hihahooo/XLPS2-Alpha.git`。
- 依赖 / 构建产物 / 密钥 / 日志已被 `.gitignore` 忽略，请勿提交。

## 本地 CodeBuddy 环境

- 本地已安装 CodeBuddy Code CLI（`codebuddy` / `cbc`）。
- GitHub 连接器已连接（用于只读 API 读取）；写操作（push 等）走 SSH 密钥。
- SSH 配置见 `~/.ssh/config`：`github.com` → `ssh.github.com:443`，IdentityFile `~/.ssh/id_ed25519`。

## 常见操作

```bash
# 克隆
git clone git@github.com:hihahooo/XLPS2-Alpha.git

# 创建功能分支
git checkout -b feat/your-feature

# 提交并推送
git add -A && git commit -m "feat: ..." && git push -u origin feat/your-feature
```

## TODO

- [ ] 明确技术栈与构建方式
- [ ] 完善 `src/` 核心模块
- [ ] 补充 `docs/` 设计文档
- [ ] 接入 CI / 测试流程
