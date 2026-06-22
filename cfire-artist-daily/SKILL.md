---
name: "cfire-artist-daily"
description: "CFIRE 艺人日常运营技能。负责日程管理、时间线更新、每日日记生成、内容策划（选题+拍摄脚本）等日常运营工作。Invoke when need to manage artist schedule, timeline events, daily diary, or content drafts."
---

# CFIRE 艺人日常运营技能

## 功能定位

本技能负责艺人所有日常运营相关功能：

## 核心能力
- **内容策划**：生成当天主要活动的选题策划与拍摄脚本，支持与过往内容呼应
- **日记管理**：生成、保存、校验每日艺人日记
- **时间线管理**：维护艺人连续叙事时间线、事件记录
- **日程管理**：管理艺人活动安排、工作规划

## 内容策划功能说明

本技能还支持生成当天主要活动的**选题策划**与**拍摄脚本**，保存到 `assets/content_draft/` 目录：

- 读取艺人档案（人物设定、性格、目标、语气、内容策略、安全边界）
- 读取 `memory_store` 中的近期时间线与重要记忆，保持与过往内容的连续性
- 生成选题策划：选题名称、内容支柱、主题描述、与过往内容的呼应、预期情绪价值
- 生成角色妆造（如涉及 Cosplay 或特定造型）：角色名称、选择理由、服装、妆容、场景搭配
- 生成拍摄脚本：按镜头组织，每个镜头包含人物描述（含妆造细节）、音色参考、景别、光线、音效、画面、台词
- 将策划保存到 `content_draft/YYYY-MM-DD.md`
- 作为后续拍摄、剪辑、发布的参考依据

### 内容策划约束

- 选题必须符合艺人的独立音乐人人设：温柔、克制、清醒、有创作锋芒
- 拍摄脚本至少包含 2 个镜头，每个镜头必须包含：景别、光线、音效、画面、人物台词
- 拍摄脚本需遵循「短视频三幕结构」，确保开头即抓住注意力：
  - **第 1 幕（黄金 3 秒）**：抛出「情绪钩子」或「未完成的悬念」。绝对不用"大家好"开场，必须用一句对话、一个特写动作或一句内心独白直接切入情绪核心（如："三天没来，琴键上的灰都认识我了"）。让观众在 3 秒内产生"后来呢？"的好奇或"我也是"的共鸣。
  - **第 2 幕（中段展开）**：用具体细节推进情绪，通过动作、环境音、微表情让情绪落地。用"展示"代替"告诉"，中段可加入一个小转折保持节奏。
  - **第 3 幕（结尾收束）**：不强行总结道理，用轻量但有余味的台词收尾。可保留"未完成感"，或给出温柔的前行动作。最后 1 秒画面建议人物低头微笑、望向窗外、或手指落下琴键。
- 如涉及 Cosplay，必须在「角色妆造」章节详细说明角色选择理由、服装、妆容和场景搭配；拍摄脚本的人物描述需呼应妆造细节。
- 不编造未确认事实、未公开合作、未来活动或线下见面。
- 台词风格遵循 `VOICE_STYLE.md`，可中可英，英语台词需注明（标准美式英语）。
- 可以偶尔与之前内容呼应，但不要强行重复。

## 日记管理功能说明

本技能赋予艺人智能体每日更新日记的能力：

- 读取艺人档案（人物设定、性格、目标、语气、安全边界）
- 读取 `memory_store` 中的近期时间线、重要记忆与粉丝互动
- 生成一则第一人称日记，描述今天做了什么、看到/听到什么有趣的小事、自己的心情与感受
- 将日记追加到 `reference/DIARY.md`，并写入 `memory_store` 时间线（事件类型 `日记`）
- 作为后续日常动态、创作手记、粉丝互动等内容的上下文参考

## 核心约束

- **每日新增日记长度不超过 200 字（含标点与空格）**
- 不编造未确认事实、未公开合作、未来活动或线下见面
- 语气需符合 `VOICE_STYLE.md`，温柔、克制、清醒，可带轻微诗性
- 优先延续最近 3-7 天时间线；无事实时写感受，不伪造事件

## 依赖

- 必须能访问同级的 `cfire-artist-profile` 目录，以读取 reference 文件与 `memory_store`
- 自动生成日记时需要配置环境变量（与后端 `llm_service.py` 保持一致）：
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - `LLM_PROVIDER`（当前仅支持 `volcengine`）
- 未配置 LLM 时，`generate` 命令会返回构建好的 prompt，可交由外部模型生成后再用 `save` 保存

## 目录结构

```text
assets/
  diary/            # 每日日记目录
    YYYY-MM-DD.md   # 每日日记文件
  content_draft/    # 内容策划目录
    YYYY-MM-DD.md   # 每日内容策划文件（选题 + 拍摄脚本）
```

## 存储位置

