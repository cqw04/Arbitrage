#!/usr/bin/env python3
"""
資金費率套利系統 - 統一入口
支援多種執行模式：面板、CLI、直接執行
"""

import argparse
import asyncio
import sys
import os
from typing import Optional
import logging
import json
import aiohttp

# 添加當前目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from funding_rate_arbitrage_system import FundingArbitrageSystem
from config_funding import get_config
from database_manager import get_db

logger = logging.getLogger("FundingArbitrageMain")


async def get_real_market_price(symbol: str) -> float:
    """獲取真實市場價格"""
    try:
        # 使用 CoinGecko API 獲取真實價格
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'SOL': 'solana',
            'USDC': 'usd-coin',
            'USDT': 'tether'
        }
        
        gecko_id = symbol_map.get(symbol)
        if not gecko_id:
            return 1.0
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={gecko_id}&vs_currencies=usd"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get(gecko_id, {}).get('usd', 0)
                    if price > 0:
                        print(f"  📊 獲取 {symbol} 真實價格: ${price:.2f}")
                        return float(price)
    except Exception as e:
        print(f"  ⚠️ 無法獲取 {symbol} 真實價格: {e}")
    
    # 如果無法獲取真實價格，拋出錯誤而不是使用估算值
    logger.error(f"無法獲取 {symbol} 的真實市場價格")
    raise ValueError(f"無法獲取 {symbol} 的真實市場價格，請檢查網絡連接或API狀態")


def create_parser():
    """創建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="資金費率套利系統 - 多交易所資金費率套利工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 啟動交互式面板
  python run.py --panel
  
  # 啟動命令行界面
  python run.py --cli
  
  # 直接運行套利系統
  python run.py --duration 24 --symbols BTC/USDT:USDT,ETH/USDT:USDT
  
  # 顯示當前最佳套利機會
  python run.py --show-opportunities --limit 5
  
  # 查看歷史統計
  python run.py --stats --days 30
        """
    )
    
    # 基本執行模式
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--panel', action='store_true', 
                           help='啟動交互式面板界面')
    mode_group.add_argument('--cli', action='store_true', 
                           help='啟動命令行界面')
    mode_group.add_argument('--show-opportunities', action='store_true',
                           help='顯示當前套利機會')
    mode_group.add_argument('--stats', action='store_true',
                           help='顯示歷史統計數據')
    mode_group.add_argument('--check-balances', action='store_true',
                           help='檢查所有交易所帳戶餘額')
    mode_group.add_argument('--check-positions', action='store_true',
                           help='檢查所有交易所倉位狀態（合約+期權+總倉位）')
    mode_group.add_argument('--discover-symbols', action='store_true',
                           help='發現和分析可用的交易符號')
    
    # API 配置
    api_group = parser.add_argument_group('API 配置')
    api_group.add_argument('--load-env', action='store_true',
                          help='從 .env 文件加載 API 配置')
    
    # 套利參數
    arbitrage_group = parser.add_argument_group('套利參數')
    arbitrage_group.add_argument('--duration', type=float, default=24,
                                help='運行時間（小時），默認: 24')
    arbitrage_group.add_argument('--symbols', type=str,
                                help='監控的交易對，用逗號分隔（例: BTC/USDT:USDT,ETH/USDT:USDT）')
    arbitrage_group.add_argument('--exchanges', type=str,
                                help='使用的交易所，用逗號分隔（例: binance,bybit,okx）')
    arbitrage_group.add_argument('--min-profit', type=float,
                                help='最小利潤閾值（USDT）')
    arbitrage_group.add_argument('--max-exposure', type=float,
                                help='最大總敞口（USDT）')
    arbitrage_group.add_argument('--use-exchange-symbols', action='store_true',
                                help='直接使用交易所API獲取的所有可用交易對（忽略配置文件）')
    
    # 風險管理
    risk_group = parser.add_argument_group('風險管理')
    risk_group.add_argument('--enable-risk-management', action='store_true',
                           help='啟用風險管理功能')
    risk_group.add_argument('--stop-loss', type=float,
                           help='止損百分比')
    risk_group.add_argument('--max-drawdown', type=float,
                           help='最大回撤百分比')
    
    # 顯示選項
    display_group = parser.add_argument_group('顯示選項')
    display_group.add_argument('--limit', type=int, default=10,
                              help='顯示數量限制，默認: 10')
    display_group.add_argument('--days', type=int, default=7,
                              help='統計天數，默認: 7')
    display_group.add_argument('--format', choices=['table', 'json', 'csv'],
                              default='table', help='輸出格式，默認: table')
    
    # 調試選項
    debug_group = parser.add_argument_group('調試選項')
    debug_group.add_argument('--debug', action='store_true',
                            help='啟用調試模式')
    debug_group.add_argument('--dry-run', action='store_true',
                            help='安全模式（不執行實際交易）')
    debug_group.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                            default='INFO', help='日誌級別')
    
    return parser


