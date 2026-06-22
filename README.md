# CFIRE Agent Skills

可复用的虚拟艺人运营智能体技能集合。

## 目录结构

```
agent-skills/
├── README.md              # 本文档
├── config.example.json    # 配置文件示例
├── config_loader.py       # 统一配置加载器
├── requirements.txt       # Python 依赖（仅列出 requests 和 jieba）
│
├── cfire-artist-profile/  # 艺人档案管理技能
│   ├── SKILL.md
│   ├── scripts/
│   ├── memory_store/
│   └── reference/
│
├── cfire-artist-daily/    # 日常运营技能
│   ├── SKILL.md
│   ├── scripts/
│   └── assets/
│
├── cfire-artist-post/     # 动态发布技能
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

或者单独安装：
```bash
pip install requests jieba
```

### 2. 配置

复制配置示例文件：

```bash
cp config.example.json config.json
```

然后编辑 `config.json`，填入你的 API 配置和艺人信息。

### 3. 创建新艺人档案

首次使用前，需要为艺人创建档案：

```bash
cd cfire-artist-profile

# 复制模板
cp -r reference/ my-artist-profile/
cd my-artist-profile/

# 按照 BOOTSTRAP.md 的引导流程，逐步完成艺人配置
# 或者直接编辑 template 文件并去掉 .template 后缀
```

### 4. 使用技能

每个技能都可以通过命令行使用，详细说明请查看各技能目录下的 `SKILL.md` 文件。

示例：

```bash
# 发布动态
cd cfire-artist-post
python scripts/skill.py publish -a "示例艺人" -c "今天很开心！"

# 生成日记
cd ../cfire-artist-daily
python scripts/skill.py generate -d 2026-06-22 --save
```

## 技能说明

### cfire-artist-profile

艺人档案管理技能，支持：
- 从 0 创建新艺人档案
- 读取和维护艺人身份、性格、表达风格一致性
- 记忆存储与检索（基于 SQLite）
- 人设变更审查

### cfire-artist-daily

日常运营技能，支持：
- 每日日记生成与管理
- 内容策划（选题 + 拍摄脚本）
- 时间线维护

### cfire-artist-post

动态发布技能，支持：
- 纯文字动态发布
- 图文动态发布
- 含外部视频链接的动态发布

### cfire-artist-comment-reply

评论回复技能，支持：
- 获取未读评论
- 回复指定评论

### cfire-artist-message-reply

私信回复技能，支持：
- 获取未读私信
- 回复指定私信

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

### 添加新技能

1. 在 `agent-skills/` 下创建新目录，命名为 `cfire-artist-xxx`
2. 创建 `SKILL.md` 文档
3. 在 `scripts/` 目录下实现核心逻辑
4. 使用统一的 `config_loader.py` 加载配置
5. 遵循与现有技能相同的接口风格

### 代码规范

- 遵循 PEP 8 编码规范
- 添加必要的类型注解
- 使用中文注释和文档字符串
- 包含完善的错误处理
- 日志写入到 `scripts/logs/skill.log`

## 注意事项

1. **安全性**：不要将包含真实 API Key 的 `config.json` 提交到版本控制
2. **依赖关系**：`cfire-artist-daily` 依赖 `cfire-artist-profile`，确保目录结构正确
3. **日志管理**：所有技能都会在各自的 `scripts/logs/` 目录下生成日志文件
4. **数据库**：`cfire-artist-profile/memory_store/` 会创建 SQLite 数据库文件

## 许可证

请参考项目根目录的许可证文件。
