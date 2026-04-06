import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, ScrollView, TouchableOpacity,
  TextInput, ActivityIndicator, Dimensions, FlatList, Animated, Easing, SectionList
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle, G, Defs, LinearGradient, Stop } from 'react-native-svg';
import * as Haptics from 'expo-haptics';
import axios from 'axios';


const { width } = Dimensions.get('window');
const API_URL = 'http://192.168.1.18:8000';

// ─── Color Palette ────────────────────────────────────────────────
const C = {
  bg: '#0B0C0F',
  surface: '#13151A',
  border: '#1F2128',
  muted: '#4A5060',
  text: '#E8EAF0',
  subtext: '#8890A0',
  buy: '#3DDC84',
  buyFaded: 'rgba(61,220,132,0.12)',
  sell: '#FF6B6B',
  sellFaded: 'rgba(255,107,107,0.12)',
  accent: '#4F8EF7',
  warn: '#F0A500',
};

const tag = (rec) => {
  const r = rec?.toUpperCase() || '';
  if (r === 'EXPECT UP') return { color: C.buy, bg: C.buyFaded };
  if (r === 'EXPECT DOWN') return { color: C.sell, bg: C.sellFaded };
  if (r === 'WAIT') return { color: C.warn, bg: 'rgba(240,165,0,0.12)' };
  if (r.includes('BLOCKED')) return { color: C.sell, bg: C.sellFaded };
  return { color: C.muted, bg: 'rgba(74,80,96,0.12)' }; 
};



// ─── RSI Indicator ────────────────────────────────────────────────
const RSIIndicator = ({ rsi }) => {
  const clr = rsi < 35 ? C.buy : rsi > 65 ? C.sell : C.warn;
  return (
    <View style={row.rsi}>
      <Text style={[txt.label, { color: C.muted }]}>RSI</Text>
      <View style={row.track}>
        <View style={[row.fill, { width: `${Math.min(rsi, 100)}%`, backgroundColor: clr }]} />
      </View>
      <Text style={[txt.mono, { color: clr }]}>{rsi}</Text>
    </View>
  );
};

// ─── Stock Row Card ───────────────────────�const StockRow = ({ item, onPress }) => {
  const t = tag(item.recommendation);
  const score = item.composite_score || 50;
  const scoreColor = score >= 65 ? C.buy : score >= 35 ? C.warn : C.sell;
  const changePct = item.price_change_pct || 0;
  const regime = (item.regime && typeof item.regime === 'object') ? item.regime.regime : (item.regime || 'SIDEWAYS');
  const currency = item.currency_symbol || '$';
  
  // Strip suffix for list display
  const displayTicker = item.ticker?.split('.')[0] || item.ticker;

  return (
    <TouchableOpacity onPress={() => onPress(item)} style={card.row} activeOpacity={0.7}>
      <View style={[card.accentBar, { backgroundColor: t.color }]} />
      <View style={card.rowContent}>
        <View style={card.rowLeft}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Text style={txt.ticker}>{displayTicker}</Text>
            <View style={{ backgroundColor: (regimeColors[regime] || C.muted) + '22', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 1 }}>
              <Text style={{ color: regimeColors[regime] || C.muted, fontSize: 8, fontWeight: '700' }}>{regime}</Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 3 }}>
            <Text style={txt.price}>{currency}{item.price?.toLocaleString()}</Text>
            <Text style={{ color: changePct >= 0 ? C.buy : C.sell, fontSize: 11, fontWeight: '600' }}>
              {changePct >= 0 ? '▲' : '▼'} {Math.abs(changePct).toFixed(2)}%
            </Text>
          </View>
          {item.smart_money && (
            <Text style={{ color: '#FFD700', fontSize: 9, fontWeight: '700', marginTop: 2 }}>🧠 {item.smart_money}</Text>
          )}
        </View>
        <View style={card.rowRight}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Text style={[txt.mono, { color: scoreColor, fontSize: 14, fontWeight: '800' }]}>{score}</Text>
            <View style={[card.badge, { backgroundColor: t.bg }]}>
              <Text style={[txt.badge, { color: t.color }]}>{item.recommendation}</Text>
            </View>
          </View>
          <RSIIndicator rsi={item.rsi} />
        </View>
      </View>
    </TouchableOpacity>
  );
};
/Text>
            <View style={[card.badge, { backgroundColor: t.bg }]}>
              <Text style={[txt.badge, { color: t.color }]}>{item.recommendation}</Text>
            </View>
          </View>
          <RSIIndicator rsi={item.rsi} />
        </View>
      </View>
    </TouchableOpacity>
  );
};

// ─── Premium Components ───────────────────────────────────────────