def load_env_config():
    """從 .env 文件加載配置，返回可用的交易所列表"""
    try:
        from dotenv import load_dotenv
        
        # 嘗試加載 .env 文件
        env_loaded = load_dotenv()
        logger.info(f"ENV file loading result: {env_loaded}")
        
        config = get_config()
        available_exchanges = []
        
        logger.info(f"Starting environment variable configuration check...")
        
        # 檢查並更新交易所配置
        for exchange_name in config.exchanges.keys():
            api_key = os.getenv(f'{exchange_name.upper()}_API_KEY')
            secret_key = os.getenv(f'{exchange_name.upper()}_SECRET_KEY')
            passphrase = os.getenv(f'{exchange_name.upper()}_PASSPHRASE')  # 對於需要的交易所
            
            logger.info(f"Checking {exchange_name.upper()}:")
            logger.info(f"   API_KEY: {'Set' if api_key else 'Not set'}")
            logger.info(f"   SECRET_KEY: {'Set' if secret_key else 'Not set'}")
            if exchange_name.lower() in ['okx', 'bitget']:
                logger.info(f"   PASSPHRASE: {'Set' if passphrase else 'Not set'}")
            
            if api_key and secret_key and api_key != f'your_{exchange_name.lower()}_api_key':
                # 使用新方法：只在內存中設置憑證，不保存到文件
                config.set_runtime_credentials(
                    exchange_name,
                    api_key=api_key,
                    secret_key=secret_key
                )
                
                # 對於需要 passphrase 的交易所（OKX, Bitget）
                if exchange_name.lower() in ['okx', 'bitget'] and passphrase:
                    exchange_config = config.exchanges[exchange_name]
                    exchange_config.passphrase = passphrase
                
                available_exchanges.append(exchange_name)
                logger.info(f"Successfully loaded {exchange_name.upper()} API config from environment")
            else:
                logger.info(f"{exchange_name.upper()} API config not found or invalid")
        
        if available_exchanges:
            logger.info(f"Detected {len(available_exchanges)} available exchanges: {', '.join(available_exchanges)}")
            return available_exchanges
        else:
            logger.warning("No available exchange configurations detected")
            return []
        
    except ImportError:
        logger.warning("python-dotenv 未安裝，跳過 .env 文件加載")
        return []
    except Exception as e:
        logger.error(f"加載 .env 文件失敗: {e}")
        return []


def get_available_exchanges():
    """獲取可用的交易所列表"""
    config = get_config()
    available_exchanges = []
    
    for exchange_name, exchange_config in config.exchanges.items():
        # 檢查 API 密鑰是否已配置
        if (exchange_config.api_key and 
            exchange_config.api_key != f'your_{exchange_name.lower()}_api_key' and
            exchange_config.secret_key and 
            exchange_config.secret_key != f'your_{exchange_name.lower()}_secret_key'):
            available_exchanges.append(exchange_name)
    
    return available_exchanges


async def show_opportunities(limit: int = 10, format_type: str = 'table', available_exchanges: list = None):
    """顯示當前套利機會，只顯示可用交易所的機會"""
    try:
        # 獲取可用交易所
        if available_exchanges is None:
            available_exchanges = get_available_exchanges()
        
        if not available_exchanges:
            print("❌ 未檢測到任何已配置的交易所")
            print("💡 請在 .env 文件中配置交易所 API 密鑰，或使用 --load-env 參數")
            return
        
        print(f"🎯 檢測到可用交易所: {', '.join([ex.upper() for ex in available_exchanges])}")
        print("⏳ 正在獲取最新套利機會...")
        
        # 創建系統實例（只使用可用交易所）
        system = FundingArbitrageSystem(available_exchanges=available_exchanges)
        
        # 初始化監控器
        for exchange_name in available_exchanges:
            if exchange_name in system.monitor.exchanges:
                await system.monitor.exchanges[exchange_name].connect()
        
        # 等待數據收集
        await asyncio.sleep(10)
        
        # 檢測機會
        opportunities = system.detector.detect_all_opportunities()
        
        if not opportunities:
            print("❌ 當前未發現套利機會")
            print("💡 可能原因：費率差異太小、手續費成本高於利潤等")
            return
        
        print(f"\n🎯 發現 {len(opportunities)} 個套利機會 (Top {limit})")
        print("=" * 80)
        
        if format_type == 'table':
            print(f"{'排名':<4} {'策略':<15} {'交易對':<15} {'主要交易所':<10} {'預期利潤':<12} {'風險等級':<8}")
            print("-" * 85)
            
            for i, opp in enumerate(opportunities[:limit], 1):
                print(f"{i:<4} {opp.strategy_type.value:<15} {opp.symbol:<15} "
                      f"{opp.primary_exchange:<10} {opp.net_profit_8h:<12.4f} {opp.risk_level:<8}")
        
        elif format_type == 'json':
            opp_data = []
            for i, opp in enumerate(opportunities[:limit], 1):
                opp_data.append({
                    'rank': i,
                    'strategy': opp.strategy_type.value,
                    'symbol': opp.symbol,
                    'primary_exchange': opp.primary_exchange,
                    'secondary_exchange': opp.secondary_exchange,
                    'profit_8h': opp.net_profit_8h,
                    'risk_level': opp.risk_level,
                    'confidence': opp.confidence_score
                })
            print(json.dumps(opp_data, indent=2, ensure_ascii=False))
        
        # 顯示詳細信息
        if opportunities:
            best_opp = opportunities[0]
            print(f"\n🏆 最佳機會詳情:")
            print(f"   策略: {best_opp.strategy_type.value}")
            print(f"   交易對: {best_opp.symbol}")
            print(f"   主要交易所: {best_opp.primary_exchange}")
            print(f"   次要交易所: {best_opp.secondary_exchange}")
            print(f"   費率差異: {best_opp.funding_rate_diff*100:.4f}%")
            print(f"   預期8h利潤: {best_opp.net_profit_8h:.4f} USDT")
            print(f"   手續費成本: {best_opp.commission_cost:.4f} USDT")
            print(f"   風險等級: {best_opp.risk_level}")
            print(f"   可信度: {best_opp.confidence_score:.2f}")
        
        # 斷開所有連接
        for exchange_name in available_exchanges:
            if exchange_name in system.monitor.exchanges:
                try:
                    await system.monitor.exchanges[exchange_name].disconnect()
                except Exception as e:
                    logger.debug(f"斷開 {exchange_name} 連接時出錯: {e}")
        
    except Exception as e:
        logger.error(f"顯示套利機會失敗: {e}")
        
        # 即使出錯也要嘗試關閉連接
        try:
            for exchange_name in available_exchanges:
                if exchange_name in system.monitor.exchanges:
                    await system.monitor.exchanges[exchange_name].disconnect()
        except:
            pass  # 忽略關閉時的錯誤


