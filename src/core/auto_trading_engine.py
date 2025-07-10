#!/usr/bin/env python3
"""
自動交易引擎 - 完整的風險控制和倉位管理
支援多交易所、多策略、實時風險監控和智能交易執行
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from abc import ABC, abstractmethod

logger = logging.getLogger("AutoTradingEngine")

class OrderType(Enum):
    """訂單類型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderSide(Enum):
    """訂單方向"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """訂單狀態"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PositionType(Enum):
    """倉位類型"""
    LONG = "long"
    SHORT = "short"
    HEDGED = "hedged"  # 對沖倉位

class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class Order:
    """交易訂單"""
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: float = 0.0
    commission: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Position:
    """交易倉位"""
    position_id: str
    symbol: str
    exchanges: List[str]  # 涉及的交易所
    position_type: PositionType
    entry_price: float
    current_price: float
    quantity: float
    unrealized_pnl: float
    realized_pnl: float
    commission_paid: float
    risk_level: RiskLevel
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_loss: float = 0.0
    max_profit: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None
    orders: List[str] = None  # 相關訂單ID
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.orders is None:
            self.orders = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class RiskMetrics:
    """風險指標"""
    current_exposure: float  # 當前敞口
    max_exposure_limit: float  # 最大敞口限制
    daily_pnl: float  # 日內盈虧
    daily_loss_limit: float  # 日內虧損限制
    open_positions_count: int  # 開倉數量
    max_positions_limit: int  # 最大持倉限制
    correlation_risk: float  # 相關性風險
    liquidity_risk: float  # 流動性風險
    concentration_risk: float  # 集中度風險
    var_95: float  # 95% VaR
    max_drawdown: float  # 最大回撤
    sharpe_ratio: float  # 夏普比率

