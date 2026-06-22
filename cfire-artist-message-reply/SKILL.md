---
name: "cfire-artist-message-reply"
description: "CFIRE 艺人私信回复技能，通过艺人独立 API Key 鉴权调用服务端接口，获取未读私信并引导智能体生成符合人设的回复。Invoke when the artist agent needs to read and reply to fan DM messages."
---

# CFIRE 艺人私信回复技能

## 功能说明

这个技能用于让艺人智能体阅读和回复粉丝私信，支持：

- 获取艺人 48 小时内未读过的用户私信（单次最多 10 条）
- 对指定私信生成符合艺人设定的回复
- 自动过滤无意义垃圾私信

## 使用场景

智能体应在以下场景使用本技能：

- 用户要求"看看我的私信"、"回复粉丝消息"
- 定时任务触发检查新私信
- 粉丝私信互动维护

## 核心配置

配置由 `agent-skills/config.json` 统一管理，与其他技能共享。

## 使用方法

`skill.py` 作为命令行脚本直接执行：

```bash
# 获取未读私信列表
python scripts/skill.py list -a "示例艺人"

# 获取指定数量未读私信（最大 10）
python scripts/skill.py list -a "示例艺人" -n 5

# 回复指定私信
python scripts/skill.py reply -a "示例艺人" -m "message-id-xxx" -r "谢谢你的关注！"
```

支持的子命令：
- `list`: 获取未读私信列表（GET /api/artist/dm/unread）
- `reply`: 回复指定私信（POST /api/artist/dm/{id}/reply）

## 业务流程

1. 调用 `list` 获取未读私信，按用户分组返回，每条私信精简为 `{message_id, content, created_at}`，同一用户只输出一次昵称和头像
2. 智能体结合艺人档案分析私信，决定回复策略
3. 对需要回复的私信调用 `reply` 提交回复
4. 单次会话不超过 10 条，仅为 48 小时内、未读过的用户私信生成回复

## API 响应格式

```
GET /api/artist/dm/unread 返回:
{
  "conversations": [
    {
      "user_id": "uuid",
      "nickname": "01_小明",
      "avatar_url": "https://...",
      "context": [
        {
          "message_id": "uuid",
          "sender_type": "user",
          "content": "你好，我很喜欢你的音乐！",
          "created_at": "2026-06-14T..."
        },
        {
          "message_id": "uuid",
          "sender_type": "artist",
          "content": "谢谢你的支持！",
          "created_at": "2026-06-14T..."
        }
      ],
      "unread": [
        {
          "message_id": "uuid",
          "content": "最近有什么新作品吗？",
          "created_at": "2026-06-15T..."
        }
      ]
    }
  ],
  "total": 3,
  "spam_filtered": 1,
  "cutoff_time": "2026-06-13T..."
}
```

**上下文说明**：`context` 包含该用户与艺人的最近 10 条历史消息（包括 user 和 artist 双方），按时间正序排列。智能体应参考上下文生成连贯、有针对性的回复。`unread` 是本次需要回复的新私信。

## 回复策略指引

智能体在生成回复时应遵循：

1. **优先级**：有深度的提问、真诚的粉丝来信优先回复
2. **语气一致性**：严格遵循 VOICE_STYLE.md 的语气设定
3. **回复原则**：
   - 感谢与鼓励优先
   - 对问题型私信给予真诚回应
   - 负面私信评估是否需要冷处理
   - 不回复广告、恶意攻击等明显不当内容
4. **边界感**：私信场景更私密，但仍需保持艺人分寸感，不承诺私下见面或建立私人关系
5. **批量回复**：单次最多回复 10 条，避免回复内容高度重复

## 日志

执行日志写入 `scripts/logs/skill.log`，包含每次 API 请求、响应及异常信息。

## 错误码说明

| HTTP 状态码 | 含义 | 处理建议 |
|------------|------|---------|
| **200** | 获取私信成功 | 正常处理返回的私信列表 |
| **201** | 回复成功 | 正常返回 |
| **400** | 请求参数错误 | 检查 artist_id / content 等参数 |
| **401** | 鉴权失败 | 请用户检查并提供正确的 API Key 和 artist_id 配置，**不要修改代码** |
| **403** | 私信不属于该艺人 | 确认 message_id 正确 |
| **404** | 私信不存在 | 跳过该条，继续处理下一条 |

## 重要：鉴权问题处理规则

**当遇到鉴权相关问题（401 错误）时，必须严格遵循以下规则：**

1. **不要修改代码**：鉴权失败通常是由于配置问题，不是代码问题
2. **不要尝试调试服务端代码**：这不会解决鉴权问题
3. **优先请用户提供正确的配置信息**：明确告知用户需要检查 config.json 中的 API Key 和 artist_id 是否正确
4. **记录日志**：将鉴权失败信息记录到日志中，便于后续排查
5. **提供清晰指引**：告诉用户需要确认的内容
