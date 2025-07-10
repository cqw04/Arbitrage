#!/usr/bin/env python3
"""
資金費率套利系統 - Web 界面
提供實時監控和系統控制的 Web 介面
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time

from config_funding import get_config
from database_manager import get_db
from funding_rate_arbitrage_system import FundingArbitrageSystem

logger = logging.getLogger("WebInterface")

class WebInterface:
    """Web 界面管理器 - 支援實時 WebSocket 數據"""
    
    def __init__(self, available_exchanges: list = None, use_websocket: bool = True):
        self.config = get_config()
        self.db = get_db()
        self.available_exchanges = available_exchanges or []
        self.use_websocket = use_websocket
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'funding_arbitrage_secret_key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.system = None
        self.running = False
        
        # 實時數據緩存
        self.realtime_data = {
            'funding_rates': {},
            'prices': {},
            'opportunities': [],
            'balances': {},
            'system_metrics': {}
        }
        
        # 設置路由
        self._setup_routes()
        self._setup_websocket_events()
        
        # 啟動實時數據推送任務
        self._start_realtime_tasks()
    
    def _setup_routes(self):
        """設置 Flask 路由"""
        
        @self.app.route('/')
        def index():
            """首頁"""
            return render_template_string(self._get_main_template())
        
        @self.app.route('/api/status')
        def api_status():
            """系統狀態 API"""
            return jsonify({
                'status': 'running' if self.running else 'stopped',
                'exchanges': [ex.upper() for ex in self.available_exchanges],
                'symbols': self.config.trading.symbols,
                'web_interface': self.config.system.enable_web_interface,
                'telegram_alerts': self.config.system.enable_telegram_alerts,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/opportunities')
        def api_opportunities():
            """套利機會 API"""
            try:
                # 從實際系統獲取機會數據
                if hasattr(self, 'arbitrage_system') and self.arbitrage_system:
                    # 檢測當前套利機會
                    opportunities = self.arbitrage_system.detector.detect_all_opportunities()
                    
                    # 轉換為API格式
                    api_opportunities = []
                    for opp in opportunities[:10]:  # 限制返回數量
                        api_opportunities.append({
                            'symbol': opp.symbol,
                            'primary_exchange': opp.primary_exchange.upper(),
                            'secondary_exchange': opp.secondary_exchange.upper(),
                            'profit_8h': float(opp.net_profit_8h),
                            'confidence': float(opp.confidence_score),
                            'strategy': opp.strategy_type.value if hasattr(opp.strategy_type, 'value') else str(opp.strategy_type),
                            'timestamp': opp.created_at.isoformat() if hasattr(opp, 'created_at') else datetime.now().isoformat()
                        })
                    
                    return jsonify(api_opportunities)
                else:
                    # 如果系統未運行，嘗試快速檢測
                    from funding_rate_arbitrage_system import FundingArbitrageSystem
                    import asyncio
                    
                    async def get_quick_opportunities():
                        temp_system = FundingArbitrageSystem(available_exchanges=self.available_exchanges)
                        opportunities = temp_system.detector.detect_all_opportunities()
                        return opportunities[:5]  # 快速檢測，限制數量
                    
                    opportunities = asyncio.run(get_quick_opportunities())
                    api_opportunities = []
                    for opp in opportunities:
                        api_opportunities.append({
                            'symbol': opp.symbol,
                            'primary_exchange': opp.primary_exchange.upper(),
                            'secondary_exchange': opp.secondary_exchange.upper(),
                            'profit_8h': float(opp.net_profit_8h),
                            'confidence': float(opp.confidence_score),
                            'strategy': str(opp.strategy_type),
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    return jsonify(api_opportunities)
                    
            except Exception as e:
                logger.error(f"獲取套利機會失敗: {e}")
                return jsonify([])
        
        @self.app.route('/api/balances')
        def api_balances():
            """帳戶餘額 API"""
            try:
                # 從實際系統獲取餘額數據
                if hasattr(self, 'arbitrage_system') and self.arbitrage_system:
                    # 使用已運行的系統獲取餘額
                    import asyncio
                    
                    async def get_all_balances():
                        balances = {}
                        for exchange_name in self.available_exchanges:
                            if exchange_name in self.arbitrage_system.monitor.exchanges:
                                connector = self.arbitrage_system.monitor.exchanges[exchange_name]
                                try:
                                    balance_data = await connector.get_account_balance()
                                    
                                    # 處理餘額數據格式
                                    processed_balance = {}
                                    if isinstance(balance_data, dict):
                                        if balance_data.get('status') == 'success':
                                            # 提取主要資產
                                            for asset, details in balance_data.items():
                                                if asset not in ['status', 'total_value', 'message']:
                                                    if isinstance(details, dict):
                                                        total = float(details.get('available', 0)) + float(details.get('locked', 0))
                                                        if total > 0:
                                                            processed_balance[asset] = total
                                                    elif isinstance(details, (int, float)):
                                                        if float(details) > 0:
                                                            processed_balance[asset] = float(details)
                                        
                                        # 添加總價值
                                        if 'total_value' in balance_data:
                                            processed_balance['total_value'] = balance_data['total_value']
                                    
                                    processed_balance['status'] = 'connected'
                                    balances[exchange_name.upper()] = processed_balance
                                    
                                except Exception as e:
                                    balances[exchange_name.upper()] = {
                                        'status': 'error',
                                        'error': str(e)
                                    }
                        return balances
                    
                    return jsonify(asyncio.run(get_all_balances()))
                else:
                    # 如果系統未運行，返回狀態信息
                    balances = {}
                    for exchange in self.available_exchanges:
                        balances[exchange.upper()] = {
                            'status': 'not_connected',
                            'message': '系統未運行，無法獲取餘額'
                        }
                    return jsonify(balances)
                    
            except Exception as e:
                logger.error(f"獲取帳戶餘額失敗: {e}")
                return jsonify({})
    
    def _setup_websocket_events(self):
        """設置 WebSocket 事件"""
        
        @self.socketio.on('connect')
        def handle_connect():
            logger.info("客戶端已連接到 WebSocket")
            emit('status', {'message': '已連接到套利系統'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info("客戶端已斷開 WebSocket 連接")
        
        @self.socketio.on('start_system')
        def handle_start_system(data):
            """啟動套利系統"""
            try:
                if not self.running:
                    self.running = True
                    emit('status', {'message': '套利系統已啟動'})
                    logger.info("通過 Web 界面啟動套利系統")
                else:
                    emit('status', {'message': '系統已在運行中'})
            except Exception as e:
                emit('error', {'message': f'啟動失敗: {e}'})
        
        @self.socketio.on('stop_system')
        def handle_stop_system(data):
            """停止套利系統"""
            try:
                if self.running:
                    self.running = False
                    emit('status', {'message': '套利系統已停止'})
                    logger.info("通過 Web 界面停止套利系統")
                else:
                    emit('status', {'message': '系統已停止'})
            except Exception as e:
                emit('error', {'message': f'停止失敗: {e}'})
        
        @self.socketio.on('subscribe_realtime')
        def handle_subscribe_realtime(data):
            """訂閱實時數據"""
            try:
                data_type = data.get('type', 'all')  # funding_rates, prices, opportunities, all
                logger.info(f"客戶端訂閱實時數據: {data_type}")
                emit('subscription_confirmed', {'type': data_type, 'status': 'active'})
            except Exception as e:
                emit('error', {'message': f'訂閱失敗: {e}'})
        
        @self.socketio.on('get_historical_data')
        def handle_get_historical_data(data):
            """獲取歷史數據"""
            try:
                symbol = data.get('symbol')
                exchange = data.get('exchange')
                days = data.get('days', 7)
                
                # 這裡可以從數據庫獲取歷史數據
                historical_data = self._get_historical_funding_rates(exchange, symbol, days)
                emit('historical_data', {
                    'symbol': symbol,
                    'exchange': exchange,
                    'data': historical_data
                })
            except Exception as e:
                emit('error', {'message': f'獲取歷史數據失敗: {e}'})
    
    def _start_realtime_tasks(self):
        """啟動實時數據推送任務"""
        def realtime_worker():
            while True:
                try:
                    if self.running and self.system:
                        self._push_realtime_data()
                    time.sleep(5)  # 每5秒推送一次
                except Exception as e:
                    logger.error(f"實時數據推送錯誤: {e}")
                    time.sleep(10)
        
        # 在背景執行緒中運行
        realtime_thread = threading.Thread(target=realtime_worker, daemon=True)
        realtime_thread.start()
    
    def _push_realtime_data(self):
        """推送實時數據到客戶端"""
        try:
            # 推送資金費率數據
            if hasattr(self.system, 'monitor') and self.system.monitor.funding_data:
                funding_rates = self._format_funding_rates()
                self.socketio.emit('funding_rates_update', funding_rates)
            
            # 推送套利機會
            opportunities = self._get_current_opportunities()
            if opportunities:
                self.socketio.emit('opportunities_update', opportunities)
            
            # 推送系統指標
            metrics = self._get_system_metrics()
            self.socketio.emit('metrics_update', metrics)
            
            # 推送價格數據（如果有WebSocket數據）
            if hasattr(self.system, 'monitor') and hasattr(self.system.monitor, 'ws_data_cache'):
                prices = self._format_price_data()
                if prices:
                    self.socketio.emit('prices_update', prices)
            
        except Exception as e:
            logger.error(f"推送實時數據失敗: {e}")
    
    def _format_funding_rates(self) -> Dict:
        """格式化資金費率數據"""
        formatted_data = {}
        try:
            for exchange, symbols_data in self.system.monitor.funding_data.items():
                formatted_data[exchange] = {}
                for symbol, rate_info in symbols_data.items():
                    formatted_data[exchange][symbol] = {
                        'funding_rate': float(rate_info.funding_rate),
                        'mark_price': float(rate_info.mark_price),
                        'next_funding_time': rate_info.next_funding_time.isoformat() if rate_info.next_funding_time else None,
                        'timestamp': rate_info.timestamp.isoformat(),
                        'predicted_rate': float(rate_info.predicted_rate)
                    }
        except Exception as e:
            logger.error(f"格式化資金費率數據失敗: {e}")
        
        return formatted_data
    
    def _format_price_data(self) -> Dict:
        """格式化價格數據"""
        formatted_data = {}
        try:
            if hasattr(self.system.monitor, 'ws_data_cache'):
                for key, cache_data in self.system.monitor.ws_data_cache.items():
                    if 'ticker' in cache_data:
                        exchange, symbol = key.split(':', 1)
                        if exchange not in formatted_data:
                            formatted_data[exchange] = {}
                        
                        ticker = cache_data['ticker']
                        formatted_data[exchange][symbol] = {
                            'price': float(ticker.get('price', 0)),
                            'volume': float(ticker.get('volume', 0)),
                            'change_24h': float(ticker.get('change_24h', 0)),
                            'timestamp': cache_data.get('last_price_update', datetime.now()).isoformat()
                        }
        except Exception as e:
            logger.error(f"格式化價格數據失敗: {e}")
        
        return formatted_data
    
    def _get_current_opportunities(self) -> List[Dict]:
        """獲取當前套利機會"""
        try:
            if hasattr(self.system, 'detector'):
                opportunities = self.system.detector.detect_all_opportunities()
                return [{
                    'symbol': opp.symbol,
                    'strategy': opp.strategy_type.value if hasattr(opp.strategy_type, 'value') else str(opp.strategy_type),
                    'primary_exchange': opp.primary_exchange,
                    'secondary_exchange': opp.secondary_exchange,
                    'funding_rate_diff': float(opp.funding_rate_diff),
                    'estimated_profit_8h': float(opp.estimated_profit_8h),
                    'net_profit_8h': float(opp.net_profit_8h),
                    'confidence_score': float(opp.confidence_score),
                    'risk_level': opp.risk_level,
                    'created_at': opp.created_at.isoformat() if hasattr(opp, 'created_at') else datetime.now().isoformat()
                } for opp in opportunities[:20]]  # 限制返回數量
        except Exception as e:
            logger.error(f"獲取套利機會失敗: {e}")
        
        return []
    
    def _get_system_metrics(self) -> Dict:
        """獲取系統指標"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'running': self.running,
                'websocket_enabled': self.use_websocket,
                'exchanges_count': len(self.available_exchanges),
                'active_connections': 0,
                'data_updates_per_minute': 0,
                'memory_usage': 0,
                'uptime': 0
            }
            
            # 如果系統正在運行，獲取更詳細的指標
            if self.running and self.system:
                # WebSocket 連接數
                if hasattr(self.system.monitor, 'ws_manager') and self.system.monitor.ws_manager:
                    metrics['active_connections'] = len(self.system.monitor.ws_manager.connectors)
                
                # 數據更新頻率
                if hasattr(self.system.monitor, 'ws_data_cache'):
                    metrics['cached_data_points'] = len(self.system.monitor.ws_data_cache)
                
                # 統計信息
                if hasattr(self.system, 'stats'):
                    metrics.update({
                        'opportunities_found': self.system.stats.get('opportunities_found', 0),
                        'trades_executed': self.system.stats.get('trades_executed', 0),
                        'total_profit': self.system.stats.get('total_profit', 0)
                    })
            
            return metrics
            
        except Exception as e:
            logger.error(f"獲取系統指標失敗: {e}")
            return {'timestamp': datetime.now().isoformat(), 'error': str(e)}
    
    def _get_historical_funding_rates(self, exchange: str, symbol: str, days: int) -> List[Dict]:
        """獲取歷史資金費率數據"""
        try:
            historical_data = []
            
            # 優先從套利系統獲取真實歷史數據
            if self.running and self.system and hasattr(self.system.monitor, 'fetch_funding_rate_history'):
                import asyncio
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    historical_data = loop.run_until_complete(
                        self.system.monitor.fetch_funding_rate_history(exchange, symbol, days)
                    )
                    loop.close()
                    
                    if historical_data:
                        logger.info(f"✅ 獲取到 {exchange} {symbol} {len(historical_data)} 筆歷史數據")
                        return historical_data
                except Exception as e:
                    logger.error(f"從套利系統獲取歷史數據失敗: {e}")
            
            # 嘗試從數據庫獲取歷史數據
            try:
                from database_manager import get_db
                db = get_db()
                
                # 從數據庫查詢歷史數據
                historical_data = db.get_funding_rate_history(exchange, symbol, days)
                
                if historical_data:
                    logger.info(f"✅ 從數據庫獲取到 {exchange} {symbol} {len(historical_data)} 筆歷史數據")
                    return historical_data
                    
            except Exception as e:
                logger.warning(f"從數據庫獲取歷史數據失敗: {e}")
            
            # 如果都失敗，返回空列表而不是模擬數據
            logger.warning(f"未能獲取 {exchange} {symbol} 的歷史資金費率數據")
            return []
            
        except Exception as e:
            logger.error(f"獲取歷史資金費率失敗: {e}")
            return []
    
    def set_arbitrage_system(self, system):
        """設置套利系統實例"""
        self.system = system
        if system:
            self.running = True
            logger.info("✅ Web界面已連接到套利系統")
    
    def _get_main_template(self):
        """獲取主頁面模板"""
        return '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>資金費率套利系統 - 監控面板</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        .header {
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        .title {
            text-align: center;
            color: #2c3e50;
            font-size: 2.2em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #3498db, #8e44ad);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        .card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background-color: #27ae60; }
        .status-stopped { background-color: #e74c3c; }
        .status-warning { background-color: #f39c12; }
        .control-buttons {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            flex: 1;
        }
        .btn-primary { 
            background: linear-gradient(45deg, #3498db, #2980b9);
            color: white;
        }
        .btn-danger { 
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white;
        }
        .btn:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .opportunities-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .opportunities-table th,
        .opportunities-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .opportunities-table th {
            background: linear-gradient(45deg, #3498db, #2980b9);
            color: white;
            font-weight: bold;
        }
        .opportunities-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        .profit-positive { color: #27ae60; font-weight: bold; }
        .confidence-high { color: #27ae60; }
        .confidence-medium { color: #f39c12; }
        .confidence-low { color: #e74c3c; }
        .log-container {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            margin-top: 15px;
        }
        .exchange-badge {
            display: inline-block;
            background: linear-gradient(45deg, #8e44ad, #9b59b6);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin: 2px;
        }
        @media (max-width: 768px) {
            .status-grid { grid-template-columns: 1fr; }
            .control-buttons { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 頭部 -->
        <div class="header">
            <h1 class="title">🚀 資金費率套利系統</h1>
            <p style="text-align: center; color: #7f8c8d; font-size: 1.1em;">
                多交易所實時監控與自動套利平台
            </p>
        </div>

        <!-- 狀態網格 -->
        <div class="status-grid">
            <!-- 系統狀態 -->
            <div class="card">
                <h3>🔧 系統狀態</h3>
                <p>
                    <span class="status-indicator status-stopped" id="status-indicator"></span>
                    <span id="system-status">正在載入...</span>
                </p>
                <p><strong>可用交易所:</strong> <span id="exchanges-list">載入中...</span></p>
                <p><strong>監控交易對:</strong> <span id="symbols-count">-</span> 個</p>
                <p><strong>上次更新:</strong> <span id="last-update">-</span></p>
                
                <div class="control-buttons">
                    <button class="btn btn-primary" onclick="startSystem()">▶️ 啟動系統</button>
                    <button class="btn btn-danger" onclick="stopSystem()">⏹️ 停止系統</button>
                </div>
            </div>

            <!-- 套利機會 -->
            <div class="card">
                <h3>💰 當前套利機會</h3>
                <div id="opportunities-container">
                    <p>正在載入套利機會...</p>
                </div>
            </div>

            <!-- 帳戶餘額 -->
            <div class="card">
                <h3>💳 帳戶餘額</h3>
                <div id="balances-container">
                    <p>正在載入帳戶餘額...</p>
                </div>
            </div>

            <!-- 系統日誌 -->
            <div class="card">
                <h3>📋 系統日誌</h3>
                <div class="log-container" id="log-container">
                    系統啟動中...
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket 連接
        const socket = io();
        
        // 系統狀態管理
        let systemRunning = false;
        
        socket.on('connect', function() {
            addLog('✅ 已連接到系統');
            loadSystemStatus();
            loadOpportunities();
            loadBalances();
        });
        
        socket.on('status', function(data) {
            addLog('📊 ' + data.message);
        });
        
        socket.on('error', function(data) {
            addLog('❌ ' + data.message);
        });
        
        // 載入系統狀態
        function loadSystemStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateSystemStatus(data);
                })
                .catch(error => {
                    console.error('載入系統狀態失敗:', error);
                });
        }
        
        // 更新系統狀態顯示
        function updateSystemStatus(data) {
            const indicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('system-status');
            const exchangesList = document.getElementById('exchanges-list');
            const symbolsCount = document.getElementById('symbols-count');
            const lastUpdate = document.getElementById('last-update');
            
            systemRunning = data.status === 'running';
            
            if (systemRunning) {
                indicator.className = 'status-indicator status-running';
                statusText.textContent = '系統運行中';
            } else {
                indicator.className = 'status-indicator status-stopped';
                statusText.textContent = '系統已停止';
            }
            
            // 顯示交易所標籤
            exchangesList.innerHTML = data.exchanges.map(ex => 
                `<span class="exchange-badge">${ex}</span>`
            ).join('');
            
            symbolsCount.textContent = data.symbols.length;
            lastUpdate.textContent = new Date(data.timestamp).toLocaleString('zh-TW');
        }
        
        // 載入套利機會
        function loadOpportunities() {
            fetch('/api/opportunities')
                .then(response => response.json())
                .then(data => {
                    updateOpportunities(data);
                })
                .catch(error => {
                    console.error('載入套利機會失敗:', error);
                });
        }
        
        // 更新套利機會顯示
        function updateOpportunities(opportunities) {
            const container = document.getElementById('opportunities-container');
            
            if (opportunities.length === 0) {
                container.innerHTML = '<p style="color: #7f8c8d;">暫無套利機會</p>';
                return;
            }
            
            let html = '<table class="opportunities-table"><thead><tr>';
            html += '<th>交易對</th><th>策略</th><th>預期利潤</th><th>可信度</th>';
            html += '</tr></thead><tbody>';
            
            opportunities.forEach(opp => {
                const confidenceClass = opp.confidence >= 0.8 ? 'confidence-high' : 
                                      opp.confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
                
                html += '<tr>';
                html += `<td>${opp.symbol}</td>`;
                html += `<td>${opp.strategy}</td>`;
                html += `<td class="profit-positive">+${opp.profit_8h.toFixed(2)} USDT</td>`;
                html += `<td class="${confidenceClass}">${(opp.confidence * 100).toFixed(1)}%</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        // 載入帳戶餘額
        function loadBalances() {
            fetch('/api/balances')
                .then(response => response.json())
                .then(data => {
                    updateBalances(data);
                })
                .catch(error => {
                    console.error('載入帳戶餘額失敗:', error);
                });
        }
        
        // 更新帳戶餘額顯示
        function updateBalances(balances) {
            const container = document.getElementById('balances-container');
            
            if (Object.keys(balances).length === 0) {
                container.innerHTML = '<p style="color: #7f8c8d;">暫無餘額數據</p>';
                return;
            }
            
            let html = '';
            Object.entries(balances).forEach(([exchange, balance]) => {
                html += `<div style="margin-bottom: 10px;">`;
                html += `<strong>${exchange}:</strong> `;
                html += `USDT: ${balance.USDT.toFixed(2)}, `;
                html += `BTC: ${balance.BTC.toFixed(4)}, `;
                html += `ETH: ${balance.ETH.toFixed(3)}`;
                html += `</div>`;
            });
            
            container.innerHTML = html;
        }
        
        // 啟動系統
        function startSystem() {
            socket.emit('start_system', {});
            addLog('🚀 正在啟動套利系統...');
        }
        
        // 停止系統
        function stopSystem() {
            socket.emit('stop_system', {});
            addLog('⏹️ 正在停止套利系統...');
        }
        
        // 添加日誌
        function addLog(message) {
            const logContainer = document.getElementById('log-container');
            const timestamp = new Date().toLocaleTimeString('zh-TW');
            const logEntry = `[${timestamp}] ${message}\\n`;
            logContainer.textContent += logEntry;
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 定期更新數據
        setInterval(() => {
            loadSystemStatus();
            loadOpportunities();
            loadBalances();
        }, 30000); // 每30秒更新一次
        
        // 頁面載入完成後立即更新
        document.addEventListener('DOMContentLoaded', function() {
            addLog('🌐 Web 界面已載入');
        });
    </script>
</body>
</html>
        '''
    
    def run(self, host='0.0.0.0', port=None, debug=False):
        """啟動 Web 界面"""
        port = port or self.config.system.web_port
        
        logger.info(f"啟動 Web 界面服務器: http://{host}:{port}")
        
        try:
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logger.error(f"Web 界面啟動失敗: {e}")
    
    def start_background(self, host='0.0.0.0', port=None):
        """在背景執行緒中啟動 Web 界面"""
        def run_server():
            self.run(host=host, port=port, debug=False)
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread

def create_web_interface(available_exchanges: list = None) -> WebInterface:
    """創建 Web 界面實例"""
    return WebInterface(available_exchanges=available_exchanges)

if __name__ == "__main__":
    # 測試運行
    from config_funding import ConfigManager, ExchangeDetector
    
    config_manager = ConfigManager()
    available_exchanges = ExchangeDetector.detect_configured_exchanges(config_manager)
    
    web_interface = create_web_interface(available_exchanges)
    
    print("🌐 啟動 Web 界面...")
    print("📱 請打開瀏覽器訪問: http://localhost:8080")
    print("🔧 按 Ctrl+C 停止服務器")
    
    web_interface.run(debug=True) 