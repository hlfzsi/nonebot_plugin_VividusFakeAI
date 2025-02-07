from functools import lru_cache
from typing import List, Optional, Tuple, Any
import asyncio
import json
import random


import aiosqlite
import numpy as np
from datasketch import MinHash, MinHashLSH
import jieba
from nonebot_plugin_ACMD.connection_pool import SQLitePool


class DatabaseManager:
    """
    数据库管理类，支持权重管理、异步操作、minhash缓存和系统统计

    Attributes:
        db_path (str): 数据库路径
    """
    __slots__ = ('pool')

    def __init__(self, db_path: str = "qa_database.db"):
        self.pool = SQLitePool(db_path, max_size=10)

    async def initialize(self) -> None:
        """初始化数据库连接并创建表结构"""
        async with self.pool.connection() as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await self._create_tables(conn)

    async def _create_tables(self, conn: aiosqlite.Connection) -> None:
        """创建带权重字段、minhash缓存字段和统计表的数据库表结构"""
        await conn.execute('PRAGMA journal_mode=WAL;')

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                name TEXT PRIMARY KEY,
                description TEXT
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                image_folder TEXT,
                group_name TEXT NOT NULL,
                weight INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(question, answer, group_name, image_folder),
                FOREIGN KEY (group_name) REFERENCES groups(name) ON DELETE CASCADE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_minhashes (
                qa_id INTEGER PRIMARY KEY,
                minhash BLOB,
                FOREIGN KEY (qa_id) REFERENCES qa_pairs(id) ON DELETE CASCADE
            )
        """)

        await conn.commit()

    async def add_or_update_qa(self, question: str, answer: str, group_name: str, image_folder: Optional[str]) -> int:
        async with self.pool.connection() as conn:
            if not await conn.execute_fetchall("SELECT 1 FROM groups WHERE name = ?", (group_name,)):
                raise ValueError(f"分组 {group_name} 不存在")
            if not image_folder:
                image_folder = ''

            async with conn.execute("""
                INSERT INTO qa_pairs (question, answer, group_name, image_folder)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(question, answer, group_name, image_folder) 
                DO UPDATE SET 
                    weight = weight + 1,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (question, answer, group_name, image_folder)) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    raise Exception("Failed to insert or update QA pair.")
                qa_id = row[0]
                await conn.commit()

        return qa_id

    async def get_qa_weight(self, qa_id: int) -> int:
        """获取指定问答对的权重"""
        async with self.pool.connection() as conn:
            cursor = await conn.execute_fetchall(
                "SELECT weight FROM qa_pairs WHERE id = ?",
                (qa_id,)
            )
            return cursor[0][0] if cursor else 0

    async def delete_qa(self, qa_id: int) -> None:
        """
        删除指定问答对

        Args:
            qa_id: 问答对ID
        """
        async with self.pool.connection() as conn:
            await conn.execute("DELETE FROM qa_pairs WHERE id = ?", (qa_id,))
            await conn.commit()

    async def get_all_qa(self) -> List[Tuple[int, str, str, str, str]]:
        """获取所有问答对"""
        async with self.pool.connection() as conn:
            cursor = await conn.execute_fetchall(
                "SELECT id, question, answer, group_name, image_folder FROM qa_pairs"
            )
            return cursor

    async def get_qa_by_group(self, group_name: str) -> List[Tuple[int, str, str, str]]:
        """获取指定分组的问答对"""
        async with self.pool.connection() as conn:
            cursor = await conn.execute_fetchall(
                "SELECT id, question, answer, image_folder FROM qa_pairs WHERE group_name = ?",
                (group_name,)
            )
            return cursor

    async def get_qa(self, qa_id: int) -> Optional[Tuple[int, str, str, str, str]]:
        """获取指定ID的问答对"""
        async with self.pool.connection() as conn:
            cursor = await conn.execute_fetchall(
                "SELECT id, question, answer, group_name, image_folder FROM qa_pairs WHERE id = ?",
                (qa_id,)
            )
            return cursor[0] if cursor else None

    async def add_group(self, name: str, description: str = "") -> None:
        """
        添加新分组

        如果分组已存在，则忽略本次插入操作。

        Args:
            name: 分组名称
            description: 分组描述
        """
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO groups (name, description) VALUES (?, ?)",
                (name, description)
            )
            await conn.commit()

    async def delete_group(self, name: str) -> None:
        """
        删除分组及其关联问答对

        Args:
            name: 要删除的分组名称
        """
        async with self.pool.connection() as conn:
            await conn.execute("DELETE FROM groups WHERE name = ?", (name,))
            await conn.commit()

    async def get_groups(self) -> List[Tuple[str, str, str]]:
        """获取所有分组信息"""
        async with self.pool.connection() as conn:
            cursor = await conn.execute_fetchall("SELECT name, description FROM groups")
            return cursor

    async def cache_minhash(self, qa_id: int, minhash) -> None:
        """存储预计算的MinHash"""
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO qa_minhashes VALUES (?, ?)",
                (qa_id, json.dumps(minhash.hashvalues.tolist()))
            )
            await conn.commit()

    @lru_cache(maxsize=None)
    async def get_cached_minhash(self, qa_id: int):
        """获取缓存的MinHash"""
        async with self.pool.connection() as conn:
            cursor = await conn.execute_fetchall(
                "SELECT minhash FROM qa_minhashes WHERE qa_id = ?",
                (qa_id,)
            )
            if cursor:
                hash_values = json.loads(cursor[0][0])
                minhash = MinHash(num_perm=_Config.NUM_PERM)
                minhash.hashvalues = hash_values
                return minhash
            return None


