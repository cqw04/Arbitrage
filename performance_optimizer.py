#!/usr/bin/env python3
"""
性能優化模組 - 連接池、數據快取、異步處理優化
提供全面的性能提升解決方案，包括內存管理和並發優化
"""

import asyncio
import aiohttp
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import json
import threading
import weakref
from functools import wraps, lru_cache
import gc
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("PerformanceOptimizer")

@dataclass
class CacheEntry:
    """快取條目"""
    key: str
    value: Any
    timestamp: datetime
    ttl: float  # 生存時間（秒）
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)
    
    def touch(self):
        """更新訪問信息"""
        self.access_count += 1
        self.last_access = datetime.now()

class ConnectionPool:
    """HTTP連接池管理器"""
    
    def __init__(self, max_connections: int = 100, max_connections_per_host: int = 20):
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.connection_stats = defaultdict(int)
        self.lock = asyncio.Lock()
        
        # 連接器配置
        self.connector_config = {
            'limit': max_connections,
            'limit_per_host': max_connections_per_host,
            'ttl_dns_cache': 300,  # DNS快取5分鐘
            'use_dns_cache': True,
            'keepalive_timeout': 60,
            'enable_cleanup_closed': True
        }
        
        logger.info(f"✅ 連接池已初始化: 最大連接數={max_connections}, 每主機={max_connections_per_host}")
    
    async def get_session(self, session_key: str = "default") -> aiohttp.ClientSession:
        """獲取會話"""
        async with self.lock:
            if session_key not in self.sessions:
                connector = aiohttp.TCPConnector(**self.connector_config)
                
                # 設置超時
                timeout = aiohttp.ClientTimeout(
                    total=30,          # 總超時
                    connect=10,        # 連接超時
                    sock_connect=10,   # socket連接超時
                    sock_read=20       # socket讀取超時
                )
                
                self.sessions[session_key] = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'FundingArbitrageBot/2.0',
                        'Accept': 'application/json',
                        'Accept-Encoding': 'gzip, deflate'
                    }
                )
                
                logger.info(f"🔗 創建新會話: {session_key}")
            
            self.connection_stats[session_key] += 1
            return self.sessions[session_key]
    
    async def close_session(self, session_key: str):
        """關閉特定會話"""
        async with self.lock:
            if session_key in self.sessions:
                await self.sessions[session_key].close()
                del self.sessions[session_key]
                logger.info(f"🔒 會話已關閉: {session_key}")
    
    async def close_all(self):
        """關閉所有會話"""
        async with self.lock:
            for session_key, session in self.sessions.items():
                await session.close()
                logger.info(f"🔒 會話已關閉: {session_key}")
            
            self.sessions.clear()
            logger.info("✅ 所有連接池會話已關閉")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取連接統計"""
        return {
            'active_sessions': len(self.sessions),
            'max_connections': self.max_connections,
            'connection_usage': dict(self.connection_stats),
            'total_requests': sum(self.connection_stats.values())
        }

class AdvancedCache:
    """高級快取系統"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.data: Dict[str, CacheEntry] = {}
        self.access_times = deque()  # LRU追蹤
        self.lock = asyncio.Lock()
        
        # 統計信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        logger.info(f"✅ 高級快取已初始化: 最大大小={max_size}, 默認TTL={default_ttl}秒")
    
    async def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        async with self.lock:
            self.stats['total_requests'] += 1
            
            if key not in self.data:
                self.stats['misses'] += 1
                return None
            
            entry = self.data[key]
            
            # 檢查過期
            if entry.is_expired():
                del self.data[key]
                self.stats['misses'] += 1
                return None
            
            # 更新訪問信息
            entry.touch()
            self.access_times.append((time.time(), key))
            self.stats['hits'] += 1
            
            logger.debug(f"快取命中: {key}")
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """設置快取值"""
        async with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=datetime.now(),
                ttl=ttl
            )
            
            # 檢查容量限制
            if len(self.data) >= self.max_size:
                await self._evict_lru()
            
            self.data[key] = entry
            self.access_times.append((time.time(), key))
            
            logger.debug(f"快取設置: {key}, TTL={ttl}秒")
    
    async def delete(self, key: str) -> bool:
        """刪除快取值"""
        async with self.lock:
            if key in self.data:
                del self.data[key]
                logger.debug(f"快取刪除: {key}")
                return True
            return False
    
    async def clear(self):
        """清空快取"""
        async with self.lock:
            self.data.clear()
            self.access_times.clear()
            logger.info("🗑️ 快取已清空")
    
    async def _evict_lru(self):
        """驅逐最少使用的條目"""
        if not self.data:
            return
        
        # 找到最少使用的key
        oldest_key = None
        oldest_time = float('inf')
        
        for key, entry in self.data.items():
            if entry.last_access.timestamp() < oldest_time:
                oldest_time = entry.last_access.timestamp()
                oldest_key = key
        
        if oldest_key:
            del self.data[oldest_key]
            self.stats['evictions'] += 1
            logger.debug(f"LRU驅逐: {oldest_key}")
    
    async def cleanup_expired(self):
        """清理過期條目"""
        async with self.lock:
            expired_keys = [
                key for key, entry in self.data.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.data[key]
            
            if expired_keys:
                logger.info(f"🧹 清理過期快取: {len(expired_keys)} 個條目")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計"""
        hit_rate = (self.stats['hits'] / max(1, self.stats['total_requests'])) * 100
        
        return {
            'size': len(self.data),
            'max_size': self.max_size,
            'hit_rate': hit_rate,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'total_requests': self.stats['total_requests']
        }

class AsyncTaskManager:
    """異步任務管理器"""
    
    def __init__(self, max_concurrent_tasks: int = 50):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_stats = defaultdict(int)
        self.lock = asyncio.Lock()
        
        logger.info(f"✅ 異步任務管理器已初始化: 最大併發={max_concurrent_tasks}")
    
    async def submit_task(self, task_id: str, coro, priority: int = 0) -> asyncio.Task:
        """提交異步任務"""
        async with self.semaphore:
            async with self.lock:
                # 如果任務已存在且未完成，先取消
                if task_id in self.active_tasks and not self.active_tasks[task_id].done():
                    self.active_tasks[task_id].cancel()
                
                # 創建新任務
                task = asyncio.create_task(coro)
                self.active_tasks[task_id] = task
                self.task_stats['submitted'] += 1
                
                logger.debug(f"📋 提交任務: {task_id}")
                
                # 設置完成回調
                task.add_done_callback(lambda t: self._task_done_callback(task_id, t))
                
                return task
    
    def _task_done_callback(self, task_id: str, task: asyncio.Task):
        """任務完成回調"""
        try:
            if task.cancelled():
                self.task_stats['cancelled'] += 1
                logger.debug(f"❌ 任務已取消: {task_id}")
            elif task.exception():
                self.task_stats['failed'] += 1
                logger.warning(f"⚠️ 任務失敗: {task_id}, 錯誤: {task.exception()}")
            else:
                self.task_stats['completed'] += 1
                logger.debug(f"✅ 任務完成: {task_id}")
        finally:
            # 清理完成的任務
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        async with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if not task.done():
                    task.cancel()
                    logger.info(f"🚫 任務已取消: {task_id}")
                    return True
            return False
    
    async def cancel_all_tasks(self):
        """取消所有任務"""
        async with self.lock:
            for task_id, task in self.active_tasks.items():
                if not task.done():
                    task.cancel()
            
            logger.info(f"🚫 已取消所有任務: {len(self.active_tasks)} 個")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取任務統計"""
        return {
            'active_tasks': len(self.active_tasks),
            'max_concurrent': self.max_concurrent_tasks,
            'submitted': self.task_stats['submitted'],
            'completed': self.task_stats['completed'],
            'failed': self.task_stats['failed'],
            'cancelled': self.task_stats['cancelled']
        }

class MemoryManager:
    """內存管理器"""
    
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.gc_stats = {
            'manual_collections': 0,
            'objects_collected': 0,
            'last_collection': None
        }
        
        logger.info(f"✅ 內存管理器已初始化: 最大內存={max_memory_mb}MB")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """獲取內存使用情況"""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': memory_percent,
            'max_memory_mb': self.max_memory_mb,
            'available_system_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def should_collect_garbage(self) -> bool:
        """檢查是否需要垃圾回收"""
        memory_info = self.get_memory_usage()
        
        # 如果內存使用超過80%，觸發垃圾回收
        if memory_info['rss_mb'] > self.max_memory_mb * 0.8:
            return True
        
        # 如果系統可用內存低於1GB，觸發垃圾回收
        if memory_info['available_system_mb'] < 1024:
            return True
        
        return False
    
    def collect_garbage(self) -> Dict[str, Any]:
        """執行垃圾回收"""
        logger.info("🗑️ 執行垃圾回收...")
        
        before_memory = self.get_memory_usage()
        
        # 執行垃圾回收
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        after_memory = self.get_memory_usage()
        freed_mb = before_memory['rss_mb'] - after_memory['rss_mb']
        
        # 更新統計
        self.gc_stats['manual_collections'] += 1
        self.gc_stats['objects_collected'] += collected
        self.gc_stats['last_collection'] = datetime.now()
        
        result = {
            'objects_collected': collected,
            'memory_freed_mb': freed_mb,
            'before_memory_mb': before_memory['rss_mb'],
            'after_memory_mb': after_memory['rss_mb']
        }
        
        logger.info(f"✅ 垃圾回收完成: 回收對象={collected}, 釋放內存={freed_mb:.2f}MB")
        return result
    
    def get_gc_stats(self) -> Dict[str, Any]:
        """獲取垃圾回收統計"""
        return {
            'manual_collections': self.gc_stats['manual_collections'],
            'objects_collected': self.gc_stats['objects_collected'],
            'last_collection': self.gc_stats['last_collection'].isoformat() if self.gc_stats['last_collection'] else None,
            'gc_counts': gc.get_count(),
            'gc_thresholds': gc.get_threshold()
        }

class PerformanceMonitor:
    """性能監控器"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = time.time()
        self.lock = threading.Lock()
        
        logger.info("✅ 性能監控器已初始化")
    
    def record_metric(self, name: str, value: float, timestamp: Optional[float] = None):
        """記錄性能指標"""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.metrics[name].append((timestamp, value))
            
            # 保持最近1000個數據點
            if len(self.metrics[name]) > 1000:
                self.metrics[name] = self.metrics[name][-1000:]
    
    def get_metric_stats(self, name: str, duration_seconds: int = 3600) -> Dict[str, Any]:
        """獲取指標統計"""
        cutoff_time = time.time() - duration_seconds
        
        with self.lock:
            if name not in self.metrics:
                return {}
            
            # 過濾時間範圍內的數據
            recent_data = [
                (ts, value) for ts, value in self.metrics[name]
                if ts >= cutoff_time
            ]
            
            if not recent_data:
                return {}
            
            values = [value for _, value in recent_data]
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1],
                'duration_seconds': duration_seconds
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """獲取系統性能指標"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 網絡I/O
        net_io = psutil.net_io_counters()
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': memory.available / 1024 / 1024,
            'disk_percent': (disk.used / disk.total) * 100,
            'disk_free_gb': disk.free / 1024 / 1024 / 1024,
            'net_bytes_sent': net_io.bytes_sent,
            'net_bytes_recv': net_io.bytes_recv,
            'uptime_seconds': time.time() - self.start_time
        }

