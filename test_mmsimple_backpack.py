#!/usr/bin/env python3
"""
臨時測試文件 - 使用 MM-Simple 方式測試 Backpack 資產獲取
測試是否能正常獲取加密貨幣資產而不是只有 POINTS
"""

import asyncio
import aiohttp
import json
import base64
import time
import os
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

class MMSimpleBackpackTest:
    """使用 MM-Simple 方式測試 Backpack 資產獲取"""
    
    def __init__(self):
        self.base_url = "https://api.backpack.exchange"
        self.signing_key = None
        
        # 嘗試多種方式獲取 API 憑證
        self.api_key, self.secret_key = self._get_api_credentials()
        
        if not self.api_key or not self.secret_key:
            print("❌ 無法獲取 BACKPACK API 憑證")
            print("💡 請檢查以下任一配置方式:")
            print("   1. 環境變數: BACKPACK_API_KEY, BACKPACK_SECRET_KEY")
            print("   2. config.json 文件中的 backpack 配置")
            print("   3. .env 文件配置")
            return
        
        print(f"✅ API Key: {self.api_key[:8]}...")
        print(f"✅ Secret Key: {self.secret_key[:8]}...")
        
        # 初始化簽名密鑰
        try:
            self.signing_key = SigningKey(base64.b64decode(self.secret_key))
            print("✅ ED25519 簽名密鑰初始化成功")
        except Exception as e:
            print(f"❌ 簽名密鑰初始化失敗: {e}")
            self.signing_key = None
    
    def _get_api_credentials(self):
        """嘗試多種方式獲取 API 憑證"""
        
        # 方式1: 環境變數
        api_key = os.getenv('BACKPACK_API_KEY')
        secret_key = os.getenv('BACKPACK_SECRET_KEY')
        
        if api_key and secret_key:
            print("📡 從環境變數獲取 API 憑證")
            return api_key, secret_key
        
        # 方式2: config.json 文件
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                backpack_config = config.get('exchanges', {}).get('backpack', {})
                api_key = backpack_config.get('api_key')
                secret_key = backpack_config.get('secret_key')
                
                if api_key and secret_key and api_key != 'BACKPACK_API_KEY':
                    print("📡 從 config.json 獲取 API 憑證")
                    return api_key, secret_key
        except Exception as e:
            print(f"⚠️  讀取 config.json 失敗: {e}")
        
                 # 方式3: .env 文件
        try:
            if os.path.exists('.env'):
                with open('.env', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('BACKPACK_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                        elif line.startswith('BACKPACK_SECRET_KEY='):
                            secret_key = line.split('=', 1)[1].strip()
                
                if api_key and secret_key:
                    print("📡 從 .env 文件獲取 API 憑證")
                    return api_key, secret_key
        except Exception as e:
            print(f"⚠️  讀取 .env 文件失敗: {e}")
        
        # 所有方式都失敗，返回 None
        print("❌ 無法從任何來源獲取 API 憑證")
        print("📝 請使用以下任一方式配置:")
        print("   1. 設置環境變數: BACKPACK_API_KEY, BACKPACK_SECRET_KEY")
        print("   2. 修改 config.json 中的 backpack 配置")
        print("   3. 創建 .env 文件並配置憑證")
        
        return None, None
    
    def create_signature(self, instruction: str, params: dict = None) -> tuple:
        """創建 MM-Simple 風格的簽名"""
        if not self.signing_key:
            return None, None, None
        
        try:
            timestamp = str(int(time.time() * 1000))
            window = "5000"
            
            # 構建簽名字符串
            if params:
                query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                message = f"instruction={instruction}&{query_string}&timestamp={timestamp}&window={window}"
            else:
                message = f"instruction={instruction}&timestamp={timestamp}&window={window}"
            
            # 簽名
            signature_bytes = self.signing_key.sign(message.encode()).signature
            signature = base64.b64encode(signature_bytes).decode()
            
            print(f"🔐 簽名訊息: {message}")
            print(f"🔐 生成簽名: {signature[:20]}...")
            
            return signature, timestamp, window
        except Exception as e:
            print(f"❌ 簽名創建失敗: {e}")
            return None, None, None
    
    async def get_balance(self) -> dict:
        """MM-Simple 風格的餘額查詢 - /api/v1/capital"""
        print("\n🎯 測試 MM-Simple 風格餘額查詢...")
        
        try:
            signature, timestamp, window = self.create_signature("balanceQuery")
            if not signature:
                return {"error": "簽名創建失敗"}
            
            headers = {
                "X-API-KEY": self.api_key,
                "X-SIGNATURE": signature,
                "X-TIMESTAMP": timestamp,
                "X-WINDOW": window,
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/api/v1/capital"
            
            async with aiohttp.ClientSession() as session:
                print(f"📡 請求: GET {url}")
                print(f"📡 Headers: {json.dumps({k: v[:10] + '...' if len(v) > 10 else v for k, v in headers.items()}, indent=2)}")
                
                async with session.get(url, headers=headers) as response:
                    status = response.status
                    text = await response.text()
                    
                    print(f"📨 響應狀態: {status}")
                    print(f"📨 響應內容: {text}")
                    
                    if status == 200:
                        try:
                            data = json.loads(text)
                            return {"status": "success", "data": data}
                        except json.JSONDecodeError as e:
                            return {"status": "json_error", "error": str(e), "raw": text}
                    else:
                        return {"status": "http_error", "code": status, "response": text}
                        
        except Exception as e:
            print(f"❌ 餘額查詢異常: {e}")
            return {"status": "exception", "error": str(e)}
    
    async def get_collateral(self) -> dict:
        """MM-Simple 風格的抵押品查詢 - /api/v1/capital/collateral"""
        print("\n🎯 測試 MM-Simple 風格抵押品查詢...")
        
        try:
            signature, timestamp, window = self.create_signature("collateralQuery")
            if not signature:
                return {"error": "簽名創建失敗"}
            
            headers = {
                "X-API-KEY": self.api_key,
                "X-SIGNATURE": signature,
                "X-TIMESTAMP": timestamp,
                "X-WINDOW": window,
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/api/v1/capital/collateral"
            
            async with aiohttp.ClientSession() as session:
                print(f"📡 請求: GET {url}")
                print(f"📡 Headers: {json.dumps({k: v[:10] + '...' if len(v) > 10 else v for k, v in headers.items()}, indent=2)}")
                
                async with session.get(url, headers=headers) as response:
                    status = response.status
                    text = await response.text()
                    
                    print(f"📨 響應狀態: {status}")
                    print(f"📨 響應內容: {text}")
                    
                    if status == 200:
                        try:
                            data = json.loads(text)
                            return {"status": "success", "data": data}
                        except json.JSONDecodeError as e:
                            return {"status": "json_error", "error": str(e), "raw": text}
                    else:
                        return {"status": "http_error", "code": status, "response": text}
                        
        except Exception as e:
            print(f"❌ 抵押品查詢異常: {e}")
            return {"status": "exception", "error": str(e)}
    
    def format_balance_data(self, balance_result: dict) -> None:
        """格式化並顯示餘額數據"""
        print("\n" + "="*60)
        print("📊 餘額查詢結果分析")
        print("="*60)
        
        if balance_result.get("status") != "success":
            print(f"❌ 查詢失敗: {balance_result}")
            return
        
        data = balance_result.get("data", {})
        print(f"📋 原始數據類型: {type(data)}")
        print(f"📋 原始數據: {json.dumps(data, indent=2)}")
        
        if isinstance(data, dict):
            print(f"\n💰 發現 {len(data)} 種資產:")
            for asset, details in data.items():
                print(f"  🔸 {asset}: {details}")
                
                # 檢查是否有真實的加密貨幣資產
                if asset != "POINTS":
                    if isinstance(details, dict):
                        available = details.get('available', '0')
                        locked = details.get('locked', '0')
                        total = float(available) + float(locked)
                        if total > 0:
                            print(f"    ✅ 發現真實資產! 總量: {total}")
                    elif isinstance(details, (int, float, str)):
                        if float(details) > 0:
                            print(f"    ✅ 發現真實資產! 數量: {details}")
        
        elif isinstance(data, list):
            print(f"\n💰 發現 {len(data)} 個資產項目:")
            for item in data:
                print(f"  🔸 {item}")
    
    def format_collateral_data(self, collateral_result: dict) -> None:
        """格式化並顯示抵押品數據"""
        print("\n" + "="*60)
        print("🏦 抵押品查詢結果分析")
        print("="*60)
        
        if collateral_result.get("status") != "success":
            print(f"❌ 查詢失敗: {collateral_result}")
            return
        
        data = collateral_result.get("data", {})
        print(f"📋 原始數據類型: {type(data)}")
        print(f"📋 原始數據: {json.dumps(data, indent=2)}")
        
        if isinstance(data, dict):
            print(f"\n🏦 發現 {len(data)} 種抵押品:")
            for asset, details in data.items():
                print(f"  🔸 {asset}: {details}")
        elif isinstance(data, list):
            print(f"\n🏦 發現 {len(data)} 個抵押品項目:")
            for item in data:
                print(f"  🔸 {item}")

    async def run_tests(self):
        """運行所有測試"""
        print("🧪 MM-Simple 風格 Backpack 資產測試")
        print("="*60)
        print("🎯 目標: 測試是否能獲取真實加密貨幣資產，而不是只有 POINTS")
        print()
        
        try:
            # 測試餘額查詢
            balance_result = await self.get_balance()
            self.format_balance_data(balance_result)
            
            # 測試抵押品查詢
            collateral_result = await self.get_collateral()
            self.format_collateral_data(collateral_result)
            
            # 總結
            print("\n" + "="*60)
            print("📋 測試總結")
            print("="*60)
            
            balance_success = balance_result.get("status") == "success"
            collateral_success = collateral_result.get("status") == "success"
            
            print(f"✅ 餘額查詢: {'成功' if balance_success else '失敗'}")
            print(f"✅ 抵押品查詢: {'成功' if collateral_success else '失敗'}")
            
            if balance_success:
                balance_data = balance_result.get("data", {})
                has_crypto = any(asset != "POINTS" and (
                    isinstance(details, dict) and (float(details.get('available', 0)) + float(details.get('locked', 0))) > 0
                    or isinstance(details, (int, float, str)) and float(details) > 0
                ) for asset, details in balance_data.items() if isinstance(balance_data, dict))
                
                print(f"💰 是否有真實加密貨幣資產: {'是' if has_crypto else '否，只有 POINTS'}")
        
            print("\n💡 如果只有 POINTS，可能原因:")
            print("   1. 帳戶中確實沒有其他加密貨幣")
            print("   2. 需要先入金到 Backpack 帳戶")
            print("   3. API 權限限制")
            print("   4. 帳戶狀態或驗證問題")
            
        except Exception as e:
            print(f"❌ 測試過程中發生異常: {e}")
            import traceback
            traceback.print_exc()

def demo_mode():
    """演示模式: 不需要 API 憑證，展示 API 結構和簽名過程"""
    print("\n🎭 演示模式: Backpack API 結構分析")
    print("=" * 60)
    
    print("\n📋 1. API 端點結構:")
    endpoints = {
        "餘額查詢": "/api/v1/capital",
        "抵押品查詢": "/api/v1/collateral", 
        "市場數據": "/api/v1/markets",
        "訂單查詢": "/api/v1/orders",
        "持倉查詢": "/api/v1/positions"
    }
    
    for name, endpoint in endpoints.items():
        print(f"   • {name}: {endpoint}")
    
    print("\n🔐 2. MM-Simple 簽名過程:")
    print("   步驟 1: 創建指令字符串")
    print("   步驟 2: 使用 ED25519 私鑰簽名")
    print("   步驟 3: Base64 編碼簽名")
    print("   步驟 4: 添加到請求標頭")
    
    print("\n📤 3. 請求標頭格式:")
    headers = {
        "X-API-Key": "[您的 API Key]",
        "X-Signature": "[ED25519 簽名]", 
        "X-Timestamp": "[Unix 時間戳]",
        "Content-Type": "application/json"
    }
    
    for key, value in headers.items():
        print(f"   {key}: {value}")
    
    print("\n🎯 4. 預期響應格式:")
    print("   餘額響應: { balances: [{ available, locked }] }")
    print("   抵押品響應: { collateral: { amount, asset } }")
    
    print("\n💡 5. 使用說明:")
    print("   • 配置真實 API 憑證後，程序將:")
    print("     - 查詢賬戶餘額")
    print("     - 檢查抵押品狀態") 
    print("     - 分析是否只有 POINTS 或包含真實加密貨幣")
    print("     - 提供詳細的資產分析報告")

async def main():
    """主函數"""
    # 檢查是否有 --demo 參數
    import sys
    if "--demo" in sys.argv:
        demo_mode()
    else:
        # 正常運行測試
        tester = MMSimpleBackpackTest()
        if tester.signing_key:
            await tester.run_tests()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 