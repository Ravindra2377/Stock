import sys
import os
import pandas as pd
from typing import Dict

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.indicator_service import IndicatorService

def test_panvi_fusion():
    print("🚀 Starting Panvi Convergence Test...")
    
    # 1. Mock Data: Strong Bullish setup
    # AI Score: 90
    # Indicator Score: 80
    # Structure Score: 85
    
    ai_prob = 0.9
    ind_score = 80.0
    struct_score = 85.0
    
    # Expected: (0.4 * 90) + (0.3 * 80) + (0.3 * 85)
    # = 36 + 24 + 25.5 = 85.5
    
    fusion_score = IndicatorService.calculate_panvi_fusion(ai_prob, ind_score, struct_score)
    print(f"Computed Fusion Score: {fusion_score}")
    
    expected = (0.4 * 90) + (0.3 * 80) + (0.3 * 85)
    assert abs(fusion_score - expected) < 0.1, f"Fusion error! Expected {expected}, got {fusion_score}"
    print("✅ Fusion Formula Validated.")

    # 2. Test Execution Price Logic (50/30/20)
    # Support: 100, EMA20: 105, Close: 110
    # Formula: 0.5 * 100 + 0.3 * 105 + 0.2 * 110
    # = 50 + 31.5 + 22 = 103.5
    
    # Mock DF (Need at least 5 rows for indicator service)
    df = pd.DataFrame({
        'Close': [105, 106, 107, 108, 109, 110, 110, 110, 110, 110],
        'High': [107, 108, 109, 110, 111, 112, 112, 112, 112, 112],
        'Low': [103, 104, 105, 106, 107, 108, 108, 108, 108, 108],
        'EMA_20': [105]*10,
        'ATR': [2.0]*10,
        'RSI': [55]*10
    })
    support = 100.0
    ema20 = 105.0

    
    correct_buy = IndicatorService.calculate_correct_buy_price(df, support, ema20)
    print(f"Computed Correct Buy Price: {correct_buy}")
    expected_buy = 103.5
    assert abs(correct_buy - expected_buy) < 0.1, f"Price error! Expected {expected_buy}, got {correct_buy}"
    print("✅ Value Zone Entry (50/30/20) Validated.")

    # 3. Test Prob-Adjusted High
    # P_bull: 0.8, T1: 120, T2: 130
    # Formula: (0.8 * 130) + (0.2 * 120) = 104 + 24 = 128
    
    p_bull = 0.8
    t1, t2 = 120.0, 130.0
    expected_high = IndicatorService.calculate_prob_adjusted_high(p_bull, t1, t2)
    print(f"Computed Expected High: {expected_high}")
    target_high = 128.0
    assert abs(expected_high - target_high) < 0.1, f"Target error! Expected {target_high}, got {expected_high}"
    print("✅ Probability-Adjusted High Validated.")

    # 4. Test HOLD Case Projections
    # Score 60 (HOLD because < 65)
    print("\n🧐 Testing HOLD Case (Score 60)...")
    recommendation = "HOLD"
    # Mock data for HOLD
    # sr_zones = {'support': [{'price': 100}]}
    # last = {'EMA_20': 105, 'Close': 110}
    # last_lows = [108, 107, 109, 108, 107]
    
    # We call generate_trade_structure directly for verification
    # Mock parameters
    sr_zones = {'support': [{'price': 100}], 'resistance': [{'price': 115}]}
    breakout = {'status': 'NONE'}
    overextended = False
    
    trade_hold = IndicatorService.generate_trade_structure(df, sr_zones, "HOLD", breakout, overextended)
    print(f"HOLD direction: {trade_hold['direction']}")
    print(f"HOLD Correct Buy: {trade_hold.get('correct_buy_price')}")
    print(f"HOLD Expected High: {trade_hold.get('expected_high')}")
    print(f"HOLD Expected Low: {trade_hold.get('expected_low')}")
    
    assert trade_hold['direction'] == "WAIT"
    assert trade_hold['correct_buy_price'] is not None
    assert trade_hold['expected_high'] is not None
    assert trade_hold['expected_low'] is not None
    print("✅ HOLD Projections Validated.")

    print("\n💯 All Core Brain Logic Validated!")


if __name__ == "__main__":
    try:
        test_panvi_fusion()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)
