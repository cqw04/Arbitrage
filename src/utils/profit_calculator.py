#!/usr/bin/env python3
"""
資金費率套利系統 - 利潤計算器
提供詳細的手續費、利潤、風險指標計算
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

from config_funding import get_config

config = get_config()


@dataclass
class TradeCalculation:
    """交易計算結果"""
    symbol: str
    strategy_type: str
    position_size_usdt: float
    
    # 基本費用
    entry_fee: float
    exit_fee: float
    total_fees: float
    
    # 資金費率相關
    funding_rate_diff: float
    funding_periods: int
    funding_revenue: float
    
    # 利潤計算
    gross_profit: float
    net_profit: float
    profit_margin: float
    
    # 風險指標
    max_loss: float
    risk_reward_ratio: float
    break_even_periods: int
    
    # 時間相關
    holding_hours: float
    annualized_return: float


class ProfitCalculator:
    """利潤計算器"""
    
    def __init__(self):
        self.config = config
        
        # 標準資金費率收取週期（小時）
        self.funding_periods = {
            'binance': 8,
            'bybit': 8, 
            'okx': 8,
            'gate': 8,
            'bitget': 8,
            'backpack': 8  # 8小時
        }
        
        # 滑點估計（基於交易對流動性）
        self.slippage_estimates = {
            'BTC/USDT:USDT': 0.0001,  # 0.01%
            'ETH/USDT:USDT': 0.0002,  # 0.02%
            'SOL/USDT:USDT': 0.0005,  # 0.05%
            'default': 0.001          # 0.1% 默認滑點
        }
    
    def calculate_cross_exchange_arbitrage(
        self,
        symbol: str,
        long_exchange: str,
        short_exchange: str,
        long_funding_rate: float,
        short_funding_rate: float,
        position_size_usdt: float,
        holding_hours: float = 8.0
    ) -> TradeCalculation:
        """計算跨交易所套利利潤"""
        
        # 獲取手續費率
        long_fees = self.config.get_commission_rates().get(long_exchange, {'taker': 0.0005})
        short_fees = self.config.get_commission_rates().get(short_exchange, {'taker': 0.0005})
        
        # 計算交易手續費
        long_entry_fee = position_size_usdt * long_fees['taker']
        long_exit_fee = position_size_usdt * long_fees['taker']
        short_entry_fee = position_size_usdt * short_fees['taker']
        short_exit_fee = position_size_usdt * short_fees['taker']
        
        total_fees = long_entry_fee + long_exit_fee + short_entry_fee + short_exit_fee
        
        # 計算滑點成本
        slippage = self.slippage_estimates.get(symbol, self.slippage_estimates['default'])
        slippage_cost = position_size_usdt * slippage * 2  # 開平倉都有滑點
        
        # 計算資金費率差異和收益
        funding_rate_diff = abs(short_funding_rate - long_funding_rate)
        funding_periods = max(1, int(holding_hours / 8))  # 資金費率每8小時收取一次
        
        # 資金費率收益（做多方收取，做空方支付）
        funding_revenue = position_size_usdt * funding_rate_diff * funding_periods
        
        # 計算利潤
        gross_profit = funding_revenue
        net_profit = gross_profit - total_fees - slippage_cost
        profit_margin = (net_profit / position_size_usdt) * 100
        
        # 風險計算
        max_loss = total_fees + slippage_cost + (position_size_usdt * 0.002)  # 2% 價格風險
        risk_reward_ratio = abs(net_profit / max_loss) if max_loss > 0 else 0
        
        # 盈虧平衡計算
        break_even_periods = math.ceil(total_fees / (position_size_usdt * funding_rate_diff)) if funding_rate_diff > 0 else 999
        
        # 年化收益率
        if holding_hours > 0:
            annualized_return = (net_profit / position_size_usdt) * (365 * 24 / holding_hours) * 100
        else:
            annualized_return = 0
        
        return TradeCalculation(
            symbol=symbol,
            strategy_type="跨交易所套利",
            position_size_usdt=position_size_usdt,
            entry_fee=long_entry_fee + short_entry_fee,
            exit_fee=long_exit_fee + short_exit_fee,
            total_fees=total_fees,
            funding_rate_diff=funding_rate_diff,
            funding_periods=funding_periods,
            funding_revenue=funding_revenue,
            gross_profit=gross_profit,
            net_profit=net_profit,
            profit_margin=profit_margin,
            max_loss=max_loss,
            risk_reward_ratio=risk_reward_ratio,
            break_even_periods=break_even_periods,
            holding_hours=holding_hours,
            annualized_return=annualized_return
        )
    
    def calculate_extreme_funding_arbitrage(
        self,
        symbol: str,
        exchange: str,
        funding_rate: float,
        position_size_usdt: float,
        holding_hours: float = 8.0
    ) -> TradeCalculation:
        """計算極端資金費率套利利潤"""
        
        # 獲取手續費率
        exchange_fees = self.config.get_commission_rates().get(exchange, {'taker': 0.0005})
        
        # 計算交易手續費（期貨 + 現貨）
        futures_entry_fee = position_size_usdt * exchange_fees['taker']
        futures_exit_fee = position_size_usdt * exchange_fees['taker'] 
        spot_entry_fee = position_size_usdt * exchange_fees['taker']
        spot_exit_fee = position_size_usdt * exchange_fees['taker']
        
        total_fees = futures_entry_fee + futures_exit_fee + spot_entry_fee + spot_exit_fee
        
        # 計算滑點成本
        slippage = self.slippage_estimates.get(symbol, self.slippage_estimates['default'])
        slippage_cost = position_size_usdt * slippage * 2
        
        # 計算資金費率收益
        funding_periods = max(1, int(holding_hours / 8))
        funding_revenue = position_size_usdt * abs(funding_rate) * funding_periods
        
        # 計算利潤
        gross_profit = funding_revenue
        net_profit = gross_profit - total_fees - slippage_cost
        profit_margin = (net_profit / position_size_usdt) * 100
        
        # 風險計算（現貨期貨價差風險）
        basis_risk = position_size_usdt * 0.001  # 0.1% 基差風險
        max_loss = total_fees + slippage_cost + basis_risk
        risk_reward_ratio = abs(net_profit / max_loss) if max_loss > 0 else 0
        
        # 盈虧平衡計算
        break_even_periods = math.ceil(total_fees / (position_size_usdt * abs(funding_rate))) if funding_rate != 0 else 999
        
        # 年化收益率
        if holding_hours > 0:
            annualized_return = (net_profit / position_size_usdt) * (365 * 24 / holding_hours) * 100
        else:
            annualized_return = 0
        
        return TradeCalculation(
            symbol=symbol,
            strategy_type="極端費率套利",
            position_size_usdt=position_size_usdt,
            entry_fee=futures_entry_fee + spot_entry_fee,
            exit_fee=futures_exit_fee + spot_exit_fee,
            total_fees=total_fees,
            funding_rate_diff=abs(funding_rate),
            funding_periods=funding_periods,
            funding_revenue=funding_revenue,
            gross_profit=gross_profit,
            net_profit=net_profit,
            profit_margin=profit_margin,
            max_loss=max_loss,
            risk_reward_ratio=risk_reward_ratio,
            break_even_periods=break_even_periods,
            holding_hours=holding_hours,
            annualized_return=annualized_return
        )
    
    def calculate_optimal_position_size(
        self,
        available_balance: float,
        funding_rate_diff: float,
        total_fees_pct: float,
        max_risk_pct: float = 2.0
    ) -> float:
        """計算最佳倉位大小"""
        
        # 基於風險管理的最大倉位
        max_risk_amount = available_balance * (max_risk_pct / 100)
        
        # 基於利潤率的建議倉位
        if funding_rate_diff > total_fees_pct:
            profit_ratio = funding_rate_diff / total_fees_pct
            suggested_ratio = min(profit_ratio * 0.1, 0.5)  # 最多50%倉位
            suggested_amount = available_balance * suggested_ratio
        else:
            suggested_amount = 0
        
        # 返回較小值
        return min(max_risk_amount, suggested_amount, self.config.trading.max_single_position)
    
    def analyze_fee_impact(
        self,
        symbol: str,
        exchanges: List[str],
        position_size_usdt: float
    ) -> Dict[str, float]:
        """分析不同交易所的手續費影響"""
        
        fee_analysis = {}
        commission_rates = self.config.get_commission_rates()
        
        for exchange in exchanges:
            fees = commission_rates.get(exchange, {'taker': 0.0005})
            
            # 計算往返交易費用
            round_trip_fee = position_size_usdt * fees['taker'] * 2
            
            # 計算滑點
            slippage = self.slippage_estimates.get(symbol, self.slippage_estimates['default'])
            slippage_cost = position_size_usdt * slippage * 2
            
            total_cost = round_trip_fee + slippage_cost
            cost_percentage = (total_cost / position_size_usdt) * 100
            
            fee_analysis[exchange] = {
                'trading_fee': round_trip_fee,
                'slippage_cost': slippage_cost,
                'total_cost': total_cost,
                'cost_percentage': cost_percentage
            }
        
        return fee_analysis
    
    def calculate_risk_metrics(
        self,
        calculations: List[TradeCalculation],
        portfolio_size: float
    ) -> Dict[str, float]:
        """計算組合風險指標"""
        
        if not calculations:
            return {}
        
        total_exposure = sum(calc.position_size_usdt for calc in calculations)
        total_profit = sum(calc.net_profit for calc in calculations)
        total_fees = sum(calc.total_fees for calc in calculations)
        
        # 夏普比率 (簡化版)
        profits = [calc.net_profit for calc in calculations]
        if len(profits) > 1:
            avg_profit = sum(profits) / len(profits)
            profit_std = (sum((p - avg_profit) ** 2 for p in profits) / len(profits)) ** 0.5
            sharpe_ratio = avg_profit / profit_std if profit_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        max_loss = sum(calc.max_loss for calc in calculations)
        max_drawdown_pct = (max_loss / portfolio_size) * 100 if portfolio_size > 0 else 0
        
        # 利潤因子
        winning_trades = [calc for calc in calculations if calc.net_profit > 0]
        losing_trades = [calc for calc in calculations if calc.net_profit < 0]
        
        total_wins = sum(calc.net_profit for calc in winning_trades)
        total_losses = abs(sum(calc.net_profit for calc in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # 資金使用效率
        capital_efficiency = (total_profit / total_exposure) * 100 if total_exposure > 0 else 0
        
        return {
            'total_exposure': total_exposure,
            'total_profit': total_profit,
            'total_fees': total_fees,
            'profit_margin': (total_profit / total_exposure) * 100 if total_exposure > 0 else 0,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown_pct,
            'profit_factor': profit_factor,
            'capital_efficiency': capital_efficiency,
            'win_rate': len(winning_trades) / len(calculations) * 100,
            'avg_profit_per_trade': total_profit / len(calculations),
            'exposure_ratio': (total_exposure / portfolio_size) * 100 if portfolio_size > 0 else 0
        }
    
    def generate_profit_report(
        self,
        calculation: TradeCalculation
    ) -> str:
        """生成詳細的利潤報告"""
        
        report = f"""
