"""
中文文本分词器。

使用 jieba 分词 + 停用词过滤，支持 TF-IDF 计算。
分词器完全本地化，无网络依赖。
"""

import re
import json
import math
from collections import Counter
from typing import List, Dict, Tuple

try:
    import jieba
except ImportError:
    jieba = None

# 内建中文停用词表
_STOP_WORDS: set = set()
_DEFAULT_STOP_WORDS = [
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "所", "所以", "因为", "但是", "但", "而", "而且", "或", "或者", "如果",
    "虽然", "可以", "这个", "那个", "什么", "怎么", "如何", "为什么",
    "吗", "吧", "呢", "啊", "哦", "嗯", "哈", "呀", "哇",
    "与", "及", "以", "被", "把", "从", "对", "向", "让", "给",
    "还", "又", "再", "才", "刚", "已经", "正在", "将", "要",
    "能", "能够", "可能", "应该", "需要", "必须", "可以", "会",
    "很", "非常", "太", "更", "最", "比较", "特别", "十分",
    "等", "等等", "之类", "其他", "其它",
]


def _init_stop_words() -> None:
    """初始化停用词表。"""
    global _STOP_WORDS
    for w in _DEFAULT_STOP_WORDS:
        _STOP_WORDS.add(w)


_init_stop_words()


def add_stop_words(words: List[str]) -> None:
    """添加自定义停用词"""
    for w in words:
        _STOP_WORDS.add(w)


def remove_stop_words(words: List[str]) -> None:
    """移除自定义停用词"""
    for w in words:
        _STOP_WORDS.discard(w)


def tokenize(text: str, filter_stop: bool = True, min_len: int = 2) -> List[str]:
    """对中文文本进行分词，返回关键词列表。

    Args:
        text: 待分词的文本
        filter_stop: 是否过滤停用词
        min_len: 最短关键词长度（字符数）

    Returns:
        关键词列表（已去重但保留顺序）
    """
    if not text or not text.strip():
        return []

    # 清理文本
    text = re.sub(r"[^\u4e00-\u9fff\w]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if jieba is not None:
        words = jieba.lcut(text)
    else:
        # fallback: 按空格和标点分
        words = text.split()

    result = []
    seen = set()
    for w in words:
        w = w.strip().lower()
        if len(w) < min_len:
            continue
        if filter_stop and w in _STOP_WORDS:
            continue
        if w not in seen:
            seen.add(w)
            result.append(w)

    return result


def compute_tf(words: List[str]) -> Dict[str, float]:
    """计算词频 (Term Frequency)"""
    if not words:
        return {}
    counter = Counter(words)
    total = len(words)
    return {k: v / total for k, v in counter.items()}


def compute_idf(keyword: str, total_docs: int, docs_with_keyword: int) -> float:
    """计算逆文档频率 (Inverse Document Frequency)"""
    if total_docs <= 0 or docs_with_keyword <= 0:
        return 0.0
    return math.log((total_docs + 1) / (docs_with_keyword + 1)) + 1


def extract_keywords_with_positions(text: str, top_k: int = 20) -> List[Tuple[str, float, List[int]]]:
    """从文本中提取关键词及其位置。

    Returns:
        List of (keyword, tf, positions) sorted by tf descending
    """
    if jieba is not None:
        words = jieba.lcut(text)
    else:
        words = text.split()

    word_positions: Dict[str, List[int]] = {}
    for i, w in enumerate(words):
        w = w.strip().lower()
        if len(w) < 2 or w in _STOP_WORDS:
            continue
        if w not in word_positions:
            word_positions[w] = []
        word_positions[w].append(i)

    total = max(1, len(words))
    scored = []
    for word, positions in word_positions.items():
        tf = len(positions) / total
        scored.append((word, tf, positions))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
