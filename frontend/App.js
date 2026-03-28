import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, ScrollView, TouchableOpacity,
  TextInput, ActivityIndicator, Dimensions, FlatList
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native-safe-area-context';
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
  if (rec?.includes('BUY')) return { color: C.buy, bg: C.buyFaded };
  if (rec?.includes('SELL')) return { color: C.sell, bg: C.sellFaded };
  return { color: C.warn, bg: 'rgba(240,165,0,0.12)' }; // HOLD
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

// ─── Stock Row Card ────────────────────────────────────────────
const regimeColors = { TRENDING: '#4F8EF7', SIDEWAYS: '#F0A500', VOLATILE: '#FF6B6B' };
const tierColors = { 'A+': '#FFD700', 'A': '#3DDC84', 'B': '#4F8EF7', 'C': '#F0A500', 'D': '#FF6B6B' };

const StockRow = ({ item, onPress }) => {
  const t = tag(item.recommendation);
  const score = item.composite_score || 50;
  const scoreColor = score >= 65 ? C.buy : score >= 45 ? C.warn : C.sell;
  const changePct = item.price_change_pct || 0;
  const regime = item.regime || 'SIDEWAYS';
  const tier = item.signal_tier || 'C';
  return (
    <TouchableOpacity onPress={() => onPress(item)} style={card.row} activeOpacity={0.7}>
      <View style={[card.accentBar, { backgroundColor: tierColors[tier] || t.color }]} />
      <View style={card.rowContent}>
        <View style={card.rowLeft}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Text style={txt.ticker}>{item.ticker}</Text>
            <View style={{ backgroundColor: regimeColors[regime] + '22', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 1 }}>
              <Text style={{ color: regimeColors[regime], fontSize: 8, fontWeight: '700' }}>{regime}</Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 3 }}>
            <Text style={txt.price}>${item.price?.toLocaleString()}</Text>
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
            <View style={{ backgroundColor: tierColors[tier] + '25', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 }}>
              <Text style={{ color: tierColors[tier], fontSize: 9, fontWeight: '800' }}>{tier}</Text>
            </View>
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

// ─── Mini Bar for indicator score ──────────────────────────────────
const ScoreBar = ({ label, value }) => {
  const clr = value >= 65 ? C.buy : value >= 45 ? C.warn : C.sell;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
      <Text style={{ color: C.muted, fontSize: 10, width: 70, fontWeight: '600' }}>{label}</Text>
      <View style={{ flex: 1, height: 4, backgroundColor: C.border, borderRadius: 2, overflow: 'hidden', marginHorizontal: 8 }}>
        <View style={{ height: '100%', width: `${Math.min(value, 100)}%`, backgroundColor: clr, borderRadius: 2 }} />
      </View>
      <Text style={{ color: clr, fontSize: 10, fontWeight: '700', width: 28, textAlign: 'right' }}>{value}</Text>
    </View>
  );
};

