#!/usr/bin/env python3
"""
主系統整合 - 資金費率套利系統完整解決方案
整合所有功能模組：WebSocket、Web界面、自動交易、性能優化、高級通知
"""

import asyncio
import logging
import json
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import traceback

# 導入所有功能模組
from funding_rate_arbitrage_system import FundingArbitrageSystem
from websocket_manager import WebSocketManager
from web_interface import WebInterface, create_web_interface
from auto_trading_engine import AutoTradingEngine, create_auto_trading_engine
from advanced_notifier import AdvancedNotificationSystem, create_advanced_notifier, NotificationType, NotificationPriority
from performance_optimizer import PerformanceOptimizer, create_performance_optimizer
from config_funding import get_config, detect_available_exchanges

logger = logging.getLogger("MainSystemIntegration")

@dataclass
class SystemStatus:
    """系統狀態"""
    core_system_running: bool = False
    websocket_running: bool = False
    web_interface_running: bool = False
    auto_trading_running: bool = False
    notifications_running: bool = False
    performance_optimizer_running: bool = False
    start_time: Optional[datetime] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class IntegratedArbitrageSystem:
    """整合式資金費率套利系統"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or get_config()
        self.status = SystemStatus()
        
        # 核心組件
        self.core_system: Optional[FundingArbitrageSystem] = None
        self.websocket_manager: Optional[WebSocketManager] = None
        self.web_interface: Optional[WebInterface] = None
        self.auto_trading_engine: Optional[AutoTradingEngine] = None
        self.notification_system: Optional[AdvancedNotificationSystem] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        
        # 檢測可用交易所
        self.available_exchanges = detect_available_exchanges()
        
        # 系統配置
        self.use_websocket = self.config.system.get('enable_websocket', True)
        self.use_web_interface = self.config.system.get('enable_web_interface', True)
        self.use_auto_trading = self.config.system.get('enable_auto_trading', False)
        self.use_notifications = self.config.system.get('enable_notifications', True)
        self.use_performance_optimizer = self.config.system.get('enable_performance_optimizer', True)
        
        # 運行控制
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        logger.info("🚀 整合式套利系統已初始化")
        logger.info(f"   可用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        logger.info(f"   WebSocket: {'啟用' if self.use_websocket else '禁用'}")
        logger.info(f"   Web界面: {'啟用' if self.use_web_interface else '禁用'}")
        logger.info(f"   自動交易: {'啟用' if self.use_auto_trading else '禁用'}")
        logger.info(f"   通知系統: {'啟用' if self.use_notifications else '禁用'}")
        logger.info(f"   性能優化: {'啟用' if self.use_performance_optimizer else '禁用'}")
    
    async def initialize_all_components(self):
        """初始化所有組件"""
        logger.info("🔧 初始化系統組件...")
        
        try:
            # 1. 初始化性能優化器（優先啟動）
            if self.use_performance_optimizer:
                await self._initialize_performance_optimizer()
            
            # 2. 初始化通知系統
            if self.use_notifications:
                await self._initialize_notification_system()
            
            # 3. 初始化核心套利系統
            await self._initialize_core_system()
            
            # 4. 初始化自動交易引擎
            if self.use_auto_trading:
                await self._initialize_auto_trading()
            
            # 5. 初始化Web界面
            if self.use_web_interface:
                await self._initialize_web_interface()
            
            # 6. 初始化WebSocket (最後啟動，因為需要其他組件)
            if self.use_websocket:
                await self._initialize_websocket()
            
            logger.info("✅ 所有組件初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 組件初始化失敗: {e}")
            self.status.errors.append(f"初始化失敗: {e}")
            raise
    
    async def _initialize_core_system(self):
        """初始化核心套利系統"""
        logger.info("🔧 初始化核心套利系統...")
        
        self.core_system = FundingArbitrageSystem(
            available_exchanges=self.available_exchanges,
            safe_mode=self.config.trading.get('safe_mode', True),
            use_websocket=self.use_websocket
        )
        
        # 如果沒有可用交易所，警告但不阻止啟動
        if not self.available_exchanges:
            logger.warning("⚠️ 未檢測到可用交易所，系統將以演示模式運行")
            self.status.errors.append("未檢測到可用交易所")
        
        self.status.core_system_running = True
        logger.info("✅ 核心套利系統已初始化")
    
    async def _initialize_websocket(self):
        """初始化WebSocket管理器"""
        logger.info("🔧 初始化WebSocket管理器...")
        
        # 準備交易所配置
        exchanges_config = {}
        if self.core_system and self.core_system.monitor.exchanges:
            for exchange_name, connector in self.core_system.monitor.exchanges.items():
                exchanges_config[exchange_name] = {
                    "api_key": connector.api_key,
                    "secret_key": connector.secret_key,
                    "passphrase": getattr(connector, 'passphrase', '')
                }
        
        self.websocket_manager = WebSocketManager(exchanges_config)
        
        self.status.websocket_running = True
        logger.info("✅ WebSocket管理器已初始化")
    
    async def _initialize_web_interface(self):
        """初始化Web界面"""
        logger.info("🔧 初始化Web界面...")
        
        self.web_interface = create_web_interface(
            available_exchanges=self.available_exchanges,
            use_websocket=self.use_websocket
        )
        
        # 將核心系統連接到Web界面
        if self.core_system:
            self.web_interface.set_arbitrage_system(self.core_system)
        
        self.status.web_interface_running = True
        logger.info("✅ Web界面已初始化")
    
    async def _initialize_auto_trading(self):
        """初始化自動交易引擎"""
        logger.info("🔧 初始化自動交易引擎...")
        
        # 準備交易所連接器
        exchanges = {}
        if self.core_system and self.core_system.monitor.exchanges:
            exchanges = self.core_system.monitor.exchanges
        
        trading_config = {
            'trading_enabled': self.config.trading.get('auto_trading_enabled', False),
            'safe_mode': self.config.trading.get('safe_mode', True),
            'auto_close_enabled': True,
            'risk': {
                'max_daily_loss': self.config.trading.get('max_daily_loss', 1000.0),
                'max_total_exposure': self.config.trading.get('max_total_exposure', 10000.0),
                'max_single_position': self.config.trading.get('max_single_position', 2000.0),
                'max_positions': self.config.trading.get('max_positions', 10),
                'stop_loss_pct': self.config.trading.get('stop_loss_pct', 2.0),
                'take_profit_pct': self.config.trading.get('take_profit_pct', 5.0)
            }
        }
        
        self.auto_trading_engine = AutoTradingEngine(exchanges, trading_config)
        
        self.status.auto_trading_running = True
        logger.info("✅ 自動交易引擎已初始化")
    
    async def _initialize_notification_system(self):
        """初始化通知系統"""
        logger.info("🔧 初始化通知系統...")
        
        notification_config = {
            'channels': {
                'websocket': {
                    'enabled': self.use_websocket,
                    'port': self.config.system.get('websocket_port', 8765)
                },
                'email': {
                    'enabled': self.config.system.get('enable_email_notifications', False),
                    'smtp_server': self.config.system.get('email_smtp_server', ''),
                    'smtp_port': self.config.system.get('email_smtp_port', 587),
                    'username': self.config.system.get('email_username', ''),
                    'password': self.config.system.get('email_password', ''),
                    'recipients': self.config.system.get('email_recipients', [])
                },
                'telegram': {
                    'enabled': self.config.system.get('enable_telegram_alerts', False),
                    'bot_token': self.config.system.get('telegram_bot_token', ''),
                    'chat_id': self.config.system.get('telegram_chat_id', '')
                }
            }
        }
        
        self.notification_system = AdvancedNotificationSystem(notification_config)
        
        self.status.notifications_running = True
        logger.info("✅ 通知系統已初始化")
    
    async def _initialize_performance_optimizer(self):
        """初始化性能優化器"""
        logger.info("🔧 初始化性能優化器...")
        
        optimizer_config = {
            'max_connections': self.config.system.get('max_connections', 100),
            'max_connections_per_host': self.config.system.get('max_connections_per_host', 20),
            'cache_max_size': self.config.system.get('cache_max_size', 1000),
            'cache_default_ttl': self.config.system.get('cache_default_ttl', 300),
            'max_concurrent_tasks': self.config.system.get('max_concurrent_tasks', 50),
            'max_memory_mb': self.config.system.get('max_memory_mb', 512),
            'auto_optimize': True
        }
        
        self.performance_optimizer = PerformanceOptimizer(optimizer_config)
        
        self.status.performance_optimizer_running = True
        logger.info("✅ 性能優化器已初始化")
    
    async def start_all_components(self):
        """啟動所有組件"""
        logger.info("🚀 啟動所有系統組件...")
        
        self.running = True
        self.status.start_time = datetime.now()
        
        try:
            # 1. 啟動性能優化器
            if self.performance_optimizer:
                await self.performance_optimizer.start_optimization()
                logger.info("✅ 性能優化器已啟動")
            
            # 2. 啟動通知系統
            if self.notification_system:
                await self.notification_system.start()
                logger.info("✅ 通知系統已啟動")
                
                # 發送系統啟動通知
                await self.notification_system.notify(
                    NotificationType.SYSTEM_STATUS,
                    "系統啟動",
                    f"資金費率套利系統已成功啟動，可用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}",
                    {
                        'available_exchanges': self.available_exchanges,
                        'websocket_enabled': self.use_websocket,
                        'web_interface_enabled': self.use_web_interface,
                        'auto_trading_enabled': self.use_auto_trading
                    },
                    NotificationPriority.MEDIUM
                )
            
            # 3. 啟動核心監控系統
            if self.core_system:
                await self.core_system.monitor.start_monitoring()
                logger.info("✅ 核心監控系統已啟動")
            
            # 4. 啟動自動交易引擎監控
            if self.auto_trading_engine:
                asyncio.create_task(self.auto_trading_engine.start_monitoring())
                logger.info("✅ 自動交易監控已啟動")
            
            # 5. 啟動Web界面（在背景運行）
            if self.web_interface:
                web_port = self.config.system.get('web_port', 8080)
                self.web_interface.start_background(port=web_port)
                logger.info(f"✅ Web界面已啟動: http://localhost:{web_port}")
            
            # 6. 啟動WebSocket連接
            if self.websocket_manager:
                await self.websocket_manager.start_all_connections(self.available_exchanges)
                logger.info("✅ WebSocket連接已啟動")
            
            logger.info("🎉 所有組件啟動完成！")
            
            # 啟動主監控循環
            await self._start_main_monitoring_loop()
            
        except Exception as e:
            logger.error(f"❌ 組件啟動失敗: {e}")
            self.status.errors.append(f"啟動失敗: {e}")
            await self.stop_all_components()
            raise
    
    async def _start_main_monitoring_loop(self):
        """主監控循環"""
        logger.info("🔄 啟動主監控循環...")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # 檢查套利機會
                if self.core_system and self.core_system.detector:
                    opportunities = self.core_system.detector.detect_all_opportunities()
                    
                    # 處理發現的機會
                    for opportunity in opportunities:
                        await self._handle_arbitrage_opportunity(opportunity)
                
                # 檢查系統健康狀態
                await self._check_system_health()
                
                # 等待下次檢查
                await asyncio.sleep(30)  # 每30秒檢查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                
                # 發送錯誤通知
                if self.notification_system:
                    await self.notification_system.notify(
                        NotificationType.ERROR_ALERT,
                        "系統錯誤",
                        f"監控循環發生錯誤: {e}",
                        {'error': str(e), 'traceback': traceback.format_exc()},
                        NotificationPriority.HIGH
                    )
                
                await asyncio.sleep(60)  # 錯誤時延長等待時間
    
    async def _handle_arbitrage_opportunity(self, opportunity):
        """處理套利機會"""
        try:
            # 轉換為字典格式
            opp_dict = opportunity.to_dict() if hasattr(opportunity, 'to_dict') else opportunity.__dict__
            
            # 發送機會通知
            if self.notification_system:
                await self.notification_system.notify(
                    NotificationType.ARBITRAGE_OPPORTUNITY,
                    f"發現套利機會: {opp_dict.get('symbol', 'Unknown')}",
                    f"策略: {opp_dict.get('strategy_type', 'Unknown')}, 預期利潤: {opp_dict.get('net_profit_8h', 0):.2f} USDT",
                    opp_dict,
                    NotificationPriority.HIGH if opp_dict.get('net_profit_8h', 0) > 50 else NotificationPriority.MEDIUM
                )
            
            # 自動交易執行
            if self.auto_trading_engine and self.auto_trading_engine.trading_enabled:
                success = await self.auto_trading_engine.execute_arbitrage_opportunity(opp_dict)
                
                if success:
                    logger.info(f"✅ 套利機會已執行: {opp_dict.get('symbol')}")
                    
                    # 發送執行通知
                    if self.notification_system:
                        await self.notification_system.notify(
                            NotificationType.TRADE_EXECUTION,
                            "套利執行成功",
                            f"已執行套利: {opp_dict.get('symbol')}, 預期利潤: {opp_dict.get('net_profit_8h', 0):.2f} USDT",
                            opp_dict,
                            NotificationPriority.HIGH
                        )
                else:
                    logger.warning(f"⚠️ 套利機會執行失敗: {opp_dict.get('symbol')}")
        
        except Exception as e:
            logger.error(f"處理套利機會錯誤: {e}")
    
    async def _check_system_health(self):
        """檢查系統健康狀態"""
        try:
            health_issues = []
            
            # 檢查各組件狀態
            if self.core_system and not self.core_system.monitor.running:
                health_issues.append("核心監控系統已停止")
            
            if self.performance_optimizer:
                memory_usage = self.performance_optimizer.memory_manager.get_memory_usage()
                if memory_usage['percent'] > 90:
                    health_issues.append(f"內存使用過高: {memory_usage['percent']:.1f}%")
            
            # 如果有健康問題，發送警報
            if health_issues and self.notification_system:
                await self.notification_system.notify(
                    NotificationType.RISK_ALERT,
                    "系統健康警報",
                    f"檢測到 {len(health_issues)} 個問題: {'; '.join(health_issues)}",
                    {'issues': health_issues},
                    NotificationPriority.HIGH
                )
        
        except Exception as e:
            logger.error(f"健康檢查錯誤: {e}")
    
    async def stop_all_components(self):
        """停止所有組件"""
        logger.info("⏹️ 停止所有系統組件...")
        
        self.running = False
        self.shutdown_event.set()
        
        try:
            # 1. 停止核心監控
            if self.core_system:
                await self.core_system.monitor.stop_monitoring()
                logger.info("✅ 核心監控已停止")
            
            # 2. 停止WebSocket
            if self.websocket_manager:
                await self.websocket_manager.stop_all_connections()
                logger.info("✅ WebSocket連接已停止")
            
            # 3. 停止自動交易引擎（取消監控任務）
            if self.auto_trading_engine:
                # 自動交易引擎的監控會隨著主循環停止
                logger.info("✅ 自動交易監控已停止")
            
            # 4. 停止通知系統
            if self.notification_system:
                # 發送系統停止通知
                await self.notification_system.notify(
                    NotificationType.SYSTEM_STATUS,
                    "系統停止",
                    "資金費率套利系統正在關閉",
                    {'shutdown_time': datetime.now().isoformat()},
                    NotificationPriority.MEDIUM
                )
                
                await self.notification_system.stop()
                logger.info("✅ 通知系統已停止")
            
            # 5. 停止性能優化器
            if self.performance_optimizer:
                await self.performance_optimizer.stop_optimization()
                logger.info("✅ 性能優化器已停止")
            
            # 6. Web界面會隨著進程結束自動停止
            
            logger.info("🏁 所有組件已停止")
            
        except Exception as e:
            logger.error(f"停止組件時發生錯誤: {e}")
    
    def get_system_summary(self) -> Dict[str, Any]:
        """獲取系統摘要"""
        runtime = None
        if self.status.start_time:
            runtime = datetime.now() - self.status.start_time
        
        summary = {
            'system_status': {
                'running': self.running,
                'start_time': self.status.start_time.isoformat() if self.status.start_time else None,
                'runtime_hours': runtime.total_seconds() / 3600 if runtime else 0,
                'available_exchanges': self.available_exchanges,
                'errors': self.status.errors
            },
            'components': {
                'core_system': self.status.core_system_running,
                'websocket': self.status.websocket_running,
                'web_interface': self.status.web_interface_running,
                'auto_trading': self.status.auto_trading_running,
                'notifications': self.status.notifications_running,
                'performance_optimizer': self.status.performance_optimizer_running
            },
            'configuration': {
                'websocket_enabled': self.use_websocket,
                'web_interface_enabled': self.use_web_interface,
                'auto_trading_enabled': self.use_auto_trading,
                'notifications_enabled': self.use_notifications,
                'performance_optimizer_enabled': self.use_performance_optimizer
            }
        }
        
        # 添加詳細統計
        if self.core_system:
            summary['trading_stats'] = self.core_system.get_trading_summary() if hasattr(self.core_system, 'get_trading_summary') else {}
        
        if self.auto_trading_engine:
            summary['auto_trading_stats'] = self.auto_trading_engine.get_trading_summary()
        
        if self.performance_optimizer:
            summary['performance_stats'] = self.performance_optimizer.get_performance_summary()
        
        if self.notification_system:
            summary['notification_stats'] = self.notification_system.get_statistics()
        
        return summary
    
    def setup_signal_handlers(self):
        """設置信號處理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信號 {signum}，正在優雅關閉系統...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

