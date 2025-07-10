#!/usr/bin/env python3
"""
簡化套利系統 - 現貨套利 + 資金費率套利
整合多交易所，支持真實數據獲取
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
import hmac
import hashlib
import urllib.parse

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_arbitrage.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleArbitrage")

@dataclass
class ArbitrageOpportunity:
    """套利機會"""
    type: str  # "spot" 或 "funding"
    symbol: str
    exchange_a: str
    exchange_b: str
    profit_percentage: float
    estimated_profit: float
    timestamp: datetime

class ExchangeConnector:
    """交易所連接器"""
    
    def __init__(self, exchange_name: str, api_key: str = "", secret_key: str = ""):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = None
        
        # 交易所配置
        self.configs = {
            "binance": {
                "base_url": "https://api.binance.com",
                "ws_url": "wss://stream.binance.com:9443/ws",
                "maker_fee": 0.0002,
                "taker_fee": 0.0005
            },
            "bybit": {
                "base_url": "https://api.bybit.com",
                "ws_url": "wss://stream.bybit.com/v5/public/linear",
                "maker_fee": 0.0002,
                "taker_fee": 0.00055
            },
            "okx": {
                "base_url": "https://www.okx.com",
                "ws_url": "wss://ws.okx.com:8443/ws/v5/public",
                "maker_fee": 0.0002,
                "taker_fee": 0.0005
            }
        }
        
        self.config = self.configs.get(exchange_name, {})
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_spot_price(self, symbol: str) -> Optional[float]:
        """獲取現貨價格"""
        try:
            if self.exchange_name == "binance":
                url = f"{self.config['base_url']}/api/v3/ticker/price"
                params = {"symbol": symbol.replace("/", "")}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data["price"])
            
            elif self.exchange_name == "bybit":
                url = f"{self.config['base_url']}/v5/market/tickers"
                params = {"category": "spot", "symbol": symbol.replace("/", "")}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["result"]["list"]:
                            return float(data["result"]["list"][0]["lastPrice"])
            
            elif self.exchange_name == "okx":
                url = f"{self.config['base_url']}/api/v5/market/ticker"
                params = {"instId": symbol.replace("/", "-")}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["data"]:
                            return float(data["data"][0]["last"])
            
        except Exception as e:
            logger.error(f"獲取 {self.exchange_name} {symbol} 價格失敗: {e}")
        
        return None
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """獲取資金費率"""
        try:
            if self.exchange_name == "binance":
                url = f"{self.config['base_url']}/fapi/v1/fundingRate"
                params = {"symbol": symbol.replace("/", ""), "limit": 1}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            return float(data[0]["fundingRate"])
            
            elif self.exchange_name == "bybit":
                url = f"{self.config['base_url']}/v5/market/funding/history"
                params = {"category": "linear", "symbol": symbol.replace("/", ""), "limit": 1}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["result"]["list"]:
                            return float(data["result"]["list"][0]["fundingRate"])
            
            elif self.exchange_name == "okx":
                url = f"{self.config['base_url']}/api/v5/public/funding-rate"
                params = {"instId": symbol.replace("/", "-")}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["data"]:
                            return float(data["data"][0]["fundingRate"])
            
        except Exception as e:
            logger.error(f"獲取 {self.exchange_name} {symbol} 資金費率失敗: {e}")
        
        return None

class SpotArbitrageDetector:
    """現貨套利檢測器"""
    
    def __init__(self, exchanges: List[str]):
        self.exchanges = exchanges
        self.min_profit_threshold = 0.002  # 0.2% 最小利潤
    
    async def detect_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """檢測現貨套利機會"""
        opportunities = []
        
        for symbol in symbols:
            prices = {}
            
            # 獲取各交易所價格
            for exchange in self.exchanges:
                async with ExchangeConnector(exchange) as connector:
                    price = await connector.get_spot_price(symbol)
                    if price:
                        prices[exchange] = price
            
            if len(prices) >= 2:
                # 找出最高和最低價格
                sorted_prices = sorted(prices.items(), key=lambda x: x[1])
                min_exchange, min_price = sorted_prices[0]
                max_exchange, max_price = sorted_prices[-1]
                
                # 計算利潤
                profit_percentage = (max_price - min_price) / min_price
                
                if profit_percentage > self.min_profit_threshold:
                    # 扣除手續費
                    configs = {
                        "binance": {"maker_fee": 0.0002, "taker_fee": 0.0005},
                        "bybit": {"maker_fee": 0.0002, "taker_fee": 0.00055},
                        "okx": {"maker_fee": 0.0002, "taker_fee": 0.0005}
                    }
                    
                    total_fees = (
                        configs[min_exchange]["taker_fee"] + 
                        configs[max_exchange]["taker_fee"]
                    )
                    
                    net_profit = profit_percentage - total_fees
                    
                    if net_profit > 0:
                        opportunity = ArbitrageOpportunity(
                            type="spot",
                            symbol=symbol,
                            exchange_a=min_exchange,
                            exchange_b=max_exchange,
                            profit_percentage=net_profit,
                            estimated_profit=net_profit * 10000,  # 假設10,000 USDT
                            timestamp=datetime.now()
                        )
                        opportunities.append(opportunity)
                        
                        logger.info(f"📊 發現現貨套利: {symbol} "
                                   f"{min_exchange}({min_price:.4f}) → "
                                   f"{max_exchange}({max_price:.4f}) "
                                   f"利潤: {net_profit:.4%}")
        
        return opportunities

class FundingRateArbitrageDetector:
    """資金費率套利檢測器"""
    
    def __init__(self, exchanges: List[str]):
        self.exchanges = exchanges
        self.min_rate_diff = 0.001  # 0.1% 最小費率差異
    
    async def detect_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """檢測資金費率套利機會"""
        opportunities = []
        
        for symbol in symbols:
            rates = {}
            
            # 獲取各交易所資金費率
            for exchange in self.exchanges:
                async with ExchangeConnector(exchange) as connector:
                    rate = await connector.get_funding_rate(symbol)
                    if rate is not None:
                        rates[exchange] = rate
            
            if len(rates) >= 2:
                # 找出最高和最低費率
                sorted_rates = sorted(rates.items(), key=lambda x: x[1])
                min_exchange, min_rate = sorted_rates[0]
                max_exchange, max_rate = sorted_rates[-1]
                
                # 計算費率差異
                rate_diff = max_rate - min_rate
                
                if rate_diff > self.min_rate_diff:
                    opportunity = ArbitrageOpportunity(
                        type="funding",
                        symbol=symbol,
                        exchange_a=min_exchange,
                        exchange_b=max_exchange,
                        profit_percentage=rate_diff,
                        estimated_profit=rate_diff * 10000,  # 假設10,000 USDT
                        timestamp=datetime.now()
                    )
                    opportunities.append(opportunity)
                    
                    logger.info(f"💰 發現資金費率套利: {symbol} "
                               f"{min_exchange}({min_rate:.6f}) → "
                               f"{max_exchange}({max_rate:.6f}) "
                               f"差異: {rate_diff:.6f}")
        
        return opportunities

class SimpleArbitrageSystem:
    """簡化套利系統"""
    
    def __init__(self, config_file: str = "simple_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.running = False
        
        # 初始化檢測器
        exchanges = self.config.get("exchanges", ["binance", "bybit", "okx"])
        self.spot_detector = SpotArbitrageDetector(exchanges)
        self.funding_detector = FundingRateArbitrageDetector(exchanges)
        
        # 統計數據
        self.stats = {
            "spot_opportunities": 0,
            "funding_opportunities": 0,
            "total_profit": 0.0,
            "start_time": datetime.now()
        }
    
    def load_config(self) -> Dict:
        """加載配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 創建默認配置
            default_config = {
                "exchanges": ["binance", "bybit", "okx"],
                "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
                "update_interval": 30,
                "min_profit_threshold": 0.002,
                "min_funding_diff": 0.001
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    async def start(self):
        """啟動系統"""
        self.running = True
        logger.info("🚀 簡化套利系統啟動")
        
        try:
            while self.running:
                await self.run_cycle()
                await asyncio.sleep(self.config.get("update_interval", 30))
                
        except KeyboardInterrupt:
            logger.info("🛑 收到停止信號")
        except Exception as e:
            logger.error(f"❌ 系統錯誤: {e}")
        finally:
            await self.shutdown()
    
    async def run_cycle(self):
        """運行一個檢測週期"""
        symbols = self.config.get("symbols", ["BTC/USDT", "ETH/USDT"])
        
        # 檢測現貨套利機會
        spot_opportunities = await self.spot_detector.detect_opportunities(symbols)
        self.stats["spot_opportunities"] += len(spot_opportunities)
        
        # 檢測資金費率套利機會
        funding_opportunities = await self.funding_detector.detect_opportunities(symbols)
        self.stats["funding_opportunities"] += len(funding_opportunities)
        
        # 顯示統計
        if spot_opportunities or funding_opportunities:
            logger.info(f"📈 本週期發現: "
                       f"現貨套利 {len(spot_opportunities)} 個, "
                       f"資金費率套利 {len(funding_opportunities)} 個")
    
    async def shutdown(self):
        """關閉系統"""
        self.running = False
        
        # 生成報告
        runtime = datetime.now() - self.stats["start_time"]
        logger.info(f"📊 系統運行報告:")
        logger.info(f"   運行時間: {runtime}")
        logger.info(f"   現貨套利機會: {self.stats['spot_opportunities']}")
        logger.info(f"   資金費率套利機會: {self.stats['funding_opportunities']}")
        logger.info(f"   總利潤: {self.stats['total_profit']:.2f} USDT")
        
        logger.info("✅ 系統已關閉")

def main():
    """主函數"""
    print("""
    🚀 簡化套利系統
    ================
    
    功能:
    ✅ 現貨套利 - 跨交易所價差套利
    ✅ 資金費率套利 - 永續合約資金費率差異
    
    交易所:
    ✅ Binance
    ✅ Bybit  
    ✅ OKX
    
    特點:
    ✅ 真實數據獲取
    ✅ 自動檢測機會
    ✅ 簡潔易用
    ✅ 即開即用
    """)
    
    # 創建並啟動系統
    system = SimpleArbitrageSystem()
    
    try:
        asyncio.run(system.start())
    except KeyboardInterrupt:
        print("\n🛑 用戶中斷")

if __name__ == "__main__":
    main() 