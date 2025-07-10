#!/usr/bin/env python3
"""
系統整合助手
用於將 Telegram 通知整合到主套利系統中
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from telegram_notifier import TelegramNotifier, NotificationMessage
from config_funding import get_config

logger = logging.getLogger("Integration")

class SystemIntegrationHelper:
    """系統整合助手"""
    
    def __init__(self):
        self.config = get_config()
        self.telegram_notifier = None
        self._init_telegram()
    
    def _init_telegram(self):
        """初始化 Telegram 通知器"""
        try:
            if self.config.system.enable_telegram_alerts:
                self.telegram_notifier = TelegramNotifier()
                logger.info("Telegram 通知器已初始化")
            else:
                logger.info("Telegram 通知已禁用")
        except Exception as e:
            logger.error(f"初始化 Telegram 通知器失敗: {e}")
    
    async def setup_notifications(self):
        """設置通知系統"""
        if self.telegram_notifier:
            await self.telegram_notifier.initialize()
            return True
        return False
    
    async def cleanup_notifications(self):
        """清理通知系統"""
        if self.telegram_notifier:
            await self.telegram_notifier.close()
    
    async def notify_arbitrage_opportunity(self, opportunity_data: Dict[str, Any]) -> bool:
        """發送套利機會通知"""
        if not self.telegram_notifier:
            return False
        
        try:
            return await self.telegram_notifier.notify_arbitrage_opportunity(opportunity_data)
        except Exception as e:
            logger.error(f"發送套利機會通知失敗: {e}")
            return False
    
    async def notify_trade_execution(self, trade_data: Dict[str, Any]) -> bool:
        """發送交易執行通知"""
        if not self.telegram_notifier:
            return False
        
        try:
            return await self.telegram_notifier.notify_trade_execution(trade_data)
        except Exception as e:
            logger.error(f"發送交易執行通知失敗: {e}")
            return False
    
    async def notify_system_status(self, status: str, details: str = "") -> bool:
        """發送系統狀態通知"""
        if not self.telegram_notifier:
            return False
        
        try:
            return await self.telegram_notifier.notify_system_status(status, details)
        except Exception as e:
            logger.error(f"發送系統狀態通知失敗: {e}")
            return False
    
    async def notify_error(self, error_msg: str, details: str = "") -> bool:
        """發送錯誤通知"""
        if not self.telegram_notifier:
            return False
        
        try:
            return await self.telegram_notifier.notify_error(error_msg, details)
        except Exception as e:
            logger.error(f"發送錯誤通知失敗: {e}")
            return False

# 全局整合助手實例
_integration_helper = None

def get_integration_helper() -> SystemIntegrationHelper:
    """獲取整合助手實例"""
    global _integration_helper
    if _integration_helper is None:
        _integration_helper = SystemIntegrationHelper()
    return _integration_helper

async def setup_system_integrations():
    """設置系統整合"""
    helper = get_integration_helper()
    await helper.setup_notifications()
    return helper

async def cleanup_system_integrations():
    """清理系統整合"""
    global _integration_helper
    if _integration_helper:
        await _integration_helper.cleanup_notifications()
        _integration_helper = None 