const CounterText = ({ value, style, duration = 1500, prefix = '', suffix = '' }) => {
  const animatedValue = React.useRef(new Animated.Value(0)).current;
  const [displayValue, setDisplayValue] = React.useState(0);

  useEffect(() => {
    animatedValue.setValue(0);
    Animated.timing(animatedValue, {
      toValue: value,
      duration: duration,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();

    const listener = animatedValue.addListener(({ value: v }) => {
      setDisplayValue(Math.round(v));
    });
    return () => animatedValue.removeListener(listener);
  }, [value]);

  return <Text style={style}>{prefix}{displayValue}{suffix}</Text>;
};

const AnimatedFusionRing = ({ score, size = 120, color, conviction = 'LOW', delay = 500 }) => {
  const radius = (size / 2) - 10;
  const circumference = 2 * Math.PI * radius;
  const animatedValue = React.useRef(new Animated.Value(circumference)).current;
  const pulseAnim = React.useRef(new Animated.Value(1)).current;

  useEffect(() => {
    animatedValue.setValue(circumference);
    Animated.sequence([
      Animated.delay(delay),
      Animated.timing(animatedValue, {
        toValue: circumference - (score / 100) * circumference,
        duration: 1200,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: false,
      })
    ]).start();

    if (conviction === 'EXTREME' || conviction === 'HIGH') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.05, duration: 1000, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
        ])
      ).start();
    }
  }, [score, conviction]);

  return (
    <Animated.View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center', transform: [{ scale: pulseAnim }] }}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: [{ rotate: '-90deg' }] }}>
        <Defs>
          <LinearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <Stop offset="0%" stopColor={color} stopOpacity="0.8" />
            <Stop offset="100%" stopColor={color} />
          </LinearGradient>
        </Defs>
        <Circle cx={size/2} cy={size/2} r={radius} stroke="#1F2128" strokeWidth="6" fill="transparent" />
        <AnimatedCircle
          cx={size/2} cy={size/2} r={radius}
          stroke="url(#grad)" strokeWidth="8" fill="transparent"
          strokeDasharray={circumference} strokeDashoffset={animatedValue}
          strokeLinecap="round"
        />
      </Svg>
    </Animated.View>
  );
};

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

const LayerMetricBar = ({ label, value, weight, color, delay = 0 }) => {
  const animatedWidth = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    animatedWidth.setValue(0);
    Animated.sequence([
      Animated.delay(delay),
      Animated.timing(animatedWidth, {
        toValue: value,
        duration: 1000,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: false,
      })
    ]).start();
  }, [value]);

  return (
    <View style={{ marginBottom: 10 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
        <Text style={{ color: C.subtext, fontSize: 9, fontWeight: '700' }}>{label} ({weight})</Text>
        <Text style={{ color: C.text, fontSize: 9, fontWeight: '900', fontFamily: 'monospace' }}>{value.toFixed(1)}/100</Text>
      </View>
      <View style={{ height: 3, backgroundColor: '#1A202C', borderRadius: 2, overflow: 'hidden' }}>
        <Animated.View style={{ height: '100%', backgroundColor: color, width: animatedWidth.interpolate({
          inputRange: [0, 100],
          outputRange: ['0%', '100%']
        }) }} />
      </View>
    </View>
  );
};

const VerdictBanner = ({ verdict, conviction, score }) => {
  const color = score >= 65 ? C.buy : score >= 35 ? C.warn : C.sell;
  return (
    <View style={{ backgroundColor: color + '15', borderRadius: 12, padding: 16, marginBottom: 16, borderLeftWidth: 4, borderLeftColor: color }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <Text style={{ color: color, fontSize: 10, fontWeight: '900', letterSpacing: 1 }}>OFFICIAL VERDICT</Text>
        <Text style={{ color: C.subtext, fontSize: 10, fontWeight: '700' }}>CONVICTION: {conviction}</Text>
      </View>
      <Text style={{ color: C.text, fontSize: 16, fontWeight: '800' }}>{verdict}</Text>
    </View>
  );
};

const ConflictBanner = ({ conflict }) => {
  if (!conflict) return null;
  return (
    <View style={{ backgroundColor: '#FF6B6B20', borderRadius: 8, padding: 10, marginBottom: 16, flexDirection: 'row', alignItems: 'center', gap: 10, borderWidth: 1, borderColor: '#FF6B6B40' }}>
      <Text style={{ fontSize: 16 }}>⚠️</Text>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.sell, fontSize: 10, fontWeight: '900' }}>DIVERGENCE ALERT</Text>
        <Text style={{ color: C.text, fontSize: 11, fontWeight: '600' }}>{conflict}</Text>
      </View>
    </View>
  );
};

const EvidenceAccordion = ({ title, evidence, color, delay = 0 }) => {
  const [expanded, setExpanded] = useState(false);
  const anim = React.useRef(new Animated.Value(0)).current;

  const toggle = () => {
    setExpanded(!expanded);
    Animated.timing(anim, {
      toValue: expanded ? 0 : 1,
      duration: 300,
      useNativeDriver: false,
    }).start();
  };

  return (
    <View style={{ marginBottom: 12, backgroundColor: '#13151A', borderRadius: 10, overflow: 'hidden', borderWidth: 1, borderColor: expanded ? color + '40' : '#1F2128' }}>
      <TouchableOpacity onPress={toggle} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View style={{ width: 4, height: 16, backgroundColor: color, borderRadius: 2 }} />
          <Text style={{ color: C.text, fontSize: 12, fontWeight: '800' }}>{title}</Text>
        </View>
        <Text style={{ color: C.muted, fontSize: 10 }}>{expanded ? 'HIDE EVIDENCE ▲' : 'SHOW EVIDENCE ▼'}</Text>
      </TouchableOpacity>
      {expanded && (
        <View style={{ padding: 12, paddingTop: 0, borderTopWidth: 1, borderTopColor: '#1F2128' }}>
          {Array.isArray(evidence) ? evidence.map((item, idx) => (
            <Text key={idx} style={{ color: C.subtext, fontSize: 11, marginBottom: 4, lineHeight: 16 }}>• {item}</Text>
          )) : (
            <Text style={{ color: C.subtext, fontSize: 11, lineHeight: 16 }}>{evidence || 'Gathering evidence...'}</Text>
          )}
        </View>
      )}
    </View>
  );
};


