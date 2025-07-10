#!/usr/bin/env python3
"""
綜合套利系統啟動腳本
整合所有套利策略和風險管理
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# 導入模組
from comprehensive_arbitrage_system import ComprehensiveArbitrageSystem
from risk_manager import ComprehensiveRiskManager
from hybrid_arbitrage_architecture import HybridArbitrageSystem

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_arbitrage.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ComprehensiveArbitrage")

class ComprehensiveArbitrageLauncher:
    """綜合套利系統啟動器"""
    
    def __init__(self, config_path: str = "arbitrage_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.arbitrage_system = None
        self.risk_manager = None
        self.running = False
        
    def load_config(self) -> dict:
        """加載配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✅ 配置文件加載成功: {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"❌ 配置文件未找到: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"❌ 配置文件格式錯誤: {e}")
            sys.exit(1)
    
    async def initialize_system(self):
        """初始化系統"""
        logger.info("🚀 初始化綜合套利系統...")
        
        # 初始化風險管理器
        self.risk_manager = ComprehensiveRiskManager(self.config)
        logger.info("✅ 風險管理器已初始化")
        
        # 初始化套利系統
        self.arbitrage_system = ComprehensiveArbitrageSystem()
        logger.info("✅ 套利系統已初始化")
        
        # 設置信號處理
        self.setup_signal_handlers()
        
        logger.info("🎯 系統初始化完成")
    
    def setup_signal_handlers(self):
        """設置信號處理器"""
        def signal_handler(signum, frame):
            logger.info(f"📡 收到信號 {signum}，準備關閉系統...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_monitoring(self):
        """啟動監控"""
        logger.info("📊 啟動系統監控...")
        
        # 啟動性能監控任務
        asyncio.create_task(self.monitor_performance())
        
        # 啟動風險監控任務
        asyncio.create_task(self.monitor_risk())
        
        # 啟動報告生成任務
        asyncio.create_task(self.generate_reports())
    
    async def monitor_performance(self):
        """監控系統性能"""
        while self.running:
            try:
                if self.arbitrage_system:
                    # 獲取性能報告
                    performance_report = self.arbitrage_system.get_performance_report()
                    
                    # 記錄關鍵指標
                    logger.info(f"📈 性能指標: "
                               f"總機會: {performance_report['total_opportunities']}, "
                               f"已執行: {performance_report['executed_opportunities']}, "
                               f"成功率: {performance_report['success_rate']:.2%}, "
                               f"總利潤: {performance_report['total_profit']:.2f} USDT")
                    
                    # 檢查各策略表現
                    for strategy_type, stats in performance_report['by_type'].items():
                        if stats['count'] > 0:
                            logger.info(f"  {strategy_type}: "
                                       f"機會: {stats['count']}, "
                                       f"利潤: {stats['total_profit']:.2f} USDT")
                
                await asyncio.sleep(60)  # 每分鐘檢查一次
                
            except Exception as e:
                logger.error(f"性能監控錯誤: {e}")
                await asyncio.sleep(60)
    
    async def monitor_risk(self):
        """監控風險指標"""
        while self.running:
            try:
                if self.risk_manager:
                    # 獲取風險報告
                    risk_report = self.risk_manager.get_risk_report()
                    
                    # 檢查關鍵風險指標
                    risk_metrics = risk_report['risk_metrics']
                    
                    logger.info(f"⚠️ 風險指標: "
                               f"總敞口: {risk_metrics['total_exposure']:.2f} USDT, "
                               f"日內損益: {risk_metrics['daily_pnl']:.2f} USDT, "
                               f"最大回撤: {risk_metrics['max_drawdown']:.2%}")
                    
                    # 檢查熔斷器狀態
                    circuit_breakers = risk_report['circuit_breakers']
                    open_breakers = [name for name, cb in circuit_breakers.items() if cb['is_open']]
                    if open_breakers:
                        logger.warning(f"🔴 開啟的熔斷器: {', '.join(open_breakers)}")
                    
                    # 檢查是否應該停止交易
                    if self.risk_manager.should_stop_trading():
                        logger.error("🛑 風險管理要求停止交易")
                        self.running = False
                        break
                
                await asyncio.sleep(30)  # 每30秒檢查一次
                
            except Exception as e:
                logger.error(f"風險監控錯誤: {e}")
                await asyncio.sleep(30)
    
    async def generate_reports(self):
        """生成報告"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # 每小時生成一次報告
                if current_time.minute == 0:
                    await self.generate_hourly_report()
                
                # 每天生成一次報告
                if current_time.hour == 0 and current_time.minute == 0:
                    await self.generate_daily_report()
                
                # 每週生成一次報告
                if current_time.weekday() == 0 and current_time.hour == 0 and current_time.minute == 0:
                    await self.generate_weekly_report()
                
                await asyncio.sleep(60)  # 每分鐘檢查一次
                
            except Exception as e:
                logger.error(f"報告生成錯誤: {e}")
                await asyncio.sleep(60)
    
    async def generate_hourly_report(self):
        """生成小時報告"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "type": "hourly",
                "performance": self.arbitrage_system.get_performance_report() if self.arbitrage_system else {},
                "risk": self.risk_manager.get_risk_report() if self.risk_manager else {},
                "active_opportunities": len(self.arbitrage_system.get_active_opportunities()) if self.arbitrage_system else 0
            }
            
            # 保存報告
            report_path = f"reports/hourly_{datetime.now().strftime('%Y%m%d_%H')}.json"
            Path("reports").mkdir(exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📊 小時報告已生成: {report_path}")
            
        except Exception as e:
            logger.error(f"生成小時報告失敗: {e}")
    
    async def generate_daily_report(self):
        """生成日報告"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "type": "daily",
                "performance": self.arbitrage_system.get_performance_report() if self.arbitrage_system else {},
                "risk": self.risk_manager.get_risk_report() if self.risk_manager else {},
                "summary": {
                    "total_opportunities": 0,
                    "total_profit": 0.0,
                    "success_rate": 0.0,
                    "max_drawdown": 0.0
                }
            }
            
            # 保存報告
            report_path = f"reports/daily_{datetime.now().strftime('%Y%m%d')}.json"
            Path("reports").mkdir(exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📊 日報告已生成: {report_path}")
            
        except Exception as e:
            logger.error(f"生成日報告失敗: {e}")
    
    async def generate_weekly_report(self):
        """生成週報告"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "type": "weekly",
                "performance": self.arbitrage_system.get_performance_report() if self.arbitrage_system else {},
                "risk": self.risk_manager.get_risk_report() if self.risk_manager else {},
                "weekly_summary": {
                    "total_opportunities": 0,
                    "total_profit": 0.0,
                    "success_rate": 0.0,
                    "best_strategy": "",
                    "worst_strategy": ""
                }
            }
            
            # 保存報告
            report_path = f"reports/weekly_{datetime.now().strftime('%Y%m%d')}.json"
            Path("reports").mkdir(exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📊 週報告已生成: {report_path}")
            
        except Exception as e:
            logger.error(f"生成週報告失敗: {e}")
    
    async def run(self):
        """運行系統"""
        try:
            # 初始化系統
            await self.initialize_system()
            
            # 啟動監控
            await self.start_monitoring()
            
            # 啟動套利系統
            self.running = True
            logger.info("🎯 綜合套利系統已啟動")
            
            # 運行套利系統
            if self.arbitrage_system:
                await self.arbitrage_system.start()
            
        except KeyboardInterrupt:
            logger.info("🛑 收到中斷信號，正在關閉系統...")
        except Exception as e:
            logger.error(f"❌ 系統運行錯誤: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """關閉系統"""
        logger.info("🔄 正在關閉系統...")
        
        self.running = False
        
        # 生成最終報告
        try:
            if self.arbitrage_system and self.risk_manager:
                final_report = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "shutdown",
                    "performance": self.arbitrage_system.get_performance_report(),
                    "risk": self.risk_manager.get_risk_report(),
                    "runtime": "系統運行時間統計"
                }
                
                report_path = f"reports/shutdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                Path("reports").mkdir(exist_ok=True)
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(final_report, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"📊 最終報告已生成: {report_path}")
        except Exception as e:
            logger.error(f"生成最終報告失敗: {e}")
        
        logger.info("✅ 系統已安全關閉")

def main():
    """主函數"""
    print("""
    🚀 綜合套利系統啟動器
    ======================
    
    支持的套利策略:
    ✅ 現貨套利 (Spot Arbitrage)
    ✅ 資金費率套利 (Funding Rate Arbitrage)
    ✅ 三角套利 (Triangular Arbitrage)
    ✅ 期現套利 (Futures-Spot Arbitrage)
    ✅ 統計套利 (Statistical Arbitrage)
    
    風險管理:
    ✅ 實時風險監控
    ✅ 熔斷器機制
    ✅ 相關性控制
    ✅ 波動率限制
    ✅ 凱利公式倉位管理
    
    監控功能:
    ✅ 性能指標追蹤
    ✅ 自動報告生成
    ✅ 實時警報系統
    """)
    
    # 檢查配置文件
    config_path = "arbitrage_config.json"
    if not Path(config_path).exists():
        print(f"❌ 配置文件未找到: {config_path}")
        print("請確保 arbitrage_config.json 文件存在")
        sys.exit(1)
    
    # 創建啟動器
    launcher = ComprehensiveArbitrageLauncher(config_path)
    
    # 運行系統
    asyncio.run(launcher.run())

if __name__ == "__main__":
    main() 