# CFIRE Agent Skills

可复用的虚拟艺人运营智能体技能集合。提供从艺人档案管理、日常运营到内容发布、粉丝互动的完整技能体系。

## 环境要求

| 项 | 要求 |
| --- | --- |
| 操作系统 | Windows / macOS / Linux |
| Python | **3.8+**（已在 3.10 验证） |
| Git | 任意近期版本 |
| 网络 | 首次 `pip install` 需外网；运行时仅需访问 CFIRE API 域名 |
| 可选 LLM | 火山引擎方舟 API Key（仅 `cfire-artist-daily` 自动生成内容时需要） |

## 安装

### 1. 克隆仓库

```bash
git clone <your-repo-url> cfire-agent-instance
cd cfire-agent-instance
```

仓库内有两份技能代码，理解它们的分工对后续运维至关重要：

```
cfire-agent-instance/
├── cfire-agent-skills/      # 源码目录：在此修改、提交、版本管理
│   ├── README.md            # 本文档
│   ├── config.example.json
│   ├── config_loader.py
│   ├── requirements.txt
│   └── cfire-artist-*/      # 各技能源码
│
└── .trae/skills/            # 部署目录：Trae IDE 自动同步并实际执行此处的代码
    ├── config.json          # 实际生效的配置（含密钥，已 gitignore）
    └── cfire-artist-*/      # 与源码同步的运行副本
```

- **修改代码或文档** → 改 `cfire-agent-skills/`，由 Trae IDE 同步到 `.trae/skills/`
- **填写配置** → 写入 `.trae/skills/config.json`（或源码目录的 `config.json`，二选一保持一致）
- **运行时数据**（日记、SQLite DB、日志）→ 生成在 `.trae/skills/` 对应子目录下

### 2. 安装 Python 依赖

```bash
cd cfire-agent-skills
pip install -r requirements.txt
```

当前依赖：
- `requests>=2.28.0`：HTTP 请求

> `memory_store` 仅依赖 Python 标准库（`sqlite3`），无额外第三方依赖。

### 3. 配置 API 与艺人凭据

```bash
cp config.example.json config.json
```

编辑 `config.json`：

```json
{
  "api_base_url": "https://your-api-domain.com",
  "artists": {
    "凌音": {
      "artist_id": "艺人 UUID",
      "user_id": "默认操作用户 UUID",
      "api_key": "艺人独立 API Key"
    }
  }
}
```

**凭据获取方式**：
- `api_base_url`：CFIRE 平台服务端地址（联系平台管理员获取）
- `artist_id` / `user_id`：在 CFIRE 控制台艺人详情页复制
- `api_key`：艺人在 CFIRE 控制台「API Key 管理」页签生成，每个艺人独立一把

也支持环境变量覆盖（适合 CI / 容器化部署）：
- `CFIRE_API_BASE_URL`：覆盖 `api_base_url`
- `CFIRE_ARTIST_{NAME}_API_KEY`：覆盖指定艺人的 `api_key`（NAME 中空格替换为下划线，如 `CFIRE_ARTIST_凌音_API_KEY`）

### 4. 初始化艺人档案

首次使用前，需要在 `cfire-artist-profile/reference/` 目录下配置艺人档案。两种方式：

- **从 0 创建**：参考 [BOOTSTRAP.md](cfire-artist-profile/reference/BOOTSTRAP.md) 的引导流程，逐项填写
- **从模板快速开始**：编辑 `.template` 文件并去掉后缀（如 `IDENTITY.md.template` → `IDENTITY.md`）

`runtime-state.json` 中 `initialized: true` 表示档案已就绪。

### 5. 验证安装

依次执行以下命令，全部成功即代表环境就绪：

```bash
# 5.1 验证 Python 依赖与 memory_store
cd cfire-agent-skills/cfire-artist-profile
python -c "from memory_store import init, get_stats; init(); print(get_stats())"
# 预期输出：{'memories': N, 'timeline_events': N, ...}（首次为 0 或迁移后的数量）

# 5.2 验证配置加载
cd ../..
python -c "from config_loader import load_config; c=load_config(); print('artists:', list(c.get('artists', {}).keys()))"
# 预期输出：artists: ['凌音']（你在 config.json 中配置的艺人名）

# 5.3 验证 daily 技能 CLI（不调用 LLM，仅输出生成 prompt）
cd cfire-artist-daily
python scripts/skill.py generate --no-llm -d 2026-06-28
# 预期输出：包含 prompt 与 recent_events 的 JSON
```

如以上任意一步失败，参考下文「常见问题」。

### 6. 使用技能

每个技能的完整 CLI 说明见各技能目录下的 `SKILL.md`。常用命令：

