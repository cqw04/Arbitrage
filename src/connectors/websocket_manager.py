#!/usr/bin/env python3
"""
WebSocket 管理器 - 多交易所實時數據流
支援所有主要交易所的實時資金費率、價格和帳戶數據
"""

import asyncio
import json
import logging
import websockets
import aiohttp
import hashlib
import hmac
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import ssl
import certifi

logger = logging.getLogger("WebSocketManager")

@dataclass
class WebSocketMessage:
    """WebSocket 消息格式"""
    exchange: str
    message_type: str  # funding_rate, price, balance, orderbook
    symbol: str
    data: Dict[str, Any]
    timestamp: datetime

class BaseWebSocketConnector(ABC):
    """WebSocket 連接器基類"""
    
    def __init__(self, exchange_name: str, api_credentials: Dict[str, str]):
        self.exchange_name = exchange_name
        self.api_key = api_credentials.get('api_key', '')
        self.secret_key = api_credentials.get('secret_key', '')
        self.passphrase = api_credentials.get('passphrase', '')
        
        self.ws = None
        self.running = False
        self.subscriptions = set()
        self.callbacks = {}
        
        # SSL 上下文
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
    @abstractmethod
    async def get_ws_url(self) -> str:
        """獲取WebSocket URL"""
        pass
    
    @abstractmethod
    async def authenticate(self) -> Dict[str, Any]:
        """WebSocket 認證"""
        pass
    
    @abstractmethod
    def format_subscribe_message(self, channel: str, symbol: str) -> Dict[str, Any]:
        """格式化訂閱消息"""
        pass
    
    @abstractmethod
    async def parse_message(self, message: str) -> Optional[WebSocketMessage]:
        """解析接收到的消息"""
        pass
    
    async def connect(self):
        """建立WebSocket連接"""
        try:
            ws_url = await self.get_ws_url()
            logger.info(f"連接 {self.exchange_name} WebSocket: {ws_url}")
            
            self.ws = await websockets.connect(
                ws_url,
                ssl=self.ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.running = True
            logger.info(f"✅ {self.exchange_name} WebSocket 連接成功")
            
            # 開始認證和監聽
            asyncio.create_task(self._authenticate_and_listen())
            
        except Exception as e:
            logger.error(f"❌ {self.exchange_name} WebSocket 連接失敗: {e}")
            self.running = False
    
    async def _authenticate_and_listen(self):
        """認證並開始監聽"""
        try:
            # 發送認證消息
            auth_message = await self.authenticate()
            if auth_message:
                await self.ws.send(json.dumps(auth_message))
                logger.info(f"已發送 {self.exchange_name} 認證消息")
            
            # 開始監聽消息
            await self._listen_messages()
            
        except Exception as e:
            logger.error(f"{self.exchange_name} 認證或監聽失敗: {e}")
    
    async def _listen_messages(self):
        """監聽WebSocket消息"""
        try:
            async for message in self.ws:
                if not self.running:
                    break
                
                try:
                    parsed_message = await self.parse_message(message)
                    if parsed_message:
                        await self._handle_message(parsed_message)
                        
                except Exception as e:
                    logger.error(f"處理 {self.exchange_name} 消息失敗: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"{self.exchange_name} WebSocket 連接已關閉")
        except Exception as e:
            logger.error(f"{self.exchange_name} WebSocket 監聽錯誤: {e}")
        finally:
            self.running = False
    
    async def _handle_message(self, message: WebSocketMessage):
        """處理解析後的消息"""
        # 調用註冊的回調函數
        message_type = message.message_type
        if message_type in self.callbacks:
            for callback in self.callbacks[message_type]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"回調函數執行失敗: {e}")
    
    async def subscribe(self, channel: str, symbol: str, callback: Callable = None):
        """訂閱頻道"""
        try:
            subscription_key = f"{channel}:{symbol}"
            if subscription_key not in self.subscriptions:
                message = self.format_subscribe_message(channel, symbol)
                await self.ws.send(json.dumps(message))
                self.subscriptions.add(subscription_key)
                logger.info(f"已訂閱 {self.exchange_name} {channel} {symbol}")
            
            # 註冊回調函數
            if callback:
                if channel not in self.callbacks:
                    self.callbacks[channel] = []
                self.callbacks[channel].append(callback)
                
        except Exception as e:
            logger.error(f"訂閱 {self.exchange_name} {channel} {symbol} 失敗: {e}")
    
    async def disconnect(self):
        """斷開連接"""
        self.running = False
        if self.ws:
            await self.ws.close()
            logger.info(f"✅ {self.exchange_name} WebSocket 已斷開")

class BinanceWebSocketConnector(BaseWebSocketConnector):
    """Binance WebSocket 連接器"""
    
    async def get_ws_url(self) -> str:
        return "wss://fstream.binance.com/ws"
    
    async def authenticate(self) -> Optional[Dict[str, Any]]:
        """Binance 不需要WebSocket認證（公開數據）"""
        return None
    
    def format_subscribe_message(self, channel: str, symbol: str) -> Dict[str, Any]:
        """格式化Binance訂閱消息"""
        # 將標準符號格式轉換為Binance格式
        binance_symbol = symbol.replace("/", "").replace(":USDT", "").lower() + "usdt"
        
        stream_map = {
            "funding_rate": f"{binance_symbol}@markPrice",
            "ticker": f"{binance_symbol}@ticker",
            "kline": f"{binance_symbol}@kline_1m"
        }
        
        stream = stream_map.get(channel, f"{binance_symbol}@ticker")
        
        return {
            "method": "SUBSCRIBE",
            "params": [stream],
            "id": int(time.time())
        }
    
    async def parse_message(self, message: str) -> Optional[WebSocketMessage]:
        """解析Binance WebSocket消息"""
        try:
            data = json.loads(message)
            
            # 跳過非數據消息
            if 'stream' not in data:
                return None
            
            stream = data['stream']
            event_data = data['data']
            
            # 解析資金費率消息
            if '@markPrice' in stream:
                symbol = stream.split('@')[0].upper()
                symbol = f"{symbol[:-4]}/USDT:USDT"  # 轉換回標準格式
                
                return WebSocketMessage(
                    exchange="binance",
                    message_type="funding_rate", 
                    symbol=symbol,
                    data={
                        "funding_rate": float(event_data.get('r', 0)),
                        "mark_price": float(event_data.get('p', 0)),
                        "next_funding_time": int(event_data.get('T', 0))
                    },
                    timestamp=datetime.now()
                )
            
            # 解析Ticker消息
            elif '@ticker' in stream:
                symbol = stream.split('@')[0].upper()
                symbol = f"{symbol[:-4]}/USDT:USDT"
                
                return WebSocketMessage(
                    exchange="binance",
                    message_type="ticker",
                    symbol=symbol,
                    data={
                        "price": float(event_data.get('c', 0)),
                        "volume": float(event_data.get('v', 0)),
                        "change_24h": float(event_data.get('P', 0))
                    },
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"解析Binance消息失敗: {e}")
        
        return None

class BybitWebSocketConnector(BaseWebSocketConnector):
    """Bybit WebSocket 連接器"""
    
    async def get_ws_url(self) -> str:
        return "wss://stream.bybit.com/v5/public/linear"
    
    async def authenticate(self) -> Optional[Dict[str, Any]]:
        """Bybit 公開數據不需要認證"""
        return None
    
    def format_subscribe_message(self, channel: str, symbol: str) -> Dict[str, Any]:
        """格式化Bybit訂閱消息"""
        # 轉換符號格式
        bybit_symbol = symbol.replace("/", "").replace(":USDT", "")
        
        channel_map = {
            "funding_rate": "tickers",
            "ticker": "tickers", 
            "orderbook": "orderbook.1"
        }
        
        bybit_channel = channel_map.get(channel, "tickers")
        
        return {
            "op": "subscribe",
            "args": [f"{bybit_channel}.{bybit_symbol}"]
        }
    
    async def parse_message(self, message: str) -> Optional[WebSocketMessage]:
        """解析Bybit WebSocket消息"""
        try:
            data = json.loads(message)
            
            if data.get('topic') and 'tickers' in data['topic']:
                ticker_data = data.get('data', {})
                symbol = ticker_data.get('symbol', '').replace('USDT', '/USDT:USDT')
                
                return WebSocketMessage(
                    exchange="bybit",
                    message_type="funding_rate",
                    symbol=symbol,
                    data={
                        "funding_rate": float(ticker_data.get('fundingRate', 0)),
                        "mark_price": float(ticker_data.get('markPrice', 0)),
                        "next_funding_time": ticker_data.get('nextFundingTime', '')
                    },
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"解析Bybit消息失敗: {e}")
        
        return None

class OKXWebSocketConnector(BaseWebSocketConnector):
    """OKX WebSocket 連接器"""
    
    async def get_ws_url(self) -> str:
        return "wss://ws.okx.com:8443/ws/v5/public"
    
    async def authenticate(self) -> Optional[Dict[str, Any]]:
        """OKX 公開數據不需要認證"""
        return None
    
    def format_subscribe_message(self, channel: str, symbol: str) -> Dict[str, Any]:
        """格式化OKX訂閱消息"""
        # 轉換符號格式：BTC/USDT:USDT -> BTC-USDT-SWAP
        base = symbol.split('/')[0]
        okx_symbol = f"{base}-USDT-SWAP"
        
        channel_map = {
            "funding_rate": "funding-rate",
            "ticker": "tickers",
            "orderbook": "books5"
        }
        
        okx_channel = channel_map.get(channel, "tickers")
        
        return {
            "op": "subscribe",
            "args": [{
                "channel": okx_channel,
                "instId": okx_symbol
            }]
        }
    
    async def parse_message(self, message: str) -> Optional[WebSocketMessage]:
        """解析OKX WebSocket消息"""
        try:
            data = json.loads(message)
            
            if 'data' in data and data.get('arg', {}).get('channel'):
                channel = data['arg']['channel']
                inst_id = data['arg']['instId']
                
                # 轉換符號格式
                symbol = inst_id.replace('-SWAP', ':USDT').replace('-', '/')
                
                for item in data['data']:
                    if channel == 'funding-rate':
                        return WebSocketMessage(
                            exchange="okx",
                            message_type="funding_rate",
                            symbol=symbol,
                            data={
                                "funding_rate": float(item.get('fundingRate', 0)),
                                "next_funding_time": item.get('nextFundingTime', ''),
                                "funding_time": item.get('fundingTime', '')
                            },
                            timestamp=datetime.now()
                        )
                    
                    elif channel == 'tickers':
                        return WebSocketMessage(
                            exchange="okx",
                            message_type="ticker",
                            symbol=symbol,
                            data={
                                "price": float(item.get('last', 0)),
                                "volume": float(item.get('vol24h', 0)),
                                "change_24h": float(item.get('change24h', 0))
                            },
                            timestamp=datetime.now()
                        )
                        
        except Exception as e:
            logger.error(f"解析OKX消息失敗: {e}")
        
        return None

class BackpackWebSocketConnector(BaseWebSocketConnector):
    """Backpack WebSocket 連接器"""
    
    async def get_ws_url(self) -> str:
        return "wss://ws.backpack.exchange"
    
    async def authenticate(self) -> Optional[Dict[str, Any]]:
        """Backpack WebSocket 認證"""
        if not self.api_key or not self.secret_key:
            return None
        
        timestamp = str(int(time.time() * 1000))
        signature_string = f"instruction=subscribe&timestamp={timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "method": "SUBSCRIBE",
            "params": {
                "signature": signature,
                "timestamp": timestamp,
                "instruction": "subscribe"
            }
        }
    
    def format_subscribe_message(self, channel: str, symbol: str) -> Dict[str, Any]:
        """格式化Backpack訂閱消息"""
        # 轉換符號格式
        backpack_symbol = symbol.replace("/", "_").replace(":USDC", "_USDC").replace(":USDT", "_USDT")
        
        return {
            "method": "SUBSCRIBE",
            "params": [f"{channel}.{backpack_symbol}"]
        }
    
    async def parse_message(self, message: str) -> Optional[WebSocketMessage]:
        """解析Backpack WebSocket消息"""
        try:
            data = json.loads(message)
            
            # Backpack的消息格式需要根據實際API文檔調整
            if 'stream' in data and 'data' in data:
                stream_parts = data['stream'].split('.')
                if len(stream_parts) >= 2:
                    channel = stream_parts[0]
                    symbol = stream_parts[1].replace('_', '/').replace('USDC', ':USDC').replace('USDT', ':USDT')
                    
                    return WebSocketMessage(
                        exchange="backpack",
                        message_type=channel,
                        symbol=symbol,
                        data=data['data'],
                        timestamp=datetime.now()
                    )
                    
        except Exception as e:
            logger.error(f"解析Backpack消息失敗: {e}")
        
        return None

