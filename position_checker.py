#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
倉位檢查工具 - 完整的合約、期權、總倉位狀態監控
支援所有主要交易所的倉位查詢和分析
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PositionInfo:
    """倉位信息數據類"""
    exchange: str
    symbol: str
    position_type: str  # 'futures', 'options', 'spot'
    side: str  # 'long', 'short', 'buy', 'sell'
    size: float
    value: float  # 倉位價值 (USDT)
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: str
    margin: float
    created_at: datetime

@dataclass
class PositionSummary:
    """倉位摘要數據類"""
    total_positions: int
    futures_positions: int
    options_positions: int
    total_value: float
    total_unrealized_pnl: float
    total_margin_used: float
    highest_leverage: str
    profitable_count: int
    losing_count: int
    largest_position_value: float

class PositionChecker:
    """倉位檢查工具類"""
    
    def __init__(self, available_exchanges: List[str] = None):
        self.available_exchanges = available_exchanges or []
        self.positions: List[PositionInfo] = []
        self.system = None
        
    async def initialize(self):
        """初始化系統連接"""
        try:
            from funding_rate_arbitrage_system import FundingArbitrageSystem
            self.system = FundingArbitrageSystem(available_exchanges=self.available_exchanges)
            logger.info("✅ 倉位檢查器初始化成功")
        except Exception as e:
            logger.error(f"❌ 倉位檢查器初始化失敗: {e}")
            raise
    
    async def check_all_positions(self) -> Dict[str, Any]:
        """檢查所有交易所的倉位狀態"""
        if not self.system:
            await self.initialize()
        
        print("\n🔍 正在檢查所有交易所倉位狀態...")
        print("=" * 70)
        
        all_positions = []
        total_value = 0.0
        total_unrealized_pnl = 0.0
        exchange_summaries = {}
        
        try:
            for exchange_name in self.available_exchanges:
                try:
                    connector = self.system.monitor.exchanges.get(exchange_name)
                    if not connector:
                        continue
                    
                    print(f"\n📊 {exchange_name.upper()} 倉位檢查中...")
                    
                    # 確保連接
                    await connector.connect()
                    
                    # 獲取餘額信息（包含倉位）
                    balance_data = await connector.get_account_balance()
                    
                    if balance_data.get('status') != 'success':
                        print(f"   ❌ {exchange_name.upper()} 查詢失敗: {balance_data.get('message', '未知錯誤')}")
                        continue
                    
                    # 解析倉位信息
                    positions, summary = self._parse_positions(exchange_name, balance_data)
                    all_positions.extend(positions)
                    
                    exchange_summaries[exchange_name] = summary
                    total_value += summary['total_value']
                    total_unrealized_pnl += summary['total_unrealized_pnl']
                    
                    # 顯示交易所倉位摘要
                    self._display_exchange_summary(exchange_name, summary, positions)
                    
                except Exception as e:
                    print(f"   ❌ {exchange_name.upper()} 倉位檢查失敗: {e}")
                    logger.error(f"檢查 {exchange_name} 倉位失敗: {e}")
            
            # 顯示總體摘要
            overall_summary = self._calculate_overall_summary(all_positions, total_value, total_unrealized_pnl, exchange_summaries)
            self._display_overall_summary(overall_summary)
            
            # 返回詳細結果
            return {
                'positions': [self._position_to_dict(pos) for pos in all_positions],
                'exchange_summaries': exchange_summaries,
                'overall_summary': overall_summary,
                'timestamp': datetime.now().isoformat()
            }
        
        finally:
            # 確保清理所有連接
            await self._cleanup_connections()
    
    async def _cleanup_connections(self):
        """清理所有交易所連接"""
        if self.system and self.system.monitor:
            for exchange_name in self.available_exchanges:
                try:
                    connector = self.system.monitor.exchanges.get(exchange_name)
                    if connector:
                        await connector.disconnect()
                        logger.debug(f"✅ {exchange_name.upper()} 連接已清理")
                except Exception as e:
                    logger.debug(f"清理 {exchange_name} 連接時出錯: {e}")
    
    def _parse_positions(self, exchange_name: str, balance_data: Dict) -> tuple:
        """解析倉位數據"""
        positions = []
        futures_count = 0
        options_count = 0
        total_value = 0.0
        total_unrealized_pnl = 0.0
        total_margin = 0.0
        
        # 獲取帳戶總保證金餘額（用於計算保證金率）
        account_margin_balance = balance_data.get('margin_balance', 0.0)
        account_total_balance = balance_data.get('futures_balance', 0.0)
        
        # 解析期貨倉位
        for key, value in balance_data.items():
            if key.startswith('POSITION_') and isinstance(value, dict):
                symbol = key.replace('POSITION_', '')
                position = PositionInfo(
                    exchange=exchange_name,
                    symbol=symbol,
                    position_type='futures',
                    side=value.get('side', 'unknown'),
                    size=abs(float(value.get('size', 0))),
                    value=float(value.get('value', 0)),
                    entry_price=float(value.get('entry_price', 0)),
                    mark_price=float(value.get('mark_price', 0)),
                    unrealized_pnl=float(value.get('unrealized_pnl', 0)),
                    leverage=str(value.get('leverage', '1')),
                    margin=0.0,  # 計算保證金
                    created_at=datetime.now()
                )
                
                # 計算保證金
                if position.leverage and position.leverage != '1' and position.leverage != '':
                    try:
                        lev = float(position.leverage)
                        position.margin = position.value / lev if lev > 0 else position.value
                    except:
                        position.margin = position.value
                else:
                    position.margin = position.value
                
                positions.append(position)
                futures_count += 1
                total_value += position.value
                total_unrealized_pnl += position.unrealized_pnl
                total_margin += position.margin
        
        # 解析期權倉位
        for key, value in balance_data.items():
            if key.startswith('OPTIONS_POSITION_') and isinstance(value, dict):
                symbol = key.replace('OPTIONS_POSITION_', '')
                position = PositionInfo(
                    exchange=exchange_name,
                    symbol=symbol,
                    position_type='options',
                    side=value.get('side', 'unknown'),
                    size=abs(float(value.get('size', 0))),
                    value=float(value.get('value', 0)),
                    entry_price=float(value.get('entry_price', 0)),
                    mark_price=float(value.get('mark_price', 0)),
                    unrealized_pnl=float(value.get('unrealized_pnl', 0)),
                    leverage='1',  # 期權通常不使用槓桿
                    margin=float(value.get('value', 0)),  # 期權保證金等於權利金
                    created_at=datetime.now()
                )
                
                positions.append(position)
                options_count += 1
                total_value += position.value
                total_unrealized_pnl += position.unrealized_pnl
                total_margin += position.margin
        
        # 移除保證金率計算，因為無法從API獲取準確數據
        
        summary = {
            'total_positions': len(positions),
            'futures_positions': futures_count,
            'options_positions': options_count,
            'total_value': total_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_margin_used': total_margin,
            'account_margin_balance': account_margin_balance,
            'account_total_balance': account_total_balance,

            'profitable_count': len([p for p in positions if p.unrealized_pnl > 0]),
            'losing_count': len([p for p in positions if p.unrealized_pnl < 0])
        }
        
        return positions, summary
    
    def _display_exchange_summary(self, exchange_name: str, summary: Dict, positions: List[PositionInfo]):
        """顯示交易所倉位摘要"""
        print(f"   🏛️  {exchange_name.upper()} 倉位摘要:")
        
        if summary['total_positions'] == 0:
            print("      📋 目前無持倉")
            return
        
        print(f"      📊 總倉位: {summary['total_positions']} 個")
        print(f"      📈 期貨倉位: {summary['futures_positions']} 個")
        if summary['options_positions'] > 0:
            print(f"      🎯 期權倉位: {summary['options_positions']} 個")
        print(f"      💰 倉位總價值: {summary['total_value']:.2f} USDT")
        print(f"      💵 已用保證金: {summary['total_margin_used']:.2f} USDT")
        
        # 顯示保證金餘額
        margin_balance = summary.get('account_margin_balance', 0)
        if margin_balance > 0:
            print(f"      💰 保證金餘額: {margin_balance:.2f} USDT")
        
        pnl = summary['total_unrealized_pnl']
        pnl_symbol = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
        print(f"      {pnl_symbol} 未實現盈虧: {pnl:+.2f} USDT")
        
        print(f"      🟢 盈利倉位: {summary['profitable_count']} 個")
        print(f"      🔴 虧損倉位: {summary['losing_count']} 個")
        
        # 顯示前5個重要倉位
        if positions:
            print(f"\n   📋 主要倉位詳情:")
            sorted_positions = sorted(positions, key=lambda x: x.value, reverse=True)
            for i, pos in enumerate(sorted_positions[:5], 1):
                side_symbol = "🟢" if pos.side.lower() in ['long', 'buy'] else "🔴" if pos.side.lower() in ['short', 'sell'] else "⚪"
                type_symbol = "📈" if pos.position_type == 'futures' else "🎯"
                pnl_symbol = "📈" if pos.unrealized_pnl > 0 else "📉" if pos.unrealized_pnl < 0 else "➖"
                
                print(f"      {i}. {type_symbol} {side_symbol} {pos.symbol}")
                print(f"         └─ 大小: {pos.size:.4f} | 價值: ${pos.value:.2f} | {pnl_symbol} {pos.unrealized_pnl:+.2f}")
                if pos.leverage != '1' and pos.leverage != '':
                    print(f"         └─ 槓桿: {pos.leverage}x | 保證金: ${pos.margin:.2f}")
    
    def _calculate_overall_summary(self, all_positions: List[PositionInfo], total_value: float, total_unrealized_pnl: float, exchange_summaries: Dict = None) -> Dict:
        """計算總體摘要"""
        if not all_positions:
            return {
                'total_positions': 0,
                'futures_positions': 0,
                'options_positions': 0,
                'total_value': 0.0,
                'total_unrealized_pnl': 0.0,
                'total_margin_used': 0.0,
                'profitable_count': 0,
                'losing_count': 0,
                'largest_position_value': 0.0,
                'highest_leverage': '1',
                'exchanges_with_positions': 0
            }
        
        futures_count = len([p for p in all_positions if p.position_type == 'futures'])
        options_count = len([p for p in all_positions if p.position_type == 'options'])
        profitable_count = len([p for p in all_positions if p.unrealized_pnl > 0])
        losing_count = len([p for p in all_positions if p.unrealized_pnl < 0])
        
        largest_position = max(all_positions, key=lambda x: x.value)
        # 找出最高槓桿
        highest_leverage_obj = None
        max_leverage_value = 1.0
        
        for pos in all_positions:
            try:
                # 嘗試解析槓桿值
                leverage_str = str(pos.leverage).strip()
                if leverage_str and leverage_str != '' and leverage_str != '1':
                    # 處理可能的格式：'10.0', '10', '10x' 等
                    if leverage_str.endswith('x'):
                        leverage_str = leverage_str[:-1]
                    leverage_val = float(leverage_str)
                    if leverage_val > max_leverage_value:
                        max_leverage_value = leverage_val
                        highest_leverage_obj = pos
            except (ValueError, AttributeError):
                continue
        
        if highest_leverage_obj is None:
            # 如果沒有找到有效槓桿，使用第一個倉位
            highest_leverage_obj = all_positions[0] if all_positions else None
        
        exchanges_with_positions = len(set(p.exchange for p in all_positions))
        total_margin_used = sum(p.margin for p in all_positions)
        
        # 計算總保證金餘額
        total_account_margin = 0.0
        
        if exchange_summaries:
            for exchange, summary in exchange_summaries.items():
                total_account_margin += summary.get('account_margin_balance', 0)
        
        return {
            'total_positions': len(all_positions),
            'futures_positions': futures_count,
            'options_positions': options_count,
            'total_value': total_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_margin_used': total_margin_used,
            'total_account_margin': total_account_margin,
            'profitable_count': profitable_count,
            'losing_count': losing_count,
            'largest_position_value': largest_position.value,
            'largest_position_symbol': largest_position.symbol,
            'largest_position_exchange': largest_position.exchange,
            'highest_leverage': str(max_leverage_value) if max_leverage_value > 1 else '1',
            'highest_leverage_symbol': highest_leverage_obj.symbol if highest_leverage_obj else '',
            'exchanges_with_positions': exchanges_with_positions
        }
    
    def _display_overall_summary(self, summary: Dict):
        """顯示總體摘要"""
        print(f"\n{'='*70}")
        print("🎯 全部交易所倉位總摘要")
        print(f"{'='*70}")
        
        if summary['total_positions'] == 0:
            print("📋 目前所有交易所均無持倉")
            return
        
        print(f"📊 總計倉位數量: {summary['total_positions']} 個")
        print(f"   ├─ 📈 期貨倉位: {summary['futures_positions']} 個")
        print(f"   └─ 🎯 期權倉位: {summary['options_positions']} 個")
        
        print(f"\n💰 財務狀況:")
        print(f"   ├─ 倉位總價值: {summary['total_value']:.2f} USDT")
        print(f"   ├─ 已用保證金: {summary['total_margin_used']:.2f} USDT")
        
        # 顯示總保證金餘額
        total_margin_balance = summary.get('total_account_margin', 0)
        if total_margin_balance > 0:
            print(f"   ├─ 💰 總保證金餘額: {total_margin_balance:.2f} USDT")
        
        pnl = summary['total_unrealized_pnl']
        pnl_symbol = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
        pnl_percentage = (pnl / summary['total_margin_used'] * 100) if summary['total_margin_used'] > 0 else 0
        print(f"   └─ {pnl_symbol} 未實現盈虧: {pnl:+.2f} USDT ({pnl_percentage:+.2f}%)")
        
        print(f"\n📈 盈虧分布:")
        print(f"   ├─ 🟢 盈利倉位: {summary['profitable_count']} 個")
        print(f"   └─ 🔴 虧損倉位: {summary['losing_count']} 個")
        
        if summary.get('largest_position_value', 0) > 0:
            print(f"\n🏆 重要統計:")
            print(f"   ├─ 最大倉位: {summary['largest_position_symbol']} @ {summary['largest_position_exchange'].upper()}")
            print(f"   │   └─ 價值: {summary['largest_position_value']:.2f} USDT")
            print(f"   ├─ 最高槓桿: {summary['highest_leverage']}x ({summary['highest_leverage_symbol']})")
            print(f"   └─ 涉及交易所: {summary['exchanges_with_positions']} 個")
        
        # 風險評估
        self._display_risk_assessment(summary)
    
    def _display_risk_assessment(self, summary: Dict):
        """顯示風險評估"""
        print(f"\n⚠️ 風險評估:")
        
        # 移除保證金率風險評估，因為無法從API獲取準確數據
        
        
        # 集中度風險
        if summary.get('largest_position_value', 0) > summary['total_value'] * 0.5:
            print(f"   🔴 倉位集中風險: 單一倉位占比過高 ({summary['largest_position_value']/summary['total_value']*100:.1f}%)")
        elif summary.get('largest_position_value', 0) > summary['total_value'] * 0.3:
            print(f"   🟡 倉位集中度偏高: 單一倉位占比 {summary['largest_position_value']/summary['total_value']*100:.1f}%")
        else:
            print(f"   🟢 倉位分散度良好")
        
        # 盈虧比風險
        total_positions = summary['total_positions']
        if total_positions > 0:
            profitable_ratio = summary['profitable_count'] / total_positions
            if profitable_ratio < 0.3:
                print(f"   🔴 盈虧比警告: 僅 {profitable_ratio*100:.1f}% 倉位盈利")
            elif profitable_ratio < 0.5:
                print(f"   🟡 盈虧比一般: {profitable_ratio*100:.1f}% 倉位盈利")
            else:
                print(f"   🟢 盈虧比良好: {profitable_ratio*100:.1f}% 倉位盈利")
    
    def _position_to_dict(self, position: PositionInfo) -> Dict:
        """將倉位對象轉換為字典"""
        return {
            'exchange': position.exchange,
            'symbol': position.symbol,
            'position_type': position.position_type,
            'side': position.side,
            'size': position.size,
            'value': position.value,
            'entry_price': position.entry_price,
            'mark_price': position.mark_price,
            'unrealized_pnl': position.unrealized_pnl,
            'leverage': position.leverage,
            'margin': position.margin,
            'created_at': position.created_at.isoformat()
        }

