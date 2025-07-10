#!/usr/bin/env python3
"""
統一API認證工具類
支持多種交易所的不同簽名方式：HMAC SHA256、Ed25519等
"""

import hmac
import hashlib
import base64
import time
import json
from urllib.parse import urlencode
from typing import Dict, Optional, Union, Any
import logging
import nacl.signing
import sys

# ED25519 簽名支持
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False

logger = logging.getLogger(__name__)

class APIAuthenticator:
    """統一的API認證工具類"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def generate_hmac_sha256_signature(
        secret_key: str, 
        message: str, 
        encoding: str = 'utf-8'
    ) -> str:
        """生成HMAC SHA256簽名"""
        try:
            signature = hmac.new(
                secret_key.encode(encoding),
                message.encode(encoding),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            logger.error(f"生成HMAC SHA256簽名失敗: {e}")
            raise
    
    @staticmethod
    def generate_hmac_sha256_signature_b64(
        secret_key: str, 
        message: str, 
        encoding: str = 'utf-8'
    ) -> str:
        """生成Base64編碼的HMAC SHA256簽名"""
        try:
            signature = hmac.new(
                secret_key.encode(encoding),
                message.encode(encoding),
                hashlib.sha256
            ).digest()
            return base64.b64encode(signature).decode()
        except Exception as e:
            logger.error(f"生成Base64 HMAC SHA256簽名失敗: {e}")
            raise
    
    @staticmethod
    def generate_binance_signature(
        api_secret: str,
        query_string: str
    ) -> str:
        """生成Binance API簽名"""
        return APIAuthenticator.generate_hmac_sha256_signature(
            api_secret, query_string
        )
    
    @staticmethod
    def generate_bybit_signature(
        api_secret: str,
        timestamp: str,
        api_key: str,
        recv_window: str,
        query_string: str = ""
    ) -> str:
        """生成Bybit API v5簽名"""
        param_str = timestamp + api_key + recv_window + query_string
        return APIAuthenticator.generate_hmac_sha256_signature(
            api_secret, param_str
        )
    
    @staticmethod
    def generate_okx_signature(
        api_secret: str,
        timestamp: str,
        method: str,
        request_path: str,
        body: str = ""
    ) -> str:
        """生成OKX API v5簽名"""
        message = timestamp + method.upper() + request_path + body
        return APIAuthenticator.generate_hmac_sha256_signature_b64(
            api_secret, message
        )
    
    @staticmethod
    def generate_gate_io_signature(
        api_secret: str,
        method: str,
        url_path: str,
        query_string: str,
        payload_hash: str
    ) -> str:
        """生成Gate.io API簽名"""
        message = f"{method}\n{url_path}\n{query_string}\n{payload_hash}"
        return APIAuthenticator.generate_hmac_sha256_signature(
            api_secret, message
        )
    
    @staticmethod
    def generate_bitget_signature(
        api_secret: str,
        timestamp: str,
        method: str,
        request_path: str,
        body: str = ""
    ) -> str:
        """生成Bitget API簽名"""
        message = timestamp + method.upper() + request_path + body
        return APIAuthenticator.generate_hmac_sha256_signature_b64(
            api_secret, message
        )
    
    @staticmethod
    def generate_mexc_signature(
        api_secret: str,
        query_string: str
    ) -> str:
        """生成MEXC API簽名"""
        return APIAuthenticator.generate_hmac_sha256_signature(
            api_secret, query_string
        )
    
    @staticmethod
    def generate_ed25519_signature(
        private_key_base64: str,
        message: str
    ) -> str:
        """生成ED25519簽名（用於Backpack）"""
        if not ED25519_AVAILABLE:
            raise ImportError("cryptography package is required for ED25519 signatures")
        
        try:
            # 解碼Base64私鑰
            private_key_bytes = base64.b64decode(private_key_base64)
            
            # 創建ED25519私鑰對象
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            
            # 簽名消息
            signature = private_key.sign(message.encode('utf-8'))
            
            # 返回Base64編碼的簽名
            return base64.b64encode(signature).decode('utf-8')
            
        except Exception as e:
            logger.error(f"生成ED25519簽名失敗: {e}")
            raise
    
    @staticmethod
    def get_current_timestamp() -> int:
        """獲取當前時間戳（毫秒）"""
        return int(time.time() * 1000)
    
    @staticmethod
    def get_current_timestamp_seconds() -> int:
        """獲取當前時間戳（秒）"""
        return int(time.time())
    
    @staticmethod
    def prepare_query_string(params: Dict[str, Any]) -> str:
        """準備查詢字符串"""
        if not params:
            return ""
        
        # 過濾掉None值，但保持原始順序（修復BINANCE簽名問題）
        filtered_params = {k: v for k, v in params.items() if v is not None}
        # 不使用sorted()，保持字典原始順序
        return urlencode(list(filtered_params.items()))
    
    @staticmethod
    def prepare_query_string_sorted(params: Dict[str, Any]) -> str:
        """準備查詢字符串（排序版本，用於需要排序的交易所）"""
        if not params:
            return ""
        
        # 過濾掉None值並排序
        filtered_params = {k: v for k, v in params.items() if v is not None}
        return urlencode(sorted(filtered_params.items()))
    
    @staticmethod
    def prepare_json_body(params: Dict[str, Any]) -> str:
        """準備JSON請求體"""
        if not params:
            return ""
        return json.dumps(params, separators=(',', ':'))

# 具體交易所認證類
class BinanceAuth:
    """Binance API認證"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def get_headers(self) -> Dict[str, str]:
        """獲取請求頭"""
        return {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def sign_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """簽名請求"""
        if not params:
            params = {}
        
        # 添加時間戳
        params['timestamp'] = APIAuthenticator.get_current_timestamp()
        params['recvWindow'] = 5000
        
        # 生成查詢字符串
        query_string = APIAuthenticator.prepare_query_string(params)
        
        # 生成簽名
        signature = APIAuthenticator.generate_binance_signature(
            self.api_secret, query_string
        )
        
        # 添加簽名到參數
        params['signature'] = signature
        return params

class BybitAuth:
    """Bybit API v5認證"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def get_headers(self, params: Dict[str, Any] = None) -> Dict[str, str]:
        """獲取請求頭"""
        timestamp = str(APIAuthenticator.get_current_timestamp())
        recv_window = "5000"
        
        # 生成查詢字符串
        query_string = ""
        if params:
            query_string = APIAuthenticator.prepare_query_string(params)
        
        # 生成簽名
        signature = APIAuthenticator.generate_bybit_signature(
            self.api_secret, timestamp, self.api_key, recv_window, query_string
        )
        
        return {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': recv_window,
            'Content-Type': 'application/json'
        }

class OKXAuth:
    """OKX API v5認證"""
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
    
    def get_headers(
        self, 
        method: str, 
        request_path: str, 
        body: str = ""
    ) -> Dict[str, str]:
        """獲取請求頭"""
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # 生成簽名
        signature = APIAuthenticator.generate_okx_signature(
            self.api_secret, timestamp, method, request_path, body
        )
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

class GateIOAuth:
    """Gate.io API認證"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def get_headers(
        self, 
        method: str, 
        url_path: str, 
        query_string: str = "", 
        body: str = ""
    ) -> Dict[str, str]:
        """獲取請求頭"""
        timestamp = str(APIAuthenticator.get_current_timestamp_seconds())
        payload_hash = hashlib.sha512(body.encode('utf-8')).hexdigest()
        
        # 生成簽名
        signature = APIAuthenticator.generate_gate_io_signature(
            self.api_secret, method, url_path, query_string, payload_hash
        )
        
        return {
            'KEY': self.api_key,
            'Timestamp': timestamp,
            'SIGN': signature,
            'Content-Type': 'application/json'
        }

