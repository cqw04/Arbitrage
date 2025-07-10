# 項目結構說明

## 📁 整體架構

```
Arbitrage/
├── main.py                           # 🚀 主入口文件
├── simple_arbitrage_system.py        # 🔧 簡化版本
├── simple_config.json                # ⚙️ 簡化配置
├── arbitrage_config.json             # ⚙️ 完整配置
├── README_SIMPLE.md                  # 📖 簡化版說明
├── PROJECT_STRUCTURE.md              # 📖 本文件
│
├── src/                              # 📦 核心代碼目錄
│   ├── core/                         # 🎯 核心系統
│   │   ├── comprehensive_arbitrage_system.py    # 綜合套利系統
│   │   ├── start_comprehensive_arbitrage.py     # 啟動器
│   │   ├── hybrid_arbitrage_architecture.py     # 混合架構
│   │   ├── auto_trading_engine.py               # 自動交易引擎
│   │   ├── run.py                               # 運行模組
│   │   └── main_system_integration.py           # 系統整合
│   │
│   ├── strategies/                   # 📊 套利策略
│   │   └── funding_rate_arbitrage_system.py     # 資金費率套利
│   │
│   ├── risk_management/              # ⚠️ 風險管理
│   │   └── risk_manager.py                      # 風險管理器
│   │
│   ├── connectors/                   # 🔌 交易所連接
│   │   ├── websocket_manager.py                # WebSocket管理
│   │   └── api_auth_utils.py                   # API認證
│   │
│   ├── utils/                        # 🛠️ 工具模組
│   │   ├── database_manager.py                # 數據庫管理
│   │   └── profit_calculator.py               # 利潤計算
│   │
│   ├── config/                       # ⚙️ 配置管理
│   └── reports/                      # 📊 報告生成
│
├── logs/                             # 📝 日誌文件
├── data/                             # 💾 數據文件
└── docs/                             # 📚 文檔
```

## 🎯 使用方式

### 1. 快速開始（推薦新手）
```bash
python simple_arbitrage_system.py
```

### 2. 完整功能（推薦進階用戶）
```bash
python main.py
```

### 3. 直接運行特定模組
```bash
# 資金費率套利
python src/strategies/funding_rate_arbitrage_system.py

# 綜合套利系統
python src/core/comprehensive_arbitrage_system.py
```

## 📊 功能對比

| 功能 | 簡化版本 | 完整版本 |
|------|----------|----------|
| 現貨套利 | ✅ | ✅ |
| 資金費率套利 | ✅ | ✅ |
| 三角套利 | ❌ | ✅ |
| 期現套利 | ❌ | ✅ |
| 統計套利 | ❌ | ✅ |
| 風險管理 | ❌ | ✅ |
| 性能優化 | ❌ | ✅ |
| 數據庫 | ❌ | ✅ |
| WebSocket | ❌ | ✅ |
| 自動交易 | ❌ | ✅ |
| 報告生成 | ❌ | ✅ |

## 🔧 模組說明

### Core 模組
- **comprehensive_arbitrage_system.py**: 綜合套利系統主體
- **auto_trading_engine.py**: 自動交易引擎
- **hybrid_arbitrage_architecture.py**: Python + Rust 混合架構

### Strategies 模組
- **funding_rate_arbitrage_system.py**: 資金費率套利策略

### Risk Management 模組
- **risk_manager.py**: 綜合風險管理

### Connectors 模組
- **websocket_manager.py**: WebSocket 連接管理
- **api_auth_utils.py**: API 認證工具

### Utils 模組
- **database_manager.py**: 數據庫操作
- **profit_calculator.py**: 利潤計算

## 🚀 推薦使用流程

### 新手用戶
1. 運行 `python simple_arbitrage_system.py`
2. 觀察系統運行
3. 熟悉基本概念
4. 逐步學習完整功能

### 進階用戶
1. 運行 `python main.py`
2. 選擇運行模式
3. 配置參數
4. 監控運行狀態

### 開發者
1. 直接運行特定模組
2. 修改源代碼
3. 添加新功能
4. 測試和優化

## 📈 性能特點

### 簡化版本
- **啟動速度**: 快（< 1秒）
- **內存使用**: 低（< 50MB）
- **CPU使用**: 低（< 5%）
- **功能**: 基礎但完整

### 完整版本
- **啟動速度**: 中等（2-5秒）
- **內存使用**: 中等（100-200MB）
- **CPU使用**: 中等（10-20%）
- **功能**: 全面且強大

## 🔮 擴展建議

### 短期擴展
1. 添加更多交易所
2. 優化檢測算法
3. 改進用戶界面

### 長期擴展
1. 機器學習策略
2. 分佈式部署
3. 雲端服務
4. 移動應用

## ⚠️ 注意事項

1. **備份重要數據**: 定期備份配置和數據
2. **監控系統**: 注意系統資源使用
3. **更新維護**: 定期更新依賴和代碼
4. **安全考慮**: 保護API密鑰和敏感信息

---

**總結**: 這個項目提供了從簡單到複雜的完整套利解決方案，用戶可以根據自己的需求選擇合適的版本。 