// ─── Detail Bottom Sheet ───────────────────────────────────────────
const DetailSheet = ({ stock, onClose }) => {
  if (!stock) return null;

  // Staggered Entry Animation
  const slideAnim = React.useRef(new Animated.Value(300)).current;
  const fadeAnim = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(slideAnim, { toValue: 0, duration: 400, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
      Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true })
    ]).start();

    // Haptic Trigger for Signal
    if (stock.backtest_edge) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    }
  }, [stock.ticker]);

  const t = tag(stock.recommendation);
  const trade = stock.trade || {};
  const quality = stock.signal_quality || {};
  const probs = stock.probabilities || {};
  const mCtx = stock.market_context || {};
  const regime = stock.regime || {};
  const phase = stock.trend_phase || '';
  const breakout = stock.breakout || {};
  const playbook = stock.playbook || {};
  const posSize = stock.position_size || {};
  const bd = stock.breakdown || {};
  const labels = { rsi: 'RSI', macd: 'MACD', sma_cross: 'SMA 20/50', ema_cross: 'EMA 12/26', bollinger: 'Bollinger', volume: 'Volume', stochastic: 'Stochastic', breakout: 'Breakout', trend_200: 'SMA 200' };

  const score = stock.final_score || stock.composite_score || 0;
  const scoreColor = score >= 65 ? C.buy : score >= 35 ? C.warn : C.sell;

  const pf = stock.backtest_edge ? stock.backtest_edge.profit_factor : 1;
  const realEv = stock.backtest_edge ? stock.backtest_edge.historical_ev : null;
  const isEvPositive = realEv !== null && realEv > -0.1;
  const rr = trade.risk_reward || 0;
  
  let execLabel = "SYNCING";
  let execIcon = "🔍";
  let execColor = C.muted;
  
  if (stock.backtest_edge) {
      if (pf < 0.7 || !isEvPositive || stock.recommendation === 'WAIT') {
          execLabel = "BLOCKED";
          execIcon = "🔴";
          execColor = C.sell;
      } else if (pf < 1.1 || rr < 1.3) {
          execLabel = "WATCH";
          execIcon = "🟡";
          execColor = C.warn;
      } else {
          execLabel = "TRADE";
          execIcon = "🟢";
          execColor = C.buy;
      }
  }

  const biasLabel = stock.bias?.toUpperCase().includes('UP') || stock.bias?.toUpperCase().includes('BULL') ? 'EXPANDING (UP)' : 
                    stock.bias?.toUpperCase().includes('DOWN') || stock.bias?.toUpperCase().includes('BEAR') ? 'CONTRACTING (DOWN)' : 'STABILITY';

  
  const boColor = breakout.status === 'CONFIRMED' ? C.buy : breakout.status === 'ATTEMPT' ? C.warn : breakout.status === 'WEAK' ? C.sell : C.muted;
  const boIcon = breakout.status === 'CONFIRMED' ? '🚀' : breakout.status === 'ATTEMPT' ? '⚡' : breakout.status === 'WEAK' ? '⚠️' : '🔍';

  return (
    <TouchableOpacity style={sheet.overlay} onPress={onClose} activeOpacity={1}>
      <Animated.View style={{ flex: 1, opacity: fadeAnim, transform: [{ translateY: slideAnim }] }}>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ flexGrow: 1, justifyContent: 'flex-end' }}>
          <TouchableOpacity style={sheet.panel} activeOpacity={1} onPress={() => {}}>
            <View style={sheet.drag} />

            <View style={{ marginBottom: 20 }}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <View>
                  <Text style={{ color: C.text, fontSize: 32, fontWeight: '900', letterSpacing: -1 }}>{stock.ticker?.split('.')[0]}</Text>
                  <CounterText value={stock.price} prefix={stock.currency_symbol || "₹"} style={{ color: C.subtext, fontSize: 18, fontWeight: '600', marginTop: -4 }} />
                </View>
                <View style={{ backgroundColor: execColor + '15', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: execColor + '30' }}>
                  <Text style={{ color: execColor, fontSize: 12, fontWeight: '900', letterSpacing: 0.5 }}>{execIcon} {execLabel}</Text>
                </View>
              </View>

              <VerdictBanner verdict={stock.verdict} conviction={stock.conviction} score={score} />
              <ConflictBanner conflict={stock.conflict} />
            </View>

            {/* Fusion Score Ring & Layer Bars */}
            <View style={{ backgroundColor: '#13151A', borderRadius: 16, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: '#1F2128', flexDirection: 'row', alignItems: 'center', gap: 20 }}>
              <AnimatedFusionRing score={score} color={scoreColor} conviction={stock.conviction} />

              <View style={{ flex: 1 }}>
                <LayerMetricBar label="STRUCTURE" value={stock.struct_score || 50} weight="L1/30%" color="#378ADD" delay={0} />
                <LayerMetricBar label="INDICATORS" value={stock.ind_score || 50} weight="L2/30%" color="#1D9E75" delay={150} />
                <LayerMetricBar label="AI BRAIN" value={stock.ai_score || 50} weight="L3/40%" color="#BA7517" delay={300} />
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 }}>
                  <Text style={{ color: C.muted, fontSize: 9, fontWeight: '700' }}>DATA FRESHNESS:</Text>
                  <Text style={{ color: C.subtext, fontSize: 9, fontWeight: '700' }}>{stock.server_time || 'LIVE'}</Text>
                </View>
              </View>
            </View>

            {/* Evidence Trails */}
            <View style={{ marginBottom: 16 }}>
              <Text style={{ color: C.muted, fontSize: 9, fontWeight: '900', marginBottom: 8, letterSpacing: 1 }}>EVIDENCE TRAILS (TRUTH MACHINE™: {stock.ticker?.split('.')[0]})</Text>
              <EvidenceAccordion title="L1: Market Structure Evidence" evidence={stock.l1_evidence} color="#378ADD" />
              <EvidenceAccordion title="L2: Technical Indicators Evidence" evidence={stock.l2_evidence} color="#1D9E75" />
            </View>

            {/* AI Brain Enhanced Insight */}
            <View style={{ backgroundColor: '#BA751710', borderLeftWidth: 3, borderLeftColor: '#BA7517', borderRadius: 4, padding: 12, marginBottom: 16 }}>
              <Text style={{ color: '#BA7517', fontSize: 10, fontWeight: '900', marginBottom: 8, letterSpacing: 1 }}>L3: AI BRAIN INTELLIGENCE</Text>
              <Text style={{ color: C.text, fontSize: 13, lineHeight: 18, marginBottom: 12 }}>{stock.ai_insight || "Analyzing market sentiment..."}</Text>
              
              {stock.ai_sources && stock.ai_sources.length > 0 && (
                <View style={{ marginBottom: 10 }}>
                  <Text style={{ color: '#BA7517', fontSize: 9, fontWeight: '800', marginBottom: 4 }}>VERIFIED SOURCES:</Text>
                  {stock.ai_sources.map((s, i) => (
                    <Text key={i} style={{ color: C.subtext, fontSize: 10, marginBottom: 2 }}>• {s}</Text>
                  ))}
                </View>
              )}

              {stock.ai_invalidation && (
                <View style={{ backgroundColor: '#FF6B6B15', padding: 8, borderRadius: 4, marginTop: 4 }}>
                  <Text style={{ color: C.sell, fontSize: 9, fontWeight: '900', marginBottom: 2 }}>INVALIDATION CRITERIA:</Text>
                  <Text style={{ color: C.text, fontSize: 10 }}>{stock.ai_invalidation}</Text>
                </View>
              )}
            </View>

            {/* Deep Value Projections */}
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16, backgroundColor: '#13151A', padding: 12, borderRadius: 12, borderWidth: 1, borderColor: '#1F2128' }}>
              <View style={{ alignItems: 'center', flex: 1 }}>
                <Text style={{ color: C.muted, fontSize: 8, fontWeight: '900', marginBottom: 4 }}>VALUE ZONE</Text>
                <Text style={{ color: C.buy, fontSize: 16, fontWeight: '900' }}>₹{trade.correct_buy_price || '—'}</Text>
              </View>
              <View style={{ alignItems: 'center', flex: 1, borderLeftWidth: 1, borderLeftColor: '#1F2128', borderRightWidth: 1, borderRightColor: '#1F2128' }}>
                <Text style={{ color: C.muted, fontSize: 8, fontWeight: '900', marginBottom: 4 }}>EXPECT. RISING</Text>
                <Text style={{ color: C.buy, fontSize: 16, fontWeight: '900' }}>₹{trade.expected_high || '—'}</Text>
              </View>
              <View style={{ alignItems: 'center', flex: 1 }}>
                <Text style={{ color: C.muted, fontSize: 8, fontWeight: '900', marginBottom: 4 }}>EXPECT. FALLING</Text>
                <Text style={{ color: C.sell, fontSize: 16, fontWeight: '900' }}>₹{trade.expected_low || '—'}</Text>
              </View>
            </View>


            {/* Execution Playbook */}
            <View style={{ backgroundColor: '#0D1117', borderRadius: 14, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: execColor + '20' }}>
              <Text style={{ color: execColor, fontSize: 14, fontWeight: '900', marginBottom: 12, letterSpacing: 0.5 }}>
                📘 {execLabel === 'BLOCKED' ? 'RESTRICTED' : 'EXECUTION'} PLAYBOOK: {stock.ticker?.split('.')[0]}
              </Text>

              {playbook.plan && playbook.plan.length > 0 ? (
                <View style={{ marginBottom: 16, gap: 8 }}>
                  {playbook.plan.map((step, idx) => (
                    <Text key={idx} style={{ color: C.subtext, fontSize: 11, fontWeight: '500', lineHeight: 16 }}>• {step}</Text>
                  ))}
                </View>
              ) : (
                <Text style={{ color: C.muted, fontSize: 11, marginBottom: 16, fontStyle: 'italic' }}>No specific playbook steps available.</Text>
              )}

              {/* Blueprints */}
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: '#1F2128', paddingTop: 16 }}>
                <View style={{ alignItems: 'flex-start' }}>
                  <Text style={{ color: C.muted, fontSize: 8, fontWeight: '800', marginBottom: 2 }}>ENTRY</Text>
                  <Text style={{ color: C.text, fontSize: 16, fontWeight: '900' }}>₹{trade.entry || '—'}</Text>
                </View>
                <View style={{ alignItems: 'center' }}>
                  <Text style={{ color: C.muted, fontSize: 8, fontWeight: '800', marginBottom: 2 }}>TARGET</Text>
                  <Text style={{ color: C.buy, fontSize: 16, fontWeight: '900' }}>₹{trade.targets?.[0] || '—'}</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={{ color: C.muted, fontSize: 8, fontWeight: '800', marginBottom: 2 }}>STOP LOSS</Text>
                  <Text style={{ color: C.sell, fontSize: 16, fontWeight: '900' }}>₹{trade.stop_loss || '—'}</Text>
                </View>
              </View>

          {/* Position Sizer */}
              <View style={{ marginTop: 16, backgroundColor: '#13151A', padding: 12, borderRadius: 10, borderWidth: 1, borderColor: '#4F8EF730' }}>
                <Text style={{ color: '#4F8EF7', fontSize: 10, fontWeight: '900', marginBottom: 8, textAlign: 'center' }}>🧠 INSTITUTIONAL POSITION SIZER</Text>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Text style={{ color: C.muted, fontSize: 10 }}>Global Risk Limit:</Text>
                  <Text style={{ color: C.sell, fontSize: 10, fontWeight: '700' }}>1.0% (₹1,000)</Text>
                </View>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#1F2128' }}>
                  <Text style={{ color: C.text, fontSize: 11, fontWeight: '700' }}>Execution Quantity:</Text>
                  <CounterText value={posSize.shares || 0} suffix=" Shares" style={{ color: C.buy, fontSize: 14, fontWeight: '900' }} />
                </View>

                <TouchableOpacity 
                  disabled={execLabel === 'BLOCKED'}
                  onPress={async () => {
                    try {
                      const res = await axios.post(`${API_URL}/trade/create`, {
                        ticker: stock.ticker,
                        strategy: trade.strategy || "TREND_FOLLOWING",
                        entry: trade.entry,
                        stop_loss: trade.stop_loss,
                        target: trade.targets[0]
                      });
                      alert(`TRADE EXECUTED: ${res.data.status}`);
                      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
                    } catch (err) {
                      alert("Execution failed.");
                    }
                  }}
                  style={{ 
                    marginTop: 12, 
                    backgroundColor: execLabel === 'BLOCKED' ? '#1F2128' : C.buy, 
                    paddingVertical: 14, 
                    borderRadius: 10, 
                    alignItems: 'center',
                    borderWidth: 1,
                    borderColor: execLabel === 'BLOCKED' ? C.border : 'transparent'
                  }}>
                  <Text style={{ color: execLabel === 'BLOCKED' ? C.muted : '#fff', fontSize: 13, fontWeight: '900', letterSpacing: 1 }}>
                    {execLabel === 'BLOCKED' ? 'EXECUTION BLOCKED' : 'EXECUTE TRADE'}
                  </Text>
                </TouchableOpacity>

                {execLabel === 'BLOCKED' && (
                  <Text style={{ color: C.sell, fontSize: 9, fontWeight: '700', textAlign: 'center', marginTop: 8 }}>
                    ⚠️ TRUTH MACHINE: CRITICAL FILTERS BLOCKING EXECUTION
                  </Text>
                )}

              </View>
            </View>

            {/* Signal Strength Breakdown */}
            <View style={{ marginBottom: 16 }}>
              <Text style={{ color: C.muted, fontSize: 9, fontWeight: '900', marginBottom: 8, letterSpacing: 1 }}>SIGNAL STRENGTH BY COMPONENT</Text>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <View style={{ flex: 1, backgroundColor: C.buyFaded, borderRadius: 10, padding: 12, alignItems: 'center' }}>
                  <CounterText value={stock.bullish_count || 0} style={{ color: C.buy, fontSize: 22, fontWeight: '900' }} />
                  <Text style={{ color: C.buy, fontSize: 8, fontWeight: '700', marginTop: 2 }}>UPTRENDS</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: '#1A202C', borderRadius: 10, padding: 12, alignItems: 'center' }}>
                  <CounterText value={stock.neutral_count || 0} style={{ color: C.warn, fontSize: 22, fontWeight: '900' }} />
                  <Text style={{ color: C.warn, fontSize: 8, fontWeight: '700', marginTop: 2 }}>NEUTRAL</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: C.sellFaded, borderRadius: 10, padding: 12, alignItems: 'center' }}>
                  <CounterText value={stock.bearish_count || 0} style={{ color: C.sell, fontSize: 22, fontWeight: '900' }} />
                  <Text style={{ color: C.sell, fontSize: 8, fontWeight: '700', marginTop: 2 }}>DOWNTRENDS</Text>
                </View>
              </View>
            </View>

            <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#1A202C', paddingVertical: 14, borderRadius: 10, alignItems: 'center', marginBottom: 20 }}>
              <Text style={{ color: C.text, fontSize: 14, fontWeight: '700' }}>Dismiss</Text>
            </TouchableOpacity>

          </TouchableOpacity>
        </ScrollView>
      </Animated.View>
    </TouchableOpacity>
  );
};