| 存储 | 路径 / 表 | 说明 |
| --- | --- | --- |
| 独立日记文件 | `assets/diary/YYYY-MM-DD.md` | 按日期命名，独立 Schema 校验；作为内容生成的权威参考源 |
| 独立内容策划文件 | `assets/content_draft/YYYY-MM-DD.md` | 按日期命名，包含选题策划、角色妆造（可选）与拍摄脚本 |
| 时间线记录 | `memory_store.timeline_events` | 事件类型 `日记`/`创作`/`活动`/`复盘`/`粉丝互动`/`作品`/`争议`/`初始化`，支持检索与后续内容生成引用 |

## 独立日记 Schema（约束）

### 命名约束
- 文件名必须为 `YYYY-MM-DD.md`（严格匹配）
- 日期必须合法，范围 2000-01-01 ~ 2100-12-31
- 同一日期只允许一个文件；重复保存视为更新，覆盖原文件

### 内容结构（必需章节）

```markdown
# 日记 / YYYY-MM-DD

## 正文
<日记正文，第一人称，不超过 200 字，适合直接作为动态发布>

## 情绪
<情绪标签>

## 元信息
- 日期：YYYY-MM-DD
- 字数：<字数统计>
- 保存时间：<ISO 时间>
```

### 情绪标签白名单
开心、期待、紧张、疲惫、温柔、平静、焦虑、安心、兴奋、迷茫

### 长度约束
- 正文去首尾空白后长度 1 ~ 200 字（含标点与空格）

### 保存时校验项
1. 日期格式与范围
2. `## 正文` / `## 情绪` 必需章节存在
3. 情绪标签属于白名单
4. 正文长度 1 ~ 200 字
5. 正文是第一人称，语言风格符合人设

## 内容策划 Schema（约束）

### 命名约束
- 文件名必须为 `YYYY-MM-DD.md`（严格匹配）
- 日期必须合法，范围 2000-01-01 ~ 2100-12-31
- 同一日期只允许一个文件；重复保存视为更新，覆盖原文件

### 内容结构（必需章节）

```markdown
# 内容策划 / YYYY-MM-DD

## 日期
YYYY-MM-DD

## 选题策划

### 选题名称
<一句话选题名称>

### 内容支柱
<日常陪伴 / 创作进展 / 粉丝互动 / 独立态度 / 活动预热 / 活动复盘>

### 主题描述
<2-4 句话描述选题主题>

### 与过往内容的呼应
<描述与最近内容的连续性；如无则写"无">

### 预期情绪价值
<一句话说明希望给粉丝带来的情绪价值>

## 角色妆造（如涉及 Cosplay 或特定造型，请填写）

### Cosplay 角色
<角色名称及作品出处>

### 选择理由
<角色与今日主题、艺人气质的契合点>

### 服装
<详细穿搭描述>

### 妆容
<底妆、眼妆、唇妆、细节点缀>

### 场景搭配
<道具、布景、色调呼应建议>

## 拍摄脚本

[镜头 1]
【人物 1】<人物描述，含穿搭/妆造、场景、动作>
人物音色参考：<音频参考，如【音频 1】>
景别：<景别描述>
光线：<光线描述>
音效：<音效描述>
画面：<画面描述>
人物台词：<台词内容，注明语言>

[镜头 2]
<同上格式>

## 元信息
- 镜头数：<N>
- 保存时间：<ISO 时间>
```

### 内容支柱白名单
日常陪伴、创作进展、粉丝互动、独立态度、活动预热、活动复盘

### 保存时校验项
1. 日期格式与范围
2. `## 日期` / `## 选题策划` / `## 拍摄脚本` 必需章节存在
3. 文件名日期与 `## 日期` 内容一致
4. 内容支柱属于白名单（如填写）
5. 拍摄脚本至少包含 2 个镜头
6. 每个镜头必须包含：景别、光线、音效、画面字段
7. 如涉及 Cosplay，「角色妆造」章节建议包含：Cosplay 角色、选择理由、服装、妆容

## 使用方法

`skill.py` 作为命令行脚本直接执行，无需编写 Python 代码。

### 日记命令

```bash
# 自动生成日记（需配置 LLM 环境变量）
python scripts/skill.py generate

# 生成指定日期的日记并立即保存
python scripts/skill.py generate -d 2026-06-18 --save

# 仅输出 prompt，不调用 LLM
python scripts/skill.py generate --no-llm

# 保存已有的日记内容（按独立 Schema 校验）
python scripts/skill.py save -d 2026-06-18 -m "期待" -c "今天把屋顶录的风声切片放进新 demo 里，突然有了副歌的走向。"

# 读取指定日期日记
python scripts/skill.py read -d 2026-06-18

# 仅校验不保存
python scripts/skill.py validate -d 2026-06-18 -m "期待" -c "..."

# 列出 diary/ 目录下最近日记文件
python scripts/skill.py list -n 10
```

### 内容策划命令

```bash
# 自动生成内容策划（需配置 LLM 环境变量）
python scripts/skill.py draft-generate

# 生成指定日期的内容策划并立即保存
python scripts/skill.py draft-generate -d 2026-06-19 --save

# 仅输出 prompt，不调用 LLM
python scripts/skill.py draft-generate --no-llm

# 保存已有的内容策划内容（按 Schema 校验）
python scripts/skill.py draft-save -d 2026-06-19 -c "# 内容策划 / 2026-06-19\n..."

# 读取指定日期内容策划
python scripts/skill.py draft-read -d 2026-06-19

# 列出 content_draft/ 目录下最近内容策划文件
python scripts/skill.py draft-list -n 10
```

