#!/usr/bin/env python3
"""
資金費率套利系統數據庫管理器
"""

import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging
from dataclasses import asdict

from config_funding import get_config

config = get_config()
logger = logging.getLogger("DatabaseManager")


class DatabaseManager:
    """數據庫管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.system.database_url.replace('sqlite:///', '')
        self.connection = None
        self.init_database()
    
    def init_database(self):
        """初始化數據庫"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # 讓查詢結果可以像字典一樣訪問
            
            self.create_tables()
            logger.info(f"數據庫初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"數據庫初始化失敗: {e}")
    
    def create_tables(self):
        """創建數據表"""
        cursor = self.connection.cursor()
        
        # 資金費率歷史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funding_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                funding_rate REAL NOT NULL,
                predicted_rate REAL,
                mark_price REAL,
                index_price REAL,
                next_funding_time DATETIME,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 套利機會表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                primary_exchange TEXT NOT NULL,
                secondary_exchange TEXT NOT NULL,
                funding_rate_diff REAL NOT NULL,
                estimated_profit_8h REAL NOT NULL,
                commission_cost REAL NOT NULL,
                net_profit_8h REAL NOT NULL,
                confidence_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                entry_conditions TEXT,  -- JSON
                exit_conditions TEXT,   -- JSON
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 倉位記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT UNIQUE NOT NULL,
                opportunity_id INTEGER,
                position_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL,
                exit_price REAL,
                long_exchange TEXT,
                short_exchange TEXT,
                open_time DATETIME NOT NULL,
                close_time DATETIME,
                status TEXT NOT NULL,
                estimated_profit REAL,
                actual_profit REAL,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (opportunity_id) REFERENCES arbitrage_opportunities (id)
            )
        ''')
        
        # 系統統計表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                opportunities_found INTEGER DEFAULT 0,
                trades_executed INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0.0,
                total_loss REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                avg_profit_per_trade REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                active_positions INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 交易所狀態表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                status TEXT NOT NULL,  -- online, offline, error
                last_update DATETIME NOT NULL,
                error_message TEXT,
                api_calls_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 創建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_funding_rates_exchange_symbol ON funding_rates(exchange, symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_funding_rates_timestamp ON funding_rates(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_opportunities_created_at ON arbitrage_opportunities(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_position_id ON positions(position_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)')
        
        self.connection.commit()
        logger.info("數據表創建完成")
    
    def save_funding_rate(self, funding_rate_info):
        """保存資金費率數據"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO funding_rates 
                (exchange, symbol, funding_rate, predicted_rate, mark_price, index_price, next_funding_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                funding_rate_info.exchange,
                funding_rate_info.symbol,
                funding_rate_info.funding_rate,
                funding_rate_info.predicted_rate,
                funding_rate_info.mark_price,
                funding_rate_info.index_price,
                funding_rate_info.next_funding_time,
                funding_rate_info.timestamp
            ))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"保存資金費率數據失敗: {e}")
    
    def save_arbitrage_opportunity(self, opportunity) -> int:
        """保存套利機會，返回ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO arbitrage_opportunities 
                (strategy_type, symbol, primary_exchange, secondary_exchange, funding_rate_diff,
                 estimated_profit_8h, commission_cost, net_profit_8h, confidence_score, risk_level,
                 entry_conditions, exit_conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                opportunity.strategy_type.value,
                opportunity.symbol,
                opportunity.primary_exchange,
                opportunity.secondary_exchange,
                opportunity.funding_rate_diff,
                opportunity.estimated_profit_8h,
                opportunity.commission_cost,
                opportunity.net_profit_8h,
                opportunity.confidence_score,
                opportunity.risk_level,
                json.dumps(opportunity.entry_conditions),
                json.dumps(opportunity.exit_conditions)
            ))
            self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"保存套利機會失敗: {e}")
            return 0
    
    def save_position(self, position_data: Dict) -> bool:
        """保存倉位記錄"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO positions 
                (position_id, opportunity_id, position_type, symbol, size, entry_price, exit_price,
                 long_exchange, short_exchange, open_time, close_time, status, estimated_profit, 
                 actual_profit, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_data.get('position_id'),
                position_data.get('opportunity_id'),
                position_data.get('type'),
                position_data.get('symbol'),
                position_data.get('size'),
                position_data.get('entry_price'),
                position_data.get('exit_price'),
                position_data.get('long_exchange'),
                position_data.get('short_exchange'),
                position_data.get('open_time'),
                position_data.get('close_time'),
                position_data.get('status'),
                position_data.get('estimated_profit'),
                position_data.get('actual_profit'),
                position_data.get('notes')
            ))
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"保存倉位記錄失敗: {e}")
            return False
    
    def update_position(self, position_id: str, update_data: Dict) -> bool:
        """更新倉位記錄"""
        try:
            cursor = self.connection.cursor()
            
            # 構建更新語句
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            values.append(position_id)
            
            query = f"UPDATE positions SET {', '.join(set_clauses)} WHERE position_id = ?"
            cursor.execute(query, values)
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"更新倉位記錄失敗: {e}")
            return False
    
    def get_positions(self, status: str = None, limit: int = 100) -> List[Dict]:
        """獲取倉位記錄"""
        try:
            cursor = self.connection.cursor()
            
            if status:
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE status = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT * FROM positions 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"獲取倉位記錄失敗: {e}")
            return []
    
    def get_funding_rate_history(self, exchange: str, symbol: str, days: int = 7) -> List[Dict]:
        """獲取資金費率歷史"""
        try:
            cursor = self.connection.cursor()
            start_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT * FROM funding_rates 
                WHERE exchange = ? AND symbol = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (exchange, symbol, start_date))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"獲取資金費率歷史失敗: {e}")
            return []
    
    def update_daily_stats(self, date: datetime, stats: Dict):
        """更新每日統計"""
        try:
            cursor = self.connection.cursor()
            date_str = date.strftime('%Y-%m-%d')
            
            cursor.execute('''
                INSERT OR REPLACE INTO system_stats 
                (date, opportunities_found, trades_executed, total_profit, total_loss, 
                 success_rate, avg_profit_per_trade, max_drawdown, active_positions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                stats.get('opportunities_found', 0),
                stats.get('trades_executed', 0),
                stats.get('total_profit', 0.0),
                stats.get('total_loss', 0.0),
                stats.get('success_rate', 0.0),
                stats.get('avg_profit_per_trade', 0.0),
                stats.get('max_drawdown', 0.0),
                stats.get('active_positions', 0)
            ))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"更新每日統計失敗: {e}")
    
    def get_performance_stats(self, days: int = 30) -> Dict:
        """獲取性能統計"""
        try:
            cursor = self.connection.cursor()
            start_date = datetime.now() - timedelta(days=days)
            
            # 總體統計
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_opportunities,
                    SUM(CASE WHEN net_profit_8h > 0 THEN 1 ELSE 0 END) as profitable_opportunities
                FROM arbitrage_opportunities 
                WHERE created_at >= ?
            ''', (start_date,))
            
            opp_stats = cursor.fetchone()
            
            # 倉位統計
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_positions,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_positions,
                    SUM(CASE WHEN actual_profit > 0 THEN 1 ELSE 0 END) as profitable_positions,
                    AVG(actual_profit) as avg_profit,
                    SUM(actual_profit) as total_profit,
                    MAX(actual_profit) as max_profit,
                    MIN(actual_profit) as min_profit
                FROM positions 
                WHERE open_time >= ?
            ''', (start_date,))
            
            pos_stats = cursor.fetchone()
            
            return {
                'period_days': days,
                'total_opportunities': opp_stats['total_opportunities'] or 0,
                'profitable_opportunities': opp_stats['profitable_opportunities'] or 0,
                'total_positions': pos_stats['total_positions'] or 0,
                'closed_positions': pos_stats['closed_positions'] or 0,
                'profitable_positions': pos_stats['profitable_positions'] or 0,
                'success_rate': (pos_stats['profitable_positions'] or 0) / max(pos_stats['closed_positions'] or 1, 1) * 100,
                'avg_profit': pos_stats['avg_profit'] or 0,
                'total_profit': pos_stats['total_profit'] or 0,
                'max_profit': pos_stats['max_profit'] or 0,
                'min_profit': pos_stats['min_profit'] or 0
            }
            
        except Exception as e:
            logger.error(f"獲取性能統計失敗: {e}")
            return {}
    
    def get_top_performing_symbols(self, limit: int = 10) -> List[Dict]:
        """獲取表現最佳的交易符號"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT 
                    symbol,
                    COUNT(*) as trade_count,
                    AVG(actual_profit) as avg_profit,
                    SUM(actual_profit) as total_profit,
                    SUM(CASE WHEN actual_profit > 0 THEN 1 ELSE 0 END) as profitable_trades
                FROM positions 
                WHERE status = 'closed' AND actual_profit IS NOT NULL
                GROUP BY symbol
                ORDER BY total_profit DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"獲取頂級表現符號失敗: {e}")
            return []
    
    def update_exchange_status(self, exchange: str, status: str, error_message: str = None):
        """更新交易所狀態"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO exchange_status 
                (exchange, status, last_update, error_message, api_calls_count)
                VALUES (?, ?, ?, ?, COALESCE((SELECT api_calls_count FROM exchange_status WHERE exchange = ?) + 1, 1))
            ''', (exchange, status, datetime.now(), error_message, exchange))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"更新交易所狀態失敗: {e}")
    
    def cleanup_old_data(self, days: int = 30):
        """清理舊數據"""
        try:
            cursor = self.connection.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 清理舊的資金費率數據
            cursor.execute('DELETE FROM funding_rates WHERE timestamp < ?', (cutoff_date,))
            
            # 清理舊的套利機會數據（但保留有關聯倉位的）
            cursor.execute('''
                DELETE FROM arbitrage_opportunities 
                WHERE created_at < ? AND id NOT IN (
                    SELECT DISTINCT opportunity_id FROM positions WHERE opportunity_id IS NOT NULL
                )
            ''', (cutoff_date,))
            
            self.connection.commit()
            logger.info(f"清理了 {days} 天前的舊數據")
            
        except Exception as e:
            logger.error(f"清理舊數據失敗: {e}")
    
    def close(self):
        """關閉數據庫連接"""
        if self.connection:
            self.connection.close()
            logger.info("數據庫連接已關閉")


# 全局數據庫管理器實例
db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """獲取數據庫管理器實例"""
    return db_manager


if __name__ == "__main__":
    print("=== 資金費率套利系統數據庫管理 ===")
    
    # 測試數據庫連接
    db = DatabaseManager("test_arbitrage.db")
    
    # 獲取性能統計
    stats = db.get_performance_stats(30)
    print(f"過去30天統計: {stats}")
    
    # 獲取頂級表現符號
    top_symbols = db.get_top_performing_symbols(5)
    print(f"表現最佳符號: {top_symbols}")
    
    db.close() 