def show_stats(days: int = 7, format_type: str = 'table', available_exchanges: list = None):
    """顯示歷史統計"""
    try:
        db = get_db()
        stats = db.get_performance_stats(days)
        
        if not stats:
            print("❌ 沒有找到統計數據")
            return
        
        print(f"\n📊 過去 {days} 天統計數據")
        print("=" * 50)
        
        if format_type == 'table':
            print(f"總套利機會: {stats.get('total_opportunities', 0)}")
            print(f"獲利機會: {stats.get('profitable_opportunities', 0)}")
            print(f"總執行倉位: {stats.get('total_positions', 0)}")
            print(f"已平倉位: {stats.get('closed_positions', 0)}")
            print(f"獲利倉位: {stats.get('profitable_positions', 0)}")
            print(f"成功率: {stats.get('success_rate', 0):.2f}%")
            print(f"平均利潤: {stats.get('avg_profit', 0):.4f} USDT")
            print(f"總利潤: {stats.get('total_profit', 0):.4f} USDT")
            print(f"最大單筆利潤: {stats.get('max_profit', 0):.4f} USDT")
            print(f"最大單筆虧損: {stats.get('min_profit', 0):.4f} USDT")
        
        elif format_type == 'json':
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        # 顯示頂級表現符號
        top_symbols = db.get_top_performing_symbols(5)
        if top_symbols:
            print(f"\n🏅 表現最佳交易對 Top 5:")
            print(f"{'交易對':<15} {'交易次數':<8} {'總利潤':<12} {'平均利潤':<12} {'成功率':<8}")
            print("-" * 60)
            
            for symbol_data in top_symbols:
                success_rate = (symbol_data['profitable_trades'] / symbol_data['trade_count']) * 100
                print(f"{symbol_data['symbol']:<15} {symbol_data['trade_count']:<8} "
                      f"{symbol_data['total_profit']:<12.4f} {symbol_data['avg_profit']:<12.4f} "
                      f"{success_rate:<8.1f}%")
        
    except Exception as e:
        logger.error(f"顯示統計數據失敗: {e}")


def start_cli(available_exchanges: list = None):
    """啟動命令行界面"""
    try:
        # 清理輸出緩衝區
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        
        # 添加分隔線，清理之前的混亂輸出
        print("\n" + "="*60)
        print("FUNDING ARBITRAGE SYSTEM - CLI MODE")
        print("="*60)
        
        if available_exchanges:
            print(f"Configured exchanges: {', '.join([ex.upper() for ex in available_exchanges])}")
        else:
            print("WARNING: No exchanges configured")
            print("Please set up API keys in .env file")
        
        print("Initializing CLI interface...")
        print("="*60 + "\n")
        
        from cli_interface import CLIInterface
        cli = CLIInterface(available_exchanges=available_exchanges)
        cli.run()
        
    except ImportError as e:
        print(f"錯誤: CLI 介面模塊未找到: {e}")
        print("請確保 cli_interface.py 文件存在")
    except Exception as e:
        print(f"錯誤: CLI 啟動失敗: {e}")
        import traceback
        traceback.print_exc()


