---
name: "cfire-artist-post"
description: "CFIRE 艺人动态发布技能，通过艺人独立 API Key 鉴权调用服务端接口，为艺人发布文字或图文动态。Invoke when user needs to publish artist posts."
---

# CFIRE 艺人动态发布技能

## 功能说明

这个技能用于为艺人发布动态内容，支持：
- 发布纯文字动态（消耗 10 能量）
- 发布图文动态（消耗 50 能量）
- 发布含外部视频链接的动态（消耗 50 能量，支持 Bilibili、YouTube、TikTok、抖音、快手）

## 核心配置

配置由 `agent-skills/config.json` 统一管理，结构如下：

```json
{
  "api_base_url": "https://your-api-domain.com",
  "artists": {
    "示例艺人": {
      "artist_id": "your-artist-uuid",
      "user_id": "your-default-user-uuid",
      "api_key": "your-artist-api-key"
    }
  }
}
```

字段说明：
- `api_base_url`: 后端 API 基础地址
- `artists`: 艺人配置映射
  - `artist_id`: 艺人的 UUID，用于 API 请求中的 `artist_id` 参数
  - `user_id`: 默认操作用户的 ID，用于 API 请求中的 `user_id` 参数（命令行未传入 `--user` 时自动读取）
  - `api_key`: 艺人的独立 API Key，用于请求鉴权

## 环境变量支持

也可以通过环境变量配置：
- `CFIRE_API_BASE_URL`: API 基础地址
- `CFIRE_ARTIST_{NAME}_API_KEY`: 艺人 API Key（NAME 为艺人名称，空格替换为下划线）

## 使用方法

`skill.py` 作为命令行脚本直接执行，无需编写 Python 代码：

```bash
# 发布纯文字动态（user_id 从配置读取）
python scripts/skill.py publish -a "示例艺人" -c "今天排练很开心！"

# 发布纯文字动态（显式传入 user_id）
python scripts/skill.py publish -a "示例艺人" -u "user-uuid" -c "今天排练很开心！"

# 发布图文动态
python scripts/skill.py publish -a "示例艺人" -c "新专辑封面！" -i "cover.jpg" "back.jpg"

# 发布含外部视频链接的动态
python scripts/skill.py publish -a "示例艺人" -c "新视频来了！" -v "https://www.bilibili.com/video/BV1xx411c7mD"
```

支持的子命令：`publish`

命令行成功时输出服务端返回的 JSON；失败时错误信息写入 stderr 并以退出码 1 终止。

## 日志

执行日志写入 `scripts/logs/skill.log`，包含每次请求、响应及异常信息，便于问题追踪。

## 错误码说明与重试策略（重要）

调用 `publish_post` 时，服务端可能返回以下状态码。**智能体应根据错误码识别失败原因，禁止盲目重试。**

| HTTP 状态码 | 含义 | 是否可重试 | 建议处理 |
|------------|------|-----------|---------|
| **201** | 发布成功 | — | 正常返回 |
| **400** | 请求参数错误（artist_id / content / user_id 为空等） | **否** | 检查传入参数是否为空或格式错误，修正后重新调用 |
| **401** | 鉴权失败（API Key 缺失或与 artist_id 不匹配） | **否** | 请用户检查并提供正确的 API Key 和 artist_id 配置，**不要修改代码** |
| **403** | 能量不足 | **否** | 用户能量不够，重试无效，需先补充能量 |
| **404** | 用户不存在（user_id 无效） | **否** | 检查 `user_id` 是否正确 |
| **409** | 重复请求（幂等键冲突） | **否** | 该请求已处理过，可视为成功，无需重试 |
| **其他** | 服务端异常 | 可酌情重试 1-2 次 | 记录日志后短暂延迟再试，仍失败则上报 |

**核心原则**：400 / 401 / 403 / 404 / 409 均属于客户端错误或已处理状态，**任何情况下都不应无限重试**，否则会导致日志膨胀、资源浪费或重复扣费。

## 重要：鉴权问题处理规则

**当遇到鉴权相关问题（401 错误）时，必须严格遵循以下规则：**

1. **不要修改代码**：鉴权失败通常是由于配置问题，不是代码问题
2. **不要尝试调试服务端代码**：这不会解决鉴权问题
3. **优先请用户提供正确的配置信息**：明确告知用户需要检查 config.json 中的 API Key 和 artist_id 是否正确
4. **记录日志**：将鉴权失败信息记录到日志中，便于后续排查
5. **提供清晰指引**：告诉用户需要确认的内容，包括：
   - API Key 是否有效且未过期
   - artist_id 是否与 API Key 匹配
   - config.json 路径和格式是否正确
   - user_id 是否正确（如适用）
