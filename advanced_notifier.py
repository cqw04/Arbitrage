#!/usr/bin/env python3
"""
高級通知系統 - 支援 WebSocket、郵件、自定義警報
整合多種通知渠道，提供全面的系統監控和警報功能
"""

import asyncio
import smtplib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import aiosmtplib
import websockets
from abc import ABC, abstractmethod

logger = logging.getLogger("AdvancedNotifier")

class NotificationType(Enum):
    """通知類型"""
    SYSTEM_STATUS = "system_status"
    ARBITRAGE_OPPORTUNITY = "arbitrage_opportunity"
    TRADE_EXECUTION = "trade_execution"
    BALANCE_CHANGE = "balance_change"
    RISK_ALERT = "risk_alert"
    ERROR_ALERT = "error_alert"
    PRICE_ALERT = "price_alert"
    CONNECTION_STATUS = "connection_status"
    PERFORMANCE_METRIC = "performance_metric"

class NotificationPriority(Enum):
    """通知優先級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class NotificationRule:
    """通知規則"""
    name: str
    notification_type: NotificationType
    condition: Callable[[Dict], bool]  # 條件函數
    priority: NotificationPriority
    channels: List[str]  # 通知渠道 ['websocket', 'email', 'telegram']
    cooldown_minutes: int = 5  # 冷卻時間，防止重複通知
    enabled: bool = True
    last_triggered: Optional[datetime] = None

@dataclass
class NotificationMessage:
    """通知消息"""
    message_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    content: str
    data: Dict[str, Any]
    timestamp: datetime
    channels: List[str]
    
    def to_dict(self):
        return {
            'message_id': self.message_id,
            'type': self.notification_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'content': self.content,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'channels': self.channels
        }

class NotificationChannel(ABC):
    """通知渠道基類"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.last_error = None
    
    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """發送通知"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """測試連接"""
        pass

class WebSocketNotificationChannel(NotificationChannel):
    """WebSocket 通知渠道"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("websocket", config)
        self.connections = set()
        self.server = None
        self.port = config.get('port', 8765)
        
    async def start_server(self):
        """啟動 WebSocket 服務器"""
        try:
            async def handle_client(websocket, path):
                self.connections.add(websocket)
                logger.info(f"新的 WebSocket 客戶端連接: {websocket.remote_address}")
                try:
                    await websocket.wait_closed()
                finally:
                    self.connections.discard(websocket)
                    logger.info(f"WebSocket 客戶端斷開: {websocket.remote_address}")
            
            self.server = await websockets.serve(handle_client, "localhost", self.port)
            logger.info(f"✅ WebSocket 通知服務器已啟動: ws://localhost:{self.port}")
            
        except Exception as e:
            logger.error(f"❌ WebSocket 服務器啟動失敗: {e}")
    
    async def send(self, message: NotificationMessage) -> bool:
        """發送 WebSocket 通知"""
        if not self.enabled or not self.connections:
            return False
        
        try:
            message_data = json.dumps(message.to_dict(), ensure_ascii=False)
            disconnected = set()
            
            for connection in self.connections:
                try:
                    await connection.send(message_data)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(connection)
                except Exception as e:
                    logger.error(f"WebSocket 發送失敗: {e}")
                    disconnected.add(connection)
            
            # 清理斷開的連接
            self.connections -= disconnected
            
            successful_sends = len(self.connections) - len(disconnected)
            logger.info(f"📡 WebSocket 通知已發送到 {successful_sends} 個客戶端")
            return successful_sends > 0
            
        except Exception as e:
            logger.error(f"WebSocket 通知發送失敗: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """測試 WebSocket 服務器狀態"""
        return self.server is not None and not self.server.is_serving()
    
    async def stop_server(self):
        """停止 WebSocket 服務器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("✅ WebSocket 服務器已停止")

class EmailNotificationChannel(NotificationChannel):
    """郵件通知渠道"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("email", config)
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])
        self.use_tls = config.get('use_tls', True)
    
    async def send(self, message: NotificationMessage) -> bool:
        """發送郵件通知"""
        if not self.enabled or not self.recipients:
            return False
        
        try:
            # 創建郵件
            msg = MimeMultipart('alternative')
            msg['Subject'] = f"[{message.priority.value.upper()}] {message.title}"
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            
            # 創建 HTML 內容
            html_content = self._create_html_content(message)
            text_content = self._create_text_content(message)
            
            text_part = MimeText(text_content, 'plain', 'utf-8')
            html_part = MimeText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # 發送郵件
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls
            )
            
            logger.info(f"✅ 郵件通知已發送到 {len(self.recipients)} 個收件人")
            return True
            
        except Exception as e:
            logger.error(f"❌ 郵件發送失敗: {e}")
            self.last_error = str(e)
            return False
    
    def _create_html_content(self, message: NotificationMessage) -> str:
        """創建 HTML 郵件內容"""
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.MEDIUM: "#ffc107", 
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.CRITICAL: "#dc3545"
        }
        
        color = priority_colors.get(message.priority, "#6c757d")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .header {{ background: {color}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 5px; }}
                .data {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid {color}; }}
                .timestamp {{ color: #6c757d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚀 資金費率套利系統通知</h2>
                <p>優先級: {message.priority.value.upper()} | 類型: {message.notification_type.value}</p>
            </div>
            
            <div class="content">
                <h3>{message.title}</h3>
                <p>{message.content}</p>
                
                <div class="timestamp">
                    發送時間: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
            
            <div class="data">
                <h4>詳細信息:</h4>
                <pre>{json.dumps(message.data, indent=2, ensure_ascii=False)}</pre>
            </div>
        </body>
        </html>
        """
        return html
    
    def _create_text_content(self, message: NotificationMessage) -> str:
        """創建純文本郵件內容"""
        content = f"""
🚀 資金費率套利系統通知

標題: {message.title}
優先級: {message.priority.value.upper()}
類型: {message.notification_type.value}
時間: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

內容:
{message.content}

詳細信息:
{json.dumps(message.data, indent=2, ensure_ascii=False)}
        """
        return content.strip()
    
    async def test_connection(self) -> bool:
        """測試郵件服務器連接"""
        try:
            await aiosmtplib.send(
                MimeText("測試連接", 'plain', 'utf-8'),
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                recipients=self.recipients[:1] if self.recipients else [],
                dry_run=True  # 不實際發送
            )
            return True
        except Exception as e:
            logger.error(f"郵件服務器連接測試失敗: {e}")
            return False

class TelegramNotificationChannel(NotificationChannel):
    """Telegram 通知渠道 (繼承現有實現)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("telegram", config)
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
    
    async def send(self, message: NotificationMessage) -> bool:
        """發送 Telegram 通知"""
        # 這裡可以集成現有的 TelegramNotifier
        try:
            from telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            await notifier.initialize()
            
            # 根據消息類型發送不同格式的通知
            if message.notification_type == NotificationType.ARBITRAGE_OPPORTUNITY:
                return await notifier.notify_arbitrage_opportunity(message.data)
            elif message.notification_type == NotificationType.SYSTEM_STATUS:
                return await notifier.notify_system_status(message.title, message.content)
            else:
                return await notifier.send_message(f"*{message.title}*\n\n{message.content}")
            
        except Exception as e:
            logger.error(f"Telegram 通知發送失敗: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """測試 Telegram 連接"""
        try:
            from telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            await notifier.initialize()
            return await notifier.test_connection()
        except Exception as e:
            logger.error(f"Telegram 連接測試失敗: {e}")
            return False

class AdvancedNotificationSystem:
    """高級通知系統"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels = {}
        self.rules = []
        self.message_history = []
        self.max_history = 1000
        
        # 初始化通知渠道
        self._initialize_channels()
        
        # 設置默認規則
        self._setup_default_rules()
    
    def _initialize_channels(self):
        """初始化通知渠道"""
        channel_configs = self.config.get('channels', {})
        
        # WebSocket 渠道
        if 'websocket' in channel_configs:
            self.channels['websocket'] = WebSocketNotificationChannel(
                channel_configs['websocket']
            )
        
        # 郵件渠道
        if 'email' in channel_configs:
            self.channels['email'] = EmailNotificationChannel(
                channel_configs['email']
            )
        
        # Telegram 渠道
        if 'telegram' in channel_configs:
            self.channels['telegram'] = TelegramNotificationChannel(
                channel_configs['telegram']
            )
        
        logger.info(f"✅ 已初始化 {len(self.channels)} 個通知渠道: {list(self.channels.keys())}")
    
    def _setup_default_rules(self):
        """設置默認通知規則"""
        
        # 高價值套利機會
        self.add_rule(NotificationRule(
            name="高價值套利機會",
            notification_type=NotificationType.ARBITRAGE_OPPORTUNITY,
            condition=lambda data: data.get('net_profit_8h', 0) > 50,
            priority=NotificationPriority.HIGH,
            channels=['websocket', 'telegram'],
            cooldown_minutes=1
        ))
        
        # 系統錯誤
        self.add_rule(NotificationRule(
            name="系統錯誤警報",
            notification_type=NotificationType.ERROR_ALERT,
            condition=lambda data: True,  # 所有錯誤都通知
            priority=NotificationPriority.CRITICAL,
            channels=['websocket', 'email', 'telegram'],
            cooldown_minutes=5
        ))
        
        # 風險警報
        self.add_rule(NotificationRule(
            name="風險警報",
            notification_type=NotificationType.RISK_ALERT,
            condition=lambda data: data.get('risk_level') in ['high', 'critical'],
            priority=NotificationPriority.HIGH,
            channels=['websocket', 'telegram'],
            cooldown_minutes=2
        ))
        
        # 連接狀態變化
        self.add_rule(NotificationRule(
            name="交易所連接狀態",
            notification_type=NotificationType.CONNECTION_STATUS,
            condition=lambda data: data.get('status') in ['disconnected', 'error'],
            priority=NotificationPriority.MEDIUM,
            channels=['websocket'],
            cooldown_minutes=5
        ))
        
        # 性能指標異常
        self.add_rule(NotificationRule(
            name="性能指標異常",
            notification_type=NotificationType.PERFORMANCE_METRIC,
            condition=lambda data: (
                data.get('cpu_usage', 0) > 80 or 
                data.get('memory_usage', 0) > 80 or
                data.get('error_rate', 0) > 5
            ),
            priority=NotificationPriority.MEDIUM,
            channels=['websocket', 'email'],
            cooldown_minutes=10
        ))
        
        logger.info(f"✅ 已設置 {len(self.rules)} 條默認通知規則")
    
    def add_rule(self, rule: NotificationRule):
        """添加通知規則"""
        self.rules.append(rule)
        logger.info(f"➕ 添加通知規則: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除通知規則"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"➖ 移除通知規則: {rule_name}")
    
    async def start(self):
        """啟動通知系統"""
        logger.info("🚀 啟動高級通知系統...")
        
        # 啟動 WebSocket 服務器
        if 'websocket' in self.channels:
            await self.channels['websocket'].start_server()
        
        # 測試所有渠道連接
        await self.test_all_channels()
        
        logger.info("✅ 高級通知系統已啟動")
    
    async def stop(self):
        """停止通知系統"""
        logger.info("⏹️ 停止高級通知系統...")
        
        # 停止 WebSocket 服務器
        if 'websocket' in self.channels:
            await self.channels['websocket'].stop_server()
        
        logger.info("✅ 高級通知系統已停止")
    
    async def notify(self, notification_type: NotificationType, title: str, 
                    content: str, data: Dict[str, Any] = None, 
                    priority: NotificationPriority = NotificationPriority.MEDIUM,
                    force_channels: List[str] = None):
        """發送通知"""
        
        data = data or {}
        
        # 檢查匹配的規則
        matching_rules = []
        for rule in self.rules:
            if (rule.enabled and 
                rule.notification_type == notification_type and
                rule.condition(data)):
                
                # 檢查冷卻時間
                if (rule.last_triggered is None or 
                    datetime.now() - rule.last_triggered > timedelta(minutes=rule.cooldown_minutes)):
                    matching_rules.append(rule)
                    rule.last_triggered = datetime.now()
        
        if not matching_rules and not force_channels:
            logger.debug(f"無匹配規則，跳過通知: {title}")
            return
        
        # 確定通知渠道
        channels_to_use = force_channels or []
        for rule in matching_rules:
            channels_to_use.extend(rule.channels)
            # 使用最高優先級
            if rule.priority.value > priority.value:
                priority = rule.priority
        
        channels_to_use = list(set(channels_to_use))  # 去重
        
        # 創建通知消息
        message = NotificationMessage(
            message_id=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{notification_type.value}",
            notification_type=notification_type,
            priority=priority,
            title=title,
            content=content,
            data=data,
            timestamp=datetime.now(),
            channels=channels_to_use
        )
        
        # 發送到各個渠道
        success_count = 0
        for channel_name in channels_to_use:
            if channel_name in self.channels:
                try:
                    success = await self.channels[channel_name].send(message)
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"渠道 {channel_name} 發送失敗: {e}")
        
        # 記錄到歷史
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        logger.info(f"📢 通知已發送 (成功: {success_count}/{len(channels_to_use)}): {title}")
    
    async def test_all_channels(self):
        """測試所有通知渠道"""
        logger.info("🧪 測試所有通知渠道...")
        
        for name, channel in self.channels.items():
            try:
                success = await channel.test_connection()
                status = "✅ 正常" if success else "❌ 失敗"
                logger.info(f"   {name}: {status}")
                
                # 發送測試消息
                if success:
                    await channel.send(NotificationMessage(
                        message_id="test_" + name,
                        notification_type=NotificationType.SYSTEM_STATUS,
                        priority=NotificationPriority.LOW,
                        title="通知渠道測試",
                        content=f"{name} 渠道測試成功",
                        data={'channel': name, 'test': True},
                        timestamp=datetime.now(),
                        channels=[name]
                    ))
                    
            except Exception as e:
                logger.error(f"   {name}: ❌ 測試失敗 - {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取通知統計信息"""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # 統計最近的通知
        recent_hour = [m for m in self.message_history if m.timestamp >= last_hour]
        recent_day = [m for m in self.message_history if m.timestamp >= last_day]
        
        # 按類型統計
        type_stats = {}
        for message in recent_day:
            msg_type = message.notification_type.value
            type_stats[msg_type] = type_stats.get(msg_type, 0) + 1
        
        # 按優先級統計
        priority_stats = {}
        for message in recent_day:
            priority = message.priority.value
            priority_stats[priority] = priority_stats.get(priority, 0) + 1
        
        return {
            'total_messages': len(self.message_history),
            'last_hour_count': len(recent_hour),
            'last_day_count': len(recent_day),
            'by_type': type_stats,
            'by_priority': priority_stats,
            'active_channels': len([c for c in self.channels.values() if c.enabled]),
            'active_rules': len([r for r in self.rules if r.enabled])
        }

# 使用示例和工具函數
def create_advanced_notifier(config_file: str = None) -> AdvancedNotificationSystem:
    """創建高級通知系統實例"""
    
    # 默認配置
    default_config = {
        'channels': {
            'websocket': {
                'enabled': True,
                'port': 8765
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'recipients': [],
                'use_tls': True
            },
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_id': ''
            }
        }
    }
    
    # 加載配置文件（如果提供）
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                # 合併配置
                for key, value in file_config.items():
                    if key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
        except Exception as e:
            logger.warning(f"配置文件加載失敗，使用默認配置: {e}")
    
    return AdvancedNotificationSystem(default_config)

