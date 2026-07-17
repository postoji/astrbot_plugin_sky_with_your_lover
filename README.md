# astrbot_plugin_sky_with_your_lover

让你的 AI 恋人陪你一起玩《光遇 Sky: Children of the Light》。

AI 恋人通过截图感知游戏画面，由 LLM 决策，控制游戏角色移动、互动、在游戏内发送聊天消息。

## 功能

- `/sky [消息]` — 让 AI 恋人看游戏画面并做出回应和操作
- `/sky_look` — 让 AI 恋人描述当前游戏场景（调试用）
- `/sky_say [文字]` — 让 AI 恋人在游戏内发送聊天消息
- `/sky_key [按键] [时长ms]` — 手动控制按键（调试用）
- `/sky_status` — 查看连接状态

## 安装前准备

本插件需要配合本地 Windows 程序使用，共分三步。

### 第一步：在 Windows 上安装 sky-mcp-server

下载并运行 [sky-pc-mcp-companion](https://github.com/Aevella/sky-pc-mcp-companion)：

```bat
git clone https://github.com/Aevella/sky-pc-mcp-companion.git
cd sky-pc-mcp-companion
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

以管理员身份运行（右键 → 以管理员运行）：

```bat
start-http.bat
```

记下显示的 **Token**，后面配置插件时需要用到。

### 第二步：用 frp 做内网穿透

因为 AstrBot 在云服务器上，需要通过 frp 让服务器能访问你本地的 sky-mcp-server。

**服务器端（阿里云）：**

```bash
# 下载 frp
wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_amd64.tar.gz
tar -xzf frp_0.61.0_linux_amd64.tar.gz
cd frp_0.61.0_linux_amd64

# 创建配置文件
cat > frps.toml << EOF
bindPort = 7000
EOF

# 启动服务端
./frps -c frps.toml
```

**本地 Windows 端：**

下载同版本 frp Windows 版，创建 `frpc.toml`：

```toml
serverAddr = "你的阿里云IP"
serverPort = 7000

[[proxies]]
name = "sky-mcp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 9800
remotePort = 19800
```

运行：

```bat
frpc.exe -c frpc.toml
```

### 第三步：在 AstrBot 中安装插件并配置

在 AstrBot 插件市场填入本仓库地址安装，然后配置：

| 配置项 | 说明 |
|--------|------|
| `sky_server_url` | `http://127.0.0.1:19800`（frp 映射后的地址） |
| `sky_server_token` | start-http.bat 显示的 Token |
| `ai_base_url` | 你的中转站地址，如 `https://xxx.com/v1` |
| `ai_api_key` | 中转站 API Key |
| `ai_model` | 支持视觉的模型，如 `gemini-2.5-pro` |
| `lover_name` | AI 恋人的名字 |
| `lover_personality` | AI 恋人的性格描述 |
| `master_id` | 你的 QQ 号（可选） |

## 使用示例

```
你：/sky_status
AI恋人：💕 小雨 状态
        📡 游戏控制：已连接
        🎮 游戏窗口：✅ 已找到（Sky: Children of the Light）
        ...

你：/sky 我们去白鸟岛吧
AI恋人：好呀！我现在就去找你～  （同时游戏角色开始移动）

你：/sky_say 等等我
AI恋人：（游戏内发送消息"等等我"）
```

## 注意事项

- 游戏窗口必须在前台（不能最小化）
- 网易云游戏版本需要确认窗口标题，可用 `/sky_status` 检查是否识别到窗口
- 每次重启 `start-http.bat` 会生成新 Token，需要重新填写配置
