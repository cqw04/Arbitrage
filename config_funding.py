#!/usr/bin/env python3
"""
資金費率套利系統配置文件
包含所有可調參數和交易所設置
"""
from dataclasses import dataclass
from typing import Dict, List, Any
from enum import Enum
import os
import json

@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    api_key: str
    secret_key: str
    maker_fee: float = 0.0002
    taker_fee: float = 0.0004
    passphrase: str = ""  # 對於需要 passphrase 的交易所（如 OKX, Bitget）

@dataclass
class RiskConfig:
    """風險管理配置"""
    max_drawdown_pct: float = 5.0  # 最大回撤百分比
    stop_loss_pct: float = 2.0  # 止損百分比
    max_correlation: float = 0.7  # 最大相關性
    min_confidence_score: float = 0.6  # 最小可信度
    daily_loss_limit: float = 500  # 每日最大虧損 USDT

@dataclass
class TradingConfig:
    """交易配置"""
    symbols: List[str]
    max_total_exposure: float = 10000  # USDT
    max_single_position: float = 2000  # USDT
    min_spread_threshold: float = 0.001  # 0.1%
    extreme_rate_threshold: float = 0.001  # 0.1%
    min_profit_threshold: float = 0.002  # 0.2%
    update_interval: int = 30  # 秒
    position_timeout_hours: float = 8.5

@dataclass
class SystemConfig:
    """系統配置"""
    log_level: str = "INFO"
    log_file: str = "funding_arbitrage.log"
    database_url: str = "sqlite:///funding_arbitrage.db"
    enable_web_interface: bool = True
    web_port: int = 8080
    enable_telegram_alerts: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