class PerformanceOptimizer:
    """性能優化器主類"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 初始化組件
        self.connection_pool = ConnectionPool(
            max_connections=self.config.get('max_connections', 100),
            max_connections_per_host=self.config.get('max_connections_per_host', 20)
        )
        
        self.cache = AdvancedCache(
            max_size=self.config.get('cache_max_size', 1000),
            default_ttl=self.config.get('cache_default_ttl', 300)
        )
        
        self.task_manager = AsyncTaskManager(
            max_concurrent_tasks=self.config.get('max_concurrent_tasks', 50)
        )
        
        self.memory_manager = MemoryManager(
            max_memory_mb=self.config.get('max_memory_mb', 512)
        )
        
        self.monitor = PerformanceMonitor()
        
        # 自動優化任務
        self.auto_optimize_enabled = self.config.get('auto_optimize', True)
        self.optimization_task = None
        
        logger.info("🚀 性能優化器已初始化")
    
    async def start_optimization(self):
        """開始自動優化"""
        if self.auto_optimize_enabled:
            self.optimization_task = asyncio.create_task(self._optimization_loop())
            logger.info("🔄 自動優化已啟動")
    
    async def stop_optimization(self):
        """停止自動優化"""
        if self.optimization_task:
            self.optimization_task.cancel()
            logger.info("⏹️ 自動優化已停止")
        
        await self.connection_pool.close_all()
        await self.task_manager.cancel_all_tasks()
    
    async def _optimization_loop(self):
        """優化循環"""
        while True:
            try:
                # 記錄系統指標
                system_metrics = self.monitor.get_system_metrics()
                self.monitor.record_metric('cpu_percent', system_metrics['cpu_percent'])
                self.monitor.record_metric('memory_percent', system_metrics['memory_percent'])
                
                # 清理過期快取
                await self.cache.cleanup_expired()
                
                # 檢查內存使用
                if self.memory_manager.should_collect_garbage():
                    self.memory_manager.collect_garbage()
                
                # 等待下次檢查
                await asyncio.sleep(60)  # 每分鐘檢查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"優化循環錯誤: {e}")
                await asyncio.sleep(60)
    
    async def cached_request(self, session_key: str, url: str, cache_key: Optional[str] = None,
                           ttl: Optional[float] = None, **kwargs) -> Any:
        """帶快取的HTTP請求"""
        if cache_key is None:
            cache_key = f"{session_key}:{url}"
        
        # 嘗試從快取獲取
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # 發送請求
        session = await self.connection_pool.get_session(session_key)
        
        start_time = time.time()
        try:
            async with session.get(url, **kwargs) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 存入快取
                    await self.cache.set(cache_key, data, ttl)
                    
                    # 記錄性能指標
                    request_time = time.time() - start_time
                    self.monitor.record_metric('request_time', request_time)
                    
                    return data
                else:
                    logger.warning(f"HTTP請求失敗: {response.status} {url}")
                    return None
        
        except Exception as e:
            logger.error(f"請求錯誤: {e}")
            return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """獲取性能摘要"""
        return {
            'connection_pool': self.connection_pool.get_stats(),
            'cache': self.cache.get_stats(),
            'task_manager': self.task_manager.get_stats(),
            'memory': self.memory_manager.get_memory_usage(),
            'gc_stats': self.memory_manager.get_gc_stats(),
            'system': self.monitor.get_system_metrics(),
            'request_time_stats': self.monitor.get_metric_stats('request_time'),
            'auto_optimize_enabled': self.auto_optimize_enabled
        }

# 裝飾器和工具函數
def async_cached(ttl: float = 300, key_func: Optional[Callable] = None):
    """異步快取裝飾器"""
    def decorator(func):
        cache_data = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成快取鍵
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 檢查快取
            if cache_key in cache_data:
                entry_time, result = cache_data[cache_key]
                if time.time() - entry_time < ttl:
                    return result
            
            # 執行函數
            result = await func(*args, **kwargs)
            
            # 存入快取
            cache_data[cache_key] = (time.time(), result)
            
            # 清理過期條目
            current_time = time.time()
            expired_keys = [
                key for key, (entry_time, _) in cache_data.items()
                if current_time - entry_time > ttl
            ]
            for key in expired_keys:
                del cache_data[key]
            
            return result
        
        return wrapper
    return decorator

def monitor_performance(metric_name: str, monitor: Optional[PerformanceMonitor] = None):
    """性能監控裝飾器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if monitor:
                    monitor.record_metric(metric_name, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if monitor:
                    monitor.record_metric(metric_name, duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def create_performance_optimizer(config_file: str = None) -> PerformanceOptimizer:
    """創建性能優化器實例"""
    
    # 默認配置
    default_config = {
        'max_connections': 100,
        'max_connections_per_host': 20,
        'cache_max_size': 1000,
        'cache_default_ttl': 300,
        'max_concurrent_tasks': 50,
        'max_memory_mb': 512,
        'auto_optimize': True
    }
    
    # 加載配置文件
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                default_config.update(file_config)
        except Exception as e:
            logger.warning(f"配置文件加載失敗，使用默認配置: {e}")
    
    return PerformanceOptimizer(default_config)

# 測試函數
async def test_performance_optimizer():
    """測試性能優化器"""
    
    print("🧪 測試性能優化器")
    
    # 創建優化器
    optimizer = create_performance_optimizer()
    
    # 啟動優化
    await optimizer.start_optimization()
    
    # 測試快取請求
    for i in range(5):
        result = await optimizer.cached_request(
            session_key="test",
            url="https://httpbin.org/delay/1",
            cache_key=f"test_request_{i}",
            ttl=60
        )
        print(f"請求 {i}: {'成功' if result else '失敗'}")
    
    # 顯示性能摘要
    summary = optimizer.get_performance_summary()
    print(f"性能摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")
    
    # 停止優化
    await optimizer.stop_optimization()

if __name__ == "__main__":
    asyncio.run(test_performance_optimizer()) 