# 便捷通知函數
async def quick_notify(notifier: AdvancedNotificationSystem, 
                      message_type: str, title: str, content: str, **kwargs):
    """快速發送通知的便捷函數"""
    type_mapping = {
        'opportunity': NotificationType.ARBITRAGE_OPPORTUNITY,
        'error': NotificationType.ERROR_ALERT,
        'system': NotificationType.SYSTEM_STATUS,
        'trade': NotificationType.TRADE_EXECUTION,
        'balance': NotificationType.BALANCE_CHANGE,
        'risk': NotificationType.RISK_ALERT,
        'price': NotificationType.PRICE_ALERT,
        'connection': NotificationType.CONNECTION_STATUS,
        'performance': NotificationType.PERFORMANCE_METRIC
    }
    
    notification_type = type_mapping.get(message_type, NotificationType.SYSTEM_STATUS)
    await notifier.notify(notification_type, title, content, **kwargs)

# 測試函數
async def test_advanced_notifier():
    """測試高級通知系統"""
    
    print("🧪 測試高級通知系統")
    
    # 創建通知系統
    notifier = create_advanced_notifier()
    
    # 啟動系統
    await notifier.start()
    
    # 發送測試通知
    await notifier.notify(
        NotificationType.ARBITRAGE_OPPORTUNITY,
        "發現高價值套利機會",
        "BTC/USDT 跨交易所套利，預期8小時利潤: 125.50 USDT",
        {
            'symbol': 'BTC/USDT:USDT',
            'primary_exchange': 'binance',
            'secondary_exchange': 'bybit',
            'net_profit_8h': 125.50,
            'confidence_score': 0.95,
            'strategy_type': '跨交易所套利'
        }
    )
    
    # 等待消息發送
    await asyncio.sleep(2)
    
    # 顯示統計信息
    stats = notifier.get_statistics()
    print(f"📊 通知統計: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 停止系統
    await notifier.stop()

if __name__ == "__main__":
    asyncio.run(test_advanced_notifier()) 