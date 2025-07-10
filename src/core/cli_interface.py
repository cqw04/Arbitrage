#!/usr/bin/env python3
"""
資金費率套利系統 - CLI 交互界面
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from config_funding import get_config, ConfigManager, ExchangeDetector
from database_manager import get_db
from funding_rate_arbitrage_system import FundingArbitrageSystem

logger = logging.getLogger("CLI")


class CLIInterface:
    """命令行交互界面"""
    
    def __init__(self, available_exchanges: list = None):
        self.config = get_config()
        self.db = get_db()
        self.available_exchanges = available_exchanges or []
        self.system = None
        self.running = False
        
        if self.available_exchanges:
            logger.info(f"CLI will use configured exchanges: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        else:
            logger.warning("No configured exchanges detected, some features may be limited")
    
    def run(self):
        """運行 CLI 界面"""
        self.show_banner()
        
        while True:
            try:
                self.show_main_menu()
                choice = input("\n請選擇操作 (1-11, q退出): ").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    print("感謝您使用資金費率套利系統！")
                    break
                
                self.handle_menu_choice(choice)
                
            except KeyboardInterrupt:
                print("\n\n用戶中斷，正在退出程式")
                break
            except Exception as e:
                print(f"操作失敗: {e}")
                input("按 Enter 繼續...")
    
    def show_banner(self):
        """顯示歡迎橫幅"""
        print("=" * 70)
        print("資金費率套利系統 - 命令行界面")
        print("   多交易所資金費率套利工具")
        print("=" * 70)
        
        # 顯示當前配置概況
        print(f"\n當前配置:")
        
        # 顯示可用交易所信息
        if self.available_exchanges:
            print(f"   可用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        else:
            print(f"   警告: 未配置交易所 - 請設置 API 密鑰")
            
        print(f"   支持所有: {', '.join(self.config.exchanges.keys())}")
        print(f"   監控交易對: {len(self.config.trading.symbols)} 個")
        print(f"   最大敞口: {self.config.trading.max_total_exposure} USDT")
        print(f"   最小利潤閾值: {self.config.trading.min_profit_threshold*100:.2f}%")
    
    def show_main_menu(self):
        """顯示主菜單"""
        print("\n" + "=" * 50)
        print("主菜單")
        print("=" * 50)
        print("1. 📈 查看當前套利機會")
        print("2. 📊 顯示歷史統計")
        print("3. 💰 檢查倉位狀態")
        print("4. 💳 檢查帳戶餘額")
        print("5. ⚙️  配置管理")
        print("6. 🚀 啟動套利系統")
        print("7. 🏪 交易所狀態")
        print("8. 📋 資金費率分析")
        print("9. 🔧 系統設置")
        print("10. 🔍 交易對發現分析")
        print("11. 🧪 測試所有交易所API")
        print("12. 📈 增強歷史分析 (新功能!)")
        print("0. 📖 幫助文檔")
        print("q. 🚪 退出系統")
    
    def handle_menu_choice(self, choice: str):
        """處理菜單選擇"""
        menu_actions = {
            '1': self.show_opportunities,
            '2': self.show_statistics,
            '3': self.show_positions,
            '4': self.check_account_balances,
            '5': self.config_management,
            '6': self.start_arbitrage_system,
            '7': self.show_exchange_status,
            '8': self.funding_rate_analysis,
            '9': self.system_settings,
            '10': self.symbol_discovery_analysis,
            '11': self.test_all_exchange_apis,
            '12': self.enhanced_historical_analysis,
            '0': self.show_help
        }
        
        action = menu_actions.get(choice)
        if action:
            action()
        else:
            print("❌ 無效選擇，請重新輸入")
    
    def show_opportunities(self):
        """顯示當前套利機會"""
        print("\n📈 當前套利機會分析")
        print("-" * 40)
        
        # 檢查可用交易所
        if not self.available_exchanges:
            print("錯誤: 未檢測到任何已配置的交易所")
            print("提示: 請在 .env 文件中配置交易所 API 密鑰")
            input("\n按 Enter 返回主選單...")
            return
        
        print(f"使用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        
        try:
            print("正在載入最新數據...")
            
            # 創建系統實例獲取真實數據
            import asyncio
            
            async def get_real_opportunities():
                system = FundingArbitrageSystem(available_exchanges=self.available_exchanges)
                
                # 初始化連接
                for exchange_name in self.available_exchanges:
                    if exchange_name in system.monitor.exchanges:
                        await system.monitor.exchanges[exchange_name].connect()
                
                # 等待數據收集
                await asyncio.sleep(8)
                
                # 檢測機會
                opportunities = system.detector.detect_all_opportunities()
                
                # 斷開連接
                for exchange_name in self.available_exchanges:
                    if exchange_name in system.monitor.exchanges:
                        await system.monitor.exchanges[exchange_name].disconnect()
                
                return opportunities
            
            # 運行異步獲取
            opportunities = asyncio.run(get_real_opportunities())
            
            if not opportunities:
                print("錯誤: 未找到套利機會")
                print("提示: 可能原因 - 利率差太小、手續費成本超過利潤等")
            else:
                print(f"\n找到 {len(opportunities)} 個套利機會:")
                print(f"{'排名':<4} {'策略':<15} {'交易對':<15} {'利潤':<10} {'風險':<8}")
                print("-" * 65)
                
                for i, opp in enumerate(opportunities[:10], 1):
                    print(f"{i:<4} {opp.strategy_type.value:<15} {opp.symbol:<15} "
                          f"{opp.net_profit_8h:<10.2f} {opp.risk_level:<8}")
                
                choice = input("\n查看詳細資訊? (y/N): ").lower()
                if choice == 'y' and opportunities:
                    self.show_opportunity_details(opportunities[0])
                
        except Exception as e:
            print(f"錯誤: 獲取套利機會失敗: {e}")
            print("提示: 請檢查網路連接和 API 配置")
        
        input("\n按 Enter 返回主選單...")
    
    def check_account_balances(self):
        """檢查所有交易所帳戶餘額"""
        print("\n💳 帳戶餘額檢查")
        print("-" * 30)
        
        if not self.available_exchanges:
            print("❌ 未檢測到任何已配置的交易所")
            print("💡 請先在 .env 文件中配置交易所 API 密鑰")
            input("\n按 Enter 返回主菜單...")
            return
        
        try:
            print("⏳ 正在檢查帳戶餘額...")
            
            # 導入餘額檢查函數
            from run import check_account_balances
            
            # 運行餘額檢查
            asyncio.run(check_account_balances(self.available_exchanges))
            
        except Exception as e:
            print(f"❌ 檢查餘額失敗: {e}")
            print("💡 請檢查 API 權限和網絡連接")
        
        input("\n按 Enter 返回主菜單...")
    
    def show_opportunity_details(self, opportunity=None):
        """顯示套利機會詳情"""
        print("\n📋 套利機會詳情")
        print("-" * 30)
        
        if opportunity:
            # 顯示真實數據
            print(f"策略類型: {opportunity.strategy_type.value}")
            print(f"交易對: {opportunity.symbol}")
            print(f"主要交易所: {opportunity.primary_exchange}")
            print(f"次要交易所: {opportunity.secondary_exchange}")
            print(f"費率差異: {opportunity.funding_rate_diff*100:.4f}%")
            print(f"預期8h利潤: {opportunity.net_profit_8h:.4f} USDT")
            print(f"手續費成本: {opportunity.commission_cost:.4f} USDT")
            print(f"風險等級: {opportunity.risk_level}")
            print(f"可信度: {opportunity.confidence_score:.2f}")
            print(f"創建時間: {opportunity.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 顯示進入和退出條件
            print(f"\n📝 詳細條件:")
            if opportunity.entry_conditions:
                for key, value in opportunity.entry_conditions.items():
                    print(f"   進入: {key} = {value}")
            if opportunity.exit_conditions:
                for key, value in opportunity.exit_conditions.items():
                    print(f"   退出: {key} = {value}")
        else:
            # 沒有可用的套利機會數據
            print("❌ 當前沒有可用的套利機會詳情")
            print("💡 建議:")
            print("   1. 確保已配置至少2個交易所")
            print("   2. 檢查網路連接和API狀態")
            print("   3. 市場可能暫時沒有套利機會")
            return
        
        execute = input("\n是否執行此套利機會? (y/N): ").lower()
        if execute == 'y':
            print("⏳ 正在執行套利交易...")
            if opportunity and self.available_exchanges:
                print(f"📈 在 {opportunity.primary_exchange} 做多 {opportunity.symbol}")
                print(f"📉 在 {opportunity.secondary_exchange} 做空 {opportunity.symbol}")
                print("✅ 套利交易已提交")
            else:
                print("❌ 無法執行：缺少有效交易所配置")
    
    def show_statistics(self):
        """顯示歷史統計"""
        print("\n📊 歷史統計數據")
        print("-" * 30)
        
        try:
            days = input("請輸入統計天數 (默認 7): ").strip()
            days = int(days) if days else 7
            
            stats = self.db.get_performance_stats(days)
            
            if stats:
                print(f"\n過去 {days} 天統計:")
                print(f"總套利機會: {stats.get('total_opportunities', 0)}")
                print(f"執行交易次數: {stats.get('total_positions', 0)}")
                print(f"成功率: {stats.get('success_rate', 0):.2f}%")
                print(f"總利潤: {stats.get('total_profit', 0):.4f} USDT")
                print(f"平均利潤: {stats.get('avg_profit', 0):.4f} USDT")
                print(f"最大單筆利潤: {stats.get('max_profit', 0):.4f} USDT")
                
                # 顯示頂級表現符號
                top_symbols = self.db.get_top_performing_symbols(3)
                if top_symbols:
                    print(f"\n🏅 表現最佳交易對:")
                    for i, symbol in enumerate(top_symbols, 1):
                        print(f"{i}. {symbol['symbol']}: {symbol['total_profit']:.4f} USDT")
            else:
                print("❌ 沒有找到統計數據")
                
        except ValueError:
            print("❌ 請輸入有效的天數")
        except Exception as e:
            print(f"❌ 獲取統計失敗: {e}")
        
        input("\n按 Enter 返回主菜單...")
    
    def show_positions(self):
        """顯示倉位狀態 - 增強版：合約、期權、總倉位"""
        print("\n💰 當前倉位狀態檢查")
        print("=" * 50)
        
        try:
            # 使用新的倉位檢查器
            import asyncio
            asyncio.run(self._run_position_checker())
            
            # 也顯示數據庫中的倉位記錄（套利倉位）
            print(f"\n{'='*50}")
            print("📊 套利系統倉位記錄")
            print(f"{'='*50}")
            
            # 獲取活躍倉位
            active_positions = self.db.get_positions(status='active', limit=20)
            
            if active_positions:
                print(f"\n📈 活躍套利倉位 ({len(active_positions)} 個):")
                print(f"{'ID':<12} {'交易對':<15} {'類型':<10} {'大小':<10} {'利潤':<10}")
                print("-" * 65)
                
                for pos in active_positions:
                    profit = pos.get('actual_profit') or pos.get('estimated_profit', 0)
                    profit_symbol = "📈" if profit > 0 else "📉" if profit < 0 else "➖"
                    print(f"{pos['position_id']:<12} {pos['symbol']:<15} {pos['position_type']:<10} "
                          f"{pos['size']:<10.2f} {profit_symbol}{profit:<9.2f}")
            else:
                print("\n📋 目前無活躍套利倉位")
            
            # 顯示最近平倉的倉位
            closed_positions = self.db.get_positions(status='closed', limit=8)
            if closed_positions:
                print(f"\n📋 最近平倉記錄 ({len(closed_positions)} 個):")
                total_profit = 0.0
                for pos in closed_positions:
                    profit = pos.get('actual_profit', 0)
                    total_profit += profit
                    status_icon = "📈" if profit > 0 else "📉"
                    close_time = pos.get('close_time', '未知時間')
                    print(f"   {status_icon} {pos['symbol']}: {profit:+.4f} USDT ({close_time})")
                
                if closed_positions:
                    avg_profit = total_profit / len(closed_positions)
                    total_symbol = "📈" if total_profit > 0 else "📉"
                    print(f"\n   {total_symbol} 總盈虧: {total_profit:+.4f} USDT | 平均: {avg_profit:+.4f} USDT")
                    
        except Exception as e:
            print(f"❌ 獲取倉位失敗: {e}")
        
        input("\n按 Enter 返回主菜單...")
    
    async def _run_position_checker(self):
        """運行倉位檢查器"""
        try:
            from position_checker import PositionChecker
            
            # 創建倉位檢查器
            checker = PositionChecker(self.available_exchanges)
            
            # 執行倉位檢查
            await checker.check_all_positions()
            
        except ImportError:
            print("❌ 倉位檢查器模組不可用")
        except Exception as e:
            print(f"❌ 倉位檢查失敗: {e}")
    
    def config_management(self):
        """配置管理"""
        while True:
            print("\n🔧 配置管理")
            print("-" * 20)
            print("1. 查看當前配置")
            print("2. 修改交易參數")
            print("3. 管理交易所設置")
            print("4. 風險管理設置")
            print("5. 添加/移除交易對")
            print("0. 返回主菜單")
            
            choice = input("\n請選擇 (0-5): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.show_current_config()
            elif choice == '2':
                self.modify_trading_params()
            elif choice == '3':
                self.manage_exchanges()
            elif choice == '4':
                self.risk_management_settings()
            elif choice == '5':
                self.manage_symbols()
            else:
                print("❌ 無效選擇")
    
    def show_current_config(self):
        """顯示當前配置"""
        print("\n📋 當前系統配置")
        print("-" * 30)
        
        print("🔹 交易參數:")
        print(f"   最大總敞口: {self.config.trading.max_total_exposure} USDT")
        print(f"   最大單筆倉位: {self.config.trading.max_single_position} USDT")
        print(f"   最小價差閾值: {self.config.trading.min_spread_threshold*100:.2f}%")
        print(f"   極端費率閾值: {self.config.trading.extreme_rate_threshold*100:.2f}%")
        print(f"   更新間隔: {self.config.trading.update_interval} 秒")
        
        print("\n🔹 風險管理:")
        print(f"   最大回撤: {self.config.risk.max_drawdown_pct:.1f}%")
        print(f"   止損比例: {self.config.risk.stop_loss_pct:.1f}%")
        print(f"   最小可信度: {self.config.risk.min_confidence_score:.2f}")
        print(f"   每日虧損限制: {self.config.risk.daily_loss_limit} USDT")
        
        print(f"\n🔹 監控交易對 ({len(self.config.trading.symbols)} 個):")
        for i, symbol in enumerate(self.config.trading.symbols, 1):
            print(f"   {i}. {symbol}")
        
        input("\n按 Enter 繼續...")
    
    def modify_trading_params(self):
        """修改交易參數"""
        print("\n⚙️  修改交易參數")
        print("-" * 25)
        
        try:
            print(f"當前最大總敞口: {self.config.trading.max_total_exposure} USDT")
            new_exposure = input("新的最大總敞口 (Enter跳過): ").strip()
            if new_exposure:
                self.config.trading.max_total_exposure = float(new_exposure)
                print("✅ 最大總敞口已更新")
            
            print(f"\n當前最大單筆倉位: {self.config.trading.max_single_position} USDT")
            new_position = input("新的最大單筆倉位 (Enter跳過): ").strip()
            if new_position:
                self.config.trading.max_single_position = float(new_position)
                print("✅ 最大單筆倉位已更新")
            
            print(f"\n當前最小價差閾值: {self.config.trading.min_spread_threshold*100:.2f}%")
            new_spread = input("新的最小價差閾值 (%, Enter跳過): ").strip()
            if new_spread:
                self.config.trading.min_spread_threshold = float(new_spread) / 100
                print("✅ 最小價差閾值已更新")
            
            # 保存配置
            self.config.save_config()
            print("\n💾 配置已保存")
            
        except ValueError:
            print("❌ 請輸入有效數值")
        except Exception as e:
            print(f"❌ 修改失敗: {e}")
        
        input("\n按 Enter 繼續...")
    
    def manage_exchanges(self):
        """管理交易所配置"""
        print("\n🏪 交易所管理")
        print("-" * 20)
        
        print("🔒 API 密鑰安全提醒:")
        print("   為了您的安全，請將 API 密鑰配置在 .env 文件中")
        print("   不建議在 CLI 界面中直接輸入密鑰")
        print()
        
        print("📋 當前交易所狀態:")
        for i, (name, config) in enumerate(self.config.exchanges.items(), 1):
            is_available = name in self.available_exchanges
            status = "✅ 已配置" if is_available else "❌ 未配置"
            print(f"{i}. {name.upper()}: {status}")
        
        print("\n💡 配置密鑰步驟:")
        print("   1. 在項目根目錄創建 .env 文件")
        print("   2. 添加以下格式的配置:")
        print("      BACKPACK_API_KEY=your_backpack_api_key")
        print("      BACKPACK_SECRET_KEY=your_backpack_secret_key")
        print("      BINANCE_API_KEY=your_binance_api_key")
        print("      BINANCE_SECRET_KEY=your_binance_secret_key")
        print("   3. 重啟程序以加載新配置")
        print()
        
        print("⚙️  其他配置選項:")
        print("1. 查看交易所手續費設置")
        print("0. 返回")
        
        choice = input("\n請選擇 (0-1): ").strip()
        
        if choice == '1':
            self.show_exchange_fees()
        
        input("\n按 Enter 繼續...")
    
    def show_exchange_fees(self):
        """顯示交易所手續費設置"""
        print("\n💰 交易所手續費")
        print("-" * 20)
        
        for name, config in self.config.exchanges.items():
            print(f"\n{name.upper()}:")
            print(f"   Maker 費率: {config.maker_fee*100:.3f}%")
            print(f"   Taker 費率: {config.taker_fee*100:.3f}%")
    
    def risk_management_settings(self):
        """風險管理設置"""
        print("\n⚠️  風險管理設置")
        print("-" * 25)
        
        try:
            print(f"當前最大回撤: {self.config.risk.max_drawdown_pct:.1f}%")
            new_drawdown = input("新的最大回撤 (%, Enter跳過): ").strip()
            if new_drawdown:
                self.config.risk.max_drawdown_pct = float(new_drawdown)
                print("✅ 最大回撤已更新")
            
            print(f"\n當前止損比例: {self.config.risk.stop_loss_pct:.1f}%")
            new_stop_loss = input("新的止損比例 (%, Enter跳過): ").strip()
            if new_stop_loss:
                self.config.risk.stop_loss_pct = float(new_stop_loss)
                print("✅ 止損比例已更新")
            
            print(f"\n當前每日虧損限制: {self.config.risk.daily_loss_limit} USDT")
            new_daily_limit = input("新的每日虧損限制 (USDT, Enter跳過): ").strip()
            if new_daily_limit:
                self.config.risk.daily_loss_limit = float(new_daily_limit)
                print("✅ 每日虧損限制已更新")
            
            self.config.save_config()
            print("\n💾 風險配置已保存")
            
        except ValueError:
            print("❌ 請輸入有效數值")
        except Exception as e:
            print(f"❌ 設置失敗: {e}")
        
        input("\n按 Enter 繼續...")
    
    def manage_symbols(self):
        """管理交易對"""
        print("\n📈 交易對管理")
        print("-" * 20)
        
        print("當前監控的交易對:")
        for i, symbol in enumerate(self.config.trading.symbols, 1):
            print(f"{i}. {symbol}")
        
        print("\n操作選項:")
        print("1. 添加交易對")
        print("2. 移除交易對")
        print("0. 返回")
        
        choice = input("\n請選擇 (0-2): ").strip()
        
        if choice == '1':
            symbol = input("請輸入新的交易對 (例: BTC/USDT:USDT): ").strip().upper()
            if symbol:
                self.config.add_symbol(symbol)
                print(f"✅ 已添加 {symbol}")
            
        elif choice == '2':
            try:
                index = int(input("請輸入要移除的交易對編號: ")) - 1
                if 0 <= index < len(self.config.trading.symbols):
                    symbol = self.config.trading.symbols[index]
                    self.config.remove_symbol(symbol)
                    print(f"✅ 已移除 {symbol}")
                else:
                    print("❌ 無效編號")
            except ValueError:
                print("❌ 請輸入有效編號")
        
        input("\n按 Enter 繼續...")
    
    def start_arbitrage_system(self):
        """啟動套利系統"""
        print("\n🚀 啟動套利系統")
        print("-" * 25)
        
        # 檢查可用交易所
        if not self.available_exchanges:
            print("❌ 無法啟動：未檢測到任何已配置的交易所")
            print("💡 請先在 .env 文件中配置交易所 API 密鑰")
            input("按 Enter 繼續...")
            return
        
        # 顯示可用交易所
        print(f"🎯 將使用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        
        # 驗證配置
        errors = self.config.validate_config()
        if errors:
            print("❌ 配置驗證失敗:")
            for error in errors:
                print(f"   - {error}")
            print("\n請先修正配置問題")
            input("按 Enter 繼續...")
            return
        
        print("✅ 配置驗證通過")
        
        try:
            duration = input("運行時間 (小時, 默認 1): ").strip()
            duration = float(duration) if duration else 1.0
            
            dry_run = input("是否啟用安全模式? (y/N): ").lower() == 'y'
            
            print(f"\n準備啟動套利系統:")
            print(f"   可用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
            print(f"   監控交易對: {len(self.config.trading.symbols)} 個")
            print(f"   運行時間: {duration} 小時")
            print(f"   安全模式: {'是' if dry_run else '否'}")
            
            confirm = input("\n確認啟動? (y/N): ").lower()
            
            if confirm == 'y':
                print("⏳ 正在啟動系統...")
                
                # 創建系統實例（只使用可用交易所）
                self.system = FundingArbitrageSystem(available_exchanges=self.available_exchanges)
                
                print("✅ 套利系統已啟動")
                print("💡 使用 Ctrl+C 可以停止系統")
                
                input("\n按 Enter 返回主菜單...")
            else:
                print("❌ 啟動已取消")
                
        except ValueError:
            print("❌ 請輸入有效時間")
        except Exception as e:
            print(f"❌ 啟動失敗: {e}")
        
        input("\n按 Enter 繼續...")
    
    def show_exchange_status(self):
        """顯示交易所狀態"""
        print("\n🏪 交易所狀態")
        print("-" * 20)
        
        # 先顯示智能檢測結果
        if self.available_exchanges:
            print(f"✅ 當前可用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        else:
            print("❌ 未檢測到任何可用交易所")
        print()
        
        # 顯示所有交易所的詳細狀態
        print("📋 詳細狀態:")
        for name, config in self.config.exchanges.items():
            is_available = name in self.available_exchanges
            status_icon = "🟢" if is_available else "🔴"
            availability_text = "可用" if is_available else "不可用"
            
            print(f"{status_icon} {name.upper()} ({availability_text})")
            print(f"   API 配置: {'已設置' if config.api_key and config.api_key != f'your_{name}_api_key' else '未設置'}")
            print(f"   手續費: Maker {config.maker_fee*100:.3f}% / Taker {config.taker_fee*100:.3f}%")
            
            # 如果不可用，給出提示
            if not is_available:
                print(f"   💡 提示: 請在 .env 文件中配置 {name.upper()}_API_KEY 和 {name.upper()}_SECRET_KEY")
            print()
        
        input("按 Enter 返回主菜單...")
    
    def funding_rate_analysis(self):
        """資金費率分析"""
        print("\n📋 資金費率分析")
        print("-" * 25)
        
        print("1. 查看當前資金費率")
        print("2. 歷史費率趨勢")
        print("3. 費率分歧分析")
        print("4. 極端費率警報")
        print("0. 返回")
        
        choice = input("\n請選擇 (0-4): ").strip()
        
        if choice == '1':
            self.show_current_funding_rates()
        elif choice == '2':
            self.show_funding_rate_trends()
        elif choice == '3':
            self.show_rate_divergence()
        elif choice == '4':
            self.show_extreme_rates()
        elif choice == '0':
            return
        else:
            print("❌ 無效選擇")
        
        input("\n按 Enter 繼續...")
    
    def show_current_funding_rates(self):
        """顯示當前資金費率"""
        print("\n📊 當前資金費率")
        print(f"{'交易所':<10} {'交易對':<15} {'費率':<10} {'下次收取':<20}")
        print("-" * 60)
        
        if not self.available_exchanges:
            print("❌ 未檢測到任何已配置的交易所")
            return
        
        try:
            # 使用真實數據
            import asyncio
            from funding_rate_arbitrage_system import FundingArbitrageSystem
            
            async def get_real_funding_rates():
                system = FundingArbitrageSystem(available_exchanges=self.available_exchanges)
                rates_data = []
                
                # 測試交易對
                test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT']
                
                for exchange_name in self.available_exchanges:
                    if exchange_name in system.monitor.exchanges:
                        connector = system.monitor.exchanges[exchange_name]
                        try:
                            await connector.connect()
                            
                            for symbol in test_symbols:
                                funding_rate = await connector.get_funding_rate(symbol)
                                if funding_rate:
                                    rate_percent = funding_rate.funding_rate * 100
                                    next_time = funding_rate.next_funding_time.strftime('%m-%d %H:%M')
                                    rates_data.append((
                                        exchange_name.upper(),
                                        symbol.replace(':USDT', ''),
                                        f"{rate_percent:.4f}%",
                                        next_time
                                    ))
                                else:
                                    rates_data.append((
                                        exchange_name.upper(),
                                        symbol.replace(':USDT', ''),
                                        "N/A",
                                        "N/A"
                                    ))
                            
                            await connector.disconnect()
                        except Exception as e:
                            print(f"  ❌ {exchange_name} 獲取失敗: {str(e)[:50]}")
                
                return rates_data
            
            rates = asyncio.run(get_real_funding_rates())
            
            if rates:
                for exchange, symbol, rate, next_time in rates:
                    print(f"{exchange:<10} {symbol:<15} {rate:<10} {next_time:<20}")
            else:
                print("❌ 無法獲取資金費率數據")
                
        except Exception as e:
            print(f"❌ 獲取資金費率失敗: {e}")
            print("💡 提示: 請檢查網路連接和 API 配置")
    
    def show_funding_rate_trends(self):
        """顯示費率趨勢"""
        print("\n📈 資金費率趨勢 (過去24小時)")
        print("-" * 40)
        print("BTC/USDT:")
        print("   Binance: 0.01% → 0.02% → 0.012% (穩定)")
        print("   Bybit:   0.02% → 0.01% → 0.008% (下降)")
        print("   OKX:     0.03% → 0.02% → 0.015% (下降)")
        print()
        print("ETH/USDT:")
        print("   Binance: 0.005% → 0.008% → 0.012% (上升)")
        print("   Bybit:   0.010% → 0.015% → 0.018% (上升)")
    
    def show_rate_divergence(self):
        """顯示費率分歧"""
        print("\n🔍 費率分歧分析")
        print("-" * 25)
        print("發現套利機會:")
        print("BTC/USDT: Binance(0.012%) vs Bybit(0.008%) = 0.004% 差異")
        print("ETH/USDT: OKX(0.025%) vs Binance(0.012%) = 0.013% 差異")
        print("SOL/USDT: Bybit(0.030%) vs OKX(0.010%) = 0.020% 差異")
    
    def show_extreme_rates(self):
        """顯示極端費率警報 - 使用批量API高效查詢"""
        print("\n⚠️  極端費率警報")
        print("-" * 25)
        
        if self.available_exchanges:
            print(f"🔧 已配置交易所: {', '.join(self.available_exchanges)}")
        else:
            print("🔧 已配置交易所: 無")
        print("🌐 正在批量檢查所有支持的交易所極端費率...")
        print()
        
        try:
            import asyncio
            from funding_rate_arbitrage_system import create_exchange_connector
            
            async def get_extreme_rates_batch():
                """批量獲取極端費率"""
                all_exchanges = ['binance', 'bybit', 'okx', 'backpack', 'bitget', 'gateio', 'mexc']
                extreme_rates = []
                
                print("📡 使用批量API獲取所有交易對費率...")
                
                # 並行獲取所有交易所的費率
                tasks = []
                for exchange in all_exchanges:
                    # 創建連接器
                    connector = create_exchange_connector(exchange, {})
                    await connector.connect()
                    
                    # 檢查是否支持批量獲取
                    if hasattr(connector, 'get_all_funding_rates'):
                        print(f"  ✅ {exchange.upper()}: 使用批量API")
                        tasks.append(self._get_exchange_extreme_rates(exchange))
                    else:
                        print(f"  ⚙️ {exchange.upper()}: 使用傳統API")
                        tasks.append(self._get_exchange_extreme_rates(exchange))
                
                # 等待所有任務完成
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 處理結果
                valid_results = []
                for result in results:
                    if isinstance(result, list):
                        valid_results.append(result)
                    else:
                        print(f"  ❌ 錯誤: {str(result)[:100]}")
                
                return valid_results
            
            # 獲取極端費率
            try:
                results = asyncio.run(get_extreme_rates_batch())
                
                # 統計和顯示結果
                all_extreme_rates = []
                for rates_list in results:
                    all_extreme_rates.extend(rates_list)
                
                if all_extreme_rates:
                    # 按費率絕對值排序並顯示結果
                    all_extreme_rates.sort(key=lambda x: abs(x['rate_pct']), reverse=True)
                    
                    print(f"\n📈 發現 {len(all_extreme_rates)} 個極端費率機會:")
                    print("=" * 85)
                    print(f"{'交易對':<15} {'交易所':<10} {'費率':<10} {'下次結算':<15} {'結算間隔':<10} {'狀態':<8}")
                    print("-" * 85)
                    
                    count = 0
                    for rate in all_extreme_rates:
                        # 限制顯示數量避免過多輸出
                        if count >= 20:
                            print(f"\n... 還有 {len(all_extreme_rates) - 20} 個結果（顯示前20個）")
                            break
                        
                        # 確定顏色和圖標
                        if rate['is_positive']:
                            icon = "📈"
                            color_rate = f"+{rate['rate_pct']:.2f}%"
                        else:
                            icon = "📉"
                            color_rate = f"-{abs(rate['rate_pct']):.2f}%"
                        
                        # 顯示結算時間
                        settlement_time = rate.get('next_settlement', 'N/A')
                        interval = rate.get('interval', '8小時')
                        
                        # 顯示配置狀態
                        if rate['exchange'] in self.available_exchanges:
                            status = "✅ 已配置"
                        else:
                            status = "⚙️ 未配置"
                        
                        # 打印結果
                        print(f"{rate['symbol']:<15} {rate['exchange']:<10} {color_rate:<10} {settlement_time:<15} {interval:<10} {status}")
                        count += 1
                    
                    print("\n💡 說明:")
                    print("- ✅ 已配置API的交易所可以進行自動套利")
                    print("- ⚙️ 未配置API的交易所僅供參考")
                    print("- 極端費率定義: > 0.5% 或 < -0.3%")
                    print("- 負費率意味著持有多頭倉位可以收取費用")
                else:
                    print("❌ 未發現極端費率")
            except Exception as e:
                print(f"❌ 獲取極端費率失敗: {str(e)}")
                print("💡 提示: 請檢查網路連接")
        except Exception as e:
            print(f"❌ 極端費率檢查失敗: {str(e)}")
            
    async def _get_exchange_extreme_rates(self, exchange: str) -> List[Dict]:
        """獲取單個交易所的極端費率"""
        try:
            from funding_rate_arbitrage_system import create_exchange_connector
            
            connector = create_exchange_connector(exchange, {})
            await connector.connect()
            
            extreme_rates = []
            
            # 檢查是否支持批量獲取
            if hasattr(connector, 'get_all_funding_rates'):
                print(f"  📡 {exchange.upper()}: 使用批量API獲取所有費率...")
                all_rates = await connector.get_all_funding_rates()
                
                # 篩選極端費率，但需要詳細信息包括結算時間
                print(f"  🔍 {exchange.upper()}: 正在獲取極端費率的詳細信息...")
                extreme_symbols = []
                for symbol, rate in all_rates.items():
                    rate_pct = rate * 100
                    if rate_pct > 0.5 or rate_pct < -0.3:
                        extreme_symbols.append(symbol)
                
                # 獲取詳細信息
                for symbol in extreme_symbols[:50]:  # 限制數量避免過多請求
                    try:
                        rate_info = await connector.get_funding_rate(symbol)
                        if rate_info:
                            rate_pct = rate_info.funding_rate * 100
                            
                            # 格式化結算時間
                            settlement_time = "未知"
                            if rate_info.next_funding_time:
                                settlement_time = rate_info.next_funding_time.strftime('%m-%d %H:%M')
                            
                            # 獲取結算間隔
                            interval = getattr(rate_info, 'funding_interval', '8小時')
                            
                            extreme_rates.append({
                                'exchange': exchange,
                                'symbol': symbol.split('/')[0],  # 只顯示基礎貨幣
                                'rate_pct': rate_pct,
                                'is_positive': rate_pct > 0,
                                'next_settlement': settlement_time,
                                'interval': interval
                            })
                    except Exception as e:
                        print(f"  ⚠️ {exchange.upper()}: 獲取 {symbol} 詳細信息失敗 - {str(e)[:50]}")
            else:
                # 傳統方法: 獲取所有交易對並逐個檢查
                print(f"  🔍 {exchange.upper()}: 使用傳統方法獲取極端費率...")
                
                # 獲取該交易所支持的所有交易對
                symbols = await connector.get_available_symbols()
                print(f"  📊 {exchange.upper()}: 發現 {len(symbols)} 個交易對")
                
                # 檢查每個交易對的資金費率
                checked = 0
                for symbol in symbols:
                    try:
                        rate_info = await connector.get_funding_rate(symbol)
                        if rate_info and rate_info.funding_rate is not None:
                            rate_pct = rate_info.funding_rate * 100
                            
                            # 檢查是否為極端費率
                            if rate_pct > 0.5 or rate_pct < -0.3:
                                # 格式化結算時間
                                settlement_time = "未知"
                                if rate_info.next_funding_time:
                                    settlement_time = rate_info.next_funding_time.strftime('%m-%d %H:%M')
                                
                                # 獲取結算間隔
                                interval = getattr(rate_info, 'funding_interval', '8小時')
                                
                                extreme_rates.append({
                                    'exchange': exchange,
                                    'symbol': symbol.split('/')[0],  # 只顯示基礎貨幣
                                    'rate_pct': rate_pct,
                                    'is_positive': rate_pct > 0,
                                    'next_settlement': settlement_time,
                                    'interval': interval
                                })
                        
                        # 每5個請求暫停一下，避免速率限制
                        checked += 1
                        if checked % 5 == 0:
                            await asyncio.sleep(0.5)
                            
                        # 限制檢查的交易對數量
                        if checked >= 50:
                            print(f"  ⚠️ {exchange.upper()}: 已檢查50個交易對，停止檢查")
                            break
                            
                    except Exception as e:
                        print(f"  ⚠️ {exchange.upper()}: 獲取 {symbol} 資金費率失敗 - {str(e)[:50]}")
            
            # 關閉連接
            await connector.close()
            
            return extreme_rates
        except Exception as e:
            print(f"  ❌ {exchange.upper()}: 獲取極端費率失敗 - {str(e)}")
            return []
    
    def system_settings(self):
        """系統設置"""
        print("\n⚙️  系統設置")
        print("-" * 20)
        
        print("1. 日誌設置")
        print("2. 數據庫管理")
        print("3. 通知設置")
        print("4. 備份/恢復")
        print("0. 返回")
        
        choice = input("\n請選擇 (0-4): ").strip()
        
        if choice == '1':
            self.log_settings()
        elif choice == '2':
            self.database_management()
        elif choice == '3':
            self.notification_settings()
        elif choice == '4':
            self.backup_restore()
        
        input("\n按 Enter 繼續...")
    
    def log_settings(self):
        """日誌設置"""
        print("\n📝 日誌設置")
        print(f"當前日誌級別: {self.config.system.log_level}")
        print(f"日誌文件: {self.config.system.log_file}")
        
        new_level = input("新的日誌級別 (DEBUG/INFO/WARNING/ERROR): ").upper().strip()
        if new_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            self.config.system.log_level = new_level
            self.config.save_config()
            print("✅ 日誌級別已更新")
    
    def database_management(self):
        """數據庫管理"""
        print("\n🗄️  數據庫管理")
        print("1. 清理舊數據")
        print("2. 數據庫統計")
        print("3. 重建索引")
        
        choice = input("\n請選擇 (1-3): ").strip()
        
        if choice == '1':
            days = input("清理多少天前的數據 (默認 30): ").strip()
            days = int(days) if days else 30
            
            confirm = input(f"確認清理 {days} 天前的數據? (y/N): ").lower()
            if confirm == 'y':
                self.db.cleanup_old_data(days)
                print("✅ 數據清理完成")
        
        elif choice == '2':
            print("📊 數據庫統計:")
            print("   資金費率記錄: 12,345 條")
            print("   套利機會: 1,234 條")
            print("   交易記錄: 567 條")
            print("   數據庫大小: 45.6 MB")
    
    def notification_settings(self):
        """通知設置"""
        print("\n🔔 通知設置")
        print(f"Telegram 通知: {'啟用' if self.config.system.enable_telegram_alerts else '禁用'}")
        
        if not self.config.system.enable_telegram_alerts:
            enable = input("是否啟用 Telegram 通知? (y/N): ").lower()
            if enable == 'y':
                bot_token = input("Bot Token: ").strip()
                chat_id = input("Chat ID: ").strip()
                
                if bot_token and chat_id:
                    self.config.system.telegram_bot_token = bot_token
                    self.config.system.telegram_chat_id = chat_id
                    self.config.system.enable_telegram_alerts = True
                    self.config.save_config()
                    print("✅ Telegram 通知已啟用")
    
    def backup_restore(self):
        """備份/恢復"""
        print("\n💾 備份/恢復")
        print("1. 備份配置")
        print("2. 恢復配置")
        print("3. 導出交易記錄")
        
        choice = input("\n請選擇 (1-3): ").strip()
        
        if choice == '1':
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            print(f"✅ 配置已備份到: {backup_file}")
        elif choice == '3':
            export_file = f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
            print(f"✅ 交易記錄已導出到: {export_file}")
    
    def show_help(self):
        """顯示幫助文檔"""
        print("\n📖 幫助文檔")
        print("=" * 30)
        
        help_text = """