# 主函數和入口點
async def main(config_file: Optional[str] = None, duration_hours: float = 24):
    """主函數"""
    
    print("🚀 資金費率套利系統 - 完整解決方案")
    print("=" * 60)
    
    try:
        # 加載配置
        config = get_config()
        
        # 創建整合系統
        integrated_system = IntegratedArbitrageSystem(config)
        
        # 設置信號處理器
        integrated_system.setup_signal_handlers()
        
        # 初始化所有組件
        await integrated_system.initialize_all_components()
        
        # 啟動所有組件
        await integrated_system.start_all_components()
        
        # 顯示系統摘要
        summary = integrated_system.get_system_summary()
        print("\n📊 系統摘要:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        # 運行指定時間或直到收到停止信號
        try:
            await asyncio.wait_for(
                integrated_system.shutdown_event.wait(),
                timeout=duration_hours * 3600
            )
        except asyncio.TimeoutError:
            logger.info(f"⏰ 運行時間已達到 {duration_hours} 小時，正在停止系統...")
        
        # 停止所有組件
        await integrated_system.stop_all_components()
        
        # 顯示最終摘要
        final_summary = integrated_system.get_system_summary()
        print("\n📋 最終運行摘要:")
        print(json.dumps(final_summary, indent=2, ensure_ascii=False))
        
        print("\n🎉 系統已成功關閉！")
        
    except KeyboardInterrupt:
        logger.info("👋 用戶中斷，正在關閉系統...")
    except Exception as e:
        logger.error(f"❌ 系統錯誤: {e}")
        traceback.print_exc()
    finally:
        print("👋 感謝使用資金費率套利系統！")

def create_integrated_system(config_file: Optional[str] = None) -> IntegratedArbitrageSystem:
    """創建整合系統實例"""
    config = get_config()
    return IntegratedArbitrageSystem(config)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="資金費率套利系統 - 完整解決方案")
    parser.add_argument("--config", type=str, help="配置文件路徑")
    parser.add_argument("--duration", type=float, default=24, help="運行時間（小時）")
    parser.add_argument("--debug", action="store_true", help="啟用調試模式")
    
    args = parser.parse_args()
    
    # 設置日誌級別
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 運行主函數
    asyncio.run(main(args.config, args.duration)) 