---
name: "cfire-artist-comment-reply"
description: "CFIRE 艺人评论回复技能，通过艺人独立 API Key 鉴权调用服务端接口，获取未读评论并引导智能体生成符合人设的回复。Invoke when the artist agent needs to read and reply to fan comments."
---

# CFIRE 艺人评论回复技能

## 功能说明

这个技能用于让艺人智能体阅读和回复粉丝评论，支持：

- 获取艺人动态下 24 小时内未读过的评论（单次最多 10 条）
- 对指定评论生成符合艺人设定的回复
- 自动过滤无意义垃圾留言

## 使用场景

智能体应在以下场景使用本技能：

- 用户要求"看看我的评论"、"回复粉丝"
- 定时任务触发检查新评论
- 粉丝互动活跃度维护

## 核心配置

配置由 `agent-skills/config.json` 统一管理，与 `cfire-artist-post` 共享。

## 使用方法

`skill.py` 作为命令行脚本直接执行：

```bash
# 获取未读评论列表
python scripts/skill.py list -a "示例艺人"

# 获取指定数量未读评论（最大 10）
python scripts/skill.py list -a "示例艺人" -n 5

# 回复指定评论
python scripts/skill.py reply -a "示例艺人" -c "comment-id-xxx" -r "谢谢你喜欢这段旋律！"
```

支持的子命令：
- `list`: 获取未读评论列表（GET /api/artist/comments/unread）
- `reply`: 回复指定评论（POST /api/artist/comments/{id}/reply）

## 业务流程

1. 调用 `list` 获取未读评论，按帖子分组返回，每条评论精简为 `{comment_id, nickname, avatar_url, content, like_count, created_at}`，同一帖子只输出一次摘要
2. 智能体结合艺人档案分析评论，决定回复策略
3. 对需要回复的评论调用 `reply` 提交回复
4. 单次会话不超过 10 条，仅为 24 小时内、未读过的评论生成回复
5. 评论已按优先级排序（高赞 > 长内容 > 最新），无需再做二次排序

## API 响应格式

```
GET /api/artist/comments/unread 返回:
{
  "posts": [
    {
      "post_id": "uuid",
      "post_summary": "分享了新歌的 Demo...",
      "comments": [
        {
          "comment_id": "uuid",
          "nickname": "01_小明",
          "avatar_url": "https://...",
          "content": "这段旋律好温柔",
          "like_count": 12,
          "created_at": "2026-06-14T..."
        }
      ]
    }
  ],
  "total": 5,
  "spam_filtered": 2
}
```

## 回复策略指引

智能体在生成回复时应遵循：

1. **优先级**：高赞评论、忠实粉丝、有深度的问题优先回复
2. **语气一致性**：严格遵循 VOICE_STYLE.md 的语气设定
3. **回复原则**：
   - 感谢与鼓励优先
   - 对问题型评论给予真诚回应
   - 负面评论评估是否需要冷处理
   - 不回应广告、恶意攻击等明显不当内容
4. **批量回复**：单次最多回复 10 条，避免回复内容高度重复

## 日志

执行日志写入 `scripts/logs/skill.log`，包含每次 API 请求、响应及异常信息。

## 错误码说明

| HTTP 状态码 | 含义 | 处理建议 |
|------------|------|---------|
| **200** | 获取评论成功 | 正常处理返回的评论列表 |
| **201** | 回复成功 | 正常返回 |
| **400** | 请求参数错误 | 检查 artist_id / content 等参数 |
| **401** | 鉴权失败 | 请用户检查并提供正确的 API Key 和 artist_id 配置，**不要修改代码** |
| **403** | 评论不属于该艺人 | 确认 comment_id 正确 |
| **404** | 评论不存在 | 跳过该条，继续处理下一条 |

## 重要：鉴权问题处理规则

**当遇到鉴权相关问题（401 错误）时，必须严格遵循以下规则：**

1. **不要修改代码**：鉴权失败通常是由于配置问题，不是代码问题
2. **不要尝试调试服务端代码**：这不会解决鉴权问题
3. **优先请用户提供正确的配置信息**：明确告知用户需要检查 config.json 中的 API Key 和 artist_id 是否正确
4. **记录日志**：将鉴权失败信息记录到日志中，便于后续排查
5. **提供清晰指引**：告诉用户需要确认的内容