```bash
# 生成并保存日记（需配置 LLM 环境变量）
cd cfire-artist-daily
python scripts/skill.py generate -d 2026-06-28 --save

# 发布纯文字动态
cd ../cfire-artist-post
python scripts/skill.py publish -a "凌音" -c "今天排练很开心！"
```

## 常见问题

| 现象 | 排查方向 |
| --- | --- |
| `ModuleNotFoundError: No module named 'requests'` | 未执行 `pip install -r requirements.txt`，或当前 Python 不是装依赖的那个 |
| `FileNotFoundError: 未找到 cfire-artist-profile 目录` | 用 `--profile-dir` 显式指定档案目录，或将 `cfire-artist-profile/` 放在与技能脚本的同级父目录下 |
| `401 Unauthorized` | `config.json` 中的 `api_key` 错误或已失效；不要改代码，先在 CFIRE 控制台重新生成 Key |
| `403 Forbidden` | 当前艺人无该操作权限，联系平台管理员 |
| 控制台打印 `[migration] MEMORY.md not found` | 正常现象。源码目录的 `reference/` 下只有 `.template` 文件，迁移脚本找不到目标文件会跳过，不影响功能；按第 4 步从模板创建档案后即不再出现 |
| 日记生成返回 `prompt` 而非 `content` | 未配置 LLM 环境变量（`LLM_API_KEY` / `LLM_MODEL`），或 `LLM_PROVIDER` 不是 `volcengine` |
| 修改了 `cfire-agent-skills/` 代码但运行无变化 | 实际执行的是 `.trae/skills/` 下的副本，确认 Trae IDE 已同步，或直接改 `.trae/skills/` |

## 技能说明

### cfire-artist-profile

艺人档案管理技能，是所有技能的基础。核心能力：
- **艺人引导**：通过结构化问答从 0 创建完整艺人档案体系
- **人设维护**：读取并维护艺人身份、性格、表达风格的一致性
- **记忆管理**：以 Markdown 为权威源、SQLite 为派生索引的近期上下文检索
- **人设变更审查**：对角色设定变化进行风险分级与影响评估
- **安全审查**：发布前的安全与质量检查
- **学习进化**：从执行结果中积累经验，优化后续输出

### cfire-artist-daily

日常运营技能，负责艺人日常内容生产与时间线管理：
- **日记管理**：生成、保存、校验每日艺人日记（≤200字）
- **内容策划**：生成选题策划与拍摄脚本（支持短视频三幕结构）
- **时间线管理**：维护艺人连续叙事时间线、事件记录
- **日程管理**：管理艺人活动安排、工作规划

### cfire-artist-post

动态发布技能，通过艺人独立 API Key 鉴权调用服务端接口：
- 纯文字动态发布（消耗 10 能量）
- 图文动态发布（消耗 50 能量）
- 含外部视频链接的动态发布（支持 Bilibili、YouTube、TikTok、抖音、快手）
- 可持续生长动态（Growth Post）：先发布一种形态，后续可追加其他形态

## 开发指南

### 技能间依赖关系

```
cfire-artist-profile （基础）
    ↑
    ├── cfire-artist-daily
    └── cfire-artist-post
```

- `cfire-artist-profile` 是基础技能，其他技能都依赖它读取艺人档案与记忆
- `cfire-artist-daily` 额外依赖 `memory_store` 进行时间线写入与近期上下文检索

### 添加新技能

1. 在 `cfire-agent-skills/` 下创建新目录，命名为 `cfire-artist-xxx`
2. 创建 `SKILL.md` 文档（包含 YAML frontmatter 的 name 和 description）
3. 在 `scripts/` 目录下实现核心逻辑
4. 使用统一的 `config_loader.py` 加载配置
5. 遵循与现有技能相同的 CLI 接口风格
6. 日志统一写入 `scripts/logs/skill.log`

### 代码规范

- 遵循 PEP 8 编码规范
- 添加必要的类型注解
- 使用中文注释和文档字符串
- 包含完善的错误处理和幂等性设计
- 错误码处理：400/401/403/404/409 禁止盲目重试

## 注意事项

1. **安全性**：不要将包含真实 API Key 的 `config.json` 提交到版本控制
2. **依赖关系**：`cfire-artist-daily` 依赖 `cfire-artist-profile`，确保目录结构正确
3. **日志管理**：所有技能都会在各自的 `scripts/logs/` 目录下生成日志文件
4. **数据库**：`cfire-artist-profile/memory_store/` 会创建 SQLite 数据库文件（派生索引，可从 Markdown 重建）
5. **缓存文件**：`__pycache__/`、`.pyc` 文件等不要提交到版本控制
6. **鉴权问题**：遇到 401 错误优先检查配置，不要修改代码

## 许可证

请参考项目根目录的许可证文件。
