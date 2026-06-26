# CFIRE Agent Skills

可复用的虚拟艺人运营智能体技能集合。提供从艺人档案管理、日常运营到内容发布、粉丝互动的完整技能体系。

## 目录结构

```
cfire-agent-skills/
├── README.md                # 本文档
├── config.example.json      # 配置文件示例
├── config_loader.py         # 统一配置加载器
├── requirements.txt         # Python 依赖
│
├── cfire-artist-profile/    # 艺人档案管理技能
│   ├── SKILL.md
│   ├── scripts/             # 人设审查等脚本
│   ├── memory_store/        # SQLite 记忆存储与检索
│   └── reference/           # 档案模板与规范
│
├── cfire-artist-daily/      # 日常运营技能
│   ├── SKILL.md
│   ├── scripts/             # 日记、内容策划脚本
│   └── assets/              # 日记与内容策划存储
│       ├── diary/
│       └── content_draft/
│
├── cfire-artist-post/       # 动态发布技能
│   ├── SKILL.md
│   └── scripts/
│
├── cfire-artist-comment-reply/  # 评论回复技能
│   ├── SKILL.md
│   └── scripts/
│
└── cfire-artist-message-reply/  # 私信回复技能
    ├── SKILL.md
    └── scripts/
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

当前依赖：
- `requests>=2.28.0`：HTTP 请求
- `jieba>=0.42.1`：中文分词（记忆检索用）

### 2. 配置

复制配置示例文件：

```bash
cp config.example.json config.json
```

然后编辑 `config.json`，填入你的 API 配置和艺人信息。也支持通过环境变量配置，详见下文。

### 3. 初始化艺人档案

首次使用前，需要在 `cfire-artist-profile/reference/` 目录下配置艺人档案。参考 `BOOTSTRAP.md` 的引导流程，或直接编辑 `.template` 文件并去掉后缀。

### 4. 使用技能

每个技能都可以通过命令行使用，详细说明请查看各技能目录下的 `SKILL.md` 文件。

示例：

```bash
# 生成日记（需配置 LLM 环境变量）
cd cfire-artist-daily
python scripts/skill.py generate -d 2026-06-26 --save

# 发布动态
cd ../cfire-artist-post
python scripts/skill.py publish -a "示例艺人" -c "今天排练很开心！"

# 获取未读评论
cd ../cfire-artist-comment-reply
python scripts/skill.py list -a "示例艺人"
```

## 技能说明

### cfire-artist-profile

艺人档案管理技能，是所有技能的基础。核心能力：
- **艺人引导**：通过结构化问答从 0 创建完整艺人档案体系
- **人设维护**：读取并维护艺人身份、性格、表达风格的一致性
- **记忆管理**：基于 SQLite 的长周期存储与倒排索引检索
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

### cfire-artist-comment-reply

评论回复技能，让艺人智能体阅读和回复粉丝评论：
- 获取艺人动态下 24 小时内未读过的评论（单次最多 10 条）
- 对指定评论生成符合艺人设定的回复
- 自动过滤无意义垃圾留言
- 按优先级排序（高赞 > 长内容 > 最新）

### cfire-artist-message-reply

私信回复技能，让艺人智能体阅读和回复粉丝私信：
- 获取艺人 48 小时内未读过的用户私信（单次最多 10 条）
- 对指定私信生成符合艺人设定的回复
- 自动过滤无意义垃圾私信
- 包含历史消息上下文，便于连贯回复

## 配置说明

### config.json 格式

```json
{
  "api_base_url": "https://your-api-domain.com",
  "artists": {
    "艺人名称": {
      "artist_id": "艺人 UUID",
      "user_id": "默认操作用户 UUID",
      "api_key": "艺人 API Key"
    }
  }
}
```

### 环境变量

也可以通过环境变量配置：
- `CFIRE_API_BASE_URL`: API 基础地址
- `CFIRE_ARTIST_{NAME}_API_KEY`: 艺人 API Key（NAME 为艺人名称，空格替换为下划线）

## 开发指南

### 技能间依赖关系

```
cfire-artist-profile （基础）
    ↑
    ├── cfire-artist-daily
    ├── cfire-artist-post
    ├── cfire-artist-comment-reply
    └── cfire-artist-message-reply
```

- `cfire-artist-profile` 是基础技能，其他技能都依赖它读取艺人档案与记忆
- `cfire-artist-daily` 额外依赖 `memory_store` 进行时间线与记忆写入

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
4. **数据库**：`cfire-artist-profile/memory_store/` 会创建 SQLite 数据库文件
5. **缓存文件**：`__pycache__/`、`.pyc` 文件等不要提交到版本控制
6. **鉴权问题**：遇到 401 错误优先检查配置，不要修改代码

## 许可证

请参考项目根目录的许可证文件。
