#!/usr/bin/env python3
"""
Telegram 通知模組
用於發送套利機會、系統狀態和交易結果通知
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from config_funding import get_config

logger = logging.getLogger("TelegramNotifier")

@dataclass
class NotificationMessage:
    """通知消息結構"""
    title: str
    content: str
    level: str = "info"  # info, warning, error, success
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.config = get_config()
        self.bot_token = bot_token or self.config.system.telegram_bot_token
        self.chat_id = chat_id or self.config.system.telegram_chat_id
        self.enabled = self.config.system.enable_telegram_alerts
        self.session = None
        
        # 表情符號映射
        self.emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "profit": "💰",
            "trade": "📈",
            "system": "🔧",
            "alert": "🚨"
        }
        
        if self.enabled and (not self.bot_token or not self.chat_id):
            logger.warning("Telegram 通知已啟用但缺少 Bot Token 或 Chat ID")
            self.enabled = False
    
    async def initialize(self):
        """初始化會話"""
        if self.enabled:
            self.session = aiohttp.ClientSession()
            await self.test_connection()
    
    async def close(self):
        """關閉會話"""
        if self.session:
            await self.session.close()
    
    async def test_connection(self) -> bool:
        """測試 Telegram Bot 連接"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_info = data.get('result', {})
                        logger.info(f"Telegram Bot 連接成功: {bot_info.get('username')}")
                        return True
                else:
                    logger.error(f"Telegram Bot 連接失敗: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"測試 Telegram 連接時出錯: {e}")
            return False
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """發送消息到 Telegram"""
        if not self.enabled or not self.session:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"發送 Telegram 消息失敗: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"發送 Telegram 消息時出錯: {e}")
            return False
    
    def format_message(self, notification: NotificationMessage) -> str:
        """格式化通知消息"""
        emoji = self.emoji_map.get(notification.level, "📢")
        timestamp = notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"{emoji} <b>{notification.title}</b>\n\n"
        message += f"{notification.content}\n\n"
        message += f"🕐 時間: {timestamp}"
        
        return message
    
    async def notify_arbitrage_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """發送套利機會通知"""
        if not self.enabled:
            return False
        
        profit = opportunity.get('estimated_profit_8h', 0)
        symbol = opportunity.get('symbol', 'Unknown')
        primary_ex = opportunity.get('primary_exchange', '').upper()
        secondary_ex = opportunity.get('secondary_exchange', '').upper()
        confidence = opportunity.get('confidence_score', 0)
        
        title = f"🎯 套利機會發現 - {symbol}"
        content = f"""
💰 <b>預期8h利潤:</b> {profit:.2f} USDT
📊 <b>交易對:</b> {symbol}
🏪 <b>交易所:</b> {primary_ex} ↔️ {secondary_ex}
🎯 <b>可信度:</b> {confidence:.1%}
📈 <b>策略:</b> {opportunity.get('strategy_type', '跨交易所套利')}

💡 <i>請及時關注市場變化，適時進場！</i>
"""
        
        notification = NotificationMessage(
            title=title,
            content=content,
            level="profit"
        )
        
        return await self.send_message(self.format_message(notification))
    
    async def notify_trade_execution(self, trade_info: Dict[str, Any]) -> bool:
        """發送交易執行通知"""
        if not self.enabled:
            return False
        
        action = trade_info.get('action', 'Unknown')
        symbol = trade_info.get('symbol', 'Unknown')
        exchange = trade_info.get('exchange', '').upper()
        size = trade_info.get('size', 0)
        price = trade_info.get('price', 0)
        
        title = f"📈 交易執行 - {action.upper()}"
        content = f"""
📊 <b>交易對:</b> {symbol}
🏪 <b>交易所:</b> {exchange}
📏 <b>數量:</b> {size}
💲 <b>價格:</b> {price}
⏰ <b>執行時間:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        
        notification = NotificationMessage(
            title=title,
            content=content,
            level="trade"
        )
        
        return await self.send_message(self.format_message(notification))
    
    async def notify_system_status(self, status: str, details: str = "") -> bool:
        """發送系統狀態通知"""
        if not self.enabled:
            return False
        
        title = f"🔧 系統狀態更新"
        content = f"""
📊 <b>狀態:</b> {status}
{f'📝 <b>詳情:</b> {details}' if details else ''}
"""
        
        notification = NotificationMessage(
            title=title,
            content=content,
            level="system"
        )
        
        return await self.send_message(self.format_message(notification))
    
    async def notify_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """發送每日摘要通知"""
        if not self.enabled:
            return False
        
        title = "📊 每日交易摘要"
        content = f"""
💰 <b>總利潤:</b> {summary.get('total_profit', 0):.2f} USDT
📈 <b>成功交易:</b> {summary.get('successful_trades', 0)}
📉 <b>失敗交易:</b> {summary.get('failed_trades', 0)}
🎯 <b>成功率:</b> {summary.get('success_rate', 0):.1%}
🔍 <b>發現機會:</b> {summary.get('opportunities_found', 0)}
📊 <b>活躍倉位:</b> {summary.get('active_positions', 0)}

{'🎉 <i>今日表現優異！</i>' if summary.get('total_profit', 0) > 0 else '⚠️ <i>注意風險控制</i>'}
"""
        
        notification = NotificationMessage(
            title=title,
            content=content,
            level="success" if summary.get('total_profit', 0) > 0 else "warning"
        )
        
        return await self.send_message(self.format_message(notification))
    
    async def notify_error(self, error_msg: str, details: str = "") -> bool:
        """發送錯誤通知"""
        if not self.enabled:
            return False
        
        title = "❌ 系統錯誤"
        content = f"""
🚨 <b>錯誤信息:</b> {error_msg}
{f'📝 <b>詳細信息:</b> {details}' if details else ''}
⏰ <b>發生時間:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 <i>請檢查系統狀態並及時處理</i>
"""
        
        notification = NotificationMessage(
            title=title,
            content=content,
            level="error"
        )
        
        return await self.send_message(self.format_message(notification))
    
    async def notify_position_update(self, position_info: Dict[str, Any]) -> bool:
        """發送倉位更新通知"""
        if not self.enabled:
            return False
        
        action = position_info.get('action', 'Unknown')
        symbol = position_info.get('symbol', 'Unknown')
        profit = position_info.get('profit', 0)
        
        title = f"📊 倉位更新 - {action.upper()}"
        content = f"""
📈 <b>交易對:</b> {symbol}
💰 <b>盈虧:</b> {profit:+.2f} USDT
🎯 <b>操作:</b> {action}
⏰ <b>時間:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        
        notification = NotificationMessage(
            title=title,
            content=content,
            level="success" if profit > 0 else "warning"
        )
        
        return await self.send_message(self.format_message(notification))

# 全局通知器實例
_notifier = None

def get_notifier() -> TelegramNotifier:
    """獲取全局通知器實例"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier

async def initialize_notifier():
    """初始化通知器"""
    notifier = get_notifier()
    await notifier.initialize()
    return notifier

# 便捷函數
async def notify_opportunity(opportunity: Dict[str, Any]) -> bool:
    """發送套利機會通知（便捷函數）"""
    notifier = get_notifier()
    return await notifier.notify_arbitrage_opportunity(opportunity)

async def notify_trade(trade_info: Dict[str, Any]) -> bool:
    """發送交易通知（便捷函數）"""
    notifier = get_notifier()
    return await notifier.notify_trade_execution(trade_info)

async def notify_error(error_msg: str, details: str = "") -> bool:
    """發送錯誤通知（便捷函數）"""
    notifier = get_notifier()
    return await notifier.notify_error(error_msg, details)

if __name__ == "__main__":
    # 測試通知功能
    async def test_notifications():
        notifier = TelegramNotifier()
        await notifier.initialize()
        
        # 測試系統狀態通知
        await notifier.notify_system_status("系統啟動", "資金費率套利系統已成功啟動")
        
        # 測試套利機會通知
        test_opportunity = {
            'symbol': 'BTC/USDT:USDT',
            'primary_exchange': 'binance',
            'secondary_exchange': 'bybit',
            'estimated_profit_8h': 125.50,
            'confidence_score': 0.85,
            'strategy_type': '跨交易所套利'
        }
        await notifier.notify_arbitrage_opportunity(test_opportunity)
        
        await notifier.close()
    
    asyncio.run(test_notifications()) 