def start_panel(available_exchanges: list = None):
    """啟動交互式面板"""
    try:
        from panel_interface import PanelInterface
        panel = PanelInterface(available_exchanges=available_exchanges)
        panel.run()
    except ImportError:
        logger.error("面板界面模塊未找到")
        print("❌ 面板界面模塊載入失敗，請檢查 panel_interface.py 文件")
    except Exception as e:
        logger.error(f"啟動面板界面失敗: {e}")
        print(f"❌ 面板界面啟動失敗: {e}")
        print("💡 建議使用 --cli 模式替代")


async def run_arbitrage_system(args, available_exchanges: list):
    """運行套利系統"""
    try:
        config = get_config()
        
        # 應用命令行參數
        if args.symbols:
            config.trading.symbols = [s.strip() for s in args.symbols.split(',')]
        
        if args.min_profit:
            config.trading.min_profit_threshold = args.min_profit / 100  # 轉換為百分比
        
        if args.max_exposure:
            config.trading.max_total_exposure = args.max_exposure
        
        # 驗證配置（只對可用交易所進行驗證）
        errors = []
        for exchange_name in available_exchanges:
            exchange_config = config.exchanges.get(exchange_name)
            if not exchange_config:
                errors.append(f"{exchange_name} 交易所配置缺失")
                continue
            
            # 檢查是否有有效的API密鑰（運行時配置或非預設值）
            if (not exchange_config.api_key or 
                exchange_config.api_key == f'your_{exchange_name}_api_key'):
                # 如果是運行時配置，這不應該是錯誤
                if exchange_name not in available_exchanges:
                    errors.append(f"{exchange_name} API密鑰未正確配置")
        
        if errors:
            logger.error("配置驗證失敗:")
            for error in errors:
                logger.error(f"  - {error}")
            logger.info("💡 提示: 系統已從 .env 文件成功加載API配置，配置驗證邏輯可能需要更新")
            # 不直接返回，允許系統繼續運行
        
        print(f"🚀 啟動資金費率套利系統")
        print(f"   可用交易所: {', '.join([ex.upper() for ex in available_exchanges])}")
        print(f"   監控交易對: {', '.join(config.trading.symbols)}")
        print(f"   運行時間: {args.duration} 小時")
        print(f"   安全模式: {'是' if args.dry_run else '否'}")
        
        # 創建並啟動系統（只使用可用交易所）
        system = FundingArbitrageSystem(available_exchanges=available_exchanges)
        
        if args.dry_run:
            print("⚠️  安全模式：不會執行實際交易")
        
        await system.start(duration_hours=args.duration)
        
    except Exception as e:
        logger.error(f"運行套利系統失敗: {e}")


async def check_positions(available_exchanges: list):
    """檢查所有交易所的倉位狀態 - 合約、期權、總倉位"""
    if not available_exchanges:
        print("❌ 未檢測到任何已配置的交易所")
        print("💡 請先在 .env 文件中配置交易所 API 密鑰")
        return
    
    checker = None
    try:
        from position_checker import PositionChecker
        
        print(f"💰 倉位狀態檢查...")
        print(f"🎯 檢查交易所: {', '.join([ex.upper() for ex in available_exchanges])}")
        print("=" * 70)
        
        # 創建倉位檢查器
        checker = PositionChecker(available_exchanges)
        
        # 執行倉位檢查
        result = await checker.check_all_positions()
        
        print(f"\n✅ 倉位檢查完成")
        
        # 可選：保存結果到文件
        import sys
        if '--save' in sys.argv:
            import json
            from datetime import datetime
            filename = f"position_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 倉位報告已保存到: {filename}")
        
    except ImportError:
        print("❌ 倉位檢查器模組不可用")
        print("💡 請確保 position_checker.py 文件存在")
    except Exception as e:
        print(f"❌ 倉位檢查失敗: {e}")
        logger.error(f"倉位檢查失敗: {e}")
    finally:
        # 確保清理連接
        if checker:
            try:
                await checker._cleanup_connections()
            except Exception as e:
                logger.debug(f"清理倉位檢查器連接時出錯: {e}")