class WeightedRandomSelector:
    """带权重的随机选择器"""

    @staticmethod
    def weighted_choice(items: List[Tuple[Any, float]]) -> Any:
        """
        基于权重的随机选择

        Args:
            items: 包含(选项，权重)的列表

        Returns:
            随机选中的选项
        """
        total = sum(weight for _, weight in items)
        rand = random.uniform(0, total)
        cumulative = 0
        for item, weight in items:
            cumulative += weight
            if rand <= cumulative:
                return item
        return items[-1][0]  # 防止浮点误差


class TextProcessor:
    """
    文本处理类，负责文本预处理和MinHash生成

    Attributes:
        num_perm (int): MinHash的排列数，影响精度
    """
    __slots__ = ('num_perm')

    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm

    @staticmethod
    def preprocess(text: str) -> List[str]:
        """
        文本预处理流程（针对中文）：
        1. 转换为小写（对中文影响不大，但保留此步骤以兼容可能存在的英文）
        2. 使用jieba进行分词处理
        3. 过滤停用词

        Args:
            text: 原始文本

        Returns:
            处理后的词项列表
        """
        text = text.lower()
        words = jieba.lcut(text)
        return words

    def create_minhash(self, text: str) -> MinHash:
        """
        生成文本的MinHash签名

        Args:
            text: 输入文本

        Returns:
            MinHash对象
        """
        tokens = self.preprocess(text)
        minhash = MinHash(num_perm=self.num_perm)
        for token in tokens:
            minhash.update(token.encode("utf-8"))
        return minhash


