#!/usr/bin/env python3
"""
資金費率套利系統 - 面板界面
提供簡潔的面板模式入口，包含快速操作和系統狀態概覽
"""

import sys
import os
import asyncio
from datetime import datetime
from typing import List
import subprocess

class PanelInterface:
    """面板界面類 - 提供系統概覽和快速操作"""
    
    def __init__(self, available_exchanges: List[str] = None):
        self.available_exchanges = available_exchanges or []
    
    def run(self):
        """運行面板界面"""
        while True:
            try:
                self.show_panel()
                choice = input("\n請選擇操作 (1-8, q退出): ").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    print("👋 感謝使用資金費率套利系統！")
                    break
                
                self.handle_panel_choice(choice)
                
            except KeyboardInterrupt:
                print("\n\n用戶中斷操作")
                break
            except Exception as e:
                print(f"❌ 操作失敗: {e}")
                input("按 Enter 繼續...")
    
    def show_panel(self):
        """顯示面板主界面"""
        self.clear_screen()
        print("🎛️ 資金費率套利系統 - 控制面板")
        print("=" * 60)
        print(f"📅 系統時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.available_exchanges:
            print(f"🏦 已配置交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        else:
            print("⚠️  未檢測到已配置的交易所")
        
        print()
        print("🚀 快速操作:")
        print("  1. 💻 啟動 CLI 交互界面")
        print("  2. 🌐 啟動 Web 監控界面")
        print("  3. 📊 查看當前套利機會")
        print("  4. 💰 檢查賬戶餘額")
        print("  5. 🔍 發現可用交易對")
        print("  6. 📈 查看歷史統計")
        print("  7. 🧪 測試交易所API")
        print("  8. ⚙️  系統配置管理")
        print()
        print("💡 提示: 面板模式提供系統概覽和快速操作入口")
    
    def handle_panel_choice(self, choice: str):
        """處理面板選擇"""
        if choice == '1':
            self.start_cli_interface()
        elif choice == '2':
            self.start_web_interface()
        elif choice == '3':
            self.show_opportunities()
        elif choice == '4':
            self.check_balances()
        elif choice == '5':
            self.discover_symbols()
        elif choice == '6':
            self.show_statistics()
        elif choice == '7':
            self.test_api_connections()
        elif choice == '8':
            self.manage_configuration()
        else:
            print("❌ 無效選擇，請輸入 1-8 或 q")
            input("按 Enter 繼續...")
    
    def start_cli_interface(self):
        """啟動CLI界面"""
        print("💻 正在啟動 CLI 交互界面...")
        try:
            from cli_interface import CLIInterface
            cli = CLIInterface(available_exchanges=self.available_exchanges)
            cli.run()
        except ImportError:
            print("❌ CLI 界面模塊未找到")
            input("按 Enter 繼續...")
    
    def start_web_interface(self):
        """啟動Web界面"""
        print("🌐 正在啟動 Web 監控界面...")
        print("💡 Web界面將在瀏覽器中開啟，地址: http://localhost:5000")
        
        try:
            # 使用子進程啟動Web界面，避免阻塞面板
            cmd = ['python', '-c', 'from web_interface import create_web_interface; create_web_interface().run()']
            subprocess.Popen(cmd, cwd=os.getcwd())
            print("✅ Web界面已在後台啟動")
            print("🔗 請在瀏覽器中訪問: http://localhost:5000")
        except Exception as e:
            print(f"❌ 啟動Web界面失敗: {e}")
        
        input("按 Enter 繼續...")
    
    def show_opportunities(self):
        """顯示套利機會"""
        print("📊 正在查詢當前套利機會...")
        
        if not self.available_exchanges:
            print("❌ 需要配置交易所才能查詢機會")
            input("按 Enter 繼續...")
            return
        
        try:
            cmd = ['python', 'run.py', '--show-opportunities', '--limit', '10']
            subprocess.run(cmd, cwd=os.getcwd())
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
        
        input("按 Enter 繼續...")
    
    def check_balances(self):
        """檢查賬戶餘額"""
        print("💰 正在檢查賬戶餘額...")
        
        if not self.available_exchanges:
            print("❌ 需要配置交易所才能查詢餘額")
            input("按 Enter 繼續...")
            return
        
        try:
            cmd = ['python', 'run.py', '--check-balances']
            subprocess.run(cmd, cwd=os.getcwd())
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
        
        input("按 Enter 繼續...")
    
    def discover_symbols(self):
        """發現可用交易對"""
        print("🔍 正在發現可用交易對...")
        
        try:
            cmd = ['python', 'run.py', '--discover-symbols']
            subprocess.run(cmd, cwd=os.getcwd())
        except Exception as e:
            print(f"❌ 發現失敗: {e}")
        
        input("按 Enter 繼續...")
    
    def show_statistics(self):
        """顯示歷史統計"""
        print("📈 正在查詢歷史統計...")
        
        try:
            cmd = ['python', 'run.py', '--stats', '--days', '7']
            subprocess.run(cmd, cwd=os.getcwd())
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
        
        input("按 Enter 繼續...")
    
    def test_api_connections(self):
        """測試API連接"""
        print("🧪 正在測試交易所API連接...")
        
        try:
            # 使用funding_rate_arbitrage_system的測試功能
            cmd = ['python', '-c', 'import asyncio; from funding_rate_arbitrage_system import test_all_exchanges; asyncio.run(test_all_exchanges())']
            subprocess.run(cmd, cwd=os.getcwd())
        except Exception as e:
            print(f"❌ 測試失敗: {e}")
        
        input("按 Enter 繼續...")
    
    def manage_configuration(self):
        """配置管理"""
        print("⚙️  配置管理功能")
        print("-" * 40)
        print("1. 🔑 檢查API密鑰配置")
        print("2. 📁 查看配置文件位置")
        print("3. 📝 配置說明")
        print("4. 🔄 重載配置")
        
        choice = input("\n請選擇配置操作 (1-4): ").strip()
        
        if choice == '1':
            self.check_api_config()
        elif choice == '2':
            self.show_config_locations()
        elif choice == '3':
            self.show_config_help()
        elif choice == '4':
            self.reload_config()
        else:
            print("❌ 無效選擇")
        
        input("按 Enter 繼續...")
    
    def check_api_config(self):
        """檢查API配置"""
        print("🔑 API密鑰配置狀態:")
        
        # 檢查.env文件
        env_file = ".env"
        if os.path.exists(env_file):
            print("✅ .env 文件存在")
            with open(env_file, 'r') as f:
                content = f.read()
                exchanges = ['BINANCE', 'BYBIT', 'OKX', 'BACKPACK', 'BITGET', 'GATEIO', 'MEXC']
                for exchange in exchanges:
                    if f'{exchange}_API_KEY' in content:
                        print(f"  ✅ {exchange} API配置已找到")
                    else:
                        print(f"  ❌ {exchange} API配置缺失")
        else:
            print("❌ .env 文件不存在")
            print("💡 請創建 .env 文件並配置API密鑰")
    
    def show_config_locations(self):
        """顯示配置文件位置"""
        print("📁 配置文件位置:")
        print(f"  - 主配置: {os.path.abspath('config.json')}")
        print(f"  - 環境變數: {os.path.abspath('.env')}")
        print(f"  - 數據庫: {os.path.abspath('funding_arbitrage.db')}")
        print(f"  - 日誌: {os.path.abspath('funding_arbitrage.log')}")
    
    def show_config_help(self):
        """顯示配置說明"""
        print("📝 配置說明:")
        print("1. 創建 .env 文件並配置API密鑰")
        print("2. 支持的交易所: Binance, Bybit, OKX, Backpack, Bitget, Gate.io, MEXC")
        print("3. OKX和Bitget需要額外的passphrase")
        print("4. 建議先使用測試API進行驗證")
        print("5. 詳細配置請參考 setup_guide.md")
    
    def reload_config(self):
        """重載配置"""
        print("🔄 配置重載功能開發中...")
        print("💡 目前請重啟程序來重載配置")
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    # 自動檢測已配置的交易所
    try:
        from config_funding import ConfigManager, ExchangeDetector
        config_manager = ConfigManager()
        available_exchanges = ExchangeDetector.detect_configured_exchanges(config_manager)
    except:
        available_exchanges = []
    
    panel = PanelInterface(available_exchanges=available_exchanges)
    panel.run() 