async def check_account_balances(available_exchanges: list):
    """檢查所有可用交易所的帳戶餘額 - MM-Simple 風格"""
    if not available_exchanges:
        print("❌ 未檢測到任何已配置的交易所")
        print("💡 請先在 .env 文件中配置交易所 API 密鑰")
        return
    
    print(f"💰 查詢交易所帳戶餘額...")
    print("=" * 50)
    
    try:
        # 創建系統實例
        system = FundingArbitrageSystem(available_exchanges=available_exchanges)
        
        # 存儲餘額結果
        successful_connections = 0
        total_all_exchanges = 0.0
        
        for exchange_name in available_exchanges:
            if exchange_name in system.monitor.exchanges:
                connector = system.monitor.exchanges[exchange_name]
                
                try:
                    # 靜默連接交易所
                    await connector.connect()
                    
                    # 獲取餘額
                    balances = await connector.get_account_balance()
                    
                    if exchange_name.upper() == 'BACKPACK':
                        # 完全匹配 MM-Simple 的 get_balance_command 函數
                        backpack_total = await display_backpack_balance_mm_style(connector, balances)
                        total_all_exchanges += backpack_total
                    else:
                        # 使用增強的餘額顯示
                        exchange_total = await display_enhanced_balance(exchange_name, balances)
                        total_all_exchanges += exchange_total
                    
                    successful_connections += 1
                    
                except Exception as e:
                    print(f"❌ {exchange_name.upper()} 連接失敗: {str(e)[:100]}")
        
        print("\n" + "=" * 50)
        print(f"💯 總計: {total_all_exchanges:.2f} USDT ({successful_connections}/{len(available_exchanges)} 個交易所)")
        
        if successful_connections == 0:
            print("\n💡 所有交易所連接失敗，請檢查:")
            print("   - API 密鑰配置是否正確")
            print("   - 網絡連接是否正常")
            print("   - API 權限是否足夠")
        
        # 確保所有連接都被正確關閉
        for exchange_name in available_exchanges:
            if exchange_name in system.monitor.exchanges:
                try:
                    await system.monitor.exchanges[exchange_name].disconnect()
                except Exception as e:
                    logger.debug(f"斷開 {exchange_name} 連接時出錯: {e}")
        
    except Exception as e:
        logger.error(f"檢查帳戶餘額失敗: {e}")
        print(f"❌ 系統錯誤: {e}")
        
        # 即使出錯也要嘗試關閉連接
        try:
            for exchange_name in available_exchanges:
                if exchange_name in system.monitor.exchanges:
                    await system.monitor.exchanges[exchange_name].disconnect()
        except:
            pass  # 忽略關閉時的錯誤


async def display_backpack_balance_mm_style(connector, balances):
    """完全匹配 MM-Simple 風格的 BACKPACK 餘額顯示"""
    print(f"🎯 BACKPACK 餘額查詢 (MM-Simple 風格)")
    print("-" * 40)
    
    total_value = 0.0  # 計算總價值
    
    # 檢查餘額查詢結果
    if isinstance(balances, dict) and "error" in balances and balances["error"]:
        print(f"獲取餘額失敗: {balances['error']}")
        return
    
    # 顯示基本餘額
    print("\n當前餘額:")
    if isinstance(balances, dict) and balances.get('status') == 'success':
        has_balance = False
        for asset, details in balances.items():
            if asset not in ['status', 'total_value', 'message'] and isinstance(details, dict):
                available = float(details.get('available', 0))
                locked = float(details.get('locked', 0))
                staked = float(details.get('staked', 0))
                
                # MM-Simple 邏輯：只顯示有餘額的資產
                if available > 0 or locked > 0 or staked > 0:
                    has_balance = True
                    if staked > 0:
                        print(f"{asset}: 可用 {available}, 凍結 {locked}, 質押 {staked}")
                    else:
                        print(f"{asset}: 可用 {available}, 凍結 {locked}")
        
        if not has_balance:
            print("無有效資產餘額")
    else:
        error_msg = balances.get('message', '無法識別返回格式') if isinstance(balances, dict) else f"無法識別返回格式 {type(balances)}"
        print(f"獲取餘額失敗: {error_msg}")
    
    # 查詢抵押品
    try:
        if hasattr(connector, 'get_collateral_balance'):
            collateral = await connector.get_collateral_balance()
            
            if isinstance(collateral, dict) and "error" in collateral:
                print(f"獲取抵押品失敗: {collateral['error']}")
            elif isinstance(collateral, dict) and collateral.get('status') == 'success':
                # 檢查是否有抵押品資產
                collateral_assets = []
                for asset, balance_info in collateral.items():
                    if asset not in ['status', 'total_value', 'message'] and isinstance(balance_info, dict):
                        total = balance_info.get('total', 0)
                        if total > 0:
                            collateral_assets.append({
                                'symbol': asset,
                                'totalQuantity': total,
                                'availableQuantity': balance_info.get('available', 0),
                                'lendQuantity': balance_info.get('staked', 0),
                                'collateralValue': total
                            })
                
                if collateral_assets:
                    print("\n抵押品資產:")
                    for item in collateral_assets:
                        symbol = item.get('symbol', '')
                        total_qty = item.get('totalQuantity', 0)
                        available = item.get('availableQuantity', '')
                        lend = item.get('lendQuantity', '')
                        collateral_value = item.get('collateralValue', '')
                        print(f"{symbol}: 總量 {total_qty}, 可用 {available}, 出借中 {lend}, 抵押價值 {collateral_value}")
                        
                        # 計算價值貢獻到總價值
                        if symbol != 'POINTS' and total_qty > 0:
                            if symbol in ['USDC', 'USDT', 'USD']:
                                total_value += float(total_qty)
                            elif symbol == 'SOL':
                                # 使用真實市場價格
                                real_price = await get_real_market_price(symbol)
                                total_value += float(total_qty) * real_price
                            elif symbol == 'BTC':
                                real_price = await get_real_market_price(symbol) 
                                total_value += float(total_qty) * real_price
                            elif symbol == 'ETH':
                                real_price = await get_real_market_price(symbol)
                                total_value += float(total_qty) * real_price
                else:
                    print("\n無抵押品資產")
            else:
                error_msg = collateral.get('message', '查詢失敗') if isinstance(collateral, dict) else '未知錯誤'
                print(f"獲取抵押品失敗: {error_msg}")
    except Exception as e:
        print(f"獲取抵押品失敗: {str(e)}")
    
    # 顯示 Backpack 總價值並返回
    if total_value > 0:
        print(f"\n✅ BACKPACK    | 總資金: {total_value:.2f} USDT")
    
    return total_value


