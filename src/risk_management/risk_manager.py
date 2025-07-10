#!/usr/bin/env python3
"""
綜合風險管理模組
管理多策略套利系統的風險控制
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict, deque

logger = logging.getLogger("RiskManager")

class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class Position:
    """倉位信息"""
    position_id: str
    strategy_type: str
    symbol: str
    exchange: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    created_at: datetime
    updated_at: datetime

@dataclass
class RiskMetrics:
    """風險指標"""
    total_exposure: float
    daily_pnl: float
    max_drawdown: float
    var_95: float  # 95% VaR
    sharpe_ratio: float
    correlation_matrix: Dict[str, Dict[str, float]]
    volatility: float

class CircuitBreaker:
    """熔斷器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
        
    def record_failure(self):
        """記錄失敗"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"🔴 熔斷器開啟，失敗次數: {self.failure_count}")
    
    def record_success(self):
        """記錄成功"""
        if self.failure_count > 0:
            self.failure_count -= 1
    
    def can_execute(self) -> bool:
        """檢查是否可以執行"""
        if not self.is_open:
            return True
        
        # 檢查是否超過恢復時間
        if (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
            self.reset()
            return True
        
        return False
    
    def reset(self):
        """重置熔斷器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
        logger.info("🟢 熔斷器重置")