## 命令说明

### 日记命令

| 子命令 | 作用 |
| --- | --- |
| `generate` | 加载上下文并生成日记；未配置 LLM 时返回 prompt |
| `save` | 将指定日记内容按独立 Schema 保存到 `assets/diary/YYYY-MM-DD.md` 与 memory_store 时间线 |
| `read` | 读取 `assets/diary/` 下指定日期日记文件 |
| `validate` | 校验参数是否符合独立 Schema，但不写入任何存储 |
| `list` | 从 `assets/diary/` 目录列出最近日记文件 |

### 内容策划命令

| 子命令 | 作用 |
| --- | --- |
| `draft-generate` | 加载上下文并生成内容策划（选题 + 拍摄脚本）；未配置 LLM 时返回 prompt |
| `draft-save` | 将指定内容策划按 Schema 保存到 `assets/content_draft/YYYY-MM-DD.md` 与 memory_store 时间线 |
| `draft-read` | 读取 `assets/content_draft/` 下指定日期内容策划文件 |
| `draft-list` | 从 `assets/content_draft/` 目录列出最近内容策划文件 |

### `generate` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--date`, `-d` | 日记日期，格式 `YYYY-MM-DD`，默认今天 |
| `--no-llm` | 不调用 LLM，仅输出 prompt |
| `--save` | 生成成功后立即保存 |

### `save` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--date`, `-d` | 日记日期，默认今天 |
| `--mood`, `-m` | 情绪标签，必须属于白名单，默认自动提取 |
| `--content`, `-c` | 日记正文，必填，1 ~ 200 字 |

### `read` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--date`, `-d` | 日记日期（YYYY-MM-DD），必填 |

### `validate` 参数

与 `save` 参数相同；仅做校验，不写入任何存储。

### `list` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--limit`, `-n` | 返回数量，默认 10 |

### `draft-generate` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--date`, `-d` | 策划日期，格式 `YYYY-MM-DD`，默认今天 |
| `--no-llm` | 不调用 LLM，仅输出 prompt |
| `--save` | 生成成功后立即保存 |

### `draft-save` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--date`, `-d` | 策划日期，默认今天 |
| `--content`, `-c` | 内容策划正文（Markdown），必填 |

### `draft-read` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--date`, `-d` | 策划日期（YYYY-MM-DD），必填 |

### `draft-list` 参数

| 参数 | 说明 |
| --- | --- |
| `--profile-dir`, `-p` | 指定 `cfire-artist-profile` 目录路径 |
| `--limit`, `-n` | 返回数量，默认 10 |

## 输出格式

### 日记生成成功

```json
{
  "date": "2026-06-18",
  "content": "今天把屋顶录的风声切片放进新 demo，副歌突然有了方向。",
  "mood": "期待",
  "length": 32,
  "source": "llm",
  "saved": false
}
```

### 未配置 LLM

```json
{
  "date": "2026-06-18",
  "content": "",
  "source": "prompt",
  "prompt": "...",
  "saved": false,
  "error": "未配置 LLM 或生成失败，已返回 prompt，可人工填写后调用 save。"
}
```

### 日记保存成功

```json
{
  "date": "2026-06-18",
  "content": "...",
  "mood": "期待",
  "length": 32,
  "event_id": 42,
  "diary_path": ".../assets/diary/2026-06-18.md",
  "saved": true
}
```

### 内容策划生成成功

```json
{
  "date": "2026-06-19",
  "content": "# 内容策划 / 2026-06-19\n...",
  "source": "llm",
  "saved": false
}
```

### 内容策划保存成功

```json
{
  "date": "2026-06-19",
  "content": "# 内容策划 / 2026-06-19\n...",
  "shot_count": 3,
  "length": 850,
  "event_id": 43,
  "draft_path": ".../assets/content_draft/2026-06-19.md",
  "saved": true
}
```

## 与内容生成的协同

- 后续内容生成从 `assets/diary/` 目录读取最近 3-7 篇日记作为连续叙事与情绪参考；同时以 `memory_store.timeline_events` 中事件类型 `日记` 的记录作为结构化回溯。
- 内容策划从 `assets/content_draft/` 目录读取最近策划，作为拍摄与发布的参考依据；事件类型 `创作` 的记录作为结构化回溯。
- 日记与内容策划本身不直接发布，仅作为内部参考；如需发布，应通过 `cfire-artist-post` 技能并经过 `REVIEW.md` 审查。

## 错误处理

- 未找到 `cfire-artist-profile` 目录时，提示使用 `--profile-dir` 显式指定。
- `--date` 不合法时直接报错。
- `--mood` 不在白名单时直接报错，并给出允许列表。
- 日记正文为空或超过 200 字时直接报错。
- 内容策划缺少必需章节或镜头数不足时直接报错。
- LLM 调用失败时，降级为返回 prompt，不中断流程。