class QAManager:
    """
    问答管理系统，支持权重、随机选择

    Attributes:
        db (DatabaseManager): 数据库管理实例
        text_processor (TextProcessor): 文本处理实例
        lsh (MinHashLSH): 局部敏感哈希索引
        selector (WeightedRandomSelector): 权重选择器
        stats (defaultdict): 统计信息
    """
    __slots__ = ('db_path', 'threshold', 'num_perm',
                 'db', 'text_processor', 'lsh', 'selector')

    def __init__(
        self,
        db_path: str = "qa_database.db",
        threshold: float = 0.7,
        num_perm: int = 128
    ):
        """
        初始化问答系统

        Args:
            db_path: 数据库路径
            threshold: LSH相似度阈值
            num_perm: MinHash排列数
        """
        self.db = DatabaseManager(db_path)
        self.text_processor = TextProcessor(num_perm)
        self.lsh = MinHashLSH(
            threshold=threshold,
            num_perm=num_perm,
        )
        self.selector = WeightedRandomSelector()

    async def initialize(self) -> None:
        """初始化数据库和索引"""
        await self.db.initialize()
        await self._load_index_from_cache()

    async def _load_index_from_cache(self):
        """从数据库预加载MinHash"""
        qa_pairs = await self.db.get_all_qa()

        # 批量处理
        for i in range(0, len(qa_pairs), _Config.BATCH_SIZE):
            batch = qa_pairs[i:i+_Config.BATCH_SIZE]
            tasks = []
            for qa in batch:
                tasks.append(self._process_qa(qa))
            await asyncio.gather(*tasks)

    async def _process_qa(self, qa):
        qa_id, question, _, group, _ = qa
        cached = await self.db.get_cached_minhash(qa_id)
        if cached:
            if not isinstance(cached.hashvalues, np.ndarray):
                cached.hashvalues = np.array(
                    cached.hashvalues, dtype=np.uint64)
            minhash = cached
        else:
            minhash = self.text_processor.create_minhash(
                question)
            await self.db.cache_minhash(qa_id, minhash)
        self.lsh.insert(f"{group}_{qa_id}", minhash)

    async def add_qa(self, question: str, answer: str, group: str, image_folder: Optional[str] = None) -> int:
        """
        添加或更新问答对，自动处理权重

        Returns:
            问答对ID
        """
        qa_id = await self.db.add_or_update_qa(question, answer, group, image_folder)

        # 如果是新增记录才需要插入LSH
        if await self.db.get_qa_weight(qa_id) == 1:
            minhash = self.text_processor.create_minhash(question)
            key = f"{group}_{qa_id}"
            self.lsh.insert(key, minhash)

        return qa_id

    async def add_qa_batch(self, items: List[Tuple[str, str, str, str]]) -> List[int]:
        """批量添加问答对"""
        ids = []
        for question, answer, group, image_folder in items:
            qa_id = await self.add_qa(question, answer, group, image_folder)
            ids.append(qa_id)

        return ids

    async def delete_qa(self, qa_id: int) -> None:
        """删除指定问答对"""
        qa = await self.db.get_qa(qa_id)
        if qa:
            _, _, _, group = qa
            key = f"{group}_{qa_id}"
            self.lsh.remove(key)
        await self.db.delete_qa(qa_id)

    async def search(
        self,
        query: str,
        group: Optional[str] = None,
        top_n: int = 5,
        similarity_weight: float = 0.7,
        count_weight: float = 0.3
    ) -> Optional[Tuple[int, str, str, Optional[str]]]:
        """
        带权重调整的智能搜索

        Args:
            similarity_weight: 相似度权重系数（0-1）
            count_weight: 出现次数权重系数（0-1）

        Returns:
            随机选择的结果 (id, question, answer, image_folder)
        """
        raw_results = await self._basic_search(query, group, top_n*3)

        if not raw_results:
            return None

        scored = []
        for qa_id, question, answer, image_folder, similarity in raw_results:
            weight = await self.db.get_qa_weight(qa_id)
            score = (similarity ** similarity_weight) * \
                (weight ** count_weight)
            scored.append(((qa_id, question, answer, image_folder), score))

        selected = self.selector.weighted_choice(scored)
        return selected

    async def _basic_search(
        self,
        query: str,
        group: Optional[str] = None,
        top_n: int = 5
    ) -> List[Tuple[int, str, str, str, float]]:
        """
        执行相似问题查询

        Args:
            query: 查询文本
            group: 限定搜索的分组（可选）
            top_n: 返回最大结果数

        Returns:
            包含(问答对ID, 问题, 答案, 相似度)的列表
        """
        query_hash = self.text_processor.create_minhash(query)
        namespaces = [group] if group else [g[0] for g in await self.db.get_groups()]

        results = []
        for ns in namespaces:
            candidates = self.lsh.query(query_hash)
            for candidate in candidates:
                if candidate.startswith(ns + "_"):
                    qa_id = int(candidate.split("_")[1])
                    qa = await self.db.get_qa(qa_id)
                    if qa:
                        _, question, answer, _, image_folder = qa
                        q_hash = self.text_processor.create_minhash(question)
                        similarity = query_hash.jaccard(q_hash)
                        results.append(
                            (qa_id, question, answer, image_folder, similarity))

        results.sort(key=lambda x: x[4], reverse=True)
        return results[:top_n]


class _Config:
    NUM_PERM = 256
    BATCH_SIZE = 500


async def demo():
    # 初始化带监控的系统
    system = QAManager()
    await system.initialize()
    await system.db.add_group('IT')
    await system.db.add_group('DB')

    # 批量导入数据
    batch = [
        ("Python安装", "访问官网下载", "IT", '555'),
        ("Java运行", "需要JDK环境", "IT", 'None'),
        ("数据库连接", "使用连接池", "DB", 'None')
    ] * 10
    await system.add_qa_batch(batch)

    # 执行搜索
    result = await system.search("Python安装")
    print(f"搜索结果：ID:{result[0]} 问题:{result[1]} 答案:{
          result[2]} 图片目录:{result[3]}")

if __name__ == "__main__":
    asyncio.run(demo())
