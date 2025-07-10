#!/usr/bin/env python3
"""
混合架構資金費率套利系統
Python 策略層 + Rust 執行層
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import websockets

logger = logging.getLogger("HybridArbitrage")

@dataclass
class ArbitrageStrategy:
    """套利策略數據類"""
    strategy_id: str
    symbol: str
    primary_exchange: str
    secondary_exchange: str
    funding_rate_diff: float
    estimated_profit: float
    execution_type: str  # "python" 或 "rust"
    priority: int  # 1-10，10為最高優先級
    created_at: datetime

class PythonStrategyEngine:
    """Python 策略引擎 - 負責策略分析和風險管理"""
    
    def __init__(self):
        self.funding_monitor = None
        self.risk_manager = None
        self.strategy_history = []
        
    async def analyze_funding_opportunities(self, funding_data: Dict) -> List[ArbitrageStrategy]:
        """分析資金費率套利機會"""
        opportunities = []
        
        for symbol in funding_data:
            exchanges = funding_data[symbol]
            if len(exchanges) < 2:
                continue
                
            # 找出最高和最低資金費率
            rates = [(ex, data['funding_rate']) for ex, data in exchanges.items()]
            rates.sort(key=lambda x: x[1])
            
            min_rate = rates[0]
            max_rate = rates[-1]
            
            rate_diff = max_rate[1] - min_rate[1]
            
            if rate_diff > 0.001:  # 0.1% 以上差異
                strategy = ArbitrageStrategy(
                    strategy_id=f"funding_{symbol}_{datetime.now().timestamp()}",
                    symbol=symbol,
                    primary_exchange=max_rate[0],  # 高費率交易所
                    secondary_exchange=min_rate[0],  # 低費率交易所
                    funding_rate_diff=rate_diff,
                    estimated_profit=rate_diff * 10000,  # 假設10,000 USDT
                    execution_type="rust" if rate_diff > 0.005 else "python",  # 大機會用Rust
                    priority=min(10, int(rate_diff * 1000)),  # 根據差異設定優先級
                    created_at=datetime.now()
                )
                opportunities.append(strategy)
        
        return opportunities
    
    async def validate_strategy(self, strategy: ArbitrageStrategy) -> bool:
        """驗證策略可行性"""
        # 檢查風險限制
        if strategy.estimated_profit < 10:  # 最小利潤10 USDT
            return False
            
        # 檢查歷史成功率
        similar_strategies = [s for s in self.strategy_history 
                            if s.symbol == strategy.symbol and 
                            s.funding_rate_diff > strategy.funding_rate_diff * 0.8]
        
        if similar_strategies:
            success_rate = sum(1 for s in similar_strategies if s.estimated_profit > 0) / len(similar_strategies)
            if success_rate < 0.6:  # 成功率低於60%
                return False
        
        return True

class RustExecutionBridge:
    """Rust 執行橋接器 - 與 Rust MEV 引擎通信"""
    
    def __init__(self, rust_endpoint: str = "ws://localhost:8080"):
        self.rust_endpoint = rust_endpoint
        self.websocket = None
        self.connected = False
        
    async def connect(self):
        """連接到 Rust 執行引擎"""
        try:
            self.websocket = await websockets.connect(self.rust_endpoint)
            self.connected = True
            logger.info("✅ 已連接到 Rust 執行引擎")
        except Exception as e:
            logger.error(f"❌ 連接 Rust 引擎失敗: {e}")
            self.connected = False
    
    async def execute_high_frequency_arbitrage(self, strategy: ArbitrageStrategy) -> Dict:
        """執行高頻套利（通過 Rust 引擎）"""
        if not self.connected:
            await self.connect()
        
        if not self.connected:
            return {"status": "error", "message": "Rust 引擎未連接"}
        
        # 準備執行數據
        execution_data = {
            "type": "funding_rate_arbitrage",
            "strategy_id": strategy.strategy_id,
            "symbol": strategy.symbol,
            "primary_exchange": strategy.primary_exchange,
            "secondary_exchange": strategy.secondary_exchange,
            "amount": 10000,  # 執行金額
            "priority": strategy.priority,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 發送到 Rust 引擎
            await self.websocket.send(json.dumps(execution_data))
            
            # 等待執行結果
            response = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
            result = json.loads(response)
            
            logger.info(f"🚀 Rust 引擎執行結果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Rust 執行失敗: {e}")
            return {"status": "error", "message": str(e)}

class HybridArbitrageSystem:
    """混合架構套利系統"""
    
    def __init__(self):
        self.strategy_engine = PythonStrategyEngine()
        self.rust_bridge = RustExecutionBridge()
        self.running = False
        self.execution_stats = {
            "python_executions": 0,
            "rust_executions": 0,
            "total_profit": 0.0,
            "success_rate": 0.0
        }
        
    async def start(self):
        """啟動混合套利系統"""
        self.running = True
        logger.info("🚀 啟動混合架構套利系統")
        
        # 連接 Rust 引擎
        await self.rust_bridge.connect()
        
        # 啟動策略監控
        await self.monitor_and_execute()
    
    async def monitor_and_execute(self):
        """監控並執行套利策略"""
        while self.running:
            try:
                # 獲取資金費率數據
                funding_data = await self.get_funding_rates()
                
                # 分析套利機會
                opportunities = await self.strategy_engine.analyze_funding_opportunities(funding_data)
                
                # 執行策略
                for opportunity in opportunities:
                    if await self.strategy_engine.validate_strategy(opportunity):
                        await self.execute_strategy(opportunity)
                
                await asyncio.sleep(30)  # 30秒檢查一次
                
            except Exception as e:
                logger.error(f"監控執行錯誤: {e}")
                await asyncio.sleep(60)
    
    async def execute_strategy(self, strategy: ArbitrageStrategy):
        """執行套利策略"""
        logger.info(f"📊 執行策略: {strategy.symbol} "
                   f"差異: {strategy.funding_rate_diff:.4f} "
                   f"引擎: {strategy.execution_type}")
        
        if strategy.execution_type == "rust":
            # 使用 Rust 引擎執行高頻套利
            result = await self.rust_bridge.execute_high_frequency_arbitrage(strategy)
            self.execution_stats["rust_executions"] += 1
            
        else:
            # 使用 Python 引擎執行標準套利
            result = await self.execute_python_arbitrage(strategy)
            self.execution_stats["python_executions"] += 1
        
        # 更新統計
        if result.get("status") == "success":
            profit = result.get("profit", 0)
            self.execution_stats["total_profit"] += profit
            logger.info(f"✅ 策略執行成功，利潤: {profit:.2f} USDT")
        
        # 計算成功率
        total_executions = (self.execution_stats["python_executions"] + 
                           self.execution_stats["rust_executions"])
        if total_executions > 0:
            self.execution_stats["success_rate"] = (
                sum(1 for r in [result] if r.get("status") == "success") / total_executions
            )
    
    async def execute_python_arbitrage(self, strategy: ArbitrageStrategy) -> Dict:
        """Python 引擎執行套利"""
        # 這裡調用您現有的套利執行邏輯
        logger.info(f"🐍 Python 引擎執行: {strategy.symbol}")
        
        # 模擬執行結果
        return {
            "status": "success",
            "profit": strategy.estimated_profit * 0.8,  # 假設80%成功率
            "execution_time": datetime.now().isoformat()
        }
    
    async def get_funding_rates(self) -> Dict:
        """獲取資金費率數據"""
        # 這裡調用您現有的資金費率獲取邏輯
        # 返回格式: {symbol: {exchange: {funding_rate: float, ...}}}
        return {
            "BTC/USDT": {
                "binance": {"funding_rate": 0.0001},
                "bybit": {"funding_rate": 0.0002},
                "okx": {"funding_rate": 0.0003}
            },
            "ETH/USDT": {
                "binance": {"funding_rate": 0.0002},
                "bybit": {"funding_rate": 0.0001},
                "okx": {"funding_rate": 0.0004}
            }
        }
    
    def get_performance_stats(self) -> Dict:
        """獲取性能統計"""
        return {
            **self.execution_stats,
            "python_rust_ratio": (
                self.execution_stats["python_executions"] / 
                max(self.execution_stats["rust_executions"], 1)
            ),
            "avg_profit_per_execution": (
                self.execution_stats["total_profit"] / 
                max(self.execution_stats["python_executions"] + 
                    self.execution_stats["rust_executions"], 1)
            )
        }

# 使用示例
async def main():
    """主函數"""
    system = HybridArbitrageSystem()
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("🛑 系統停止")
        system.running = False
        
        # 顯示最終統計
        stats = system.get_performance_stats()
        logger.info(f"📈 最終統計: {stats}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 