class RiskManager:
    """風險管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_daily_loss = config.get('max_daily_loss', 1000.0)
        self.max_total_exposure = config.get('max_total_exposure', 10000.0)
        self.max_single_position = config.get('max_single_position', 2000.0)
        self.max_positions = config.get('max_positions', 10)
        self.max_correlation = config.get('max_correlation', 0.7)
        self.stop_loss_pct = config.get('stop_loss_pct', 2.0)
        self.take_profit_pct = config.get('take_profit_pct', 5.0)
        
        # 風險指標
        self.current_metrics = RiskMetrics(
            current_exposure=0.0,
            max_exposure_limit=self.max_total_exposure,
            daily_pnl=0.0,
            daily_loss_limit=self.max_daily_loss,
            open_positions_count=0,
            max_positions_limit=self.max_positions,
            correlation_risk=0.0,
            liquidity_risk=0.0,
            concentration_risk=0.0,
            var_95=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0
        )
        
        logger.info(f"✅ 風險管理器已初始化")
        logger.info(f"   最大日內虧損: {self.max_daily_loss} USDT")
        logger.info(f"   最大總敞口: {self.max_total_exposure} USDT")
        logger.info(f"   最大單倉位: {self.max_single_position} USDT")
        logger.info(f"   最大持倉數: {self.max_positions}")
    
    def can_open_position(self, symbol: str, quantity: float, price: float, 
                         positions: List[Position]) -> Tuple[bool, str]:
        """檢查是否可以開倉"""
        
        # 檢查持倉數量限制
        if len(positions) >= self.max_positions:
            return False, f"已達到最大持倉數限制 ({self.max_positions})"
        
        # 檢查單倉位大小限制
        position_value = quantity * price
        if position_value > self.max_single_position:
            return False, f"倉位價值 ({position_value:.2f}) 超過單倉位限制 ({self.max_single_position})"
        
        # 檢查總敞口限制
        current_exposure = sum(pos.quantity * pos.current_price for pos in positions)
        if current_exposure + position_value > self.max_total_exposure:
            return False, f"總敞口將超過限制 ({self.max_total_exposure})"
        
        # 檢查日內虧損限制
        if self.current_metrics.daily_pnl < -self.max_daily_loss:
            return False, f"已達到日內虧損限制 ({self.max_daily_loss})"
        
        # 檢查相關性風險
        correlation_risk = self._calculate_correlation_risk(symbol, positions)
        if correlation_risk > self.max_correlation:
            return False, f"相關性風險過高 ({correlation_risk:.2f} > {self.max_correlation})"
        
        return True, "風險檢查通過"
    
    def should_close_position(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """檢查是否應該平倉"""
        
        # 更新倉位價格
        old_price = position.current_price
        position.current_price = current_price
        
        # 計算當前盈虧
        if position.position_type == PositionType.LONG:
            pnl_pct = (current_price - position.entry_price) / position.entry_price * 100
        else:  # SHORT
            pnl_pct = (position.entry_price - current_price) / position.entry_price * 100
        
        # 止損檢查
        if position.stop_loss and ((position.position_type == PositionType.LONG and current_price <= position.stop_loss) or
                                   (position.position_type == PositionType.SHORT and current_price >= position.stop_loss)):
            return True, f"觸發止損: 當前價格 {current_price}, 止損價 {position.stop_loss}"
        
        # 止盈檢查
        if position.take_profit and ((position.position_type == PositionType.LONG and current_price >= position.take_profit) or
                                     (position.position_type == PositionType.SHORT and current_price <= position.take_profit)):
            return True, f"觸發止盈: 當前價格 {current_price}, 止盈價 {position.take_profit}"
        
        # 動態止損檢查（移動止損）
        if pnl_pct < -self.stop_loss_pct:
            return True, f"觸發動態止損: 虧損 {pnl_pct:.2f}%"
        
        # 風險等級檢查
        if position.risk_level == RiskLevel.EXTREME:
            return True, "極端風險等級，強制平倉"
        
        # 時間限制檢查（例如：48小時強制平倉）
        if datetime.now() - position.created_at > timedelta(hours=48):
            return True, "持倉時間過長，強制平倉"
        
        return False, "無需平倉"
    
    def _calculate_correlation_risk(self, symbol: str, positions: List[Position]) -> float:
        """計算相關性風險"""
        # 簡化的相關性計算
        # 實際應用中應該使用歷史價格數據計算相關係數
        
        base_asset = symbol.split('/')[0] if '/' in symbol else symbol
        
        correlated_positions = 0
        total_positions = len(positions)
        
        for pos in positions:
            pos_base = pos.symbol.split('/')[0] if '/' in pos.symbol else pos.symbol
            if pos_base == base_asset:
                correlated_positions += 1
        
        return correlated_positions / max(1, total_positions)
    
    def update_metrics(self, positions: List[Position], orders: List[Order]):
        """更新風險指標"""
        
        # 計算當前敞口
        current_exposure = sum(pos.quantity * pos.current_price for pos in positions)
        self.current_metrics.current_exposure = current_exposure
        
        # 計算日內盈虧
        daily_pnl = sum(pos.unrealized_pnl + pos.realized_pnl for pos in positions)
        self.current_metrics.daily_pnl = daily_pnl
        
        # 更新持倉數
        self.current_metrics.open_positions_count = len(positions)
        
        # 計算集中度風險
        if positions:
            max_position_value = max(pos.quantity * pos.current_price for pos in positions)
            self.current_metrics.concentration_risk = max_position_value / current_exposure if current_exposure > 0 else 0
        
        logger.debug(f"風險指標更新: 敞口={current_exposure:.2f}, 日內PnL={daily_pnl:.2f}, 持倉數={len(positions)}")

class PositionManager:
    """倉位管理器"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        
        logger.info("✅ 倉位管理器已初始化")
    
    def create_position(self, symbol: str, exchanges: List[str], position_type: PositionType,
                       entry_price: float, quantity: float, metadata: Dict[str, Any] = None) -> Optional[Position]:
        """創建新倉位"""
        
        # 風險檢查
        can_open, reason = self.risk_manager.can_open_position(
            symbol, quantity, entry_price, list(self.positions.values())
        )
        
        if not can_open:
            logger.warning(f"❌ 無法開倉: {reason}")
            return None
        
        # 創建倉位
        position = Position(
            position_id=str(uuid.uuid4()),
            symbol=symbol,
            exchanges=exchanges,
            position_type=position_type,
            entry_price=entry_price,
            current_price=entry_price,
            quantity=quantity,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            commission_paid=0.0,
            risk_level=self._assess_position_risk(symbol, quantity, entry_price),
            metadata=metadata or {}
        )
        
        # 設置止損止盈
        if position_type == PositionType.LONG:
            position.stop_loss = entry_price * (1 - self.risk_manager.stop_loss_pct / 100)
            position.take_profit = entry_price * (1 + self.risk_manager.take_profit_pct / 100)
        else:  # SHORT
            position.stop_loss = entry_price * (1 + self.risk_manager.stop_loss_pct / 100)
            position.take_profit = entry_price * (1 - self.risk_manager.take_profit_pct / 100)
        
        self.positions[position.position_id] = position
        
        logger.info(f"✅ 創建倉位: {symbol} {position_type.value} {quantity}@{entry_price}")
        logger.info(f"   止損: {position.stop_loss:.4f}, 止盈: {position.take_profit:.4f}")
        
        return position
    
    def update_position_price(self, position_id: str, current_price: float):
        """更新倉位價格"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        old_price = position.current_price
        position.current_price = current_price
        position.updated_at = datetime.now()
        
        # 重新計算未實現盈虧
        if position.position_type == PositionType.LONG:
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:  # SHORT
            position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
        
        # 更新最大盈虧
        position.max_profit = max(position.max_profit, position.unrealized_pnl)
        position.max_loss = min(position.max_loss, position.unrealized_pnl)
        
        logger.debug(f"更新倉位價格: {position.symbol} {old_price:.4f} -> {current_price:.4f}, PnL: {position.unrealized_pnl:.2f}")
    
    def close_position(self, position_id: str, exit_price: float) -> Optional[Position]:
        """平倉"""
        if position_id not in self.positions:
            logger.error(f"❌ 倉位不存在: {position_id}")
            return None
        
        position = self.positions[position_id]
        
        # 計算已實現盈虧
        if position.position_type == PositionType.LONG:
            realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:  # SHORT
            realized_pnl = (position.entry_price - exit_price) * position.quantity
        
        position.realized_pnl = realized_pnl - position.commission_paid
        position.unrealized_pnl = 0.0
        position.current_price = exit_price
        position.updated_at = datetime.now()
        
        # 移除倉位
        closed_position = self.positions.pop(position_id)
        
        logger.info(f"✅ 平倉完成: {position.symbol} 實現盈虧: {realized_pnl:.2f} USDT")
        
        return closed_position
    
    def _assess_position_risk(self, symbol: str, quantity: float, price: float) -> RiskLevel:
        """評估倉位風險等級"""
        position_value = quantity * price
        
        # 基於倉位大小評估風險
        if position_value > self.risk_manager.max_single_position * 0.8:
            return RiskLevel.HIGH
        elif position_value > self.risk_manager.max_single_position * 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_position_summary(self) -> Dict[str, Any]:
        """獲取倉位摘要"""
        total_positions = len(self.positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        
        return {
            'total_positions': total_positions,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_pnl': total_unrealized_pnl + total_realized_pnl,
            'positions': [asdict(pos) for pos in self.positions.values()]
        }

class OrderManager:
    """訂單管理器"""
    
    def __init__(self, exchanges: Dict[str, Any]):
        self.exchanges = exchanges
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        logger.info("✅ 訂單管理器已初始化")
    
    async def create_order(self, symbol: str, exchange: str, side: OrderSide, 
                          order_type: OrderType, quantity: float, 
                          price: Optional[float] = None, metadata: Dict[str, Any] = None) -> Optional[Order]:
        """創建訂單"""
        
        if exchange not in self.exchanges:
            logger.error(f"❌ 交易所不存在: {exchange}")
            return None
        
        # 創建訂單對象
        order = Order(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            exchange=exchange,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            metadata=metadata or {}
        )
        
        self.orders[order.order_id] = order
        
        logger.info(f"📝 創建訂單: {exchange} {symbol} {side.value} {quantity}")
        
        return order
    
    async def submit_order(self, order: Order) -> bool:
        """提交訂單到交易所"""
        try:
            exchange_connector = self.exchanges[order.exchange]
            
            # 調用交易所API提交訂單
            result = await exchange_connector.place_order(
                symbol=order.symbol,
                side=order.side.value,
                amount=order.quantity,
                order_type=order.order_type.value
            )
            
            if result.get('status') == 'success':
                order.status = OrderStatus.SUBMITTED
                order.updated_at = datetime.now()
                logger.info(f"✅ 訂單已提交: {order.order_id}")
                return True
            else:
                order.status = OrderStatus.REJECTED
                order.updated_at = datetime.now()
                logger.error(f"❌ 訂單被拒絕: {result.get('message', '未知錯誤')}")
                return False
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.now()
            logger.error(f"❌ 提交訂單失敗: {e}")
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消訂單"""
        if order_id not in self.orders:
            logger.error(f"❌ 訂單不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        try:
            exchange_connector = self.exchanges[order.exchange]
            
            # 調用交易所API取消訂單
            # 注意：這裡需要根據實際交易所API實現
            
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            logger.info(f"✅ 訂單已取消: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 取消訂單失敗: {e}")
            return False
    
    def update_order_status(self, order_id: str, status: OrderStatus, 
                           filled_quantity: float = 0.0, average_price: float = 0.0):
        """更新訂單狀態"""
        if order_id not in self.orders:
            return
        
        order = self.orders[order_id]
        order.status = status
        order.filled_quantity = filled_quantity
        order.average_price = average_price
        order.updated_at = datetime.now()
        
        logger.info(f"📊 訂單狀態更新: {order_id} -> {status.value}")
        
        # 如果訂單完成，移動到歷史記錄
        if status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
            self.order_history.append(self.orders.pop(order_id))

class AutoTradingEngine:
    """自動交易引擎"""
    
    def __init__(self, exchanges: Dict[str, Any], config: Dict[str, Any]):
        self.exchanges = exchanges
        self.config = config
        
        # 初始化管理器
        self.risk_manager = RiskManager(config.get('risk', {}))
        self.position_manager = PositionManager(self.risk_manager)
        self.order_manager = OrderManager(exchanges)
        
        # 交易控制
        self.trading_enabled = config.get('trading_enabled', False)
        self.safe_mode = config.get('safe_mode', True)
        self.auto_close_enabled = config.get('auto_close_enabled', True)
        
        # 統計數據
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'start_time': datetime.now()
        }
        
        logger.info("🚀 自動交易引擎已初始化")
        logger.info(f"   交易模式: {'安全模式' if self.safe_mode else '實盤模式'}")
        logger.info(f"   自動交易: {'啟用' if self.trading_enabled else '禁用'}")
        logger.info(f"   自動平倉: {'啟用' if self.auto_close_enabled else '禁用'}")
    
    async def execute_arbitrage_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """執行套利機會"""
        
        if not self.trading_enabled:
            logger.info("⏸️ 交易已禁用，跳過執行")
            return False
        
        symbol = opportunity.get('symbol')
        strategy = opportunity.get('strategy_type', 'unknown')
        primary_exchange = opportunity.get('primary_exchange')
        secondary_exchange = opportunity.get('secondary_exchange')
        
        logger.info(f"🎯 執行套利機會: {symbol} {strategy}")
        
        try:
            if strategy == 'cross_exchange':
                return await self._execute_cross_exchange_arbitrage(opportunity)
            elif strategy == 'extreme_funding':
                return await self._execute_extreme_funding_arbitrage(opportunity)
            else:
                logger.warning(f"⚠️ 不支持的策略類型: {strategy}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 執行套利失敗: {e}")
            self.stats['failed_trades'] += 1
            return False
    
    async def _execute_cross_exchange_arbitrage(self, opportunity: Dict[str, Any]) -> bool:
        """執行跨交易所套利"""
        
        symbol = opportunity['symbol']
        primary_exchange = opportunity['primary_exchange']
        secondary_exchange = opportunity['secondary_exchange']
        estimated_profit = opportunity.get('net_profit_8h', 0)
        
        # 計算交易數量（基於可用余額和風險限制）
        trade_quantity = await self._calculate_trade_quantity(symbol, estimated_profit)
        
        if trade_quantity <= 0:
            logger.warning("⚠️ 計算交易數量為0，跳過執行")
            return False
        
        if self.safe_mode:
            logger.info(f"🔒 安全模式: 檢測到跨交易所套利機會")
            logger.info(f"   {primary_exchange}: 做多 {trade_quantity} {symbol}")
            logger.info(f"   {secondary_exchange}: 做空 {trade_quantity} {symbol}")
            logger.info(f"   預期利潤: {estimated_profit:.2f} USDT")
            
            # 創建記錄倉位
            position = self.position_manager.create_position(
                symbol=symbol,
                exchanges=[primary_exchange, secondary_exchange],
                position_type=PositionType.HEDGED,
                entry_price=opportunity.get('primary_price', 0),
                quantity=trade_quantity,
                metadata={
                    'strategy': 'cross_exchange',
                    'primary_exchange': primary_exchange,
                    'secondary_exchange': secondary_exchange,
                    'estimated_profit': estimated_profit,
                    'safe_mode': True
                }
            )
            
            if position:
                self.stats['successful_trades'] += 1
                self.stats['total_trades'] += 1
                logger.info(f"✅ 套利機會已記錄: {position.position_id}")
                return True
            
        else:
            logger.info(f"💰 實盤模式: 執行跨交易所套利")
            
            # 創建訂單
            order1 = await self.order_manager.create_order(
                symbol=symbol,
                exchange=primary_exchange,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=trade_quantity,
                metadata={'strategy': 'cross_exchange', 'leg': 'primary'}
            )
            
            order2 = await self.order_manager.create_order(
                symbol=symbol,
                exchange=secondary_exchange,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=trade_quantity,
                metadata={'strategy': 'cross_exchange', 'leg': 'secondary'}
            )
            
            if not order1 or not order2:
                logger.error("❌ 訂單創建失敗")
                return False
            
            # 提交訂單
            success1 = await self.order_manager.submit_order(order1)
            success2 = await self.order_manager.submit_order(order2)
            
            if success1 and success2:
                # 創建實際倉位
                position = self.position_manager.create_position(
                    symbol=symbol,
                    exchanges=[primary_exchange, secondary_exchange],
                    position_type=PositionType.HEDGED,
                    entry_price=opportunity.get('primary_price', 0),
                    quantity=trade_quantity,
                    metadata={
                        'strategy': 'cross_exchange',
                        'order1_id': order1.order_id,
                        'order2_id': order2.order_id,
                        'estimated_profit': estimated_profit
                    }
                )
                
                if position:
                    self.stats['successful_trades'] += 1
                    self.stats['total_trades'] += 1
                    logger.info(f"✅ 跨交易所套利倉位已創建: {position.position_id}")
                    return True
            else:
                logger.error("❌ 訂單提交失敗")
                self.stats['failed_trades'] += 1
                self.stats['total_trades'] += 1
        
        return False
    
    async def _execute_extreme_funding_arbitrage(self, opportunity: Dict[str, Any]) -> bool:
        """執行極端資金費率套利"""
        
        symbol = opportunity['symbol']
        exchange = opportunity['primary_exchange']
        funding_rate = opportunity.get('funding_rate', 0)
        estimated_profit = opportunity.get('net_profit_8h', 0)
        
        # 計算交易數量
        trade_quantity = await self._calculate_trade_quantity(symbol, estimated_profit)
        
        if trade_quantity <= 0:
            logger.warning("⚠️ 計算交易數量為0，跳過執行")
            return False
        
        # 根據資金費率決定方向
        if funding_rate > 0:
            # 正資金費率：做空收取費率
            side = OrderSide.SELL
            position_type = PositionType.SHORT
        else:
            # 負資金費率：做多收取費率
            side = OrderSide.BUY
            position_type = PositionType.LONG
        
        if self.safe_mode:
            logger.info(f"🔒 安全模式: 檢測到極端資金費率套利機會")
            logger.info(f"   {exchange}: {side.value} {trade_quantity} {symbol}")
            logger.info(f"   資金費率: {funding_rate:.4f}")
            logger.info(f"   預期利潤: {estimated_profit:.2f} USDT")
            
            # 創建記錄倉位
            position = self.position_manager.create_position(
                symbol=symbol,
                exchanges=[exchange],
                position_type=position_type,
                entry_price=opportunity.get('mark_price', 0),
                quantity=trade_quantity,
                metadata={
                    'strategy': 'extreme_funding',
                    'funding_rate': funding_rate,
                    'estimated_profit': estimated_profit,
                    'safe_mode': True
                }
            )
            
            if position:
                self.stats['successful_trades'] += 1
                self.stats['total_trades'] += 1
                logger.info(f"✅ 極端費率機會已記錄: {position.position_id}")
                return True
        
        else:
            logger.info(f"💰 實盤模式: 執行極端資金費率套利")
            
            # 創建訂單
            order = await self.order_manager.create_order(
                symbol=symbol,
                exchange=exchange,
                side=side,
                order_type=OrderType.MARKET,
                quantity=trade_quantity,
                metadata={
                    'strategy': 'extreme_funding',
                    'funding_rate': funding_rate
                }
            )
            
            if not order:
                logger.error("❌ 訂單創建失敗")
                return False
            
            # 提交訂單
            success = await self.order_manager.submit_order(order)
            
            if success:
                # 創建實際倉位
                position = self.position_manager.create_position(
                    symbol=symbol,
                    exchanges=[exchange],
                    position_type=position_type,
                    entry_price=opportunity.get('mark_price', 0),
                    quantity=trade_quantity,
                    metadata={
                        'strategy': 'extreme_funding',
                        'order_id': order.order_id,
                        'funding_rate': funding_rate,
                        'estimated_profit': estimated_profit
                    }
                )
                
                if position:
                    self.stats['successful_trades'] += 1
                    self.stats['total_trades'] += 1
                    logger.info(f"✅ 極端費率倉位已創建: {position.position_id}")
                    return True
            else:
                logger.error("❌ 訂單提交失敗")
                self.stats['failed_trades'] += 1
                self.stats['total_trades'] += 1
        
        return False
    
    async def _calculate_trade_quantity(self, symbol: str, estimated_profit: float) -> float:
        """計算交易數量"""
        
        # 基於預期利潤和風險限制計算合適的交易數量
        max_position_value = self.risk_manager.max_single_position
        
        # 保守估算：使用最大倉位的50%
        target_position_value = min(max_position_value * 0.5, estimated_profit * 20)
        
        # 獲取真實市場價格
        real_price = await self._get_real_market_price(symbol)
        if not real_price:
            logger.warning(f"無法獲取 {symbol} 的真實價格，跳過交易")
            return 0.0
        
        quantity = target_position_value / real_price
        
        # 確保數量合理（最小0.001）
        return max(0.001, quantity)
    
    async def _get_real_market_price(self, symbol: str) -> Optional[float]:
        """獲取真實市場價格"""
        try:
            # 嘗試從任一可用的交易所獲取價格
            for exchange_name, connector in self.exchanges.items():
                if connector and hasattr(connector, 'get_market_price'):
                    try:
                        price = await connector.get_market_price(symbol)
                        if price and price > 0:
                            logger.debug(f"從 {exchange_name} 獲取 {symbol} 價格: ${price:.2f}")
                            return price
                    except Exception as e:
                        logger.debug(f"從 {exchange_name} 獲取價格失敗: {e}")
                        continue
            
            # 如果交易所獲取失敗，嘗試使用外部API
            return await self._get_external_market_price(symbol)
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 市場價格失敗: {e}")
            return None
    
    async def _get_external_market_price(self, symbol: str) -> Optional[float]:
        """從外部API獲取市場價格"""
        try:
            import aiohttp
            
            # 提取基礎貨幣
            base_currency = symbol.split('/')[0] if '/' in symbol else symbol
            
            # CoinGecko ID 映射
            symbol_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'ADA': 'cardano',
                'DOT': 'polkadot',
                'MATIC': 'polygon',
                'AVAX': 'avalanche-2',
                'UNI': 'uniswap',
                'LINK': 'chainlink',
                'LTC': 'litecoin'
            }
            
            gecko_id = symbol_map.get(base_currency)
            if not gecko_id:
                logger.warning(f"未知的貨幣符號: {base_currency}")
                return None
            
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={gecko_id}&vs_currencies=usd"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get(gecko_id, {}).get('usd')
                        if price:
                            logger.info(f"📊 從 CoinGecko 獲取 {base_currency} 價格: ${price:.2f}")
                            return float(price)
                            
        except Exception as e:
            logger.error(f"從外部API獲取價格失敗: {e}")
        
        return None
    
    async def monitor_positions(self):
        """監控倉位"""
        
        if not self.auto_close_enabled:
            return
        
        positions_to_close = []
        
        for position_id, position in self.position_manager.positions.items():
            
            # 獲取當前價格（這裡需要從實際市場數據獲取）
            current_price = await self._get_current_price(position.symbol, position.exchanges[0])
            
            if current_price:
                # 更新倉位價格
                self.position_manager.update_position_price(position_id, current_price)
                
                # 檢查是否需要平倉
                should_close, reason = self.risk_manager.should_close_position(position, current_price)
                
                if should_close:
                    positions_to_close.append((position_id, reason))
        
        # 執行平倉
        for position_id, reason in positions_to_close:
            await self._close_position(position_id, reason)
    
    async def _get_current_price(self, symbol: str, exchange: str) -> Optional[float]:
        """獲取當前價格"""
        try:
            if exchange in self.exchanges:
                connector = self.exchanges[exchange]
                return await connector.get_market_price(symbol)
        except Exception as e:
            logger.error(f"獲取價格失敗: {e}")
        
        return None
    
    async def _close_position(self, position_id: str, reason: str):
        """平倉"""
        
        position = self.position_manager.positions.get(position_id)
        if not position:
            return
        
        logger.info(f"🔄 平倉: {position.symbol} - {reason}")
        
        if self.safe_mode:
            logger.info(f"🔒 安全模式: 記錄平倉信號")
            closed_position = self.position_manager.close_position(position_id, position.current_price)
            if closed_position:
                self.stats['total_pnl'] += closed_position.realized_pnl
                logger.info(f"✅ 平倉信號已記錄，PnL: {closed_position.realized_pnl:.2f}")
        
        else:
            logger.info(f"💰 實盤模式: 執行平倉")
            
            # 創建平倉訂單
            for exchange in position.exchanges:
                
                # 根據倉位類型決定平倉方向
                close_side = OrderSide.SELL if position.position_type == PositionType.LONG else OrderSide.BUY
                
                close_order = await self.order_manager.create_order(
                    symbol=position.symbol,
                    exchange=exchange,
                    side=close_side,
                    order_type=OrderType.MARKET,
                    quantity=position.quantity,
                    metadata={'action': 'close_position', 'position_id': position_id}
                )
                
                if close_order:
                    success = await self.order_manager.submit_order(close_order)
                    if success:
                        logger.info(f"✅ 平倉訂單已提交: {close_order.order_id}")
                    else:
                        logger.error(f"❌ 平倉訂單提交失敗")
            
            # 更新倉位狀態
            closed_position = self.position_manager.close_position(position_id, position.current_price)
            if closed_position:
                self.stats['total_pnl'] += closed_position.realized_pnl
                logger.info(f"✅ 實際平倉完成，PnL: {closed_position.realized_pnl:.2f}")
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """獲取交易摘要"""
        
        runtime = datetime.now() - self.stats['start_time']
        success_rate = (self.stats['successful_trades'] / max(1, self.stats['total_trades'])) * 100
        
        position_summary = self.position_manager.get_position_summary()
        
        return {
            'runtime_hours': runtime.total_seconds() / 3600,
            'total_trades': self.stats['total_trades'],
            'successful_trades': self.stats['successful_trades'],
            'failed_trades': self.stats['failed_trades'],
            'success_rate': success_rate,
            'total_pnl': self.stats['total_pnl'],
            'open_positions': position_summary['total_positions'],
            'unrealized_pnl': position_summary['total_unrealized_pnl'],
            'realized_pnl': position_summary['total_realized_pnl'],
            'trading_enabled': self.trading_enabled,
            'safe_mode': self.safe_mode,
            'auto_close_enabled': self.auto_close_enabled
        }
    
    async def start_monitoring(self):
        """啟動監控循環"""
        logger.info("🔄 啟動自動交易監控...")
        
        while True:
            try:
                # 監控倉位
                await self.monitor_positions()
                
                # 更新風險指標
                self.risk_manager.update_metrics(
                    list(self.position_manager.positions.values()),
                    list(self.order_manager.orders.values())
                )
                
                # 等待下次檢查
                await asyncio.sleep(30)  # 每30秒檢查一次
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(60)  # 錯誤時等待更長時間