class BitgetAuth:
    """Bitget API認證"""
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
    
    def get_headers(
        self, 
        method: str, 
        request_path: str, 
        body: str = ""
    ) -> Dict[str, str]:
        """獲取請求頭"""
        timestamp = str(APIAuthenticator.get_current_timestamp())
        
        # 生成簽名
        signature = APIAuthenticator.generate_bitget_signature(
            self.api_secret, timestamp, method, request_path, body
        )
        
        return {
            'ACCESS-KEY': self.api_key,
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

class MEXCAuth:
    """MEXC API認證"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def get_headers(self) -> Dict[str, str]:
        """獲取請求頭"""
        return {
            'X-MEXC-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def sign_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """簽名請求"""
        if not params:
            params = {}
        
        # 添加時間戳
        params['timestamp'] = APIAuthenticator.get_current_timestamp()
        
        # 生成查詢字符串
        query_string = APIAuthenticator.prepare_query_string(params)
        
        # 生成簽名
        signature = APIAuthenticator.generate_mexc_signature(
            self.api_secret, query_string
        )
        
        # 添加簽名到參數
        params['signature'] = signature
        return params

class BackpackAuth:
    """BACKPACK 認證工具 - 基於官方 API 文檔"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
    
    def get_headers(self, method: str, endpoint: str, params: dict = None) -> dict:
        """生成請求頭 - 基於官方文檔的簽名方法"""
        try:
            import time
            import hmac
            import hashlib
            
            # 當前時間戳
            timestamp = str(int(time.time() * 1000))
            
            # 基本請求頭
            headers = {
                'X-API-Key': self.api_key,
                'X-Timestamp': timestamp,
                'Content-Type': 'application/json; charset=utf-8'
            }
            
            # 構建簽名字符串（根據 Backpack 文檔）
            # 格式: instruction + timestamp
            if params and 'instruction' in params:
                message = params['instruction'] + timestamp
            else:
                # 對於其他端點，使用路徑和時間戳
                message = endpoint + timestamp
            
            # 生成簽名
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers['X-Signature'] = signature
            
            return headers
            
        except Exception as e:
            logger.warning(f"BACKPACK 簽名生成失敗: {e}")
            return {
                'X-API-Key': self.api_key,
                'Content-Type': 'application/json; charset=utf-8'
            }

# 工廠模式創建認證器
class AuthFactory:
    """API認證器工廠"""
    
    @staticmethod
    def create_auth(
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None
    ) -> Union[BinanceAuth, BybitAuth, OKXAuth, GateIOAuth, BitgetAuth, MEXCAuth, BackpackAuth]:
        """創建對應交易所的認證器"""
        exchange_lower = exchange.lower()
        
        if exchange_lower == 'binance':
            return BinanceAuth(api_key, api_secret)
        elif exchange_lower == 'bybit':
            return BybitAuth(api_key, api_secret)
        elif exchange_lower == 'okx':
            if not passphrase:
                raise ValueError("OKX requires passphrase")
            return OKXAuth(api_key, api_secret, passphrase)
        elif exchange_lower == 'gateio':
            return GateIOAuth(api_key, api_secret)
        elif exchange_lower == 'bitget':
            if not passphrase:
                raise ValueError("Bitget requires passphrase")
            return BitgetAuth(api_key, api_secret, passphrase)
        elif exchange_lower == 'mexc':
            return MEXCAuth(api_key, api_secret)
        elif exchange_lower == 'backpack':
            return BackpackAuth(api_key, api_secret) 
        else:
            raise ValueError(f"Unsupported exchange: {exchange}") 

def create_signature(secret_key: str, message: str) -> Optional[str]:
    """
    創建API簽名
    
    Args:
        secret_key: API密鑰
        message: 要簽名的消息
        
    Returns:
        簽名字符串或None（如果簽名失敗）
    """
    try:
        # 嘗試對密鑰進行解碼和簽名
        decoded_key = base64.b64decode(secret_key)
        signing_key = nacl.signing.SigningKey(decoded_key)
        signature = signing_key.sign(message.encode('utf-8')).signature
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        logger.error(f"簽名創建失敗: {e}")
        logger.error("無法創建API簽名，程序將終止")
        # 強制終止程序
        sys.exit(1)

def create_backpack_auth_headers(api_key: str, secret_key: str, instruction: str, 
                                timestamp: Optional[str] = None, window: str = "5000",
                                params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    創建 Backpack API 認證請求頭
    
    Args:
        api_key: API 密鑰
        secret_key: 私鑰
        instruction: API 指令 (如 balanceQuery, collateralQuery)
        timestamp: 時間戳（毫秒），如果不提供則自動生成
        window: 時間窗口（毫秒），默認 5000
        params: 額外參數字典
        
    Returns:
        包含認證信息的請求頭字典
    """
    if timestamp is None:
        timestamp = str(int(time.time() * 1000))
    
    # 構建簽名消息
    sign_message = f"instruction={instruction}&timestamp={timestamp}&window={window}"
    
    # 添加額外參數到簽名消息
    if params:
        for key, value in sorted(params.items()):
            sign_message += f"&{key}={value}"
    
    # 創建簽名
    signature = create_signature(secret_key, sign_message)
    
    # 構建請求頭
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': api_key,
        'X-SIGNATURE': signature,
        'X-TIMESTAMP': timestamp,
        'X-WINDOW': window
    }
    
    logger.debug(f"創建認證頭成功 - 指令: {instruction}, 時間戳: {timestamp}")
    return headers

def validate_api_credentials(api_key: str, secret_key: str) -> bool:
    """
    驗證 API 憑證格式是否正確
    
    Args:
        api_key: API 密鑰
        secret_key: 私鑰
        
    Returns:
        True 如果憑證格式正確，False 否則
    """
    try:
        # 檢查 API 密鑰
        if not api_key or len(api_key) < 10:
            logger.error("API 密鑰格式不正確")
            return False
        
        # 檢查私鑰是否可以被正確解碼
        try:
            decoded_key = base64.b64decode(secret_key)
            if len(decoded_key) != 32:  # ED25519 私鑰應該是 32 字節
                logger.error("私鑰長度不正確")
                return False
        except Exception as e:
            logger.error(f"私鑰解碼失敗: {e}")
            return False
        
        logger.debug("API 憑證驗證通過")
        return True
        
    except Exception as e:
        logger.error(f"憑證驗證過程中出錯: {e}")
        return False

def test_signature_creation(secret_key: str, test_message: str = "test_message") -> bool:
    """
    測試簽名創建功能
    
    Args:
        secret_key: 私鑰
        test_message: 測試消息
        
    Returns:
        True 如果簽名創建成功，False 否則
    """
    try:
        signature = create_signature(secret_key, test_message)
        if signature and len(signature) > 0:
            logger.debug("簽名測試成功")
            return True
        else:
            logger.error("簽名測試失敗 - 返回空簽名")
            return False
    except Exception as e:
        logger.error(f"簽名測試失敗: {e}")
        return False 