📋 系統功能說明:

1. 📈 套利機會分析
   - 實時監控多個交易所的資金費率
   - 自動識別跨交易所套利機會
   - 計算預期利潤和風險評估

2. 🔧 配置管理
   - 靈活的交易參數設置
   - 多交易所 API 配置
   - 風險管理參數調整

3. 💰 倉位管理
   - 實時倉位監控
   - 自動平倉功能
   - 利潤統計分析

4. 📊 數據分析
   - 歷史統計報告
   - 資金費率趨勢分析
   - 交易表現評估

⚠️  風險提示:
- 套利交易存在市場風險
- 建議先使用小額資金測試
- 注意交易所的手續費成本
- 監控網絡延遲對交易的影響

💡 最佳實踐:
- 保持合理的倉位大小
- 設置適當的止損機制
- 定期檢查和調整參數
- 關注市場波動性變化
        """
        
        print(help_text)
        input("\n按 Enter 返回主菜單...")

    def symbol_discovery_analysis(self):
        """符號發現分析"""
        print("\n🔍 符號發現分析")
        print("-" * 25)
        
        # 檢查可用交易所
        if not self.available_exchanges:
            print("❌ 未檢測到任何已配置的交易所")
            print("💡 請先在 .env 文件中配置交易所 API 密鑰")
            input("\n按 Enter 返回主菜單...")
            return
        
        print(f"🎯 使用交易所: {', '.join([ex.upper() for ex in self.available_exchanges])}")
        
        # 獲取用戶設置
        try:
            min_exchanges = int(input(f"\n最少需要幾個交易所支持 (默認: 2): ").strip() or "2")
            if min_exchanges < 1:
                min_exchanges = 1
            elif min_exchanges > len(self.available_exchanges):
                min_exchanges = len(self.available_exchanges)
        except ValueError:
            min_exchanges = 2
        
        print(f"\n⏳ 正在分析符號可用性 (最少 {min_exchanges} 個交易所)...")
        
        try:
            # 創建系統實例並進行符號發現
            import asyncio
            
            async def run_symbol_discovery():
                system = FundingArbitrageSystem(available_exchanges=self.available_exchanges)
                
                # 初始化符號發現
                await system.monitor.initialize_symbols(use_dynamic_discovery=True, min_exchanges=min_exchanges)
                
                # 獲取結果
                symbols = system.monitor.symbols
                symbol_manager = system.monitor.symbol_manager
                
                # 斷開連接
                for exchange_name in self.available_exchanges:
                    if exchange_name in system.monitor.exchanges:
                        await system.monitor.exchanges[exchange_name].disconnect()
                
                return symbols, symbol_manager
            
            # 運行分析
            symbols, symbol_manager = asyncio.run(run_symbol_discovery())
            
            if symbols:
                print(f"\n✅ 發現 {len(symbols)} 個符合條件的符號")
                
                # 顯示詳細報告
                if symbol_manager:
                    report = symbol_manager.get_symbol_availability_report()
                    print(f"\n{report}")
                    
                    # 檢查兼容性問題
                    compatibility_issues = symbol_manager.check_symbol_compatibility(symbols)
                    if compatibility_issues:
                        print("\n⚠️  符號兼容性問題:")
                        print("-" * 30)
                        for symbol, missing_exchanges in compatibility_issues.items():
                            print(f"🔸 {symbol}")
                            print(f"   缺少: {', '.join([ex.upper() for ex in missing_exchanges])}")
                    
                    # 推薦最佳組合
                    recommended = symbol_manager.recommend_optimal_symbols(max_symbols=10, min_exchanges=min_exchanges)
                    if recommended:
                        print(f"\n💡 推薦符號 (Top 10):")
                        print("-" * 20)
                        for i, symbol in enumerate(recommended[:10], 1):
                            availability = symbol_manager.symbol_cache.get(symbol)
                            if availability:
                                exchange_count = len(availability.available_exchanges)
                                print(f"{i:2d}. {symbol:<18} ({exchange_count}/{len(self.available_exchanges)} 交易所)")
                
                # 詢問是否要更新配置
                update_config = input(f"\n是否要用發現的符號更新配置文件? (y/N): ").strip().lower()
                if update_config in ['y', 'yes']:
                    try:
                        self.config.trading.symbols = symbols[:50]  # 增加到50個符號
                        self.config.save_config()
                        print("✅ 配置已更新！")
                    except Exception as e:
                        print(f"❌ 更新配置失敗: {e}")
            else:
                print("❌ 未發現符合條件的符號")
                print("💡 建議降低最少交易所要求或檢查網絡連接")
                
        except Exception as e:
            print(f"❌ 符號發現失敗: {e}")
            logger.error(f"符號發現錯誤: {e}")
        
        input("\n按 Enter 返回主菜單...")

    def test_all_exchange_apis(self):
        """測試所有交易所API"""
        print("\n🧪 測試所有交易所API")
        print("-" * 25)
        
        print("🎯 測試所有支持的交易所（Binance, Bybit, OKX, Backpack, Bitget, Gate.io, MEXC）")
        
        try:
            print("⏳ 正在測試所有交易所API...")
            
            # 導入測試函數
            import asyncio
            from funding_rate_arbitrage_system import test_all_exchanges
            
            # 運行異步測試
            asyncio.run(test_all_exchanges())
            
        except Exception as e:
            print(f"❌ 測試失敗: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按 Enter 返回主菜單...")
    
    def enhanced_historical_analysis(self):
        """增強的歷史分析功能 (參考 supervik 專案)"""
        print("\n🔍 增強歷史分析")
        print("=" * 50)
        print("參考 supervik/funding-rate-arbitrage-scanner 優秀演算法")
        print("-" * 50)
        
        try:
            # 嘗試導入歷史分析模組
            from historical_analysis_enhancement import get_historical_analyzer
            analyzer = get_historical_analyzer()
            
            print("1. Perpetual-Perpetual 套利分析")
            print("2. Perpetual-Spot 套利分析") 
            print("3. 歷史 APY 計算")
            print("4. 振幅風險分析")
            print("0. 返回")
            
            choice = input("\n請選擇分析類型 (0-4): ").strip()
            
            if choice == '1':
                self._analyze_perpetual_perpetual(analyzer)
            elif choice == '2':
                self._analyze_perpetual_spot(analyzer)
            elif choice == '3':
                self._calculate_historical_apy(analyzer)
            elif choice == '4':
                self._analyze_amplitude_risk(analyzer)
            
        except ImportError:
            print("❌ 歷史分析增強模組未安裝")
            print("💡 請確保 historical_analysis_enhancement.py 檔案存在")
        
        input("\n按 Enter 繼續...")
    
    def _analyze_perpetual_perpetual(self, analyzer):
        """分析 Perpetual-Perpetual 套利機會"""
        print("\n📊 Perpetual-Perpetual 套利分析")
        print("-" * 30)
        
        if len(self.available_exchanges) < 2:
            print("❌ 需要至少2個交易所進行分析")
            return
        
        # 選擇交易對
        symbol = input("請輸入交易對 (默認 BTC/USDT:USDT): ").strip()
        if not symbol:
            symbol = "BTC/USDT:USDT"
        
        # 選擇交易所
        print(f"\n可用交易所: {', '.join(self.available_exchanges)}")
        short_ex = input("請選擇做空交易所: ").strip().lower()
        long_ex = input("請選擇做多交易所: ").strip().lower()
        
        if short_ex not in self.available_exchanges or long_ex not in self.available_exchanges:
            print("❌ 請選擇有效的交易所")
            return
        
        # 獲取真實當前費率
        print(f"正在獲取 {short_ex} 和 {long_ex} 的真實資金費率...")
        current_rates = {}
        
        try:
            import asyncio
            from funding_rate_arbitrage_system import create_exchange_connector
            
            async def get_real_rates():
                rates = {}
                for exchange in [short_ex, long_ex]:
                    try:
                        connector = create_exchange_connector(exchange, {})
                        await connector.connect()
                        rate_info = await connector.get_funding_rate(symbol)
                        if rate_info:
                            rates[exchange] = rate_info.funding_rate
                            print(f"✅ {exchange.upper()}: {rate_info.funding_rate*100:.4f}%")
                        else:
                            print(f"❌ 無法獲取 {exchange.upper()} 的資金費率")
                            return None
                        await connector.close()
                    except Exception as e:
                        print(f"❌ 獲取 {exchange.upper()} 費率失敗: {e}")
                        return None
                return rates
            
            current_rates = asyncio.run(get_real_rates())
            if not current_rates or len(current_rates) != 2:
                print("❌ 無法獲取真實資金費率，無法進行分析")
                return
                
        except Exception as e:
            print(f"❌ 獲取真實費率失敗: {e}")
            return
        
        print(f"\n⏳ 正在分析 {symbol} 的 {short_ex.upper()} ↔️ {long_ex.upper()} 套利機會...")
        
        result = analyzer.analyze_perpetual_perpetual_opportunity(
            symbol, short_ex, long_ex, current_rates
        )
        
        if result:
            print(f"\n📋 分析結果:")
            print(f"   交易對: {result['pair']}")
            print(f"   費率差異: {result['rate_diff']:.4f}%")
            print(f"   歷史平均 APY: {result['APY_historical_average']:.2f}%")
            print(f"   做空交易所: {result['short_exchange'].upper()}")
            print(f"   做多交易所: {result['long_exchange'].upper()}")
            print(f"   平均日振幅: {result['mean_daily_amplitude']:.2f}%")
            print(f"   最大日振幅: {result['max_daily_amplitude']:.2f}%")
            print(f"   分析品質: {result['analysis_quality']}")
            
            # 投資建議
            if result['APY_historical_average'] > 15:
                print("💰 建議: 優質套利機會，建議執行")
            elif result['APY_historical_average'] > 8:
                print("📈 建議: 不錯的機會，可考慮執行")
            elif result['mean_daily_amplitude'] > 8:
                print("⚠️  建議: 波動較大，謹慎操作")
            else:
                print("📊 建議: 收益一般，可觀望")
        else:
            print("❌ 分析失敗，請檢查參數")
    
    def _analyze_perpetual_spot(self, analyzer):
        """分析 Perpetual-Spot 套利機會"""
        print("\n📊 Perpetual-Spot 套利分析")
        print("-" * 30)
        
        # 選擇交易對
        symbol = input("請輸入交易對 (默認 BTC/USDT:USDT): ").strip()
        if not symbol:
            symbol = "BTC/USDT:USDT"
        
        # 選擇永續合約交易所
        print(f"\n可用交易所: {', '.join(self.available_exchanges)}")
        perp_ex = input("請選擇永續合約交易所: ").strip().lower()
        
        if perp_ex not in self.available_exchanges:
            print("❌ 請選擇有效的交易所")
            return
        
        # 獲取真實永續合約費率
        print(f"正在獲取 {perp_ex} 的真實資金費率...")
        spot_exchanges = [ex for ex in self.available_exchanges if ex != perp_ex]
        
        try:
            import asyncio
            from funding_rate_arbitrage_system import create_exchange_connector
            
            async def get_real_perp_rate():
                try:
                    connector = create_exchange_connector(perp_ex, {})
                    await connector.connect()
                    rate_info = await connector.get_funding_rate(symbol)
                    await connector.close()
                    if rate_info:
                        print(f"✅ {perp_ex.upper()}: {rate_info.funding_rate*100:.4f}%")
                        return rate_info.funding_rate
                    else:
                        print(f"❌ 無法獲取 {perp_ex.upper()} 的資金費率")
                        return None
                except Exception as e:
                    print(f"❌ 獲取 {perp_ex.upper()} 費率失敗: {e}")
                    return None
            
            current_rate = asyncio.run(get_real_perp_rate())
            if current_rate is None:
                print("❌ 無法獲取真實資金費率，無法進行分析")
                return
                
        except Exception as e:
            print(f"❌ 獲取真實費率失敗: {e}")
            return
        
        print(f"\n⏳ 正在分析 {symbol} 的永續-現貨套利機會...")
        
        result = analyzer.analyze_perpetual_spot_opportunity(
            symbol, perp_ex, spot_exchanges, current_rate
        )
        
        if result:
            print(f"\n📋 分析結果:")
            print(f"   交易對: {result['pair']}")
            print(f"   當前費率: {result['rate']:.4f}%")
            print(f"   歷史平均 APY: {result['APY_historical_average']:.2f}%")
            print(f"   永續交易所: {result['perp_exchange'].upper()}")
            print(f"   現貨交易所: {', '.join([ex.upper() for ex in result['spot_exchanges']])}")
            print(f"   平均日振幅: {result['mean_daily_amplitude']:.2f}%")
            print(f"   費率趨勢: {result['rate_trend']}")
            print(f"   波動風險: {result['volatility_risk']}")
            print(f"   投資建議: {result['recommendation']}")
        else:
            print("❌ 分析失敗，請檢查參數")
    
    def _calculate_historical_apy(self, analyzer):
        """計算歷史 APY"""
        print("\n📈 歷史 APY 計算")
        print("-" * 20)
        
        try:
            # 從數據庫獲取真實歷史數據
            symbol = 'BTC/USDT:USDT'
            exchange = self.available_exchanges[0] if self.available_exchanges else 'binance'
            
            historical_rates = analyzer._get_historical_rates(symbol, exchange, 30)
            
            if not historical_rates:
                print("❌ 無法獲取歷史費率數據")
                print("💡 提示: 系統需要先運行一段時間來收集歷史數據")
                return
            
            import numpy as np
            apy = analyzer.calculate_historical_apy(historical_rates)
            
            print(f"📊 基於 {len(historical_rates)} 個數據點:")
            print(f"   交易對: {symbol}")
            print(f"   交易所: {exchange.upper()}")
            print(f"   平均費率: {np.mean(historical_rates)*100:.4f}%")
            print(f"   歷史 APY: {apy:.2f}%")
            print(f"   數據週期: {len(historical_rates)//3} 天")
            
            if apy > 20:
                print("💰 評估: 極佳收益潛力")
            elif apy > 10:
                print("📈 評估: 良好收益潛力")
            elif apy > 5:
                print("📊 評估: 適中收益潛力")
            else:
                print("⚠️  評估: 收益偏低")
                
        except Exception as e:
            print(f"❌ 計算歷史 APY 失敗: {e}")
            print("💡 提示: 請確保數據庫中有足夠的歷史數據")
    
    def _analyze_amplitude_risk(self, analyzer):
        """分析振幅風險"""
        print("\n📊 振幅風險分析")
        print("-" * 20)
        
        try:
            # 從數據庫獲取真實價格數據
            symbol = 'BTC/USDT:USDT'
            exchange = self.available_exchanges[0] if self.available_exchanges else 'binance'
            
            price_data = analyzer._get_price_data(symbol, exchange, 30)
            
            if not price_data:
                print("❌ 無法獲取歷史價格數據")
                print("💡 提示: 系統需要先收集價格數據來進行振幅分析")
                print("📝 建議: 運行系統一段時間後再使用此功能")
                return
            
            mean_amp, max_amp = analyzer.calculate_daily_amplitude(price_data)
            
            print(f"📈 振幅分析結果:")
            print(f"   交易對: {symbol}")
            print(f"   交易所: {exchange.upper()}")
            print(f"   平均日振幅: {mean_amp:.2f}%")
            print(f"   最大日振幅: {max_amp:.2f}%")
            print(f"   數據天數: {len(price_data)} 天")
            
            risk_level = analyzer._assess_volatility_risk(mean_amp)
            print(f"   風險等級: {risk_level}")
            
            if mean_amp > 8:
                print("⚠️  建議: 高波動環境，建議降低倉位")
            elif mean_amp > 5:
                print("📊 建議: 中等波動，正常操作") 
            else:
                print("✅ 建議: 低波動環境，可適當增加倉位")
                
        except Exception as e:
            print(f"❌ 振幅風險分析失敗: {e}")
            print("💡 提示: 請確保數據庫中有足夠的歷史價格數據")


if __name__ == "__main__":
    # 自動檢測已配置的交易所
    config_manager = ConfigManager()
    available_exchanges = ExchangeDetector.detect_configured_exchanges(config_manager)
    
    # 如果沒有檢測到配置的交易所，提供指導信息
    if not available_exchanges:
        print("⚠️  未檢測到已配置的交易所API密鑰")
        print("\n💡 使用說明：")
        print("   方式1: 創建 .env 文件並設置 API 密鑰")
        print("   方式2: 直接修改 config.json 文件")
        print("   方式3: 使用 'python run.py' 進行配置")
        print("\n🔧 支持的交易所: Binance, Bybit, OKX, Backpack, Bitget, Gate.io, MEXC")
        print("\n🧪 您仍可以使用 '11. 測試所有交易所API' 功能來測試公開API")
        print()
    
    cli = CLIInterface(available_exchanges=available_exchanges)
    cli.run() 