// ─── Main App ──────────────────────────────────────────────────────
export default function App() {
  const [scanResults, setScanResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState('');
  const [selectivity, setSelectivity] = useState('ALL'); // ALL, STRICT
  const [performance, setPerformance] = useState(null);
  
  const [activeTab, setActiveTab] = useState('SCANNER');
  const [portfolio, setPortfolio] = useState(null);
  const [fetchingPort, setFetchingPort] = useState(false);

  useEffect(() => { 
    fetchScan(); 
    fetchPerformance();
  }, []);

  useEffect(() => {
    if (activeTab === 'PORTFOLIO') fetchPortfolio();
  }, [activeTab]);

  const fetchPortfolio = async () => {
    setFetchingPort(true);
    try {
      const res = await axios.get(`${API_URL}/portfolio`, { timeout: 30000 });
      setPortfolio(res.data);
    } catch (err) {
      setError('Failed to fetch live portfolio tracking.');
    } finally {
      setFetchingPort(false);
    }
  };

  const fetchPerformance = async () => {
    try {
      const res = await axios.get(`${API_URL}/performance`, { timeout: 10000 });
      setPerformance(res.data);
    } catch (err) {
      console.log('Failed to fetch performance metrics');
    }
  };

  const fetchScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_URL}/scan`, { timeout: 120000 });
      setScanResults(res.data);
      setLastUpdate(new Date().toLocaleTimeString());
    } catch (err) {
      if (err.code === 'ECONNABORTED') {
        setError('Scan timed out · 90 stocks take ~30s, retrying...');
      } else {
        setError('Backend unreachable · Ensure python3 main.py is running and phone is on same WiFi');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchDetail = async (ticker) => {
    setLoading(true);
    try {
      const [res, btRes] = await Promise.all([
        axios.get(`${API_URL}/stock/${ticker}`, { timeout: 60000 }),
        axios.get(`${API_URL}/backtest/${ticker}`).catch(() => ({ data: null }))
      ]);
      const d = res.data;
      const bt = btRes.data?.strategy_edge || null;
      const ta = d.ta_summary || {};
      const ai = d.ai_prediction || {};
      
      setSelected({
        ticker: d.ticker,
        price: ta.last_price,
        rsi: ta.rsi,
        bias: ai.prediction || ta.bias,
        recommendation: ai.prediction || ta.recommendation,
        composite_score: ta.composite_score,
        struct_score: ta.struct_score,
        ind_score: ta.ind_score,
        ai_score: ai.ai_score,
        final_score: ai.final_score,
        
        // New Transparency Fields
        prediction: ai.prediction,
        conviction: ai.conviction || 'LOW',
        verdict: ta.verdict || ai.insight,
        conflict: ta.conflict_alert,
        l1_evidence: ta.l1_evidence || [],
        l2_evidence: ta.l2_evidence || [],
        ai_sources: ai.sources || [],
        ai_negatives: ai.negative_factors || [],
        ai_invalidation: ai.invalidation,
        server_time: ta.timestamp,

        probability: ai.probability,
        ai_insight: ai.ai_insight || ai.insight,
        ai_sentiment: ai.ai_sentiment || ai.sentiment,
        key_risk: ai.key_risk,
        bullish_count: ai.bullish_count,
        bearish_count: ai.bearish_count,
        neutral_count: (Object.keys(ta.breakdown || {}).length) - (ai.bullish_count || 0) - (ai.bearish_count || 0),
        breakdown: ai.breakdown || ta.breakdown || {},
        
        regime: ta.regime || {},
        breakout: ta.breakout || {},
        playbook: ta.playbook || {},
        trade: ta.trade || {},
        position_size: ta.position_size || {},
        backtest_edge: bt,
      });


    } catch {
      setError('Ticker not found');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (query.trim()) fetchDetail(query.trim().toUpperCase());
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: C.bg }}>
      <StatusBar style="light" />

      {/* ── Tabs ── */}
      <View style={{ flexDirection: 'row', backgroundColor: '#1A2333', marginHorizontal: 16, marginTop: 16, borderRadius: 10, padding: 4, borderWidth: 1, borderColor: C.border }}>
        <TouchableOpacity 
          style={{ flex: 1, paddingVertical: 10, alignItems: 'center', backgroundColor: activeTab === 'SCANNER' ? C.bg : 'transparent', borderRadius: 8 }}
          onPress={() => setActiveTab('SCANNER')}>
          <Text style={{ color: activeTab === 'SCANNER' ? '#fff' : C.muted, fontWeight: '800', fontSize: 13, letterSpacing: 1 }}>SCANNER</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={{ flex: 1, paddingVertical: 10, alignItems: 'center', backgroundColor: activeTab === 'PORTFOLIO' ? C.bg : 'transparent', borderRadius: 8 }}
          onPress={() => setActiveTab('PORTFOLIO')}>
          <Text style={{ color: activeTab === 'PORTFOLIO' ? '#fff' : C.muted, fontWeight: '800', fontSize: 13, letterSpacing: 1 }}>PORTFOLIO</Text>
        </TouchableOpacity>
      </View>

      {/* ── Error ── */}
      {error && (
        <View style={{ marginHorizontal: 16, marginTop: 12, padding: 10, backgroundColor: 'rgba(255,107,107,0.08)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(255,107,107,0.2)' }}>
          <Text style={{ color: C.sell, fontSize: 12 }}>{error}</Text>
        </View>
      )}

      {activeTab === 'SCANNER' ? (
        <>
          {/* ── Header ── */}
          <View style={[header.row, { paddingBottom: 0 }]}>
            <View>
              <Text style={header.title}>Global Scanner</Text>
              {lastUpdate ? <Text style={header.sub}>Updated {lastUpdate}</Text> : null}
            </View>
            <TouchableOpacity onPress={fetchScan} style={header.refreshBtn}>
              <Text style={header.refreshTxt}>↻ Refresh</Text>
            </TouchableOpacity>
          </View>

          {/* ── Search ── */}
          <View style={search.row}>
            <View style={search.inputWrap}>
              <Text style={search.icon}>🔍</Text>
              <TextInput
                style={search.input}
                placeholder="Search ticker..."
                placeholderTextColor={C.muted}
                value={query}
                onChangeText={setQuery}
                onSubmitEditing={handleSearch}
                autoCapitalize="characters"
              />
            </View>
            <TouchableOpacity onPress={handleSearch} style={search.btn}>
              <Text style={search.btnTxt}>Search</Text>
            </TouchableOpacity>
          </View>

          {/* ── Signal Count & Selectivity ── */}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12 }}>
            <Text style={txt.sectionTitle}>SCANNER RESULTS ({scanResults.length})</Text>
            <View style={{ flexDirection: 'row', gap: 6, backgroundColor: C.surface, borderRadius: 8, padding: 3, borderWidth: 1, borderColor: C.border }}>
              <TouchableOpacity 
                onPress={() => setSelectivity('ALL')} 
                style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: selectivity === 'ALL' ? '#1A2333' : 'transparent' }}>
                <Text style={{ color: selectivity === 'ALL' ? C.accent : C.muted, fontSize: 10, fontWeight: '700' }}>ALL</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                onPress={() => setSelectivity('STRICT')} 
                style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: selectivity === 'STRICT' ? '#1A2333' : 'transparent' }}>
                <Text style={{ color: selectivity === 'STRICT' ? C.buy : C.muted, fontSize: 10, fontWeight: '700' }}>STRICT (A/A+)</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* ── List ── */}
          {loading
            ? <ActivityIndicator color={C.accent} style={{ marginTop: 60 }} />
            : (() => {
                const filtered = selectivity === 'STRICT' ? scanResults.filter(s => s.composite_score >= 65) : scanResults;
                const sessions = [
                  { title: 'EXPECT UP', data: filtered.filter(s => s.recommendation === 'EXPECT UP') },
                  { title: 'EXPECT DOWN', data: filtered.filter(s => s.recommendation === 'EXPECT DOWN') },
                  { title: 'WAITING', data: filtered.filter(s => s.recommendation === 'WAIT') },
                ].filter(s => s.data.length > 0);

                return (
                  <SectionList
                    sections={sessions}
                    keyExtractor={i => i.ticker}
                    renderItem={({ item }) => <StockRow item={item} onPress={(s) => fetchDetail(s.ticker)} />}
                    renderSectionHeader={({ section: { title } }) => (
                      <View style={{ backgroundColor: C.bg, paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.border }}>
                        <Text style={{ color: title === 'EXPECT UP' ? C.buy : title === 'EXPECT DOWN' ? C.sell : C.muted, fontSize: 10, fontWeight: '900', letterSpacing: 1.5 }}>{title}</Text>
                      </View>
                    )}
                    contentContainerStyle={{ paddingBottom: 40 }}
                    ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: C.border, marginLeft: 16 }} />}
                    stickySectionHeadersEnabled={true}
                    showsVerticalScrollIndicator={false}
                  />
                );
              })()
          }
        </>
      ) : (
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Text style={{ color: C.text, fontSize: 22, fontWeight: '800' }}>Live Tracking</Text>
            <TouchableOpacity onPress={fetchPortfolio} style={header.refreshBtn}>
              <Text style={header.refreshTxt}>↻ Sync DB</Text>
            </TouchableOpacity>
          </View>
          
          {fetchingPort ? (
            <ActivityIndicator color={C.accent} style={{ marginTop: 40 }} />
          ) : portfolio && portfolio.summary ? (
            <>
              {/* Portfolio Stats */}
              <View style={{ marginBottom: 20, padding: 16, backgroundColor: '#0D1117', borderRadius: 12, borderWidth: 1, borderColor: C.border }}>
                <Text style={[txt.label, { marginBottom: 16, textAlign: 'center', color: '#4F8EF7' }]}>📊 REALIZED STRATEGY EDGE</Text>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <View style={{ alignItems: 'center', flex: 1 }}>
                    <Text style={{ color: C.muted, fontSize: 9, fontWeight: '700', marginBottom: 6 }}>WIN RATE</Text>
                    <Text style={{ color: portfolio.summary.win_rate > 50 ? C.buy : C.warn, fontSize: 20, fontWeight: '800' }}>{portfolio.summary.win_rate}%</Text>
                  </View>
                  <View style={{ width: 1, backgroundColor: C.border }} />
                  <View style={{ alignItems: 'center', flex: 1 }}>
                    <Text style={{ color: C.muted, fontSize: 9, fontWeight: '700', marginBottom: 6 }}>PROFIT FACTOR</Text>
                    <Text style={{ color: portfolio.summary.profit_factor >= 1.5 ? C.buy : C.warn, fontSize: 20, fontWeight: '800' }}>{portfolio.summary.profit_factor}</Text>
                  </View>
                  <View style={{ width: 1, backgroundColor: C.border }} />
                  <View style={{ alignItems: 'center', flex: 1 }}>
                    <Text style={{ color: C.muted, fontSize: 9, fontWeight: '700', marginBottom: 6 }}>CLOSED</Text>
                    <Text style={{ color: C.text, fontSize: 20, fontWeight: '800' }}>{portfolio.summary.total_closed}</Text>
                  </View>
                </View>
              </View>

              {/* Active Trades */}
              <Text style={{ color: C.subtext, fontSize: 13, fontWeight: '800', letterSpacing: 1.5, marginBottom: 12, marginTop: 10 }}>ACTIVE POSITIONS ({portfolio.summary.active_positions})</Text>
              
               {portfolio.active_trades.map(t => (
                <View key={t.id.toString()} style={{ backgroundColor: C.surface, padding: 14, borderRadius: 10, marginBottom: 10, borderWidth: 1, borderLeftWidth: 4, borderColor: C.border, borderLeftColor: t.direction === 'LONG' ? C.buy : C.sell }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                    <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                      <Text style={{ color: C.text, fontSize: 16, fontWeight: '800' }}>{t.ticker}</Text>
                      <View style={{ backgroundColor: '#2D3748', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 }}>
                        <Text style={{ color: '#fff', fontSize: 9, fontWeight: '700' }}>{t.strategy}</Text>
                      </View>
                    </View>
                    <Text style={{ color: t.floating_pnl_pct >= 0 ? C.buy : C.sell, fontSize: 16, fontWeight: '800' }}>
                      {t.floating_pnl_pct >= 0 ? '+' : ''}{t.floating_pnl_pct.toFixed(2)}%
                    </Text>
                  </View>
                  
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text style={{ color: C.muted, fontSize: 11 }}>Entry: {t.entry_price.toFixed(2)}</Text>
                    <Text style={{ color: C.text, fontSize: 11, fontWeight: '600' }}>Live: {t.current_price ? t.current_price.toFixed(2) : '---'}</Text>
                  </View>
                  
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 16 }}>
                    <Text style={{ color: C.sell, fontSize: 9, fontWeight: '600' }}>Stop: {t.stop_loss.toFixed(2)}</Text>
                    <Text style={{ color: C.buy, fontSize: 9, fontWeight: '600' }}>Target: {t.target_price.toFixed(2)}</Text>
                  </View>
                </View>
              ))}

              {portfolio.active_trades.length === 0 && (
                 <Text style={{ color: C.muted, fontSize: 13, textAlign: 'center', marginVertical: 20 }}>No active market positions.</Text>
              )}

              {/* Closed History */}
              <Text style={{ color: C.subtext, fontSize: 13, fontWeight: '800', letterSpacing: 1.5, marginBottom: 12, marginTop: 24 }}>CLOSED PERFORMANCE HISTORY</Text>
              {portfolio.closed_trades.slice(0, 10).map(t => (
                <View key={t.id.toString()} style={{ backgroundColor: '#0D1117', padding: 12, borderRadius: 8, marginBottom: 8, borderLeftWidth: 3, borderLeftColor: t.pnl_r > 0 ? C.buy : C.sell }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    <Text style={{ color: '#fff', fontSize: 14, fontWeight: '700' }}>{t.ticker}</Text>
                    <Text style={{ color: t.pnl_r >= 0 ? C.buy : C.sell, fontSize: 14, fontWeight: '900' }}>
                      {t.pnl_r >= 0 ? '+' : ''}{t.pnl_r}R
                    </Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 }}>
                    <Text style={{ color: C.muted, fontSize: 10 }}>{t.strategy}</Text>
                    <Text style={{ color: C.muted, fontSize: 10 }}>{t.exit_time}</Text>
                  </View>
                </View>
              ))}
            </>

          ) : null}
        </ScrollView>
      )}

      {/* ── Detail Sheet ── */}
      {selected && <DetailSheet stock={selected} onClose={() => setSelected(null)} />}
    </SafeAreaView>
  );
}

// ─── Shared Style Objects ──────────────────────────────────────────

const txt = StyleSheet.create({
  ticker: { color: C.text, fontSize: 16, fontWeight: '700', letterSpacing: 0.3 },
  price: { color: C.subtext, fontSize: 14, marginTop: 3 },
  badge: { fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  label: { color: C.muted, fontSize: 10, fontWeight: '700', letterSpacing: 1.5, marginBottom: 2 },
  mono: { fontSize: 11, fontWeight: '700', width: 34, textAlign: 'right' },
  sectionTitle: { color: C.subtext, fontSize: 10, fontWeight: '800', letterSpacing: 2 },
  sheetTicker: { color: C.text, fontSize: 28, fontWeight: '800' },
  sheetPrice: { fontSize: 18, fontWeight: '600', marginTop: 2 },
  metricVal: { color: C.text, fontSize: 18, fontWeight: '700', marginTop: 6 },
});

const row = StyleSheet.create({
  rsi: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  track: { flex: 1, height: 3, backgroundColor: C.border, borderRadius: 2, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 2 },
});

const card = StyleSheet.create({
  row: { flexDirection: 'row', backgroundColor: C.bg, overflow: 'hidden' },
  accentBar: { width: 3 },
  rowContent: { flex: 1, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14 },
  rowLeft: {},
  rowRight: { alignItems: 'flex-end', flex: 1, paddingLeft: 12 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
});

const header = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14 },
  title: { color: C.text, fontSize: 18, fontWeight: '700' },
  sub: { color: C.muted, fontSize: 11, marginTop: 2 },
  refreshBtn: { paddingHorizontal: 12, paddingVertical: 6, backgroundColor: C.surface, borderRadius: 8, borderWidth: 1, borderColor: C.border },
  refreshTxt: { color: C.accent, fontSize: 12, fontWeight: '600' },
});

const search = StyleSheet.create({
  row: { flexDirection: 'row', marginHorizontal: 16, marginTop: 14, marginBottom: 10, gap: 8 },
  inputWrap: { flex: 1, flexDirection: 'row', alignItems: 'center', backgroundColor: C.surface, borderRadius: 10, paddingHorizontal: 12, borderWidth: 1, borderColor: C.border },
  icon: { fontSize: 13, marginRight: 6 },
  input: { flex: 1, color: C.text, fontSize: 13, paddingVertical: 10 },
  btn: { backgroundColor: C.accent, paddingHorizontal: 16, borderRadius: 10, justifyContent: 'center' },
  btnTxt: { color: '#fff', fontSize: 13, fontWeight: '700' },
});

const sheet = StyleSheet.create({
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  panel: { backgroundColor: C.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, borderTopWidth: 1, borderColor: C.border },
  drag: { width: 40, height: 4, backgroundColor: C.border, borderRadius: 2, alignSelf: 'center', marginBottom: 20 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  metricsRow: { flexDirection: 'row', borderWidth: 1, borderColor: C.border, borderRadius: 12, marginBottom: 20, overflow: 'hidden' },
  metric: { flex: 1, padding: 14, backgroundColor: C.bg },
  probSection: { marginBottom: 18 },
  probTrack: { height: 4, backgroundColor: C.border, borderRadius: 2, overflow: 'hidden' },
  probFill: { height: '100%', borderRadius: 2 },
  insightBox: { backgroundColor: C.bg, borderRadius: 12, padding: 14, marginBottom: 18, borderWidth: 1, borderColor: C.border },
  insightText: { color: C.subtext, fontSize: 12, lineHeight: 18, marginTop: 6 },
  closeBtn: { borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 14, alignItems: 'center' },
  closeBtnText: { color: C.muted, fontSize: 13, fontWeight: '600' },
});