class PositionManager:
    """倉位管理器"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.position_history: List[Position] = []
        self.max_positions = 20
        
    def add_position(self, position: Position):
        """添加倉位"""
        if len(self.positions) >= self.max_positions:
            # 移除最舊的倉位
            oldest_position = min(self.positions.values(), key=lambda p: p.created_at)
            self.close_position(oldest_position.position_id)
        
        self.positions[position.position_id] = position
        logger.info(f"📊 添加倉位: {position.symbol} {position.side} {position.size}")
    
    def update_position(self, position_id: str, current_price: float, unrealized_pnl: float):
        """更新倉位"""
        if position_id in self.positions:
            position = self.positions[position_id]
            position.current_price = current_price
            position.unrealized_pnl = unrealized_pnl
            position.updated_at = datetime.now()
    
    def close_position(self, position_id: str, close_price: float = None):
        """關閉倉位"""
        if position_id in self.positions:
            position = self.positions[position_id]
            
            if close_price:
                position.current_price = close_price
                position.realized_pnl = position.unrealized_pnl
            
            # 移到歷史記錄
            self.position_history.append(position)
            del self.positions[position_id]
            
            logger.info(f"📊 關閉倉位: {position.symbol} 利潤: {position.realized_pnl:.2f}")
    
    def get_total_exposure(self) -> float:
        """獲取總敞口"""
        return sum(abs(p.size * p.current_price) for p in self.positions.values())
    
    def get_daily_pnl(self) -> float:
        """獲取日內損益"""
        today = datetime.now().date()
        today_positions = [p for p in self.position_history 
                          if p.updated_at.date() == today]
        return sum(p.realized_pnl for p in today_positions)
    
    def get_strategy_exposure(self, strategy_type: str) -> float:
        """獲取特定策略的敞口"""
        return sum(abs(p.size * p.current_price) for p in self.positions.values() 
                  if p.strategy_type == strategy_type)

class CorrelationManager:
    """相關性管理器"""
    
    def __init__(self, lookback_period: int = 100):
        self.lookback_period = lookback_period
        self.price_history = defaultdict(lambda: deque(maxlen=lookback_period))
        self.correlation_matrix = {}
        
    def update_price(self, symbol: str, price: float):
        """更新價格歷史"""
        self.price_history[symbol].append(price)
    
    def calculate_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """計算相關性矩陣"""
        symbols = list(self.price_history.keys())
        correlation_matrix = {}
        
        for i, symbol1 in enumerate(symbols):
            correlation_matrix[symbol1] = {}
            for j, symbol2 in enumerate(symbols):
                if i == j:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    correlation = self.calculate_correlation(symbol1, symbol2)
                    correlation_matrix[symbol1][symbol2] = correlation
        
        self.correlation_matrix = correlation_matrix
        return correlation_matrix
    
    def calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """計算兩個符號的相關性"""
        prices1 = list(self.price_history[symbol1])
        prices2 = list(self.price_history[symbol2])
        
        if len(prices1) < 10 or len(prices2) < 10:
            return 0.0
        
        # 確保長度一致
        min_length = min(len(prices1), len(prices2))
        prices1 = prices1[-min_length:]
        prices2 = prices2[-min_length:]
        
        # 計算收益率
        returns1 = np.diff(prices1) / prices1[:-1]
        returns2 = np.diff(prices2) / prices2[:-1]
        
        if len(returns1) == 0 or len(returns2) == 0:
            return 0.0
        
        # 計算相關性
        correlation = np.corrcoef(returns1, returns2)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def check_correlation_limit(self, new_symbol: str, existing_symbols: List[str], limit: float = 0.7) -> bool:
        """檢查相關性限制"""
        if not existing_symbols:
            return True
        
        for symbol in existing_symbols:
            if symbol in self.correlation_matrix and new_symbol in self.correlation_matrix[symbol]:
                correlation = abs(self.correlation_matrix[symbol][new_symbol])
                if correlation > limit:
                    logger.warning(f"⚠️ 相關性過高: {symbol} vs {new_symbol} = {correlation:.3f}")
                    return False
        
        return True

class VolatilityManager:
    """波動率管理器"""
    
    def __init__(self, window: int = 20):
        self.window = window
        self.returns_history = defaultdict(lambda: deque(maxlen=window))
        
    def update_returns(self, symbol: str, price: float):
        """更新收益率"""
        if len(self.returns_history[symbol]) > 0:
            last_price = self.returns_history[symbol][-1] if self.returns_history[symbol] else price
            returns = (price - last_price) / last_price
            self.returns_history[symbol].append(returns)
        else:
            self.returns_history[symbol].append(0.0)
    
    def calculate_volatility(self, symbol: str) -> float:
        """計算波動率"""
        returns = list(self.returns_history[symbol])
        if len(returns) < 5:
            return 0.0
        
        return np.std(returns) * np.sqrt(252)  # 年化波動率
    
    def check_volatility_limit(self, symbol: str, limit: float = 0.5) -> bool:
        """檢查波動率限制"""
        volatility = self.calculate_volatility(symbol)
        if volatility > limit:
            logger.warning(f"⚠️ 波動率過高: {symbol} = {volatility:.3f}")
            return False
        return True

class KellyCriterion:
    """凱利公式"""
    
    @staticmethod
    def calculate_position_size(win_rate: float, avg_win: float, avg_loss: float, 
                               max_position_size: float = 1.0) -> float:
        """計算凱利公式建議的倉位大小"""
        if avg_loss == 0:
            return 0.0
        
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # 限制在合理範圍內
        kelly_fraction = max(0.0, min(kelly_fraction, max_position_size))
        
        return kelly_fraction

class ComprehensiveRiskManager:
    """綜合風險管理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.position_manager = PositionManager()
        self.correlation_manager = CorrelationManager()
        self.volatility_manager = VolatilityManager()
        
        # 熔斷器
        self.circuit_breakers = {
            "global": CircuitBreaker(),
            "spot_arbitrage": CircuitBreaker(),
            "funding_rate_arbitrage": CircuitBreaker(),
            "triangular_arbitrage": CircuitBreaker(),
            "futures_spot_arbitrage": CircuitBreaker(),
            "statistical_arbitrage": CircuitBreaker()
        }
        
        # 風險指標
        self.risk_metrics = RiskMetrics(
            total_exposure=0.0,
            daily_pnl=0.0,
            max_drawdown=0.0,
            var_95=0.0,
            sharpe_ratio=0.0,
            correlation_matrix={},
            volatility=0.0
        )
        
        # 歷史數據
        self.pnl_history = deque(maxlen=1000)
        self.max_equity = 0.0
        
        logger.info("✅ 綜合風險管理器已初始化")
    
    async def check_risk_limits(self, strategy_type: str, symbol: str, 
                               size: float, price: float) -> Tuple[bool, str]:
        """檢查風險限制"""
        
        # 1. 檢查熔斷器
        if not self.circuit_breakers["global"].can_execute():
            return False, "全局熔斷器開啟"
        
        if not self.circuit_breakers[strategy_type].can_execute():
            return False, f"{strategy_type} 熔斷器開啟"
        
        # 2. 檢查總敞口限制
        new_exposure = self.position_manager.get_total_exposure() + abs(size * price)
        max_exposure = self.config["risk_management"]["global"]["max_total_exposure"]
        
        if new_exposure > max_exposure:
            return False, f"總敞口超限: {new_exposure:.2f} > {max_exposure}"
        
        # 3. 檢查策略敞口限制
        strategy_config = self.config["strategies"][strategy_type]
        strategy_exposure = self.position_manager.get_strategy_exposure(strategy_type) + abs(size * price)
        max_strategy_exposure = strategy_config["max_position_size"]
        
        if strategy_exposure > max_strategy_exposure:
            return False, f"策略敞口超限: {strategy_exposure:.2f} > {max_strategy_exposure}"
        
        # 4. 檢查日內損失限制
        daily_pnl = self.position_manager.get_daily_pnl()
        max_daily_loss = self.config["risk_management"]["global"]["max_daily_loss"]
        
        if daily_pnl < -max_daily_loss:
            return False, f"日內損失超限: {daily_pnl:.2f} < -{max_daily_loss}"
        
        # 5. 檢查相關性限制
        existing_symbols = [p.symbol for p in self.position_manager.positions.values()]
        correlation_limit = self.config["risk_management"]["per_strategy"]["correlation_limit"]
        
        if not self.correlation_manager.check_correlation_limit(symbol, existing_symbols, correlation_limit):
            return False, "相關性過高"
        
        # 6. 檢查波動率限制
        volatility_limit = self.config["risk_management"]["per_strategy"]["volatility_limit"]
        
        if not self.volatility_manager.check_volatility_limit(symbol, volatility_limit):
            return False, "波動率過高"
        
        return True, "風險檢查通過"
    
    def calculate_position_size(self, strategy_type: str, confidence_score: float, 
                               estimated_profit: float, max_loss: float) -> float:
        """計算倉位大小"""
        
        # 獲取策略配置
        strategy_config = self.config["strategies"][strategy_type]
        max_position_size = strategy_config["max_position_size"]
        
        # 使用凱利公式
        win_rate = confidence_score
        avg_win = estimated_profit
        avg_loss = max_loss
        
        kelly_size = KellyCriterion.calculate_position_size(win_rate, avg_win, avg_loss)
        
        # 應用風險限制
        final_size = min(kelly_size * max_position_size, max_position_size)
        
        return final_size
    
    def record_trade_result(self, strategy_type: str, success: bool, profit: float):
        """記錄交易結果"""
        
        if success:
            self.circuit_breakers[strategy_type].record_success()
            self.circuit_breakers["global"].record_success()
        else:
            self.circuit_breakers[strategy_type].record_failure()
            self.circuit_breakers["global"].record_failure()
        
        # 更新PNL歷史
        self.pnl_history.append(profit)
        
        # 更新最大權益
        current_equity = sum(self.pnl_history)
        self.max_equity = max(self.max_equity, current_equity)
        
        # 計算最大回撤
        if self.max_equity > 0:
            drawdown = (self.max_equity - current_equity) / self.max_equity
            self.risk_metrics.max_drawdown = max(self.risk_metrics.max_drawdown, drawdown)
    
    def update_risk_metrics(self):
        """更新風險指標"""
        
        # 更新總敞口
        self.risk_metrics.total_exposure = self.position_manager.get_total_exposure()
        
        # 更新日內損益
        self.risk_metrics.daily_pnl = self.position_manager.get_daily_pnl()
        
        # 更新相關性矩陣
        self.risk_metrics.correlation_matrix = self.correlation_manager.calculate_correlation_matrix()
        
        # 計算VaR
        if len(self.pnl_history) > 10:
            pnl_array = np.array(list(self.pnl_history))
            self.risk_metrics.var_95 = np.percentile(pnl_array, 5)
            
            # 計算夏普比率
            if np.std(pnl_array) > 0:
                self.risk_metrics.sharpe_ratio = np.mean(pnl_array) / np.std(pnl_array)
        
        # 計算整體波動率
        all_volatilities = []
        for symbol in self.volatility_manager.returns_history.keys():
            vol = self.volatility_manager.calculate_volatility(symbol)
            if vol > 0:
                all_volatilities.append(vol)
        
        if all_volatilities:
            self.risk_metrics.volatility = np.mean(all_volatilities)
    
    def get_risk_report(self) -> Dict:
        """獲取風險報告"""
        self.update_risk_metrics()
        
        return {
            "risk_metrics": asdict(self.risk_metrics),
            "circuit_breakers": {
                name: {
                    "is_open": cb.is_open,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for name, cb in self.circuit_breakers.items()
            },
            "positions": {
                "total_count": len(self.position_manager.positions),
                "total_exposure": self.position_manager.get_total_exposure(),
                "by_strategy": {
                    strategy: self.position_manager.get_strategy_exposure(strategy)
                    for strategy in set(p.strategy_type for p in self.position_manager.positions.values())
                }
            },
            "performance": {
                "total_pnl": sum(self.pnl_history),
                "max_drawdown": self.risk_metrics.max_drawdown,
                "sharpe_ratio": self.risk_metrics.sharpe_ratio,
                "var_95": self.risk_metrics.var_95
            }
        }
    
    def should_stop_trading(self) -> bool:
        """檢查是否應該停止交易"""
        
        # 檢查全局熔斷器
        if self.circuit_breakers["global"].is_open:
            return True
        
        # 檢查最大回撤
        max_drawdown_limit = self.config["risk_management"]["global"]["max_drawdown"]
        if self.risk_metrics.max_drawdown > max_drawdown_limit:
            logger.warning(f"🛑 達到最大回撤限制: {self.risk_metrics.max_drawdown:.3f} > {max_drawdown_limit}")
            return True
        
        # 檢查日內損失
        max_daily_loss = self.config["risk_management"]["global"]["max_daily_loss"]
        if self.risk_metrics.daily_pnl < -max_daily_loss:
            logger.warning(f"🛑 達到日內損失限制: {self.risk_metrics.daily_pnl:.2f} < -{max_daily_loss}")
            return True
        
        return False

# 使用示例
async def main():
    """測試風險管理器"""
    
    # 加載配置
    with open("arbitrage_config.json", "r") as f:
        config = json.load(f)
    
    risk_manager = ComprehensiveRiskManager(config)
    
    # 模擬一些交易
    for i in range(10):
        # 檢查風險
        can_trade, reason = await risk_manager.check_risk_limits(
            "spot_arbitrage", "BTC/USDT", 1000, 50000
        )
        
        if can_trade:
            # 計算倉位大小
            position_size = risk_manager.calculate_position_size(
                "spot_arbitrage", 0.8, 100, 50
            )
            
            print(f"交易 {i+1}: 可以交易，倉位大小: {position_size:.2f}")
            
            # 記錄結果
            success = i % 3 != 0  # 70% 成功率
            profit = 50 if success else -30
            risk_manager.record_trade_result("spot_arbitrage", success, profit)
        else:
            print(f"交易 {i+1}: 不能交易，原因: {reason}")
        
        await asyncio.sleep(1)
    
    # 獲取風險報告
    report = risk_manager.get_risk_report()
    print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 