async def main():
    """主函數 - 命令行使用"""
    import sys
    import os
    
    # 檢測可用交易所 - 直接使用 run.py 的邏輯
    try:
        # 嘗試從 run.py 導入函數
        try:
            from run import load_env_config, get_available_exchanges
            
            # 優先嘗試從 .env 文件加載配置
            available_exchanges = load_env_config()
            
            # 如果 .env 文件沒有有效配置，回退到檢查 config.json
            if not available_exchanges:
                available_exchanges = get_available_exchanges()
                
        except ImportError:
            # 如果無法導入 run.py，直接檢查環境變量
            from config_funding import get_config
            import os
            
            config = get_config()
            available_exchanges = []
            
            for exchange_name in config.exchanges.keys():
                api_key = os.getenv(f'{exchange_name.upper()}_API_KEY')
                secret_key = os.getenv(f'{exchange_name.upper()}_SECRET_KEY')
                
                if api_key and secret_key and api_key != f'your_{exchange_name.lower()}_api_key':
                    available_exchanges.append(exchange_name)
        
        if not available_exchanges:
            print("❌ 未檢測到任何已配置的交易所")
            print("💡 請先在 .env 文件中配置交易所 API 密鑰")
            print("💡 或者使用: python run.py --check-positions")
            return
        
        print(f"✅ 檢測到可用交易所: {', '.join([ex.upper() for ex in available_exchanges])}")
        
        # 創建倉位檢查器
        checker = PositionChecker(available_exchanges)
        
        # 執行倉位檢查
        result = await checker.check_all_positions()
        
        # 可選：保存結果到文件
        if len(sys.argv) > 1 and sys.argv[1] == '--save':
            filename = f"position_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 倉位報告已保存到: {filename}")
        
        print(f"\n✅ 倉位檢查完成")
        
    except Exception as e:
        print(f"❌ 倉位檢查失敗: {e}")
        logger.error(f"倉位檢查失敗: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 