// ─── Detail Bottom Sheet ───────────────────────────────────────────
const DetailSheet = ({ stock, onClose }) => {
  if (!stock) return null;
  const t = tag(stock.recommendation);
  const prob = parseFloat(stock.probability) || 50;
  const bd = stock.breakdown || {};
  const labels = { rsi: 'RSI', macd: 'MACD', sma_cross: 'SMA 20/50', ema_cross: 'EMA 12/26', bollinger: 'Bollinger', volume: 'Volume', stochastic: 'Stochastic', breakout: 'Breakout', trend_200: 'SMA 200' };
  const trade = stock.trade || {};
  const regime = stock.regime || {};
  const breakout = stock.breakout || {};
  const quality = stock.signal_quality || {};
  const momentum = stock.momentum || {};

  const boColor = breakout.status === 'CONFIRMED' ? C.buy : breakout.status === 'ATTEMPT' ? C.warn : breakout.status === 'WEAK' ? C.sell : C.muted;
  const boIcon = breakout.status === 'CONFIRMED' ? '✅' : breakout.status === 'ATTEMPT' ? '⚠️' : breakout.status === 'WEAK' ? '❌' : '';

  return (
    <TouchableOpacity style={sheet.overlay} onPress={onClose} activeOpacity={1}>
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ justifyContent: 'flex-end', flexGrow: 1 }}>
        <TouchableOpacity style={sheet.panel} activeOpacity={1} onPress={() => {}}>
          <View style={sheet.drag} />

          {/* Title + Quality Tier */}
          <View style={sheet.titleRow}>
            <View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Text style={txt.sheetTicker}>{stock.ticker}</Text>
                {quality.tier && (
                  <View style={{ backgroundColor: (tierColors[quality.tier] || C.muted) + '30', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 }}>
                    <Text style={{ color: tierColors[quality.tier] || C.muted, fontSize: 11, fontWeight: '800' }}>⭐ {quality.tier} {quality.label || ''}</Text>
                  </View>
                )}
              </View>
              <Text style={[txt.sheetPrice, { color: t.color }]}>${stock.price?.toLocaleString()}</Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <View style={[card.badge, { backgroundColor: t.bg, paddingHorizontal: 14, paddingVertical: 8 }]}>
                <Text style={[txt.badge, { color: t.color, fontSize: 12 }]}>{stock.recommendation}</Text>
              </View>
              <Text style={{ color: C.muted, fontSize: 10, marginTop: 4 }}>Score: {stock.final_score || stock.composite_score || '—'}/100</Text>
            </View>
          </View>

          {/* Regime + Breakout + Momentum Row */}
          <View style={{ flexDirection: 'row', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
            {regime.regime && (
              <View style={{ backgroundColor: (regimeColors[regime.regime] || C.muted) + '22', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 }}>
                <Text style={{ color: regimeColors[regime.regime] || C.muted, fontSize: 10, fontWeight: '700' }}>{regime.regime} {regime.strength || ''}</Text>
              </View>
            )}
            {breakout.status && breakout.status !== 'NONE' && (
              <View style={{ backgroundColor: boColor + '22', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 }}>
                <Text style={{ color: boColor, fontSize: 10, fontWeight: '700' }}>{boIcon} BREAKOUT {breakout.status}</Text>
              </View>
            )}
            {momentum.acceleration && momentum.acceleration !== 'STEADY' && (
              <View style={{ backgroundColor: C.accent + '22', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 }}>
                <Text style={{ color: C.accent, fontSize: 10, fontWeight: '700' }}>⚡ {momentum.acceleration}</Text>
              </View>
            )}
          </View>

          {/* Metrics Row */}
          <View style={sheet.metricsRow}>
            <View style={sheet.metric}>
              <Text style={txt.label}>RSI</Text>
              <Text style={[txt.metricVal, { color: stock.rsi < 35 ? C.buy : stock.rsi > 65 ? C.sell : C.warn }]}>{stock.rsi}</Text>
            </View>
            <View style={[sheet.metric, { borderLeftWidth: 1, borderLeftColor: C.border, borderRightWidth: 1, borderRightColor: C.border }]}>
              <Text style={txt.label}>CONFIDENCE</Text>
              <Text style={[txt.metricVal, { color: t.color }]}>{prob.toFixed(1)}%</Text>
            </View>
            <View style={sheet.metric}>
              <Text style={txt.label}>SENTIMENT</Text>
              <Text style={[txt.metricVal, { color: stock.ai_sentiment === 'bullish' ? C.buy : stock.ai_sentiment === 'bearish' ? C.sell : C.warn, fontSize: 13 }]}>
                {(stock.ai_sentiment || 'neutral').toUpperCase()}
              </Text>
            </View>
          </View>

          {/* Trade Structure */}
          {trade.direction && trade.direction !== 'WAIT' && (
            <View style={{ backgroundColor: '#0D1117', borderRadius: 10, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: trade.direction === 'LONG' ? C.buy + '30' : C.sell + '30' }}>
              <Text style={[txt.label, { marginBottom: 8, color: trade.direction === 'LONG' ? C.buy : C.sell }]}>🎯 TRADE STRUCTURE ({trade.direction})</Text>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <View style={{ alignItems: 'center', flex: 1 }}>
                  <Text style={{ color: C.muted, fontSize: 9, fontWeight: '600' }}>ENTRY</Text>
                  <Text style={{ color: C.text, fontSize: 14, fontWeight: '700' }}>{trade.entry}</Text>
                </View>
                <View style={{ alignItems: 'center', flex: 1 }}>
                  <Text style={{ color: C.muted, fontSize: 9, fontWeight: '600' }}>TARGET 1</Text>
                  <Text style={{ color: C.buy, fontSize: 14, fontWeight: '700' }}>{trade.targets?.[0]}</Text>
                </View>
                <View style={{ alignItems: 'center', flex: 1 }}>
                  <Text style={{ color: C.muted, fontSize: 9, fontWeight: '600' }}>TARGET 2</Text>
                  <Text style={{ color: C.buy, fontSize: 14, fontWeight: '700' }}>{trade.targets?.[1]}</Text>
                </View>
                <View style={{ alignItems: 'center', flex: 1 }}>
                  <Text style={{ color: C.muted, fontSize: 9, fontWeight: '600' }}>STOP LOSS</Text>
                  <Text style={{ color: C.sell, fontSize: 14, fontWeight: '700' }}>{trade.stop_loss}</Text>
                </View>
              </View>
              <Text style={{ color: C.subtext, fontSize: 10, marginTop: 6, textAlign: 'center' }}>Risk:Reward = {trade.risk_reward} | ATR = {trade.atr}</Text>
            </View>
          )}

          {/* Signal Strength */}
          {(stock.bullish_count != null) && (
            <View style={{ marginBottom: 12 }}>
              <Text style={[txt.label, { marginBottom: 8 }]}>SIGNAL STRENGTH</Text>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <View style={{ flex: 1, backgroundColor: C.buyFaded, borderRadius: 8, padding: 10, alignItems: 'center' }}>
                  <Text style={{ color: C.buy, fontSize: 20, fontWeight: '800' }}>{stock.bullish_count}</Text>
                  <Text style={{ color: C.buy, fontSize: 9, fontWeight: '600', marginTop: 2 }}>BULLISH</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: 'rgba(240,165,0,0.12)', borderRadius: 8, padding: 10, alignItems: 'center' }}>
                  <Text style={{ color: C.warn, fontSize: 20, fontWeight: '800' }}>{stock.neutral_count || 0}</Text>
                  <Text style={{ color: C.warn, fontSize: 9, fontWeight: '600', marginTop: 2 }}>NEUTRAL</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: C.sellFaded, borderRadius: 8, padding: 10, alignItems: 'center' }}>
                  <Text style={{ color: C.sell, fontSize: 20, fontWeight: '800' }}>{stock.bearish_count}</Text>
                  <Text style={{ color: C.sell, fontSize: 9, fontWeight: '600', marginTop: 2 }}>BEARISH</Text>
                </View>
              </View>
            </View>
          )}

          {/* Indicator Breakdown */}
          {Object.keys(bd).length > 0 && (
            <View style={sheet.insightBox}>
              <Text style={[txt.label, { marginBottom: 8 }]}>INDICATOR BREAKDOWN</Text>
              {Object.entries(bd).map(([key, val]) => (
                <ScoreBar key={key} label={labels[key] || key} value={val} />
              ))}
            </View>
          )}

          {/* AI Analysis */}
          {stock.ai_insight && (
            <View style={sheet.insightBox}>
              <Text style={txt.label}>ANALYSIS</Text>
              <Text style={sheet.insightText}>{stock.ai_insight}</Text>
            </View>
          )}

          {/* Risk Warnings (always-on) */}
          {(stock.risk_warnings?.length > 0 || stock.key_risk) && (
            <View style={[sheet.insightBox, { borderColor: 'rgba(255,107,107,0.2)' }]}>
              <Text style={[txt.label, { color: C.sell }]}>⚠ RISK ASSESSMENT</Text>
              {stock.risk_warnings?.map((w, i) => (
                <Text key={i} style={[sheet.insightText, { color: '#B8505E', marginTop: 3 }]}>• {w}</Text>
              ))}
              {stock.key_risk && !stock.risk_warnings?.length && (
                <Text style={[sheet.insightText, { color: '#B8505E' }]}>{stock.key_risk}</Text>
              )}
            </View>
          )}

          {/* R:R Rejection Note */}
          {trade.note && (
            <View style={{ backgroundColor: '#2A1A00', borderRadius: 8, padding: 10, marginBottom: 12, borderLeftWidth: 3, borderLeftColor: C.warn }}>
              <Text style={{ color: C.warn, fontSize: 11, fontWeight: '600' }}>💡 {trade.note}</Text>
            </View>
          )}

          {/* Trap Alert */}
          {stock.trap?.trap && (
            <View style={{ backgroundColor: '#2A0A0A', borderRadius: 8, padding: 10, marginBottom: 12, borderLeftWidth: 3, borderLeftColor: C.sell }}>
              <Text style={{ color: C.sell, fontSize: 11, fontWeight: '700' }}>🚨 {stock.trap.type}: {stock.trap.detail}</Text>
            </View>
          )}

          <TouchableOpacity onPress={onClose} style={sheet.closeBtn}>
            <Text style={sheet.closeBtnText}>Dismiss</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      </ScrollView>
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

  useEffect(() => { fetchScan(); }, []);

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
      const res = await axios.get(`${API_URL}/stock/${ticker}`, { timeout: 60000 });
      const d = res.data;
      const ta = d.ta_summary;
      const ai = d.ai_prediction;
      setSelected({
        ticker: d.ticker,
        price: ta.last_price,
        rsi: ta.rsi,
        recommendation: ai.prediction || ta.recommendation,
        composite_score: ta.composite_score,
        final_score: ai.final_score,
        probability: ai.probability,
        ai_insight: ai.ai_insight,
        ai_sentiment: ai.ai_sentiment,
        key_risk: ai.key_risk,
        bullish_count: ai.bullish_count,
        bearish_count: ai.bearish_count,
        neutral_count: (Object.keys(ta.breakdown || {}).length) - (ai.bullish_count || 0) - (ai.bearish_count || 0),
        breakdown: ai.breakdown || ta.breakdown || {},
        // Pro engine fields
        regime: ta.regime || {},
        breakout: ta.breakout || {},
        trap: ta.trap || {},
        volume_intel: ta.volume_intel || {},
        momentum: ta.momentum || {},
        trade: ta.trade || {},
        mtf: ta.mtf || {},
        signal_quality: ta.signal_quality || {},
        risk_warnings: ta.risk_warnings || [],
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

      {/* ── Header ── */}
      <View style={header.row}>
        <View>
          <Text style={header.title}>Global Scanner</Text>
          {lastUpdate ? <Text style={header.sub}>Updated {lastUpdate}</Text> : null}
        </View>
        <TouchableOpacity onPress={fetchScan} style={header.refreshBtn}>
          <Text style={header.refreshTxt}>↻ Refresh</Text>
        </TouchableOpacity>
      </View>

      {/* ── Divider ── */}
      <View style={{ height: 1, backgroundColor: C.border }} />

      {/* ── Search ── */}
      <View style={search.row}>
        <View style={search.inputWrap}>
          <Text style={search.icon}>🔍</Text>
          <TextInput
            style={search.input}
            placeholder="Search ticker (AAPL, RELIANCE.NS...)"
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

      {/* ── Error ── */}
      {error && (
        <View style={{ marginHorizontal: 16, marginBottom: 10, padding: 10, backgroundColor: 'rgba(255,107,107,0.08)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(255,107,107,0.2)' }}>
          <Text style={{ color: C.sell, fontSize: 12 }}>{error}</Text>
        </View>
      )}

      {/* ── Signal Count ── */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 8 }}>
        <Text style={txt.sectionTitle}>SCANNER RESULTS</Text>
        <Text style={[txt.label, { color: C.muted }]}>{scanResults.length} signals</Text>
      </View>

      {/* ── List ── */}
      {loading
        ? <ActivityIndicator color={C.accent} style={{ marginTop: 60 }} />
        : <FlatList
            data={scanResults}
            keyExtractor={i => i.ticker}
            renderItem={({ item }) => <StockRow item={item} onPress={(s) => fetchDetail(s.ticker)} />}
            contentContainerStyle={{ paddingBottom: 40 }}
            ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: C.border, marginLeft: 16 }} />}
            showsVerticalScrollIndicator={false}
          />
      }

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