# 工具函數
def create_auto_trading_engine(exchanges: Dict[str, Any], config_file: str = None) -> AutoTradingEngine:
    """創建自動交易引擎實例"""
    
    # 默認配置
    default_config = {
        'trading_enabled': False,
        'safe_mode': True,
        'auto_close_enabled': True,
        'risk': {
            'max_daily_loss': 1000.0,
            'max_total_exposure': 10000.0,
            'max_single_position': 2000.0,
            'max_positions': 10,
            'stop_loss_pct': 2.0,
            'take_profit_pct': 5.0
        }
    }
    
    # 加載配置文件
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                default_config.update(file_config)
        except Exception as e:
            logger.warning(f"配置文件加載失敗，使用默認配置: {e}")
    
    return AutoTradingEngine(exchanges, default_config)

# 測試函數
async def test_auto_trading_engine():
    """測試自動交易引擎"""
    
    print("🧪 測試自動交易引擎")
    
    # 創建測試交易所連接
    test_exchanges = {
        'binance': None,  # 這裡應該是實際的連接器
        'bybit': None
    }
    
    # 創建引擎
    engine = create_auto_trading_engine(test_exchanges)
    
    # 測試套利機會
    opportunity = {
        'symbol': 'BTC/USDT:USDT',
        'strategy_type': 'cross_exchange',
        'primary_exchange': 'binance',
        'secondary_exchange': 'bybit',
        'net_profit_8h': 125.50,
        'primary_price': 45000,
        'secondary_price': 45100,
        'confidence_score': 0.95
    }
    
    # 執行套利
    success = await engine.execute_arbitrage_opportunity(opportunity)
    print(f"套利執行結果: {success}")
    
    # 顯示交易摘要
    summary = engine.get_trading_summary()
    print(f"交易摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(test_auto_trading_engine()) 