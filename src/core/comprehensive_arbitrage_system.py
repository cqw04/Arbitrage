#!/usr/bin/env python3
"""
綜合套利系統 - 多策略、多交易所、多資產
支持現貨套利、資金費率套利、期現套利、三角套利等
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from abc import ABC, abstractmethod

# 導入現有模組
from funding_rate_arbitrage_system import FundingRateMonitor, ExchangeConnector
from hybrid_arbitrage_architecture import HybridArbitrageSystem

logger = logging.getLogger("ComprehensiveArbitrage")

class ArbitrageType(Enum):
    """套利類型枚舉"""
    SPOT_ARBITRAGE = "spot_arbitrage"           # 現貨套利
    FUNDING_RATE_ARBITRAGE = "funding_rate"     # 資金費率套利
    FUTURES_SPOT_ARBITRAGE = "futures_spot"     # 期現套利
    TRIANGULAR_ARBITRAGE = "triangular"         # 三角套利
    STATISTICAL_ARBITRAGE = "statistical"       # 統計套利
    PAIRS_TRADING = "pairs_trading"             # 配對交易
    MEAN_REVERSION = "mean_reversion"           # 均值回歸
    MOMENTUM_ARBITRAGE = "momentum"             # 動量套利

class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class ArbitrageOpportunity:
    """套利機會數據類"""
    opportunity_id: str
    arbitrage_type: ArbitrageType
    symbol: str
    exchanges: List[str]
    estimated_profit: float
    risk_level: RiskLevel
    confidence_score: float
    execution_time: datetime
    expiry_time: datetime
    requirements: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class SpotArbitrageData:
    """現貨套利數據"""
    symbol: str
    exchange_a: str
    exchange_b: str
    price_a: float
    price_b: float
    spread: float
    volume_a: float
    volume_b: float
    timestamp: datetime

@dataclass
class TriangularArbitrageData:
    """三角套利數據"""
    base_currency: str
    intermediate_currency: str
    target_currency: str
    path: List[str]
    rates: List[float]
    final_rate: float
    profit_potential: float
    timestamp: datetime

class SpotArbitrageDetector:
    """現貨套利檢測器"""
    
    def __init__(self, exchanges: List[str]):
        self.exchanges = exchanges
        self.price_cache = {}
        self.min_spread_threshold = 0.002  # 0.2% 最小價差
        
    async def detect_spot_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """檢測現貨套利機會"""
        opportunities = []
        
        for symbol in symbols:
            prices = await self.get_symbol_prices(symbol)
            
            if len(prices) < 2:
                continue
                
            # 找出最高和最低價格
            sorted_prices = sorted(prices.items(), key=lambda x: x[1]['price'])
            min_price = sorted_prices[0]
            max_price = sorted_prices[-1]
            
            spread = (max_price[1]['price'] - min_price[1]['price']) / min_price[1]['price']
            
            if spread > self.min_spread_threshold:
                opportunity = ArbitrageOpportunity(
                    opportunity_id=str(uuid.uuid4()),
                    arbitrage_type=ArbitrageType.SPOT_ARBITRAGE,
                    symbol=symbol,
                    exchanges=[min_price[0], max_price[0]],
                    estimated_profit=spread * 10000,  # 假設10,000 USDT
                    risk_level=self.assess_spot_risk(spread, min_price[1], max_price[1]),
                    confidence_score=min(0.95, spread * 100),
                    execution_time=datetime.now(),
                    expiry_time=datetime.now() + timedelta(minutes=5),
                    requirements={
                        "buy_exchange": min_price[0],
                        "sell_exchange": max_price[0],
                        "buy_price": min_price[1]['price'],
                        "sell_price": max_price[1]['price'],
                        "min_volume": min(min_price[1]['volume'], max_price[1]['volume'])
                    },
                    metadata={
                        "spread": spread,
                        "volume_available": min(min_price[1]['volume'], max_price[1]['volume'])
                    }
                )
                opportunities.append(opportunity)
        
        return opportunities
    
    async def get_symbol_prices(self, symbol: str) -> Dict[str, Dict]:
        """獲取多個交易所的價格"""
        prices = {}
        
        # 這裡應該調用實際的交易所API
        # 現在使用模擬數據
        for exchange in self.exchanges:
            base_price = 50000 if "BTC" in symbol else 3000 if "ETH" in symbol else 100
            prices[exchange] = {
                "price": base_price * (1 + (hash(exchange) % 100 - 50) / 10000),
                "volume": 1000 + (hash(exchange) % 500),
                "timestamp": datetime.now()
            }
        
        return prices
    
    def assess_spot_risk(self, spread: float, buy_data: Dict, sell_data: Dict) -> RiskLevel:
        """評估現貨套利風險"""
        if spread > 0.01:  # 1%以上
            return RiskLevel.HIGH
        elif spread > 0.005:  # 0.5%以上
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

class TriangularArbitrageDetector:
    """三角套利檢測器"""
    
    def __init__(self):
        self.triangular_paths = [
            ["BTC", "USDT", "ETH"],
            ["ETH", "USDT", "SOL"],
            ["BTC", "ETH", "USDT"],
            ["SOL", "USDT", "ADA"],
        ]
        
    async def detect_triangular_opportunities(self) -> List[ArbitrageOpportunity]:
        """檢測三角套利機會"""
        opportunities = []
        
        for path in self.triangular_paths:
            rates = await self.get_triangular_rates(path)
            
            if len(rates) == 3:
                # 計算三角套利機會
                # 路徑: A -> B -> C -> A
                rate_1 = rates[0]  # A/B
                rate_2 = rates[1]  # B/C
                rate_3 = rates[2]  # C/A
                
                final_rate = rate_1 * rate_2 * rate_3
                profit_potential = (final_rate - 1) * 100
                
                if profit_potential > 0.1:  # 0.1%以上利潤
                    opportunity = ArbitrageOpportunity(
                        opportunity_id=str(uuid.uuid4()),
                        arbitrage_type=ArbitrageType.TRIANGULAR_ARBITRAGE,
                        symbol=f"{path[0]}/{path[1]}/{path[2]}",
                        exchanges=["binance", "bybit", "okx"],
                        estimated_profit=profit_potential * 100,  # 假設100 USDT
                        risk_level=RiskLevel.HIGH,
                        confidence_score=min(0.8, profit_potential / 10),
                        execution_time=datetime.now(),
                        expiry_time=datetime.now() + timedelta(minutes=2),
                        requirements={
                            "path": path,
                            "rates": rates,
                            "final_rate": final_rate
                        },
                        metadata={
                            "profit_potential": profit_potential,
                            "execution_complexity": "high"
                        }
                    )
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def get_triangular_rates(self, path: List[str]) -> List[float]:
        """獲取三角套利路徑的匯率"""
        # 模擬獲取匯率
        rates = []
        for i in range(len(path) - 1):
            base_rate = 1.0
            if path[i] == "BTC" and path[i+1] == "USDT":
                base_rate = 50000
            elif path[i] == "ETH" and path[i+1] == "USDT":
                base_rate = 3000
            elif path[i] == "SOL" and path[i+1] == "USDT":
                base_rate = 100
            elif path[i] == "BTC" and path[i+1] == "ETH":
                base_rate = 16.67
            elif path[i] == "ETH" and path[i+1] == "SOL":
                base_rate = 30
            
            # 添加隨機波動
            rate = base_rate * (1 + (hash(f"{path[i]}{path[i+1]}") % 100 - 50) / 10000)
            rates.append(rate)
        
        return rates

class FuturesSpotArbitrageDetector:
    """期現套利檢測器"""
    
    def __init__(self):
        self.funding_monitor = FundingRateMonitor()
        
    async def detect_futures_spot_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """檢測期現套利機會"""
        opportunities = []
        
        for symbol in symbols:
            # 獲取期貨價格和現貨價格
            futures_price = await self.get_futures_price(symbol)
            spot_price = await self.get_spot_price(symbol)
            funding_rate = await self.get_funding_rate(symbol)
            
            if futures_price and spot_price:
                basis = (futures_price - spot_price) / spot_price
                
                # 計算理論基差
                theoretical_basis = funding_rate * 3  # 假設3個資金費率週期
                
                # 如果實際基差偏離理論基差，存在套利機會
                basis_misalignment = abs(basis - theoretical_basis)
                
                if basis_misalignment > 0.001:  # 0.1%以上偏離
                    opportunity = ArbitrageOpportunity(
                        opportunity_id=str(uuid.uuid4()),
                        arbitrage_type=ArbitrageType.FUTURES_SPOT_ARBITRAGE,
                        symbol=symbol,
                        exchanges=["binance", "bybit"],
                        estimated_profit=basis_misalignment * 10000,
                        risk_level=RiskLevel.MEDIUM,
                        confidence_score=min(0.9, basis_misalignment * 1000),
                        execution_time=datetime.now(),
                        expiry_time=datetime.now() + timedelta(hours=8),
                        requirements={
                            "futures_price": futures_price,
                            "spot_price": spot_price,
                            "funding_rate": funding_rate,
                            "basis": basis,
                            "theoretical_basis": theoretical_basis
                        },
                        metadata={
                            "basis_misalignment": basis_misalignment,
                            "direction": "long_futures_short_spot" if basis > theoretical_basis else "short_futures_long_spot"
                        }
                    )
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def get_futures_price(self, symbol: str) -> Optional[float]:
        """獲取期貨價格"""
        # 模擬期貨價格
        base_price = 50000 if "BTC" in symbol else 3000 if "ETH" in symbol else 100
        return base_price * (1 + 0.0001)  # 略高於現貨
    
    async def get_spot_price(self, symbol: str) -> Optional[float]:
        """獲取現貨價格"""
        # 模擬現貨價格
        base_price = 50000 if "BTC" in symbol else 3000 if "ETH" in symbol else 100
        return base_price
    
    async def get_funding_rate(self, symbol: str) -> float:
        """獲取資金費率"""
        # 模擬資金費率
        return 0.0001 + (hash(symbol) % 100 - 50) / 1000000

class StatisticalArbitrageDetector:
    """統計套利檢測器"""
    
    def __init__(self):
        self.price_history = {}
        self.correlation_threshold = 0.8
        self.mean_reversion_threshold = 2.0  # 標準差倍數
        
    async def detect_statistical_opportunities(self, symbol_pairs: List[Tuple[str, str]]) -> List[ArbitrageOpportunity]:
        """檢測統計套利機會"""
        opportunities = []
        
        for pair in symbol_pairs:
            symbol_a, symbol_b = pair
            
            # 獲取歷史價格數據
            prices_a = await self.get_price_history(symbol_a)
            prices_b = await self.get_price_history(symbol_b)
            
            if len(prices_a) > 100 and len(prices_b) > 100:
                # 計算相關性
                correlation = self.calculate_correlation(prices_a, prices_b)
                
                if correlation > self.correlation_threshold:
                    # 計算價差統計
                    spread_series = self.calculate_spread_series(prices_a, prices_b)
                    mean_spread = sum(spread_series) / len(spread_series)
                    std_spread = self.calculate_std(spread_series)
                    
                    current_spread = spread_series[-1]
                    z_score = abs(current_spread - mean_spread) / std_spread
                    
                    if z_score > self.mean_reversion_threshold:
                        opportunity = ArbitrageOpportunity(
                            opportunity_id=str(uuid.uuid4()),
                            arbitrage_type=ArbitrageType.STATISTICAL_ARBITRAGE,
                            symbol=f"{symbol_a}/{symbol_b}",
                            exchanges=["binance", "bybit"],
                            estimated_profit=z_score * 10,  # 基於Z-score的利潤估計
                            risk_level=RiskLevel.MEDIUM,
                            confidence_score=min(0.85, correlation),
                            execution_time=datetime.now(),
                            expiry_time=datetime.now() + timedelta(hours=24),
                            requirements={
                                "symbol_a": symbol_a,
                                "symbol_b": symbol_b,
                                "correlation": correlation,
                                "z_score": z_score,
                                "mean_spread": mean_spread,
                                "std_spread": std_spread
                            },
                            metadata={
                                "strategy": "mean_reversion",
                                "position_size": "dynamic"
                            }
                        )
                        opportunities.append(opportunity)
        
        return opportunities
    
    async def get_price_history(self, symbol: str) -> List[float]:
        """獲取歷史價格數據"""
        # 模擬歷史價格數據
        base_price = 50000 if "BTC" in symbol else 3000 if "ETH" in symbol else 100
        prices = []
        
        for i in range(200):
            # 模擬價格走勢
            price = base_price * (1 + 0.1 * (i % 100 - 50) / 100)
            prices.append(price)
        
        return prices
    
    def calculate_correlation(self, prices_a: List[float], prices_b: List[float]) -> float:
        """計算相關性"""
        if len(prices_a) != len(prices_b):
            return 0.0
        
        # 簡化的相關性計算
        mean_a = sum(prices_a) / len(prices_a)
        mean_b = sum(prices_b) / len(prices_b)
        
        numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(prices_a, prices_b))
        denominator_a = sum((a - mean_a) ** 2 for a in prices_a)
        denominator_b = sum((b - mean_b) ** 2 for b in prices_b)
        
        if denominator_a == 0 or denominator_b == 0:
            return 0.0
        
        return numerator / (denominator_a * denominator_b) ** 0.5
    
    def calculate_spread_series(self, prices_a: List[float], prices_b: List[float]) -> List[float]:
        """計算價差序列"""
        return [a / b for a, b in zip(prices_a, prices_b)]
    
    def calculate_std(self, values: List[float]) -> float:
        """計算標準差"""
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

class ComprehensiveArbitrageSystem:
    """綜合套利系統"""
    
    def __init__(self):
        self.spot_detector = SpotArbitrageDetector(["binance", "bybit", "okx", "backpack"])
        self.triangular_detector = TriangularArbitrageDetector()
        self.futures_spot_detector = FuturesSpotArbitrageDetector()
        self.statistical_detector = StatisticalArbitrageDetector()
        self.funding_monitor = FundingRateMonitor()
        
        self.hybrid_system = HybridArbitrageSystem()
        
        self.opportunities = []
        self.execution_history = []
        self.performance_stats = {
            "total_opportunities": 0,
            "executed_opportunities": 0,
            "total_profit": 0.0,
            "success_rate": 0.0,
            "by_type": {}
        }
        
        self.running = False
        
    async def start(self):
        """啟動綜合套利系統"""
        self.running = True
        logger.info("🚀 啟動綜合套利系統")
        
        # 啟動所有檢測器
        await asyncio.gather(
            self.monitor_spot_arbitrage(),
            self.monitor_triangular_arbitrage(),
            self.monitor_futures_spot_arbitrage(),
            self.monitor_statistical_arbitrage(),
            self.monitor_funding_rate_arbitrage(),
            self.execute_opportunities()
        )
    
    async def monitor_spot_arbitrage(self):
        """監控現貨套利機會"""
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
        
        while self.running:
            try:
                opportunities = await self.spot_detector.detect_spot_opportunities(symbols)
                
                for opportunity in opportunities:
                    await self.add_opportunity(opportunity)
                
                await asyncio.sleep(30)  # 30秒檢查一次
                
            except Exception as e:
                logger.error(f"現貨套利監控錯誤: {e}")
                await asyncio.sleep(60)
    
    async def monitor_triangular_arbitrage(self):
        """監控三角套利機會"""
        while self.running:
            try:
                opportunities = await self.triangular_detector.detect_triangular_opportunities()
                
                for opportunity in opportunities:
                    await self.add_opportunity(opportunity)
                
                await asyncio.sleep(10)  # 10秒檢查一次
                
            except Exception as e:
                logger.error(f"三角套利監控錯誤: {e}")
                await asyncio.sleep(30)
    
    async def monitor_futures_spot_arbitrage(self):
        """監控期現套利機會"""
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        while self.running:
            try:
                opportunities = await self.futures_spot_detector.detect_futures_spot_opportunities(symbols)
                
                for opportunity in opportunities:
                    await self.add_opportunity(opportunity)
                
                await asyncio.sleep(60)  # 1分鐘檢查一次
                
            except Exception as e:
                logger.error(f"期現套利監控錯誤: {e}")
                await asyncio.sleep(120)
    
    async def monitor_statistical_arbitrage(self):
        """監控統計套利機會"""
        symbol_pairs = [
            ("BTC/USDT", "ETH/USDT"),
            ("SOL/USDT", "ADA/USDT"),
            ("BNB/USDT", "ETH/USDT")
        ]
        
        while self.running:
            try:
                opportunities = await self.statistical_detector.detect_statistical_opportunities(symbol_pairs)
                
                for opportunity in opportunities:
                    await self.add_opportunity(opportunity)
                
                await asyncio.sleep(300)  # 5分鐘檢查一次
                
            except Exception as e:
                logger.error(f"統計套利監控錯誤: {e}")
                await asyncio.sleep(600)
    
    async def monitor_funding_rate_arbitrage(self):
        """監控資金費率套利機會"""
        while self.running:
            try:
                # 使用現有的資金費率監控
                funding_data = await self.funding_monitor.get_funding_rates()
                
                # 轉換為套利機會
                for symbol, exchanges in funding_data.items():
                    if len(exchanges) >= 2:
                        rates = [(ex, data['funding_rate']) for ex, data in exchanges.items()]
                        rates.sort(key=lambda x: x[1])
                        
                        rate_diff = rates[-1][1] - rates[0][1]
                        
                        if rate_diff > 0.001:  # 0.1%以上差異
                            opportunity = ArbitrageOpportunity(
                                opportunity_id=str(uuid.uuid4()),
                                arbitrage_type=ArbitrageType.FUNDING_RATE_ARBITRAGE,
                                symbol=symbol,
                                exchanges=[rates[0][0], rates[-1][0]],
                                estimated_profit=rate_diff * 10000,
                                risk_level=RiskLevel.LOW,
                                confidence_score=min(0.9, rate_diff * 1000),
                                execution_time=datetime.now(),
                                expiry_time=datetime.now() + timedelta(hours=8),
                                requirements={
                                    "long_exchange": rates[0][0],
                                    "short_exchange": rates[-1][0],
                                    "funding_rate_diff": rate_diff
                                },
                                metadata={
                                    "funding_rate_diff": rate_diff,
                                    "next_settlement": "8_hours"
                                }
                            )
                            await self.add_opportunity(opportunity)
                
                await asyncio.sleep(60)  # 1分鐘檢查一次
                
            except Exception as e:
                logger.error(f"資金費率套利監控錯誤: {e}")
                await asyncio.sleep(120)
    
    async def add_opportunity(self, opportunity: ArbitrageOpportunity):
        """添加套利機會"""
        # 檢查是否已存在
        existing = [o for o in self.opportunities if o.opportunity_id == opportunity.opportunity_id]
        if existing:
            return
        
        self.opportunities.append(opportunity)
        self.performance_stats["total_opportunities"] += 1
        
        # 更新類型統計
        type_name = opportunity.arbitrage_type.value
        if type_name not in self.performance_stats["by_type"]:
            self.performance_stats["by_type"][type_name] = {
                "count": 0,
                "total_profit": 0.0,
                "success_rate": 0.0
            }
        
        self.performance_stats["by_type"][type_name]["count"] += 1
        
        logger.info(f"📊 發現套利機會: {opportunity.arbitrage_type.value} "
                   f"{opportunity.symbol} 利潤: {opportunity.estimated_profit:.2f} USDT")
    
    async def execute_opportunities(self):
        """執行套利機會"""
        while self.running:
            try:
                # 過濾有效的機會
                valid_opportunities = [
                    o for o in self.opportunities 
                    if o.expiry_time > datetime.now() and o.confidence_score > 0.6
                ]
                
                # 按利潤排序
                valid_opportunities.sort(key=lambda x: x.estimated_profit, reverse=True)
                
                # 執行前3個最佳機會
                for opportunity in valid_opportunities[:3]:
                    await self.execute_opportunity(opportunity)
                
                # 清理過期機會
                self.opportunities = [o for o in self.opportunities if o.expiry_time > datetime.now()]
                
                await asyncio.sleep(10)  # 10秒執行一次
                
            except Exception as e:
                logger.error(f"執行機會錯誤: {e}")
                await asyncio.sleep(30)
    
    async def execute_opportunity(self, opportunity: ArbitrageOpportunity):
        """執行單個套利機會"""
        try:
            logger.info(f"🚀 執行套利: {opportunity.arbitrage_type.value} {opportunity.symbol}")
            
            # 根據套利類型選擇執行策略
            if opportunity.arbitrage_type == ArbitrageType.FUNDING_RATE_ARBITRAGE:
                result = await self.execute_funding_rate_arbitrage(opportunity)
            elif opportunity.arbitrage_type == ArbitrageType.SPOT_ARBITRAGE:
                result = await self.execute_spot_arbitrage(opportunity)
            elif opportunity.arbitrage_type == ArbitrageType.TRIANGULAR_ARBITRAGE:
                result = await self.execute_triangular_arbitrage(opportunity)
            elif opportunity.arbitrage_type == ArbitrageType.FUTURES_SPOT_ARBITRAGE:
                result = await self.execute_futures_spot_arbitrage(opportunity)
            elif opportunity.arbitrage_type == ArbitrageType.STATISTICAL_ARBITRAGE:
                result = await self.execute_statistical_arbitrage(opportunity)
            else:
                result = {"status": "error", "message": "不支持的套利類型"}
            
            # 記錄執行結果
            self.execution_history.append({
                "opportunity_id": opportunity.opportunity_id,
                "arbitrage_type": opportunity.arbitrage_type.value,
                "symbol": opportunity.symbol,
                "result": result,
                "execution_time": datetime.now()
            })
            
            # 更新統計
            if result.get("status") == "success":
                profit = result.get("profit", 0)
                self.performance_stats["executed_opportunities"] += 1
                self.performance_stats["total_profit"] += profit
                
                # 更新類型統計
                type_name = opportunity.arbitrage_type.value
                self.performance_stats["by_type"][type_name]["total_profit"] += profit
                
                logger.info(f"✅ 套利執行成功，利潤: {profit:.2f} USDT")
            
            # 從機會列表中移除
            self.opportunities = [o for o in self.opportunities if o.opportunity_id != opportunity.opportunity_id]
            
        except Exception as e:
            logger.error(f"執行套利失敗: {e}")
    
    async def execute_funding_rate_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict:
        """執行資金費率套利"""
        # 使用混合架構系統
        return await self.hybrid_system.execute_strategy(opportunity)
    
    async def execute_spot_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict:
        """執行現貨套利"""
        # 模擬現貨套利執行
        await asyncio.sleep(1)  # 模擬執行時間
        
        success_rate = 0.8 if opportunity.risk_level == RiskLevel.LOW else 0.6
        success = hash(opportunity.opportunity_id) % 100 < success_rate * 100
        
        if success:
            return {
                "status": "success",
                "profit": opportunity.estimated_profit * 0.8,
                "execution_time": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "現貨套利執行失敗",
                "execution_time": datetime.now().isoformat()
            }
    
    async def execute_triangular_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict:
        """執行三角套利"""
        # 模擬三角套利執行
        await asyncio.sleep(0.5)  # 模擬執行時間
        
        success_rate = 0.7  # 三角套利成功率較低
        success = hash(opportunity.opportunity_id) % 100 < success_rate * 100
        
        if success:
            return {
                "status": "success",
                "profit": opportunity.estimated_profit * 0.7,
                "execution_time": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "三角套利執行失敗",
                "execution_time": datetime.now().isoformat()
            }
    
    async def execute_futures_spot_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict:
        """執行期現套利"""
        # 模擬期現套利執行
        await asyncio.sleep(2)  # 模擬執行時間
        
        success_rate = 0.85  # 期現套利成功率較高
        success = hash(opportunity.opportunity_id) % 100 < success_rate * 100
        
        if success:
            return {
                "status": "success",
                "profit": opportunity.estimated_profit * 0.85,
                "execution_time": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "期現套利執行失敗",
                "execution_time": datetime.now().isoformat()
            }
    
    async def execute_statistical_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict:
        """執行統計套利"""
        # 模擬統計套利執行
        await asyncio.sleep(5)  # 模擬執行時間
        
        success_rate = 0.75  # 統計套利成功率
        success = hash(opportunity.opportunity_id) % 100 < success_rate * 100
        
        if success:
            return {
                "status": "success",
                "profit": opportunity.estimated_profit * 0.75,
                "execution_time": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "統計套利執行失敗",
                "execution_time": datetime.now().isoformat()
            }
    
    def get_performance_report(self) -> Dict:
        """獲取性能報告"""
        total_executed = self.performance_stats["executed_opportunities"]
        total_opportunities = self.performance_stats["total_opportunities"]
        
        if total_executed > 0:
            self.performance_stats["success_rate"] = total_executed / total_opportunities
        
        # 計算各類型成功率
        for type_name, stats in self.performance_stats["by_type"].items():
            if stats["count"] > 0:
                stats["success_rate"] = stats["count"] / total_opportunities
        
        return self.performance_stats
    
    def get_active_opportunities(self) -> List[ArbitrageOpportunity]:
        """獲取活躍的套利機會"""
        return [o for o in self.opportunities if o.expiry_time > datetime.now()]

# 使用示例
async def main():
    """主函數"""
    system = ComprehensiveArbitrageSystem()
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("🛑 系統停止")
        system.running = False
        
        # 顯示最終報告
        report = system.get_performance_report()
        logger.info(f"📈 最終性能報告: {json.dumps(report, indent=2, default=str)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 