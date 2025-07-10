#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from tabulate import tabulate

from funding_rate_arbitrage_system import (
    BinanceConnector, BybitConnector, OKXConnector, BackpackConnector,
    BitgetConnector, GateioConnector, MEXCConnector
)

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("結算時間檢查")

# 常見交易對列表（用於比較相同交易對在不同交易所的結算時間）
COMMON_PAIRS = [
    "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", 
    "BNB/USDT:USDT", "DOGE/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT",
    "MATIC/USDT:USDT", "DOT/USDT:USDT", "LINK/USDT:USDT", "ATOM/USDT:USDT"
]

# 極端費率交易對（從之前的結果中獲取）
EXTREME_PAIRS = [
    "M/USDT:USDT", "GMX/USDT:USDT", "MAGIC/USDT:USDT", "CUDIS/USDT:USDT",
    "SQD/USDT:USDT", "STARTUP/USDT:USDT", "1000000BOB/USDT:USDT", "BOBBSC/USDT:USDT"
]

async def get_settlement_times():
    """獲取不同交易所的結算時間"""
    
    # 創建所有交易所連接器
    connectors = {
        "Binance": BinanceConnector({}),
        "Bybit": BybitConnector({}),
        "OKX": OKXConnector({}),
        "Backpack": BackpackConnector({}),
        "Bitget": BitgetConnector({}),
        "Gate.io": GateioConnector({}),
        "MEXC": MEXCConnector({})
    }
    
    # 連接所有交易所
    for name, connector in connectors.items():
        print(f"🔄 連接 {name}...")
        await connector.connect()
    
    results = []
    
    # 1. 檢查常見交易對的結算時間
    print("\n📊 檢查常見交易對的結算時間...")
    for pair in COMMON_PAIRS:
        print(f"\n🔍 檢查 {pair} 在各交易所的結算時間...")
        pair_results = []
        
        for name, connector in connectors.items():
            try:
                rate_info = await connector.get_funding_rate(pair)
                if rate_info and rate_info.next_funding_time:
                    next_time = rate_info.next_funding_time.strftime('%m-%d %H:%M')
                    interval = getattr(rate_info, 'funding_interval', '8小時')
                    rate_pct = rate_info.funding_rate * 100 if rate_info.funding_rate is not None else None
                    
                    pair_results.append({
                        "交易所": name,
                        "交易對": pair,
                        "費率": f"{rate_pct:.4f}%" if rate_pct is not None else "N/A",
                        "下次結算": next_time,
                        "結算間隔": interval
                    })
                    print(f"  ✅ {name}: {pair} 下次結算時間 {next_time}, 費率 {rate_pct:.4f}% 間隔 {interval}")
                else:
                    print(f"  ❌ {name}: 無法獲取 {pair} 的結算時間")
            except Exception as e:
                print(f"  ❌ {name}: 獲取 {pair} 結算時間失敗 - {str(e)[:50]}")
        
        results.extend(pair_results)
    
    # 2. 檢查極端費率交易對
    print("\n📈 檢查極端費率交易對的結算時間...")
    for pair in EXTREME_PAIRS:
        print(f"\n🔍 檢查 {pair} 在各交易所的結算時間...")
        pair_results = []
        
        for name, connector in connectors.items():
            try:
                rate_info = await connector.get_funding_rate(pair)
                if rate_info and rate_info.next_funding_time:
                    next_time = rate_info.next_funding_time.strftime('%m-%d %H:%M')
                    interval = getattr(rate_info, 'funding_interval', '8小時')
                    rate_pct = rate_info.funding_rate * 100 if rate_info.funding_rate is not None else None
                    
                    pair_results.append({
                        "交易所": name,
                        "交易對": pair,
                        "費率": f"{rate_pct:.4f}%" if rate_pct is not None else "N/A",
                        "下次結算": next_time,
                        "結算間隔": interval
                    })
                    print(f"  ✅ {name}: {pair} 下次結算時間 {next_time}, 費率 {rate_pct:.4f}% 間隔 {interval}")
                else:
                    print(f"  ❌ {name}: 無法獲取 {pair} 的結算時間")
            except Exception as e:
                print(f"  ❌ {name}: 獲取 {pair} 結算時間失敗 - {str(e)[:50]}")
        
        results.extend(pair_results)
    
    # 關閉所有連接
    for name, connector in connectors.items():
        await connector.close()
    
    return results