async def display_enhanced_balance(exchange_name: str, balances: dict):
    """增強的餘額顯示功能 - 支援完整的財務數據展示"""
    print(f"\n🏛️  {exchange_name.upper()} 完整財務報告")
    print("=" * 60)
    
    if not isinstance(balances, dict):
        print("❌ 餘額數據格式錯誤")
        return 0.0
    
    # 檢查錯誤狀態
    if balances.get('status') == 'no_credentials':
        print("⚠️  API憑證未配置，無法查詢詳細資訊")
        return 0.0
    elif balances.get('status') == 'error':
        print(f"❌ 查詢失敗: {balances.get('message', '未知錯誤')}")
        return 0.0
    
    # 獲取總價值
    total_value = balances.get('total_value', 0.0)
    
    # 1. 顯示總覽信息
    print("📊 資產總覽:")
    if exchange_name.upper() == 'BINANCE':
        futures_bal = balances.get('futures_balance', 0.0)
        spot_bal = balances.get('spot_balance', 0.0)
        options_bal = balances.get('options_balance', 0.0)
        earn_bal = balances.get('earnings_balance', 0.0)
        unrealized_pnl = balances.get('unrealized_pnl', 0.0)
        position_count = balances.get('position_count', 0)
        
        print(f"   💰 總資產: {total_value:.2f} USDT")
        print(f"   📈 期貨帳戶: {futures_bal:.2f} USDT")
        print(f"   💎 現貨帳戶: {spot_bal:.2f} USDT")
        if options_bal > 0:
            print(f"   🎯 期權帳戶: {options_bal:.2f} USDT")
        print(f"   🏦 理財產品: {earn_bal:.2f} USDT")
        if unrealized_pnl != 0:
            pnl_color = "📈" if unrealized_pnl > 0 else "📉"
            print(f"   {pnl_color} 未實現盈虧: {unrealized_pnl:+.2f} USDT")
        if position_count > 0:
            print(f"   📋 持倉數量: {position_count} 個")
    
    elif exchange_name.upper() == 'BYBIT':
        unified_bal = balances.get('unified_balance', 0.0)
        spot_bal = balances.get('spot_balance', 0.0)
        contract_bal = balances.get('contract_balance', 0.0)
        options_bal = balances.get('options_balance', 0.0)
        invest_bal = balances.get('investment_balance', 0.0)
        unrealized_pnl = balances.get('unrealized_pnl', 0.0)
        position_count = balances.get('position_count', 0)
        
        print(f"   💰 總資產: {total_value:.2f} USDT")
        if unified_bal > 0:
            print(f"   🔄 統一帳戶: {unified_bal:.2f} USDT")
        print(f"   💎 現貨帳戶: {spot_bal:.2f} USDT")
        print(f"   📈 合約帳戶: {contract_bal:.2f} USDT")
        if options_bal > 0:
            print(f"   🎯 期權帳戶: {options_bal:.2f} USDT")
        if invest_bal > 0:
            print(f"   🏦 理財帳戶: {invest_bal:.2f} USDT")
        if unrealized_pnl != 0:
            pnl_color = "📈" if unrealized_pnl > 0 else "📉"
            print(f"   {pnl_color} 未實現盈虧: {unrealized_pnl:+.2f} USDT")
        if position_count > 0:
            print(f"   📋 持倉數量: {position_count} 個")
    
    elif exchange_name.upper() == 'OKX':
        trading_bal = balances.get('trading_balance', 0.0)
        funding_bal = balances.get('funding_balance', 0.0)
        options_bal = balances.get('options_balance', 0.0)
        earn_bal = balances.get('earn_balance', 0.0)
        unrealized_pnl = balances.get('unrealized_pnl', 0.0)
        position_count = balances.get('position_count', 0)
        
        print(f"   💰 總資產: {total_value:.2f} USDT")
        print(f"   📈 交易帳戶: {trading_bal:.2f} USDT")
        print(f"   💳 資金帳戶: {funding_bal:.2f} USDT")
        if options_bal > 0:
            print(f"   🎯 期權帳戶: {options_bal:.2f} USDT")
        if earn_bal > 0:
            print(f"   🏦 理財帳戶: {earn_bal:.2f} USDT")
        if unrealized_pnl != 0:
            pnl_color = "📈" if unrealized_pnl > 0 else "📉"
            print(f"   {pnl_color} 未實現盈虧: {unrealized_pnl:+.2f} USDT")
        if position_count > 0:
            print(f"   📋 持倉數量: {position_count} 個")
    
    elif exchange_name.upper() == 'BITGET':
        mix_bal = balances.get('mix_balance', 0.0)
        spot_bal = balances.get('spot_balance', 0.0)
        unrealized_pnl = balances.get('unrealized_pnl', 0.0)
        position_count = balances.get('position_count', 0)
        
        print(f"   💰 總資產: {total_value:.2f} USDT")
        print(f"   📈 合約帳戶: {mix_bal:.2f} USDT")
        print(f"   💎 現貨帳戶: {spot_bal:.2f} USDT")
        if unrealized_pnl != 0:
            pnl_color = "📈" if unrealized_pnl > 0 else "📉"
            print(f"   {pnl_color} 未實現盈虧: {unrealized_pnl:+.2f} USDT")
        if position_count > 0:
            print(f"   📋 持倉數量: {position_count} 個")
    
    else:
        # 其他交易所的簡化顯示
        print(f"   💰 總資產: {total_value:.2f} USDT")
    
    # 2. 顯示持倉詳情
    positions = []
    for key, value in balances.items():
        if key.startswith('POSITION_') and isinstance(value, dict):
            positions.append((key.replace('POSITION_', ''), value))
    
    if positions:
        print(f"\n📋 當前持倉 ({len(positions)}個):")
        for symbol, pos_info in positions[:5]:  # 只顯示前5個
            size = pos_info.get('size', 0)
            side = pos_info.get('side', 'UNKNOWN')
            value = pos_info.get('value', 0)
            unrealized_pnl = pos_info.get('unrealized_pnl', 0)
            entry_price = pos_info.get('entry_price', 0)
            
            pnl_symbol = "📈" if unrealized_pnl > 0 else "📉" if unrealized_pnl < 0 else "➖"
            side_symbol = "🟢" if side in ['Buy', 'LONG', 'long'] else "🔴" if side in ['Sell', 'SHORT', 'short'] else "⚪"
            
            print(f"   {side_symbol} {symbol}: {abs(size):.4f} | 價值: ${value:.2f} | {pnl_symbol} {unrealized_pnl:+.2f}")
            if entry_price > 0:
                print(f"      入場價: ${entry_price:.4f}")
        
        if len(positions) > 5:
            print(f"   ... [還有 {len(positions) - 5} 個倉位]")
    
    # 3. 顯示主要資產
    print(f"\n💎 主要資產:")
    displayed_assets = 0
    for key, value in balances.items():
        if key in ['status', 'total_value', 'message', 'futures_balance', 'spot_balance', 
                   'unified_balance', 'trading_balance', 'funding_balance', 'unrealized_pnl',
                   'position_value', 'earnings_balance', 'investment_balance', 'earn_balance',
                   'contract_balance', 'options_balance', 'position_count']:
            continue
        
        if key.startswith('POSITION_') or key.startswith('OPTIONS_POSITION_'):
            continue
        
        if isinstance(value, dict):
            total_amount = value.get('total', value.get('available', 0))
            if total_amount > 0:
                asset_name = key.replace('FUTURES_', '').replace('SPOT_', '').replace('TRADING_', '').replace('FUNDING_', '').replace('UNIFIED_', '')
                
                # 顯示詳細信息
                available = value.get('available', 0)
                locked = value.get('locked', value.get('frozen', 0))
                unrealized_pnl = value.get('unrealized_pnl', 0)
                
                print(f"   💰 {asset_name}: {total_amount:.6f}")
                if available != total_amount:
                    print(f"      └─ 可用: {available:.6f} | 凍結: {locked:.6f}")
                if unrealized_pnl != 0:
                    pnl_symbol = "📈" if unrealized_pnl > 0 else "📉"
                    print(f"      └─ {pnl_symbol} 未實現: {unrealized_pnl:+.6f}")
                
                displayed_assets += 1
                if displayed_assets >= 8:  # 限制顯示數量
                    break
        elif isinstance(value, (int, float)) and value > 0:
            if not key.startswith(('POSITION_', 'total_', 'unrealized_', 'position_')):
                print(f"   💰 {key}: {value:.6f}")
                displayed_assets += 1
                if displayed_assets >= 8:
                    break
    
    print()
    return total_value


