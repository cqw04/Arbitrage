# 資金費率套利系統 2.0 🚀

一個專業的多交易所資金費率套利系統，參考優秀開源專案設計，提供完整的監控、分析和執行功能。

## ✨ 2.0 版本亮點

### 🎯 **統一入口設計 (New!)**
參考 [Backpack 做市專案](https://github.com/yanowo/Backpack-MM-Simple.git) 的優秀設計：
- **多模式執行**: 面板、CLI、直接執行
- **靈活參數**: 豐富的命令行參數配置
- **模擬模式**: 無風險的模擬運行測試

### 💻 **完整 CLI 界面 (New!)**
- **交互式菜單**: 友好的命令行操作界面
- **實時監控**: 查看套利機會和倉位狀態
- **配置管理**: 圖形化配置交易所和參數
- **統計分析**: 詳細的歷史數據和表現分析

### 🧮 **專業利潤計算器 (New!)**
- **精確計算**: 考慮手續費、滑點、基差風險
- **多策略支持**: 跨交易所套利、極端費率套利
- **風險評估**: 風險回報比、最大回撤分析
- **年化收益**: 投資回報率計算

### 🔧 **靈活配置系統 (Enhanced!)**
- **環境變數**: 支持 .env 文件管理 API 密鑰
- **動態配置**: 運行時修改參數無需重啟
- **配置驗證**: 自動檢查配置有效性
- **設定持久化**: 自動保存用戶設置

## 🚀 快速開始

### 1. 安裝系統
```bash
# 安裝依賴
pip install -r requirements_funding.txt
```

### 2. 配置 API 密鑰
```bash
# 複製環境變數範本
cp env_example.txt .env

# 編輯 .env 文件，填入真實的 API 密鑰
# BINANCE_API_KEY=your_real_api_key
# BINANCE_SECRET_KEY=your_real_secret_key
```

### 3. 使用系統

#### 🎛️ 啟動交互式 CLI (推薦新手)
```bash
python run.py --cli
```

#### 📊 查看當前套利機會
```bash
python run.py --show-opportunities --limit 10
```

#### 🚀 直接運行套利系統
```bash
python run.py --duration 24 --symbols BTC/USDT:USDT --dry-run
```

#### 📈 查看歷史統計
```bash
python run.py --stats --days 30 --format table
```

## 💡 使用示例

### 基本操作
```bash
# 啟動 CLI 界面進行交互式操作
python run.py --cli

# 模擬運行 8 小時，監控 BTC 和 ETH
python run.py --duration 8 --symbols BTC/USDT:USDT --dry-run

# 實際交易，設置最小利潤閾值
python run.py --duration 24 --min-profit 10 --max-exposure 5000
```

### 高級功能
```bash
# 使用環境變數加載 API 配置
python run.py --load-env --cli

# 啟用風險管理功能
python run.py --enable-risk-management --stop-loss 2.0 --max-drawdown 5.0

# JSON 格式輸出機會，便於程序化處理
python run.py --show-opportunities --format json --limit 5
```

## 📊 CLI 界面功能

### 主菜單 (9 大功能模塊)
1. **📈 查看當前套利機會** - 實時機會分析和詳情
2. **📊 顯示歷史統計** - 交易表現和盈虧數據
3. **💰 查看倉位狀態** - 活躍和歷史倉位管理
4. **🔧 配置管理** - 交易所和參數設置
5. **🚀 啟動套利系統** - 一鍵啟動自動交易
6. **🏪 交易所狀態** - API 連接和狀態檢查
7. **📋 資金費率分析** - 深度費率分析工具
8. **⚙️ 系統設置** - 日誌、通知、備份管理
9. **📖 幫助文檔** - 完整的使用指南

### 配置管理子功能
- **交易參數調整**: 敞口、倉位、閾值精細控制
- **交易所 API 設置**: 安全的密鑰管理
- **風險管理參數**: 止損、回撤、信心度設置
- **交易對管理**: 動態添加/移除監控符號

## 🧮 利潤計算功能

### 計算能力
- **跨交易所套利**: 考慮雙邊手續費和滑點成本
- **極端費率套利**: 現貨期貨對沖全成本分析
- **最佳倉位計算**: 基於風險和收益的智能優化
- **費用影響分析**: 不同交易所成本對比

### 風險指標
- **夏普比率**: 風險調整後收益衡量
- **最大回撤**: 最大可能虧損評估
- **利潤因子**: 盈虧比例分析
- **年化收益**: 長期投資回報預測

### 示例報告
```
📊 跨交易所套利 - 利潤分析報告
==================================================

🎯 基本信息:
   交易對: BTC/USDT:USDT
   倉位大小: 1,000.00 USDT
   持倉時間: 8.0 小時
   資金費率週期: 1 次

💰 費用分析:
   開倉手續費: 1.0000 USDT
   平倉手續費: 1.0000 USDT
   總手續費: 2.0000 USDT
   手續費率: 0.2000%

📈 收益分析:
   資金費率差異: 1.4000%
   資金費率收益: 14.0000 USDT
   毛利潤: 14.0000 USDT
   淨利潤: 11.8000 USDT
   利潤率: 1.1800%
   年化收益率: 129.54%

⚠️ 風險分析:
   最大可能虧損: 4.2000 USDT
   風險回報比: 2.81
   盈虧平衡週期: 1 次

📊 投資建議:
   ✅ 建議執行 - 利潤率良好
   ⚠️ 適中風險 - 風險回報比一般
```

## 🏗️ 系統架構升級

```
FundingArbitrageSystem 2.0
├── 📊 FundingRateMonitor     # 資金費率監控器 (Enhanced)
│   ├── ✨ 歷史數據分析
│   ├── ✨ 費率模式識別  
│   ├── ✨ 趨勢預測
│   └── ✨ 波動性計算
├── 🔍 ArbitrageDetector      # 套利機會檢測器 (Enhanced)
│   ├── ✨ 四種展示模式
│   ├── ✨ 機會信心評分
│   ├── ✨ 多交易所分歧分析
│   └── ✨ 極端費率識別
├── ⚡ ArbitrageExecutor      # 套利執行器 (Enhanced)
│   ├── 智能倉位管理
│   ├── 動態風險控制
│   └── 自動平倉策略
├── 💾 DatabaseManager        # 數據庫管理 (New!)
│   ├── ✨ 完整數據持久化
│   ├── ✨ 性能統計分析
│   ├── ✨ 歷史數據查詢
│   └── ✨ 數據清理維護
├── 🧮 ProfitCalculator       # 利潤計算器 (New!)
│   ├── ✨ 精確費用分析
│   ├── ✨ 風險指標計算
│   ├── ✨ 收益預測模型
│   └── ✨ 策略比較分析
├── 💻 CLIInterface           # CLI 界面 (New!)
│   ├── ✨ 交互式菜單
│   ├── ✨ 實時數據顯示
│   ├── ✨ 配置管理界面
│   └── ✨ 統計報告功能
└── ⚙️ ConfigManager          # 配置管理器 (Enhanced)
    ├── ✨ 環境變數支持
    ├── ✨ 動態配置更新
    ├── ✨ 配置驗證機制
    └── ✨ 設定持久化
```

## 📈 支持的交易所

| 交易所 | 支持狀態 | 資金費率 | 歷史數據 | 手續費率 | 特殊說明 |
|--------|----------|----------|----------|----------|----------|
| 🎒 Backpack | ✅ | ✅ | ✅ | 0.02%/0.04% | 新興交易所，UI/UX 優秀 |
| 🟡 Binance | ✅ | ✅ | ✅ | 0.02%/0.04% | 最大流動性，費率穩定 |
| 🟣 Bybit | ✅ | ✅ | ✅ | 0.01%/0.06% | 衍生品專業，費率競爭 |
| 🟦 OKX | ✅ | ✅ | 🔄 | 0.015%/0.04% | 全球化，產品豐富 |
| 🟢 Gate.io | ✅ | ✅ | 🔄 | 0.015%/0.04% | 費率變化頻繁 |
| 🟠 Bitget | ✅ | ✅ | 🔄 | 0.02%/0.06% | 跟單交易特色 |

## 📋 完整命令行參數

### 執行模式
```bash
--panel                    # 啟動交互式面板界面
--cli                      # 啟動命令行界面  
--show-opportunities       # 顯示當前套利機會
--stats                    # 顯示歷史統計數據
```

### API 配置
```bash
--load-env                 # 從 .env 文件加載 API 配置
```

### 套利參數
```bash
--duration HOURS           # 運行時間（小時），默認: 24
--symbols SYMBOLS          # 監控的交易對，用逗號分隔
--exchanges EXCHANGES      # 使用的交易所，用逗號分隔
--min-profit USDT          # 最小利潤閾值（USDT）
--max-exposure USDT        # 最大總敞口（USDT）
```

### 風險管理
```bash
--enable-risk-management   # 啟用風險管理功能
--stop-loss PERCENT        # 止損百分比
--max-drawdown PERCENT     # 最大回撤百分比
```

### 顯示選項
```bash
--limit NUMBER             # 顯示數量限制，默認: 10
--days NUMBER              # 統計天數，默認: 7
--format FORMAT            # 輸出格式 (table/json/csv)
```

### 調試選項
```bash
--debug                    # 啟用調試模式
--dry-run                  # 模擬運行（不執行實際交易）
--log-level LEVEL          # 日誌級別 (DEBUG/INFO/WARNING/ERROR)
```

## 🔧 配置文件詳解

### .env 環境變數
```bash
# 交易所 API 配置
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
BYBIT_API_KEY=your_bybit_api_key
BYBIT_SECRET_KEY=your_bybit_secret_key

# 風險管理設置
MAX_TOTAL_EXPOSURE=10000
MAX_SINGLE_POSITION=2000
MIN_PROFIT_THRESHOLD=0.2
DAILY_LOSS_LIMIT=500

# 通知設置
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 系統設置
LOG_LEVEL=INFO
TESTNET=true
WEB_PORT=8080
```

### config.json 結構
```json
{
  "exchanges": {
    "binance": {
      "api_key": "your_api_key",
      "secret_key": "your_secret_key",
      "testnet": true,
      "maker_fee": 0.0001,
      "taker_fee": 0.0004
    }
  },
  "trading": {
    "symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
    "max_total_exposure": 10000,
    "max_single_position": 2000,
    "min_spread_threshold": 0.002,
    "extreme_rate_threshold": 0.01,
    "min_profit_threshold": 0.003,
    "update_interval": 30
  },
  "risk": {
    "max_drawdown_pct": 5.0,
    "stop_loss_pct": 2.0,
    "min_confidence_score": 0.6,
    "daily_loss_limit": 500,
    "position_timeout_hours": 24
  },
  "system": {
    "log_level": "INFO",
    "log_file": "funding_arbitrage.log",
    "enable_telegram_alerts": false,
    "telegram_bot_token": "",
    "telegram_chat_id": ""
  }
}
```

## 📊 數據庫功能

### 數據表結構
- **funding_rates**: 歷史資金費率數據
- **arbitrage_opportunities**: 套利機會記錄
- **positions**: 倉位和交易記錄
- **system_stats**: 系統統計數據
- **exchange_status**: 交易所狀態監控

### 統計功能
```python
# 獲取性能統計
stats = db.get_performance_stats(days=30)
print(f"成功率: {stats['success_rate']:.2f}%")
print(f"總利潤: {stats['total_profit']:.4f} USDT")

# 獲取頂級表現符號
top_symbols = db.get_top_performing_symbols(5)
for symbol in top_symbols:
    print(f"{symbol['symbol']}: {symbol['total_profit']:.4f} USDT")
```

## 🎯 實際使用場景

### 場景 1: 新手學習
```bash
# 1. 啟動 CLI 學習系統功能
python run.py --cli

# 2. 查看當前市場機會
python run.py --show-opportunities --limit 5

# 3. 模擬運行測試理解
python run.py --dry-run --duration 1 --debug
```

### 場景 2: 專業交易
```bash
# 1. 配置環境變數
cp env_example.txt .env
# 編輯 .env 填入真實 API 密鑰

# 2. 啟動實際交易
python run.py --load-env --duration 24 --min-profit 15 --enable-risk-management

# 3. 監控交易表現
python run.py --stats --days 7 --format table
```

### 場景 3: 策略開發
```bash
# 1. 分析歷史數據
python run.py --cli  # 選擇 "7. 資金費率分析"

# 2. 測試不同參數
python run.py --dry-run --min-profit 5 --max-exposure 1000

# 3. 比較策略表現
python run.py --show-opportunities --format json > opportunities.json
```

## 🚨 重要提示

### ⚠️ 風險警告
- **市場風險**: 套利不保證盈利，存在虧損可能
- **技術風險**: 網絡延遲、API 限制影響交易執行
- **流動性風險**: 低流動性市場平倉困難
- **操作風險**: 配置錯誤導致意外損失

### 🛡️ 安全建議
1. **小額測試**: 先用小資金驗證系統穩定性
2. **模擬優先**: 大量使用 `--dry-run` 模式
3. **監控日誌**: 定期檢查系統運行狀況
4. **備份數據**: 定期備份配置和交易記錄
5. **逐步增加**: 從小倉位開始，逐步增加投入

### 🔄 版本升級
- 從 1.0 升級: 無需額外操作，配置文件自動遷移
- 新功能: 全部向後兼容，可以逐步體驗新功能
- 數據庫: 自動創建，歷史數據無縫保留

## 🆚 與其他專案對比

| 功能 | 本系統 2.0 | 其他套利系統 | Backpack 做市 |
|------|------------|--------------|---------------|
| 統一入口 | ✅ 參考優秀設計 | ❌ 分散入口 | ✅ 設計優秀 |
| CLI 界面 | ✅ 完整功能 | ❌ 缺少 | ✅ 功能豐富 |
| 利潤計算 | ✅ 專業分析 | ⚠️ 簡單估算 | ✅ 精確計算 |
| 配置管理 | ✅ 靈活完整 | ❌ 硬編碼 | ✅ 設計良好 |
| 風險管理 | ✅ 多層控制 | ⚠️ 基本功能 | ✅ 完善機制 |
| 數據持久化 | ✅ 完整實現 | ❌ 缺少 | ⚠️ 部分實現 |
| 環境變數 | ✅ 安全管理 | ❌ 缺少 | ✅ 支持良好 |

## 📞 技術支持

### 🐛 常見問題
1. **配置驗證失敗**: 檢查 API 密鑰格式和權限
2. **連接失敗**: 確認網絡和代理設置
3. **計算異常**: 檢查交易對格式和交易所支持
4. **數據庫錯誤**: 檢查文件權限和磁盤空間

### 📧 聯繫方式
- 📧 技術支持: [您的郵箱]
- 💬 Telegram: [您的 Telegram]
- 🐛 問題反饋: [GitHub Issues]
- 📖 文檔wiki: [項目 Wiki]

## 📄 許可證

MIT License - 查看 [LICENSE](LICENSE) 文件了解詳情。

---

**免責聲明**: 本系統僅供教育和研究用途。任何交易活動均存在風險，請根據自身情況謹慎使用。開發者不承擔任何因使用本系統而產生的損失責任。

**致謝**: 感謝 [Backpack 做市專案](https://github.com/yanowo/Backpack-MM-Simple.git) 的優秀設計理念，為本系統的改進提供了寶貴參考。 