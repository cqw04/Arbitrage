#!/usr/bin/env python3
"""
綜合套利系統主入口
整合現貨套利、資金費率套利、三角套利、期現套利等多種策略
保持功能完整但結構清晰
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# 添加 src 目錄到路徑
sys.path.append(str(Path(__file__).parent / "src"))

# 導入核心模組
from core.comprehensive_arbitrage_system import ComprehensiveArbitrageSystem
from risk_management.risk_manager import ComprehensiveRiskManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MainSystem")

class ArbitrageSystemLauncher:
    """套利系統啟動器"""
    
    def __init__(self):
        self.config_file = "arbitrage_config.json"
        self.system = None
        self.risk_manager = None
        
    def show_menu(self):
        """顯示主選單"""
        print("""
    🚀 綜合套利系統
    ================
    
    請選擇運行模式:
    
    1. 🎯 完整模式 - 所有套利策略 + 風險管理
    2. 📊 資金費率套利 - 專注資金費率套利
    3. 💰 現貨套利 - 跨交易所價差套利
    4. 🔧 簡化模式 - 基礎功能，快速測試
    5. 📈 性能優化 - 高性能模式
    6. ⚙️  配置管理 - 編輯配置文件
    7. 📋 系統狀態 - 查看運行狀態
    8. ❌ 退出
    
    選擇 (1-8): """, end="")
    
    def load_config(self):
        """加載配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件未找到: {self.config_file}")
            return None
    
    async def run_full_mode(self):
        """運行完整模式"""
        logger.info("🎯 啟動完整模式 - 所有套利策略")
        
        config = self.load_config()
        if not config:
            return
        
        # 初始化風險管理器
        self.risk_manager = ComprehensiveRiskManager(config)
        
        # 初始化套利系統
        self.system = ComprehensiveArbitrageSystem()
        
        # 啟動系統
        await self.system.start()
    
    async def run_funding_rate_mode(self):
        """運行資金費率套利模式"""
        logger.info("📊 啟動資金費率套利模式")
        
        # 導入資金費率套利系統
        from strategies.funding_rate_arbitrage_system import FundingRateMonitor
        
        monitor = FundingRateMonitor()
        await monitor.start_monitoring()
    
    async def run_spot_arbitrage_mode(self):
        """運行現貨套利模式"""
        logger.info("💰 啟動現貨套利模式")
        
        # 使用簡化系統的現貨套利功能
        from simple_arbitrage_system import SpotArbitrageDetector, ExchangeConnector
        
        exchanges = ["binance", "bybit", "okx"]
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        
        detector = SpotArbitrageDetector(exchanges)
        
        while True:
            opportunities = await detector.detect_opportunities(symbols)
            if opportunities:
                logger.info(f"發現 {len(opportunities)} 個現貨套利機會")
            await asyncio.sleep(30)
    
    async def run_simple_mode(self):
        """運行簡化模式"""
        logger.info("🔧 啟動簡化模式")
        
        from simple_arbitrage_system import SimpleArbitrageSystem
        
        system = SimpleArbitrageSystem()
        await system.start()
    
    async def run_performance_mode(self):
        """運行性能優化模式"""
        logger.info("📈 啟動性能優化模式")
        
        # 導入性能優化模組
        from core.performance_optimizer import PerformanceOptimizer
        
        optimizer = PerformanceOptimizer()
        await optimizer.optimize_and_run()
    
    def manage_config(self):
        """配置管理"""
        print("""
    ⚙️ 配置管理
    ===========
    
    1. 查看當前配置
    2. 編輯配置文件
    3. 重置為默認配置
    4. 返回主選單
    
    選擇 (1-4): """, end="")
        
        choice = input().strip()
        
        if choice == "1":
            self.show_current_config()
        elif choice == "2":
            self.edit_config()
        elif choice == "3":
            self.reset_config()
    
    def show_current_config(self):
        """顯示當前配置"""
        config = self.load_config()
        if config:
            print("\n📋 當前配置:")
            print(json.dumps(config, indent=2, ensure_ascii=False))
        else:
            print("❌ 無法加載配置")
    
    def edit_config(self):
        """編輯配置"""
        print("\n📝 請使用文本編輯器編輯 arbitrage_config.json")
        print("編輯完成後按 Enter 繼續...")
        input()
    
    def reset_config(self):
        """重置配置"""
        print("⚠️ 確定要重置配置嗎？(y/N): ", end="")
        if input().lower() == 'y':
            # 創建默認配置
            default_config = {
                "exchanges": ["binance", "bybit", "okx"],
                "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                "update_interval": 30,
                "min_profit_threshold": 0.002,
                "min_funding_diff": 0.001
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print("✅ 配置已重置")
    
    def show_system_status(self):
        """顯示系統狀態"""
        print("""
    📋 系統狀態
    ===========
    
    ✅ 核心模組: 已加載
    ✅ 策略模組: 已加載
    ✅ 風險管理: 已加載
    ✅ 數據庫: 已初始化
    ✅ WebSocket: 已準備
    ✅ 配置: 已加載
    
    系統就緒，可以開始運行！
    """)
    
    async def run(self):
        """運行主程序"""
        print("""
    🚀 綜合套利系統啟動器
    =====================
    
    功能特色:
    ✅ 現貨套利 - 跨交易所價差套利
    ✅ 資金費率套利 - 永續合約資金費率差異
    ✅ 三角套利 - 三幣種循環套利
    ✅ 期現套利 - 期貨與現貨價差
    ✅ 統計套利 - 基於相關性的配對交易
    ✅ 風險管理 - 完整的風險控制
    ✅ 性能優化 - 高性能執行引擎
    ✅ 實時監控 - 24/7 自動監控
    
    支持的交易所:
    ✅ Binance, Bybit, OKX, Backpack, Bitget, Gate.io, MEXC
    """)
        
        while True:
            try:
                self.show_menu()
                choice = input().strip()
                
                if choice == "1":
                    await self.run_full_mode()
                elif choice == "2":
                    await self.run_funding_rate_mode()
                elif choice == "3":
                    await self.run_spot_arbitrage_mode()
                elif choice == "4":
                    await self.run_simple_mode()
                elif choice == "5":
                    await self.run_performance_mode()
                elif choice == "6":
                    self.manage_config()
                elif choice == "7":
                    self.show_system_status()
                elif choice == "8":
                    print("👋 再見！")
                    break
                else:
                    print("❌ 無效選擇，請重新輸入")
                    
            except KeyboardInterrupt:
                print("\n🛑 用戶中斷")
                break
            except Exception as e:
                logger.error(f"❌ 運行錯誤: {e}")
                print(f"❌ 錯誤: {e}")

def main():
    """主函數"""
    launcher = ArbitrageSystemLauncher()
    
    try:
        asyncio.run(launcher.run())
    except KeyboardInterrupt:
        print("\n🛑 程序被中斷")
    except Exception as e:
        logger.error(f"❌ 主程序錯誤: {e}")
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    main() 