📊 {calculation.strategy_type} - 利潤分析報告
{'='*50}

🎯 基本信息:
   交易對: {calculation.symbol}
   倉位大小: {calculation.position_size_usdt:,.2f} USDT
   持倉時間: {calculation.holding_hours:.1f} 小時
   資金費率週期: {calculation.funding_periods} 次

💰 費用分析:
   開倉手續費: {calculation.entry_fee:.4f} USDT
   平倉手續費: {calculation.exit_fee:.4f} USDT
   總手續費: {calculation.total_fees:.4f} USDT
   手續費率: {(calculation.total_fees/calculation.position_size_usdt)*100:.4f}%

📈 收益分析:
   資金費率差異: {calculation.funding_rate_diff*100:.4f}%
   資金費率收益: {calculation.funding_revenue:.4f} USDT
   毛利潤: {calculation.gross_profit:.4f} USDT
   淨利潤: {calculation.net_profit:.4f} USDT
   利潤率: {calculation.profit_margin:.4f}%
   年化收益率: {calculation.annualized_return:.2f}%

⚠️  風險分析:
   最大可能虧損: {calculation.max_loss:.4f} USDT
   風險回報比: {calculation.risk_reward_ratio:.2f}
   盈虧平衡週期: {calculation.break_even_periods} 次