class WebSocketManager:
    """WebSocket 管理器 - 統一管理所有交易所的WebSocket連接"""
    
    def __init__(self, exchanges_config: Dict[str, Dict[str, str]]):
        self.exchanges_config = exchanges_config
        self.connectors = {}
        self.running = False
        
        # 數據儲存
        self.funding_rates = {}
        self.tickers = {}
        self.orderbooks = {}
        
        # 回調函數
        self.message_handlers = {
            "funding_rate": [],
            "ticker": [],
            "orderbook": [],
            "balance": []
        }
    
    async def initialize(self, exchanges: List[str] = None):
        """初始化WebSocket連接器"""
        exchanges = exchanges or list(self.exchanges_config.keys())
        
        connector_classes = {
            "binance": BinanceWebSocketConnector,
            "bybit": BybitWebSocketConnector, 
            "okx": OKXWebSocketConnector,
            "backpack": BackpackWebSocketConnector
        }
        
        for exchange in exchanges:
            if exchange in connector_classes and exchange in self.exchanges_config:
                connector_class = connector_classes[exchange]
                credentials = self.exchanges_config[exchange]
                
                self.connectors[exchange] = connector_class(exchange, credentials)
                logger.info(f"已初始化 {exchange} WebSocket 連接器")
    
    async def start_all_connections(self):
        """啟動所有WebSocket連接"""
        self.running = True
        tasks = []
        
        for exchange, connector in self.connectors.items():
            task = asyncio.create_task(self._start_connector(connector))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _start_connector(self, connector: BaseWebSocketConnector):
        """啟動單個連接器"""
        try:
            await connector.connect()
            
            # 註冊通用消息處理器
            connector.callbacks["funding_rate"] = [self._handle_funding_rate]
            connector.callbacks["ticker"] = [self._handle_ticker]
            connector.callbacks["orderbook"] = [self._handle_orderbook]
            
        except Exception as e:
            logger.error(f"啟動 {connector.exchange_name} WebSocket 失敗: {e}")
    
    async def subscribe_funding_rates(self, symbols: List[str]):
        """訂閱所有交易所的資金費率"""
        for exchange, connector in self.connectors.items():
            for symbol in symbols:
                await connector.subscribe("funding_rate", symbol)
                logger.info(f"已訂閱 {exchange} {symbol} 資金費率")
    
    async def subscribe_tickers(self, symbols: List[str]):
        """訂閱所有交易所的價格數據"""
        for exchange, connector in self.connectors.items():
            for symbol in symbols:
                await connector.subscribe("ticker", symbol)
                logger.info(f"已訂閱 {exchange} {symbol} 價格數據")
    
    async def _handle_funding_rate(self, message: WebSocketMessage):
        """處理資金費率消息"""
        key = f"{message.exchange}:{message.symbol}"
        self.funding_rates[key] = {
            "exchange": message.exchange,
            "symbol": message.symbol,
            "data": message.data,
            "timestamp": message.timestamp
        }
        
        # 調用用戶註冊的處理器
        for handler in self.message_handlers["funding_rate"]:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"資金費率處理器執行失敗: {e}")
    
    async def _handle_ticker(self, message: WebSocketMessage):
        """處理價格消息"""
        key = f"{message.exchange}:{message.symbol}"
        self.tickers[key] = {
            "exchange": message.exchange,
            "symbol": message.symbol,
            "data": message.data,
            "timestamp": message.timestamp
        }
        
        # 調用用戶註冊的處理器
        for handler in self.message_handlers["ticker"]:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"價格處理器執行失敗: {e}")
    
    async def _handle_orderbook(self, message: WebSocketMessage):
        """處理訂單簿消息"""
        key = f"{message.exchange}:{message.symbol}"
        self.orderbooks[key] = {
            "exchange": message.exchange,
            "symbol": message.symbol,
            "data": message.data,
            "timestamp": message.timestamp
        }
    
    def register_handler(self, message_type: str, handler: Callable):
        """註冊消息處理器"""
        if message_type in self.message_handlers:
            self.message_handlers[message_type].append(handler)
    
    def get_latest_funding_rate(self, exchange: str, symbol: str) -> Optional[Dict]:
        """獲取最新資金費率"""
        key = f"{exchange}:{symbol}"
        return self.funding_rates.get(key)
    
    def get_latest_ticker(self, exchange: str, symbol: str) -> Optional[Dict]:
        """獲取最新價格"""
        key = f"{exchange}:{symbol}"
        return self.tickers.get(key)
    
    async def stop_all_connections(self):
        """停止所有WebSocket連接"""
        self.running = False
        tasks = []
        
        for connector in self.connectors.values():
            task = asyncio.create_task(connector.disconnect())
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ 所有WebSocket連接已停止")

# 使用示例
async def example_usage():
    """WebSocket管理器使用示例"""
    
    # 配置
    exchanges_config = {
        "binance": {"api_key": "", "secret_key": ""},
        "bybit": {"api_key": "", "secret_key": ""},
        "okx": {"api_key": "", "secret_key": "", "passphrase": ""}
    }
    
    # 創建管理器
    ws_manager = WebSocketManager(exchanges_config)
    
    # 註冊消息處理器
    async def on_funding_rate(message: WebSocketMessage):
        print(f"資金費率更新: {message.exchange} {message.symbol} {message.data}")
    
    ws_manager.register_handler("funding_rate", on_funding_rate)
    
    # 初始化並啟動
    await ws_manager.initialize()
    await ws_manager.start_all_connections()
    
    # 訂閱數據
    symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    await ws_manager.subscribe_funding_rates(symbols)
    await ws_manager.subscribe_tickers(symbols)
    
    # 運行一段時間
    await asyncio.sleep(60)
    
    # 停止
    await ws_manager.stop_all_connections()

if __name__ == "__main__":
    asyncio.run(example_usage()) 