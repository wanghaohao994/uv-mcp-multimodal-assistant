"""
意图缓存模块 - 实现多级缓存策略，减少LLM调用次数
"""

import os
import json
import time
import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
import jieba  # 使用结巴分词进行关键词提取

# 移除循环导入
# from core.intent_recognizer import Intent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent_cache")

class IntentCache:
    """
    意图缓存管理器 - 提供多级缓存查询以减少LLM调用
    """
    
    def __init__(self, cache_file_path: str = "data/intent_cache.json", max_entries: int = 1000):
        """
        初始化意图缓存
        
        参数:
            cache_file_path: 缓存文件路径
            max_entries: 最大缓存条目数
        """
        self.cache_file = cache_file_path
        self.max_entries = max_entries
        
        # 缓存数据结构
        self.exact_cache = {}  # 精确匹配缓存
        self.keyword_index = {}  # 关键词索引
        self.last_save_time = time.time()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        
        # 加载缓存
        self.load_cache()
        logger.info(f"意图缓存初始化完成，已加载 {len(self.exact_cache)} 个条目")
    
    def load_cache(self) -> None:
        """从文件加载缓存"""
        if not os.path.exists(self.cache_file):
            logger.info(f"缓存文件不存在，创建新缓存: {self.cache_file}")
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 加载精确匹配缓存
                self.exact_cache = data.get("exact_cache", {})
                
                # 重建关键词索引
                self.keyword_index = {}
                for query, intent_dict in self.exact_cache.items():
                    self._index_keywords(query)
                    
            logger.info(f"从 {self.cache_file} 加载了 {len(self.exact_cache)} 个缓存条目")
        except Exception as e:
            logger.error(f"加载缓存文件失败: {str(e)}")
            # 如果加载失败，使用空缓存
            self.exact_cache = {}
            self.keyword_index = {}
    
    def save_cache(self, force: bool = False) -> None:
        """
        保存缓存到文件
        
        参数:
            force: 是否强制保存，不考虑时间间隔
        """
        current_time = time.time()
        
        # 每隔至少30秒才保存一次，除非强制保存
        if not force and (current_time - self.last_save_time < 30):
            return
            
        try:
            data = {
                "exact_cache": self.exact_cache,
                "updated_at": current_time
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.last_save_time = current_time
            logger.info(f"已保存 {len(self.exact_cache)} 个缓存条目到 {self.cache_file}")
        except Exception as e:
            logger.error(f"保存缓存文件失败: {str(e)}")
    
    def lookup(self, query: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        多级查找缓存
        
        参数:
            query: 用户查询
            threshold: 关键词匹配阈值
            
        返回:
            命中的缓存条目或None
        """
        # 1. 精确匹配
        if query in self.exact_cache:
            logger.info(f"缓存精确匹配命中: '{query}'")
            return self.exact_cache[query]
        
        # 2. 关键词匹配
        keywords = self._extract_keywords(query)
        if not keywords:
            return None
            
        candidates = self._find_candidates(keywords)
        if candidates:
            best_match, similarity = self._find_best_match(query, keywords, candidates)
            if similarity >= threshold:
                logger.info(f"缓存关键词匹配命中: '{query}' -> '{best_match}' (相似度: {similarity:.2f})")
                return self.exact_cache[best_match]
        
        # 未命中
        return None
    
    def add(self, query: str, intent_dict: Dict[str, Any]) -> None:
        """
        添加条目到缓存
        
        参数:
            query: 用户查询
            intent_dict: 意图识别结果字典
        """
        # 检查是否需要清理旧条目
        if len(self.exact_cache) >= self.max_entries:
            self._cleanup_cache()
            
        # 添加到精确匹配缓存
        self.exact_cache[query] = intent_dict
        
        # 更新关键词索引
        self._index_keywords(query)
        
        # 如果缓存条目数是100的倍数，保存缓存
        if len(self.exact_cache) % 100 == 0:
            self.save_cache()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取文本中的关键词"""
        # 使用结巴分词提取关键词
        words = jieba.cut_for_search(text)
        # 过滤停用词和过短词
        keywords = [w for w in words if len(w) > 1]
        return keywords
    
    def _index_keywords(self, query: str) -> None:
        """为查询建立关键词索引"""
        keywords = self._extract_keywords(query)
        for keyword in keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = set()
            self.keyword_index[keyword].add(query)
    
    def _find_candidates(self, keywords: List[str]) -> Dict[str, int]:
        """
        找出包含关键词的候选查询
        
        返回:
            字典 {查询: 匹配关键词数}
        """
        candidates = {}
        
        for keyword in keywords:
            if keyword in self.keyword_index:
                for query in self.keyword_index[keyword]:
                    candidates[query] = candidates.get(query, 0) + 1
        
        return candidates
    
    def _find_best_match(self, query: str, query_keywords: List[str], 
                        candidates: Dict[str, int]) -> Tuple[str, float]:
        """
        找出最佳匹配的候选查询
        
        返回:
            (最佳匹配查询, 相似度得分)
        """
        best_match = ""
        best_score = 0.0
        
        query_set = set(query_keywords)
        query_len = len(query_set)
        
        for candidate, keyword_matches in candidates.items():
            # 计算两个查询的关键词重叠比例
            candidate_keywords = self._extract_keywords(candidate)
            candidate_set = set(candidate_keywords)
            candidate_len = len(candidate_set)
            
            # 交集大小
            overlap = len(query_set.intersection(candidate_set))
            
            # Jaccard相似度: 交集/并集
            similarity = overlap / (query_len + candidate_len - overlap) if (query_len + candidate_len - overlap) > 0 else 0
            
            if similarity > best_score:
                best_score = similarity
                best_match = candidate
        
        return best_match, best_score
    
    def _cleanup_cache(self) -> None:
        """
        清理缓存中最旧或最少使用的条目
        当前简单实现：删除前25%的条目
        """
        if len(self.exact_cache) <= self.max_entries / 2:
            return
            
        # 删除25%的条目
        items_to_remove = int(len(self.exact_cache) * 0.25)
        keys_to_remove = list(self.exact_cache.keys())[:items_to_remove]
        
        # 从缓存和索引中删除
        for key in keys_to_remove:
            # 从关键词索引中删除
            keywords = self._extract_keywords(key)
            for keyword in keywords:
                if keyword in self.keyword_index and key in self.keyword_index[keyword]:
                    self.keyword_index[keyword].remove(key)
                    # 如果关键词没有对应的查询了，删除该关键词
                    if not self.keyword_index[keyword]:
                        del self.keyword_index[keyword]
            
            # 从精确缓存中删除
            del self.exact_cache[key]
            
        logger.info(f"缓存清理完成，删除了 {len(keys_to_remove)} 个条目")

# 单例模式实例
_cache_instance = None

def get_intent_cache(cache_file: str = "data/intent_cache.json") -> IntentCache:
    """获取意图缓存单例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = IntentCache(cache_file)
    return _cache_instance 