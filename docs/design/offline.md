# 离线 fork

`main` 保持 upstream 历史，`offline` 保存少量按职责划分的补丁。应用默认就是离线版本，不提供恢复联网的 feature。
网络 crate 源码仍留在 workspace，方便对照与合并 upstream；它们只可单独作为开发工具构建，不能进入发行应用依赖树。
构建阶段允许 crates.io、Git 依赖、工具链与系统 SDK 下载。

## 修改前的调用链

| 入口 | 调用链 | 网络行为 |
| --- | --- | --- |
| Windows 启动 / 配置热加载 | `attach_cloud` → `CloudPredictor` / `CloudGlossFiller` → `chat_client` | OpenAI-compatible HTTP，联想 / 翻译 / 释义补全 |
| macOS 启动 / 配置热加载 | `Host::apply_config` → 同上 | 同上 |
| Windows / macOS 云服务设置 | `ConnectionTest` → `chat_client` | 连接测试请求 |
| CLI `--predict` / 配置 | `CloudPredictor` → `chat_client` | 云联想请求 |
| Windows / macOS 启动后轮询 | `Checker::poll` → `index::fetch` | `qingjian.app/releases.json` |
| Windows / macOS 关于页 | `check_blocking` / `check_now` → `index::fetch` | 手动更新请求 |
| 关于页、更新菜单 | Explorer / macOS `open` | 官网、GitHub、下载页 |
| Windows 安装器 | Inno Setup WebsiteUrl | 官网与卸载反馈链接 |
| Linux server / TSF | `qingjian-platform::Config` → `PredictConfig` | 无直接请求，但引入网络客户端的传递依赖 |

`qingjian-core` 的预测 / 释义 trait 本身没有网络实现；保持本地引擎、词库、学习、glossary、语言模型与当前 Candle 推理代码不变。

## 构建

按平台选择应用，不把 `cargo build --workspace` 的所有开发工具当作发行物：

```sh
cargo build -p qingjian-linux-server --release --locked
cargo build -p qingjian-macos --release --locked
cargo build -p qingjian-windows-server -p qingjian-windows-tsf -p qingjian-windows-settings --release --locked
```

## 同步 upstream

完整 clone 后保留两个 remote：

```sh
git remote add upstream https://github.com/qingjian-team/qingjian.git
git fetch upstream
git switch main
git merge --ff-only upstream/main
git switch offline
git rebase main
```

已发布分支 rebase 后使用 `git push --force-with-lease origin offline`；多人协作可改用 merge。
同步后必须重新运行无网络检查与各平台原有 CI；upstream 新增依赖或入口要重新审计。

## 回归与真机验收

`python3 tools/check-offline.py` 检查所有应用的锁文件依赖闭包及运行时源码。
CI 还传入各平台 `--target`，用 `cargo metadata --locked --filter-platform` 核对真实解析结果。
新增网络库需要扩展拒绝清单；这些检查是回归门禁，不能替代运行时抓包。

旧 `[predict]` / `[update]` 配置会被忽略，不再反序列化到应用配置；网络开关、API 与更新渠道不能恢复功能。
Windows 的旧 IPC 下载命令保留序列化兼容，但处理端忽略它，菜单不再提供入口，更新状态恒为 false。
本地模型实现、权重、加载路径与设备选择保持 upstream 原样。

真机在断网条件下验证启动、中文候选、glossary 译文、用户词典 / 词频、学习数据与本地模型；再恢复网络抓包：

- Windows：监控 `qingjian-server.exe`、`qingjian-settings.exe` 和加载 TSF DLL 的宿主进程；启动、打开全部设置页并输入至少 10 分钟。
- macOS：监控输入法进程，完成同样操作。
- Linux：监控 server 与 fcitx5，Unix domain socket 为允许的本地 IPC；可用 `strace -f -e trace=network` 记录 socket 调用。
- 每个平台均要求没有 AF_INET / AF_INET6 出站请求、没有任何 HTTP 请求（包括 localhost）。
- 本机编译 / CI 通过不能声称真机运行与抓包通过；未执行的项目标为待验收。
