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

// ─── Stock Row Card ────────────────────────────────────────────────
const StockRow = ({ item, onPress }) => {
  const t = tag(item.recommendation);
  const score = item.composite_score || 50;
  const scoreColor = score >= 65 ? C.buy : score >= 45 ? C.warn : C.sell;
  const changePct = item.price_change_pct || 0;
  return (
    <TouchableOpacity onPress={() => onPress(item)} style={card.row} activeOpacity={0.7}>
      <View style={[card.accentBar, { backgroundColor: t.color }]} />
      <View style={card.rowContent}>
        <View style={card.rowLeft}>
          <Text style={txt.ticker}>{item.ticker}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 3 }}>
            <Text style={txt.price}>${item.price?.toLocaleString()}</Text>
            <Text style={{ color: changePct >= 0 ? C.buy : C.sell, fontSize: 11, fontWeight: '600' }}>
              {changePct >= 0 ? '▲' : '▼'} {Math.abs(changePct).toFixed(2)}%
            </Text>
          </View>
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

// ─── Detail Bottom Sheet ───────────────────────────────────────────
const DetailSheet = ({ stock, onClose }) => {
  if (!stock) return null;
  const t = tag(stock.recommendation);
  const prob = parseFloat(stock.probability) || 50;

  return (
    <TouchableOpacity style={sheet.overlay} onPress={onClose} activeOpacity={1}>
      <TouchableOpacity style={sheet.panel} activeOpacity={1} onPress={() => {}}>
        <View style={sheet.drag} />

        {/* Title Row */}
        <View style={sheet.titleRow}>
          <View>
            <Text style={txt.sheetTicker}>{stock.ticker}</Text>
            <Text style={[txt.sheetPrice, { color: t.color }]}>${stock.price?.toLocaleString()}</Text>
          </View>
          <View style={[card.badge, { backgroundColor: t.bg, paddingHorizontal: 14, paddingVertical: 8 }]}>
            <Text style={[txt.badge, { color: t.color, fontSize: 12 }]}>{stock.recommendation}</Text>
          </View>
        </View>

        {/* Metrics Grid */}
        <View style={sheet.metricsRow}>
          <View style={sheet.metric}>
            <Text style={txt.label}>RSI</Text>
            <Text style={[txt.metricVal, { color: stock.rsi < 35 ? C.buy : stock.rsi > 65 ? C.sell : C.warn }]}>{stock.rsi}</Text>
          </View>
          <View style={[sheet.metric, { borderLeftWidth: 1, borderLeftColor: C.border, borderRightWidth: 1, borderRightColor: C.border }]}>
            <Text style={txt.label}>AI PROBABILITY</Text>
            <Text style={[txt.metricVal, { color: t.color }]}>{prob.toFixed(1)}%</Text>
          </View>
          <View style={sheet.metric}>
            <Text style={txt.label}>GEO RISK</Text>
            <Text style={[txt.metricVal, { color: stock.geopolitical_risk === 'High' ? C.sell : C.buy }]}>
              {stock.geopolitical_risk || 'LOW'}
            </Text>
          </View>
        </View>

        {/* Probability Bar */}
        <View style={sheet.probSection}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
            <Text style={txt.label}>CONFIDENCE</Text>
            <Text style={[txt.label, { color: t.color }]}>{prob.toFixed(1)}%</Text>
          </View>
          <View style={sheet.probTrack}>
            <View style={[sheet.probFill, { width: `${prob}%`, backgroundColor: t.color }]} />
          </View>
        </View>

        {/* AI Insight */}
        {stock.ai_insight && (
          <View style={sheet.insightBox}>
            <Text style={txt.label}>AI ANALYSIS</Text>
            <Text style={sheet.insightText}>{stock.ai_insight}</Text>
          </View>
        )}

        <TouchableOpacity onPress={onClose} style={sheet.closeBtn}>
          <Text style={sheet.closeBtnText}>Dismiss</Text>
        </TouchableOpacity>
      </TouchableOpacity>
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
      const res = await axios.get(`${API_URL}/stock/${ticker}`);
      const d = res.data;
      setSelected({
        ticker: d.ticker,
        price: d.ta_summary.last_price,
        rsi: d.ta_summary.rsi,
        recommendation: d.ta_summary.recommendation,
        probability: d.ai_prediction.probability,
        ai_insight: d.ai_prediction.ai_insight,
        geopolitical_risk: d.ai_prediction.geopolitical_risk,
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
