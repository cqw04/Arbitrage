#!/usr/bin/env python3
"""
歷史分析增強模組
參考 supervik/funding-rate-arbitrage-scanner 的優秀分析演算法
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from database_manager import get_db
from config_funding import get_config

logger = logging.getLogger("HistoricalAnalysis")

class HistoricalAnalysisEnhancer:
    """
    歷史分析增強器
    參考 supervik 專案的分析方法
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = get_db()
    
    def calculate_historical_apy(self, 
                               funding_rates: List[float], 
                               periods_per_day: int = 3) -> float:
        """
        計算歷史平均 APY
        參考 supervik 專案的計算方法
        
        Args:
            funding_rates: 歷史資金費率列表
            periods_per_day: 每日資金費率週期數 (通常為3次)
        
        Returns:
            年化收益率 (APY)
        """
        if not funding_rates:
            return 0.0
        
        try:
            # 計算平均資金費率
            avg_rate = np.mean(funding_rates)
            
            # 轉換為年化收益率
            periods_per_year = periods_per_day * 365
            apy = avg_rate * periods_per_year * 100
            
            return round(apy, 4)
            
        except Exception as e:
            logger.error(f"計算歷史 APY 失敗: {e}")
            return 0.0
    
    def calculate_daily_amplitude(self, 
                                price_data: List[Dict],
                                days: int = 30) -> Tuple[float, float]:
        """
        計算日均振幅和最大振幅
        參考 supervik 專案的波動性分析
        
        Args:
            price_data: 價格數據列表 [{'high': float, 'low': float, 'date': str}]
            days: 計算天數
        
        Returns:
            (平均日振幅, 最大日振幅)
        """
        if not price_data:
            return 0.0, 0.0
        
        try:
            amplitudes = []
            
            for data in price_data[-days:]:
                high = data.get('high', 0)
                low = data.get('low', 0)
                
                if high > 0 and low > 0:
                    # 計算振幅百分比
                    amplitude = ((high - low) / low) * 100
                    amplitudes.append(amplitude)
            
            if amplitudes:
                mean_amplitude = np.mean(amplitudes)
                max_amplitude = np.max(amplitudes)
                return round(mean_amplitude, 4), round(max_amplitude, 4)
            
            return 0.0, 0.0
            
        except Exception as e:
            logger.error(f"計算日振幅失敗: {e}")
            return 0.0, 0.0
    
    def calculate_cumulative_rate(self, 
                                funding_rates: List[float],
                                start_date: datetime = None) -> float:
        """
        計算累積資金費率
        參考 supervik 專案的累積計算方法
        
        Args:
            funding_rates: 資金費率列表
            start_date: 開始日期
        
        Returns:
            累積資金費率
        """
        if not funding_rates:
            return 0.0
        
        try:
            # 計算累積資金費率 (複利效應)
            cumulative = 1.0
            for rate in funding_rates:
                cumulative *= (1 + rate / 100)
            
            # 轉換為百分比
            cumulative_rate = (cumulative - 1) * 100
            return round(cumulative_rate, 6)
            
        except Exception as e:
            logger.error(f"計算累積費率失敗: {e}")
            return 0.0
    
    def analyze_perpetual_perpetual_opportunity(self,
                                              symbol: str,
                                              short_exchange: str,
                                              long_exchange: str,
                                              current_rates: Dict[str, float],
                                              days: int = 30) -> Dict:
        """
        分析 Perpetual-Perpetual 套利機會
        參考 supervik 專案的分析方法
        
        Returns:
            詳細的分析結果字典
        """
        try:
            # 獲取歷史資金費率
            short_historical = self._get_historical_rates(symbol, short_exchange, days)
            long_historical = self._get_historical_rates(symbol, long_exchange, days)
            
            # 獲取價格數據用於振幅計算
            price_data = self._get_price_data(symbol, short_exchange, days)
            
            # 計算分析指標
            rate_diff = current_rates.get(short_exchange, 0) - current_rates.get(long_exchange, 0)
            
            # 計算歷史平均 APY
            rate_diff_history = [s - l for s, l in zip(short_historical, long_historical) 
                               if s is not None and l is not None]
            historical_apy = self.calculate_historical_apy(rate_diff_history)
            
            # 計算振幅
            mean_amplitude, max_amplitude = self.calculate_daily_amplitude(price_data, days)
            
            # 計算累積費率
            short_cumulative = self.calculate_cumulative_rate(short_historical)
            long_cumulative = self.calculate_cumulative_rate(long_historical)
            
            return {
                'pair': symbol,
                'rate_diff': round(rate_diff, 6),
                'APY_historical_average': historical_apy,
                'short_exchange': short_exchange,
                'long_exchange': long_exchange,
                'mean_daily_amplitude': mean_amplitude,
                'max_daily_amplitude': max_amplitude,
                'short_rate': current_rates.get(short_exchange, 0),
                'long_rate': current_rates.get(long_exchange, 0),
                'short_cumulative_rate': short_cumulative,
                'long_cumulative_rate': long_cumulative,
                'short_historical_rates': short_historical,
                'long_historical_rates': long_historical,
                'analysis_quality': self._assess_analysis_quality(
                    len(short_historical), len(long_historical), mean_amplitude
                )
            }
            
        except Exception as e:
            logger.error(f"分析 Perpetual-Perpetual 機會失敗: {e}")
            return {}
    
    def analyze_perpetual_spot_opportunity(self,
                                         symbol: str,
                                         perp_exchange: str,
                                         spot_exchanges: List[str],
                                         current_rate: float,
                                         days: int = 30) -> Dict:
        """
        分析 Perpetual-Spot 套利機會
        參考 supervik 專案的分析方法
        """
        try:
            # 獲取歷史資金費率
            historical_rates = self._get_historical_rates(symbol, perp_exchange, days)
            
            # 獲取價格數據
            price_data = self._get_price_data(symbol, perp_exchange, days)
            
            # 計算分析指標
            historical_apy = self.calculate_historical_apy(historical_rates)
            mean_amplitude, max_amplitude = self.calculate_daily_amplitude(price_data, days)
            
            return {
                'pair': symbol,
                'rate': current_rate,
                'APY_historical_average': historical_apy,
                'perp_exchange': perp_exchange,
                'spot_exchanges': spot_exchanges,
                'mean_daily_amplitude': mean_amplitude,
                'max_daily_amplitude': max_amplitude,
                'historical_rates': historical_rates,
                'rate_trend': self._calculate_rate_trend(historical_rates),
                'volatility_risk': self._assess_volatility_risk(mean_amplitude),
                'recommendation': self._generate_recommendation(
                    current_rate, historical_apy, mean_amplitude
                )
            }
            
        except Exception as e:
            logger.error(f"分析 Perpetual-Spot 機會失敗: {e}")
            return {}
    
    def _get_historical_rates(self, symbol: str, exchange: str, days: int) -> List[float]:
        """從資料庫獲取歷史資金費率"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 從數據庫獲取實際歷史數據
            if hasattr(self, 'db') and self.db:
                historical_data = self.db.get_funding_rates(
                    symbol=symbol,
                    exchange=exchange,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if historical_data:
                    # 提取費率值
                    rates = [float(record['funding_rate']) for record in historical_data]
                    logger.info(f"從數據庫獲取到 {len(rates)} 條 {exchange} {symbol} 的歷史費率數據")
                    return rates
            
            # 如果數據庫中沒有數據，嘗試從交易所獲取
            logger.warning(f"數據庫中沒有 {exchange} {symbol} 的歷史數據，無法進行歷史分析")
            return []
            
        except Exception as e:
            logger.error(f"獲取歷史費率失敗: {e}")
            return []
    
    def _get_price_data(self, symbol: str, exchange: str, days: int) -> List[Dict]:
        """獲取價格數據用於振幅計算"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 從數據庫獲取歷史價格數據
            if hasattr(self, 'db') and self.db:
                price_data = self.db.get_price_history(
                    symbol=symbol,
                    exchange=exchange,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if price_data:
                    logger.info(f"從數據庫獲取到 {len(price_data)} 條 {exchange} {symbol} 的歷史價格數據")
                    return price_data
            
            # 如果數據庫中沒有價格數據，嘗試從交易所API獲取
            logger.warning(f"數據庫中沒有 {exchange} {symbol} 的歷史價格數據")
            logger.info("提示：要獲得準確的振幅分析，需要收集歷史價格數據")
            
            return []
            
        except Exception as e:
            logger.error(f"獲取價格數據失敗: {e}")
            return []
    
    def _assess_analysis_quality(self, 
                               short_data_points: int,
                               long_data_points: int, 
                               amplitude: float) -> str:
        """評估分析品質"""
        min_points = 50  # 最少數據點
        
        if short_data_points < min_points or long_data_points < min_points:
            return "數據不足"
        elif amplitude > 10:
            return "高波動風險"
        elif amplitude > 5:
            return "中等風險"
        else:
            return "優質機會"
    
    def _calculate_rate_trend(self, rates: List[float]) -> str:
        """計算費率趨勢"""
        if len(rates) < 10:
            return "數據不足"
        
        recent = rates[-10:]
        earlier = rates[-20:-10] if len(rates) >= 20 else rates[:-10]
        
        recent_avg = np.mean(recent)
        earlier_avg = np.mean(earlier)
        
        if recent_avg > earlier_avg * 1.1:
            return "上升趨勢"
        elif recent_avg < earlier_avg * 0.9:
            return "下降趨勢"
        else:
            return "穩定趨勢"
    
    def _assess_volatility_risk(self, amplitude: float) -> str:
        """評估波動性風險"""
        if amplitude > 10:
            return "極高風險"
        elif amplitude > 5:
            return "高風險"
        elif amplitude > 3:
            return "中等風險"
        else:
            return "低風險"
    
    def _generate_recommendation(self, 
                               current_rate: float,
                               historical_apy: float, 
                               amplitude: float) -> str:
        """生成投資建議"""
        if abs(current_rate) < 0.001:
            return "費率過低，不建議執行"
        elif amplitude > 8:
            return "波動過大，謹慎操作"
        elif historical_apy > 10:
            return "歷史表現良好，建議執行"
        elif historical_apy > 5:
            return "適中機會，可考慮執行"
        else:
            return "收益偏低，建議觀望"

def get_historical_analyzer() -> HistoricalAnalysisEnhancer:
    """獲取歷史分析增強器實例"""
    return HistoricalAnalysisEnhancer()

# 測試功能
if __name__ == "__main__":
    analyzer = get_historical_analyzer()
    
    # 測試 Perpetual-Perpetual 分析
    current_rates = {
        'binance': 0.015,
        'bybit': 0.008
    }
    
    pp_result = analyzer.analyze_perpetual_perpetual_opportunity(
        'BTC/USDT:USDT',
        'binance',
        'bybit', 
        current_rates
    )
    
    print("🔍 Perpetual-Perpetual 分析結果:")
    print(f"交易對: {pp_result.get('pair')}")
    print(f"費率差異: {pp_result.get('rate_diff'):.4f}%")
    print(f"歷史平均 APY: {pp_result.get('APY_historical_average'):.2f}%")
    print(f"平均日振幅: {pp_result.get('mean_daily_amplitude'):.2f}%")
    print(f"分析品質: {pp_result.get('analysis_quality')}") 