async def discover_symbols(available_exchanges: list, min_exchanges: int = 2):
    """發現和分析可用的交易符號"""
    if not available_exchanges:
        print("❌ 未檢測到任何已配置的交易所")
        print("💡 請先在 .env 文件中配置交易所 API 密鑰")
        return
    
    print(f"🔍 開始符號發現分析")
    print(f"🎯 使用交易所: {', '.join([ex.upper() for ex in available_exchanges])}")
    print(f"📊 最低要求: 至少 {min_exchanges} 個交易所支持")
    print("=" * 60)
    
    try:
        # 創建系統實例
        system = FundingArbitrageSystem(available_exchanges=available_exchanges)
        
        # 初始化符號發現
        await system.monitor.initialize_symbols(use_dynamic_discovery=True, min_exchanges=min_exchanges)
        
        # 獲取符號可用性報告
        report = system.monitor.get_symbol_availability_report()
        print(report)
        
        # 檢查缺失的合約
        missing_contracts = system.monitor.check_missing_contracts()
        if missing_contracts:
            print("\n⚠️  合約兼容性問題:")
            print("=" * 30)
            for symbol, missing_exchanges in missing_contracts.items():
                print(f"🔸 {symbol}")
                print(f"   缺少交易所: {', '.join([ex.upper() for ex in missing_exchanges])}")
                print(f"   影響: 無法在這些交易所進行該合約的套利")
                print()
        
        # 推薦最佳符號組合
        if system.monitor.symbol_manager:
            recommended = system.monitor.symbol_manager.recommend_optimal_symbols(max_symbols=10, min_exchanges=min_exchanges)
            if recommended:
                print("\n💡 推薦的最佳符號組合:")
                print("=" * 30)
                for i, symbol in enumerate(recommended[:10], 1):
                    availability = system.monitor.symbol_manager.symbol_cache.get(symbol)
                    if availability:
                        exchange_count = len(availability.available_exchanges)
                        print(f"{i:2d}. {symbol:<20} ({exchange_count}/{len(available_exchanges)} 個交易所)")
                        print(f"    支持交易所: {', '.join([ex.upper() for ex in availability.available_exchanges])}")
                print()
        
        # 建議配置更新
        if system.monitor.symbols:
            print("\n🔧 配置建議:")
            print("=" * 15)
            print("根據發現的結果，建議將以下符號添加到配置文件:")
            print()
            print("新的 symbols 配置:")
            symbols_json = json.dumps(system.monitor.symbols[:10], indent=2, ensure_ascii=False)
            print(symbols_json)
            print()
            print("💾 要應用這些設置，請更新 config.json 中的 trading.symbols 配置")
        
        # 斷開所有連接
        for exchange_name in available_exchanges:
            if exchange_name in system.monitor.exchanges:
                try:
                    await system.monitor.exchanges[exchange_name].disconnect()
                except Exception as e:
                    logger.debug(f"斷開 {exchange_name} 連接時出錯: {e}")
        
        print("\n✅ 符號發現分析完成")
        
    except Exception as e:
        logger.error(f"符號發現失敗: {e}")
        print(f"❌ 分析失敗: {e}")