class StrategyType(Enum):
    """策略類型"""
    ALL = "all"
    CROSS_EXCHANGE = "cross_exchange"
    EXTREME_FUNDING = "extreme_funding"
    SPOT_FUTURES = "spot_futures"
    LENDING_ARBITRAGE = "lending_arbitrage"

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.exchanges: Dict[str, ExchangeConfig] = {}
        self.trading: TradingConfig = TradingConfig(symbols=[])
        self.risk: RiskConfig = RiskConfig()
        self.system: SystemConfig = SystemConfig()
        
        self.load_config()
    
    def load_config(self):
        """加載配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 加載交易所配置
                for exchange_name, exchange_data in config_data.get('exchanges', {}).items():
                    self.exchanges[exchange_name] = ExchangeConfig(
                        name=exchange_name,
                        api_key=exchange_data.get('api_key', ''),
                        secret_key=exchange_data.get('secret_key', ''),
                        maker_fee=exchange_data.get('maker_fee', 0.0002),
                        taker_fee=exchange_data.get('taker_fee', 0.0004),
                        passphrase=exchange_data.get('passphrase', '')
                    )
                
                # 加載交易配置
                trading_data = config_data.get('trading', {})
                self.trading = TradingConfig(
                    symbols=trading_data.get('symbols', self._get_default_symbols()),
                    max_total_exposure=trading_data.get('max_total_exposure', 10000),
                    max_single_position=trading_data.get('max_single_position', 2000),
                    min_spread_threshold=trading_data.get('min_spread_threshold', 0.001),
                    extreme_rate_threshold=trading_data.get('extreme_rate_threshold', 0.001),
                    min_profit_threshold=trading_data.get('min_profit_threshold', 0.002),
                    update_interval=trading_data.get('update_interval', 30),
                    position_timeout_hours=trading_data.get('position_timeout_hours', 8.5)
                )
                
                # 加載風險配置
                risk_data = config_data.get('risk', {})
                self.risk = RiskConfig(
                    max_drawdown_pct=risk_data.get('max_drawdown_pct', 5.0),
                    stop_loss_pct=risk_data.get('stop_loss_pct', 2.0),
                    max_correlation=risk_data.get('max_correlation', 0.7),
                    min_confidence_score=risk_data.get('min_confidence_score', 0.6),
                    daily_loss_limit=risk_data.get('daily_loss_limit', 500)
                )
                
                # 加載系統配置
                system_data = config_data.get('system', {})
                self.system = SystemConfig(
                    log_level=system_data.get('log_level', 'INFO'),
                    log_file=system_data.get('log_file', 'funding_arbitrage.log'),
                    database_url=system_data.get('database_url', 'sqlite:///funding_arbitrage.db'),
                    enable_web_interface=system_data.get('enable_web_interface', True),
                    web_port=system_data.get('web_port', 8080),
                    enable_telegram_alerts=system_data.get('enable_telegram_alerts', False),
                    telegram_bot_token=system_data.get('telegram_bot_token', ''),
                    telegram_chat_id=system_data.get('telegram_chat_id', '')
                )
                
                print(f"配置已從 {self.config_file} 加載")
                
            except Exception as e:
                print(f"加載配置失敗: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """創建默認配置"""
        print(f"創建默認配置文件: {self.config_file}")
        
        # 默認交易所配置
        self.exchanges = {
            'backpack': ExchangeConfig(
                name='backpack',
                api_key='your_backpack_api_key',
                secret_key='your_backpack_secret_key',
                maker_fee=0.0002,
                taker_fee=0.0004
            ),
            'binance': ExchangeConfig(
                name='binance',
                api_key='your_binance_api_key',
                secret_key='your_binance_secret_key',
                maker_fee=0.0002,
                taker_fee=0.0004
            ),
            'bybit': ExchangeConfig(
                name='bybit',
                api_key='your_bybit_api_key',
                secret_key='your_bybit_secret_key',
                maker_fee=0.0002,
                taker_fee=0.0005
            )
        }
        
        # 默認交易配置
        self.trading = TradingConfig(
            symbols=self._get_default_symbols(),
            max_total_exposure=10000,
            max_single_position=2000,
            min_spread_threshold=0.001,
            extreme_rate_threshold=0.001,
            min_profit_threshold=0.002,
            update_interval=30,
            position_timeout_hours=8.5
        )
        
        # 默認風險配置
        self.risk = RiskConfig()
        
        # 默認系統配置
        self.system = SystemConfig()
        
        self.save_config()
    
    def _get_default_symbols(self) -> List[str]:
        """獲取默認交易符號"""
        return [
            'BTC/USDT:USDT',
            'ETH/USDT:USDT',
            'SOL/USDT:USDT',
            'MATIC/USDT:USDT',
            'AVAX/USDT:USDT',
            'LINK/USDT:USDT',
            'ADA/USDT:USDT',
            'DOT/USDT:USDT',
            'UNI/USDT:USDT',
            'LTC/USDT:USDT'
        ]
    
    def save_config(self):
        """保存配置"""
        try:
            config_data = {
                'exchanges': {},
                'trading': {
                    'symbols': self.trading.symbols,
                    'max_total_exposure': self.trading.max_total_exposure,
                    'max_single_position': self.trading.max_single_position,
                    'min_spread_threshold': self.trading.min_spread_threshold,
                    'extreme_rate_threshold': self.trading.extreme_rate_threshold,
                    'min_profit_threshold': self.trading.min_profit_threshold,
                    'update_interval': self.trading.update_interval,
                    'position_timeout_hours': self.trading.position_timeout_hours
                },
                'risk': {
                    'max_drawdown_pct': self.risk.max_drawdown_pct,
                    'stop_loss_pct': self.risk.stop_loss_pct,
                    'max_correlation': self.risk.max_correlation,
                    'min_confidence_score': self.risk.min_confidence_score,
                    'daily_loss_limit': self.risk.daily_loss_limit
                },
                'system': {
                    'log_level': self.system.log_level,
                    'log_file': self.system.log_file,
                    'database_url': self.system.database_url,
                    'enable_web_interface': self.system.enable_web_interface,
                    'web_port': self.system.web_port,
                    'enable_telegram_alerts': self.system.enable_telegram_alerts,
                    'telegram_bot_token': self.system.telegram_bot_token,
                    'telegram_chat_id': self.system.telegram_chat_id
                }
            }
            
            # 加入交易所配置
            for name, config in self.exchanges.items():
                config_data['exchanges'][name] = {
                    'api_key': config.api_key,
                    'secret_key': config.secret_key,
                    'maker_fee': config.maker_fee,
                    'taker_fee': config.taker_fee,
                    'passphrase': config.passphrase
                }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print(f"配置已保存到 {self.config_file}")
            
        except Exception as e:
            print(f"保存配置失敗: {e}")
    
    def get_exchange_credentials(self) -> Dict[str, Dict[str, str]]:
        """獲取交易所認證信息"""
        credentials = {}
        for name, config in self.exchanges.items():
            credentials[name] = {
                'api_key': config.api_key,
                'secret_key': config.secret_key,
            }
        return credentials
    
    def get_commission_rates(self) -> Dict[str, Dict[str, float]]:
        """獲取手續費率"""
        rates = {}
        for name, config in self.exchanges.items():
            rates[name] = {
                'maker': config.maker_fee,
                'taker': config.taker_fee
            }
        return rates
    
    def update_exchange_config(self, exchange_name: str, **kwargs):
        """更新交易所配置"""
        if exchange_name in self.exchanges:
            config = self.exchanges[exchange_name]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self.save_config()
        else:
            print(f"交易所 {exchange_name} 不存在")
    
    def set_runtime_credentials(self, exchange_name: str, api_key: str, secret_key: str):
        """設置運行時憑證（僅在內存中，不保存到文件）"""
        if exchange_name in self.exchanges:
            config = self.exchanges[exchange_name]
            config.api_key = api_key
            config.secret_key = secret_key
            # 注意：不調用 save_config()，只在內存中修改
        else:
            print(f"交易所 {exchange_name} 不存在")
    
    def add_symbol(self, symbol: str):
        """添加交易符號"""
        if symbol not in self.trading.symbols:
            self.trading.symbols.append(symbol)
            self.save_config()
            print(f"已添加交易符號: {symbol}")
    
    def remove_symbol(self, symbol: str):
        """移除交易符號"""
        if symbol in self.trading.symbols:
            self.trading.symbols.remove(symbol)
            self.save_config()
            print(f"已移除交易符號: {symbol}")
    
    def validate_config(self) -> List[str]:
        """驗證配置"""
        errors = []
        
        # 檢查交易所配置
        for name, config in self.exchanges.items():
            if not config.api_key or config.api_key == f'your_{name.lower()}_api_key':
                errors.append(f"{name} API密鑰未配置")
            if not config.secret_key or config.secret_key == f'your_{name.lower()}_secret_key':
                errors.append(f"{name} 密鑰未配置")
        
        # 檢查交易配置
        if not self.trading.symbols:
            errors.append("沒有配置交易符號")
        
        if self.trading.max_total_exposure <= 0:
            errors.append("最大總敞口必須大於0")
        
        if self.trading.max_single_position <= 0:
            errors.append("最大單筆倉位必須大於0")
        
        # 檢查風險配置
        if self.risk.max_drawdown_pct <= 0:
            errors.append("最大回撤百分比必須大於0")
        
        return errors

# 全局配置管理器實例
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """獲取全局配置實例"""
    return ConfigManager()

class ExchangeDetector:
    """交易所檢測器 - 檢測哪些交易所已正確配置"""
    
    @staticmethod
    def detect_configured_exchanges(config: ConfigManager) -> List[str]:
        """檢測已正確配置的交易所"""
        configured_exchanges = []
        
        for exchange_name, exchange_config in config.exchanges.items():
            # 檢查是否有有效的API密鑰（不是預設值）
            if (exchange_config.api_key and 
                exchange_config.secret_key and
                not exchange_config.api_key.startswith('your_') and
                not exchange_config.secret_key.startswith('your_')):
                configured_exchanges.append(exchange_name)
        
        return configured_exchanges
    
    @staticmethod
    def is_exchange_configured(config: ConfigManager, exchange_name: str) -> bool:
        """檢查特定交易所是否已配置"""
        if exchange_name not in config.exchanges:
            return False
        
        exchange_config = config.exchanges[exchange_name]
        return (exchange_config.api_key and 
                exchange_config.secret_key and
                not exchange_config.api_key.startswith('your_') and
                not exchange_config.secret_key.startswith('your_'))

# 配置驗證和提示
if __name__ == "__main__":
    print("=== 資金費率套利系統配置管理 ===")
    
    # 驗證配置
    errors = config_manager.validate_config()
    if errors:
        print("\n❌ 配置錯誤:")
        for error in errors:
            print(f"  - {error}")
        print("\n請編輯 config.json 文件修正這些問題")
    else:
        print("\n✅ 配置驗證通過")
    
    print(f"\n📊 當前配置:")
    print(f"  - 支持交易所: {', '.join(config_manager.exchanges.keys())}")
    print(f"  - 監控符號數量: {len(config_manager.trading.symbols)}")
    print(f"  - 最大總敞口: {config_manager.trading.max_total_exposure} USDT")
    print(f"  - 更新間隔: {config_manager.trading.update_interval} 秒")
    print(f"  - Web界面: {'啟用' if config_manager.system.enable_web_interface else '禁用'}") 