def analyze_settlement_patterns(results: List[Dict]):
    """分析結算時間模式"""
    
    # 按交易所分組
    by_exchange = {}
    for item in results:
        exchange = item["交易所"]
        if exchange not in by_exchange:
            by_exchange[exchange] = []
        by_exchange[exchange].append(item)
    
    print("\n🔄 各交易所結算時間模式分析:")
    print("=" * 80)
    
    for exchange, items in by_exchange.items():
        if not items:
            continue
            
        times = [item["下次結算"] for item in items if "下次結算" in item]
        if not times:
            continue
            
        # 提取小時
        hours = [t.split(" ")[1].split(":")[0] for t in times if " " in t and ":" in t.split(" ")[1]]
        unique_hours = sorted(set(hours))
        
        print(f"\n📊 {exchange} 結算時間分析:")
        print(f"  🕒 結算小時: {', '.join(unique_hours)}")
        
        # 檢查是否所有交易對都在同一時間結算
        if len(unique_hours) == 1:
            print(f"  ✅ 所有交易對在同一時間結算: {unique_hours[0]}:00")
        else:
            print(f"  ⚠️ 不同交易對有不同的結算時間")
            
        # 檢查結算間隔
        intervals = [item.get("結算間隔", "未知") for item in items]
        unique_intervals = set(intervals)
        if len(unique_intervals) == 1:
            print(f"  ⏱️ 結算間隔: {next(iter(unique_intervals))}")
        else:
            print(f"  ⏱️ 結算間隔不一: {', '.join(unique_intervals)}")
            
            # 分析不同間隔的交易對
            interval_groups = {}
            for item in items:
                interval = item.get("結算間隔", "未知")
                if interval not in interval_groups:
                    interval_groups[interval] = []
                interval_groups[interval].append(item["交易對"])
                
            # 顯示不同間隔的交易對
            for interval, symbols in interval_groups.items():
                if len(symbols) > 3:
                    print(f"    - {interval}: {len(symbols)}個交易對，包括 {', '.join(symbols[:3])} 等")
                else:
                    print(f"    - {interval}: {', '.join(symbols)}")
        
        # 檢查極端費率交易對的結算間隔
        extreme_rates = []
        for item in items:
            rate_str = item.get("費率", "N/A")
            if rate_str != "N/A":
                try:
                    rate = float(rate_str.replace("%", ""))
                    if abs(rate) > 0.1:  # 0.1%以上視為極端費率
                        extreme_rates.append(item)
                except:
                    pass
        
        if extreme_rates:
            print(f"  🔥 極端費率交易對 ({len(extreme_rates)}個):")
            for item in extreme_rates:
                symbol = item["交易對"]
                rate = item.get("費率", "N/A")
                settlement = item.get("下次結算", "未知")
                interval = item.get("結算間隔", "未知")
                print(f"    - {symbol}: 費率 {rate}, 結算時間 {settlement}, 間隔 {interval}")

def print_settlement_table(results: List[Dict]):
    """打印結算時間表格"""
    
    # 按交易對分組
    by_pair = {}
    for item in results:
        pair = item["交易對"]
        if pair not in by_pair:
            by_pair[pair] = []
        by_pair[pair].append(item)
    
    print("\n📋 交易對結算時間比較:")
    print("=" * 80)
    
    for pair, items in by_pair.items():
        if not items:
            continue
            
        print(f"\n🔍 {pair} 在各交易所的結算時間:")
        
        # 準備表格數據
        table_data = []
        for item in sorted(items, key=lambda x: x["交易所"]):
            table_data.append([
                item["交易所"],
                item.get("費率", "N/A"),
                item.get("下次結算", "未知"),
                item.get("結算間隔", "未知")
            ])
        
        # 打印表格 - 修復tabulate調用
        headers = ["交易所", "費率", "下次結算", "結算間隔"]
        from tabulate import tabulate
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))
        
    # 按結算間隔分析
    print("\n⏱️ 不同結算間隔的交易對分析:")
    print("=" * 80)
    
    interval_groups = {}
    for item in results:
        interval = item.get("結算間隔", "未知")
        if interval not in interval_groups:
            interval_groups[interval] = []
        interval_groups[interval].append(item)
    
    for interval, items in sorted(interval_groups.items()):
        if interval == "未知":
            continue
            
        # 按交易所和交易對分組
        pairs_by_exchange = {}
        for item in items:
            exchange = item["交易所"]
            pair = item["交易對"]
            if exchange not in pairs_by_exchange:
                pairs_by_exchange[exchange] = set()
            pairs_by_exchange[exchange].add(pair)
        
        print(f"\n🕒 {interval}結算間隔的交易對:")
        for exchange, pairs in pairs_by_exchange.items():
            if len(pairs) > 5:
                print(f"  - {exchange}: {len(pairs)}個交易對，包括 {', '.join(list(pairs)[:5])} 等")
            else:
                print(f"  - {exchange}: {', '.join(pairs)}")

async def main():
    """主函數"""
    print("🕒 開始檢查不同交易所的結算時間...")
    
    try:
        results = await get_settlement_times()
        
        if results:
            # 分析結算模式
            analyze_settlement_patterns(results)
            
            # 打印結算時間表格
            print_settlement_table(results)
            
            print("\n💡 結論:")
            print("1. 不同交易所有不同的結算時間和間隔")
            print("2. 同一交易所內，不同交易對可能有不同的結算時間")
            print("3. 極端費率交易對通常有更短的結算間隔（4小時、2小時甚至1小時）")
            print("4. 結算間隔越短，套利機會越多，可以更頻繁地執行套利策略")
            print("5. 極端費率機會需要考慮結算時間和間隔來優化策略")
        else:
            print("\n❌ 未獲取到任何結算時間數據")
    except Exception as e:
        print(f"\n❌ 檢查過程中發生錯誤: {str(e)}")

if __name__ == "__main__":
    try:
        import tabulate
    except ImportError:
        print("正在安裝所需依賴...")
        import subprocess
        subprocess.check_call(["pip", "install", "tabulate"])
    
    asyncio.run(main()) 