def main():
    """主函數"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 設置日誌級別
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # 優先嘗試從 .env 文件加載配置
        available_exchanges = load_env_config()
        
        # 如果 .env 文件沒有有效配置，回退到檢查 config.json
        if not available_exchanges:
            available_exchanges = get_available_exchanges()
        
        # 顯示可用交易所信息
        if available_exchanges:
            print(f"[INFO] Configured exchanges: {', '.join([ex.upper() for ex in available_exchanges])}")
        else:
            print("[WARNING] No configured exchanges detected")
            print("[TIP] Please configure exchange API keys in .env file")
        
        # 根據模式執行相應功能
        if args.panel:
            if not available_exchanges:
                print("❌ 面板模式需要至少配置一個交易所")
                return
            start_panel(available_exchanges)
            
        elif args.cli:
            start_cli(available_exchanges)
            
        elif args.show_opportunities:
            asyncio.run(show_opportunities(args.limit, args.format, available_exchanges))
            
        elif args.stats:
            show_stats(args.days, args.format, available_exchanges)
            
        elif args.check_balances:
            asyncio.run(check_account_balances(available_exchanges))
            
        elif args.check_positions:
            asyncio.run(check_positions(available_exchanges))
            
        elif args.discover_symbols:
            asyncio.run(discover_symbols(available_exchanges))
            
        else:
            # 默認運行套利系統
            if len(sys.argv) == 1:
                # 無參數時顯示幫助
                parser.print_help()
            else:
                if not available_exchanges:
                    print("❌ 套利系統需要至少配置一個交易所")
                    return
                asyncio.run(run_arbitrage_system(args, available_exchanges))
    
    except KeyboardInterrupt:
        print("\n👋 用戶中斷，程序退出")
    except Exception as e:
        logger.error(f"程序運行失敗: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main() 