📊 投資建議:
"""
        
        # 投資建議
        if calculation.profit_margin > 1.0:
            report += "   ✅ 建議執行 - 利潤率良好\n"
        elif calculation.profit_margin > 0.5:
            report += "   ⚠️  謹慎考慮 - 利潤率一般\n"
        else:
            report += "   ❌ 不建議執行 - 利潤率偏低\n"
        
        if calculation.risk_reward_ratio > 3.0:
            report += "   ✅ 風險可控 - 風險回報比優秀\n"
        elif calculation.risk_reward_ratio > 1.5:
            report += "   ⚠️  適中風險 - 風險回報比一般\n"
        else:
            report += "   ❌ 風險偏高 - 風險回報比不佳\n"
        
        return report
    
    def compare_strategies(
        self,
        calculations: List[TradeCalculation]
    ) -> str:
        """比較不同策略的表現"""
        
        if not calculations:
            return "❌ 沒有可比較的策略"
        
        # 按淨利潤排序
        sorted_calcs = sorted(calculations, key=lambda x: x.net_profit, reverse=True)
        
        report = "\n📊 策略比較分析\n"
        report += "="*60 + "\n"
        report += f"{'排名':<4} {'策略':<15} {'交易對':<15} {'利潤率':<10} {'風險比':<8}\n"
        report += "-"*60 + "\n"
        
        for i, calc in enumerate(sorted_calcs, 1):
            report += f"{i:<4} {calc.strategy_type:<15} {calc.symbol:<15} "
            report += f"{calc.profit_margin:<10.2f}% {calc.risk_reward_ratio:<8.2f}\n"
        
        # 最佳策略推薦
        best = sorted_calcs[0]
        report += f"\n🏆 推薦策略: {best.strategy_type} - {best.symbol}\n"
        report += f"   預期利潤: {best.net_profit:.4f} USDT\n"
        report += f"   利潤率: {best.profit_margin:.2f}%\n"
        report += f"   風險等級: {'低' if best.risk_reward_ratio > 3 else '中' if best.risk_reward_ratio > 1.5 else '高'}\n"
        
        return report


# 實用函數
def quick_profit_estimate(
    funding_rate_diff: float,
    position_size: float,
    fee_rate: float = 0.001
) -> Dict[str, float]:
    """快速利潤估算"""
    
    gross_profit = position_size * funding_rate_diff
    total_fees = position_size * fee_rate
    net_profit = gross_profit - total_fees
    profit_margin = (net_profit / position_size) * 100
    
    return {
        'gross_profit': gross_profit,
        'total_fees': total_fees,
        'net_profit': net_profit,
        'profit_margin': profit_margin
    }


def calculate_minimum_spread(
    position_size: float,
    exchange1_fee: float,
    exchange2_fee: float,
    target_profit: float = 10.0
) -> float:
    """計算達到目標利潤所需的最小價差"""
    
    total_fees = position_size * (exchange1_fee + exchange2_fee)
    required_revenue = total_fees + target_profit
    min_spread = required_revenue / position_size
    
    return min_spread


if __name__ == "__main__":
    # 測試計算器
    calc = ProfitCalculator()
    
    # 測試跨交易所套利
    result = calc.calculate_cross_exchange_arbitrage(
        symbol="BTC/USDT:USDT",
        long_exchange="binance",
        short_exchange="bybit", 
        long_funding_rate=0.001,
        short_funding_rate=0.015,
        position_size_usdt=1000,
        holding_hours=8
    )
    
    print(calc.generate_profit_report(result)) 