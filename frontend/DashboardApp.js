import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import axios from 'axios';

const API_URL = 'http://192.168.1.18:8000';

const palette = {
  bg: '#090D16',
  card: '#121827',
  cardSoft: '#1A2235',
  border: '#25304A',
  text: '#E8EDF9',
  muted: '#9FAAC5',
  up: '#24D07A',
  down: '#FF6B6B',
  wait: '#F5B742',
  accent: '#5A7CFF',
};

const scoreColor = (score) => {
  if (score >= 65) return palette.up;
  if (score <= 35) return palette.down;
  return palette.wait;
};

const riskColor = (riskLevel) => {
  if (riskLevel === 'HIGH') return palette.down;
  if (riskLevel === 'LOW') return palette.up;
  return palette.wait;
};

const fmtNum = (value, fallback = '-') => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return fallback;
  }
  return Number(value).toFixed(2);
};

function Header() {
  return (
    <View style={styles.headerWrap}>
      <Text style={styles.title}>Jiva Stock Intelligence</Text>
      <Text style={styles.subtitle}>AI + technical + risk dashboard (paper-trading focused)</Text>
    </View>
  );
}

function KpiCard({ label, value, color }) {
  return (
    <View style={styles.kpiCard}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={[styles.kpiValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

function ProbabilityBars({ probabilities }) {
  const bullish = probabilities?.bullish || 0;
  const sideways = probabilities?.sideways || 0;
  const bearish = probabilities?.bearish || 0;

  const rows = [
    { label: 'Up', value: bullish, color: palette.up },
    { label: 'Sideways', value: sideways, color: palette.wait },
    { label: 'Down', value: bearish, color: palette.down },
  ];

  return (
    <View style={styles.blockCard}>
      <Text style={styles.blockTitle}>Probability Structure</Text>
      {rows.map((row) => (
        <View key={row.label} style={styles.probRow}>
          <Text style={styles.probLabel}>{row.label}</Text>
          <View style={styles.probTrack}>
            <View style={[styles.probFill, { width: `${Math.max(0, Math.min(100, row.value))}%`, backgroundColor: row.color }]} />
          </View>
          <Text style={styles.probValue}>{row.value}%</Text>
        </View>
      ))}
    </View>
  );
}

function RiskPanel({ risk }) {
  const warnings = risk?.warnings || [];
  const level = risk?.level || 'MEDIUM';
  const levelClr = riskColor(level);

  return (
    <View style={styles.blockCard}>
      <View style={styles.rowBetween}>
        <Text style={styles.blockTitle}>Risk View</Text>
        <Text style={[styles.riskLevel, { color: levelClr }]}>{level}</Text>
      </View>
      <Text style={styles.smallMuted}>
        Capital Safety Score: {fmtNum(risk?.capital_safety_score, '0.00')}
      </Text>
      {warnings.length === 0 ? (
        <Text style={[styles.smallMuted, { marginTop: 8 }]}>No active risk warnings.</Text>
      ) : (
        warnings.slice(0, 4).map((w, idx) => (
          <Text key={`${w}-${idx}`} style={styles.warningText}>• {w}</Text>
        ))
      )}
    </View>
  );
}

function OpportunityCard({ item, onPress }) {
  const clr = scoreColor(item.composite_score || 50);
  const rec = item.recommendation || 'WAIT';

  return (
    <TouchableOpacity onPress={() => onPress(item.ticker)} activeOpacity={0.85} style={styles.stockCard}>
      <View style={[styles.stockAccent, { backgroundColor: clr }]} />
      <View style={styles.stockBody}>
        <View style={styles.rowBetween}>
          <Text style={styles.stockTicker}>{item.ticker}</Text>
          <Text style={[styles.stockScore, { color: clr }]}>{fmtNum(item.composite_score, '50')}</Text>
        </View>
        <View style={[styles.rowBetween, { marginTop: 4 }]}> 
          <Text style={styles.stockMeta}>Price: {item.price ?? '-'}</Text>
          <Text style={[styles.stockMeta, { color: clr }]}>{rec}</Text>
        </View>
        <Text style={styles.stockMeta}>Regime: {item.regime || 'SIDEWAYS'} • RSI: {fmtNum(item.rsi, '0.00')}</Text>
      </View>
    </TouchableOpacity>
  );
}

export default function DashboardApp() {
  const [ticker, setTicker] = useState('AAPL');
  const [selected, setSelected] = useState(null);
  const [scanData, setScanData] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [error, setError] = useState('');

  const canAnalyze = useMemo(() => (ticker || '').trim().length > 0, [ticker]);

  const fetchPerformance = async () => {
    try {
      const res = await axios.get(`${API_URL}/performance`, { timeout: 20000 });
      setPerformance(res.data || null);
    } catch {
      setPerformance(null);
    }
  };

  const fetchScan = async () => {
    setScanLoading(true);
    try {
      const res = await axios.get(`${API_URL}/scan`, { timeout: 120000 });
      const rows = Array.isArray(res.data) ? res.data.slice(0, 40) : [];
      setScanData(rows);
    } catch {
      setScanData([]);
      setError('Could not fetch scanner data. Check backend host/IP.');
    } finally {
      setScanLoading(false);
    }
  };

  const analyzeTicker = async (tickerInput) => {
    const symbol = (tickerInput || '').trim().toUpperCase();
    if (!symbol) return;

    setTicker(symbol);
    setLoading(true);
    setError('');

    try {
      const res = await axios.get(`${API_URL}/analysis/${symbol}`, { timeout: 60000 });
      setSelected(res.data);
    } catch (e) {
      const msg = e?.response?.data?.detail || 'Analysis failed. Verify ticker and backend status.';
      setError(String(msg));
      setSelected(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformance();
    fetchScan();
    analyzeTicker('AAPL');
  }, []);

  const summary = performance?.summary || {};

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Header />

        <View style={styles.searchWrap}>
          <TextInput
            style={styles.input}
            value={ticker}
            onChangeText={setTicker}
            autoCapitalize="characters"
            placeholder="Enter ticker (e.g., AAPL or RELIANCE.NS)"
            placeholderTextColor={palette.muted}
          />
          <TouchableOpacity
            style={[styles.primaryBtn, !canAnalyze ? styles.btnDisabled : null]}
            disabled={!canAnalyze || loading}
            onPress={() => analyzeTicker(ticker)}
          >
            {loading ? <ActivityIndicator color={palette.text} /> : <Text style={styles.primaryBtnText}>Analyze</Text>}
          </TouchableOpacity>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={styles.kpiGrid}>
          <KpiCard label="Win Rate" value={`${fmtNum(summary.win_rate, '0.00')}%`} color={palette.up} />
          <KpiCard label="Total Equity (R)" value={fmtNum(summary.total_equity_r, '0.00')} color={palette.accent} />
          <KpiCard label="Active Risk (R)" value={fmtNum(summary.active_risk_r, '0.00')} color={palette.wait} />
          <KpiCard label="Closed Trades" value={`${summary.closed_trades || 0}`} color={palette.text} />
        </View>

        {selected ? (
          <View style={styles.analysisCard}>
            <View style={styles.rowBetween}>
              <View>
                <Text style={styles.analysisTicker}>{selected.ticker}</Text>
                <Text style={styles.analysisPrice}>{selected.currency_symbol || '$'} {fmtNum(selected.price, '0.00')}</Text>
              </View>
              <View style={styles.scorePill}>
                <Text style={[styles.scoreText, { color: scoreColor(selected.final_score || 50) }]}>{fmtNum(selected.final_score, '50.0')}</Text>
              </View>
            </View>

            <Text style={styles.verdictText}>{selected.verdict || 'Stability (Hold)'}</Text>
            <Text style={styles.smallMuted}>
              Conviction: {selected.conviction || 'LOW'} • Probability: {selected.probability || '50.0%'}
            </Text>
            <Text style={[styles.smallMuted, { marginTop: 8 }]}>AI Insight: {selected?.ai?.insight || 'No AI insight available.'}</Text>
          </View>
        ) : null}

        <ProbabilityBars probabilities={selected?.probabilities} />
        <RiskPanel risk={selected?.risk} />

        <View style={[styles.rowBetween, { marginBottom: 10, marginTop: 4 }]}> 
          <Text style={styles.sectionTitle}>Global Opportunities</Text>
          <TouchableOpacity style={styles.refreshBtn} onPress={fetchScan}>
            <Text style={styles.refreshText}>{scanLoading ? 'Loading...' : 'Refresh'}</Text>
          </TouchableOpacity>
        </View>

        {scanLoading ? (
          <View style={styles.loaderWrap}>
            <ActivityIndicator color={palette.accent} />
            <Text style={styles.smallMuted}>Scanning global tickers...</Text>
          </View>
        ) : (
          <FlatList
            data={scanData}
            keyExtractor={(item, index) => `${item.ticker}-${index}`}
            scrollEnabled={false}
            renderItem={({ item }) => (
              <OpportunityCard item={item} onPress={analyzeTicker} />
            )}
            ListEmptyComponent={<Text style={styles.smallMuted}>No opportunities available right now.</Text>}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingBottom: 28,
  },
  headerWrap: {
    marginTop: 8,
    marginBottom: 14,
  },
  title: {
    color: palette.text,
    fontSize: 26,
    fontWeight: '800',
  },
  subtitle: {
    color: palette.muted,
    fontSize: 13,
    marginTop: 4,
  },
  searchWrap: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  input: {
    flex: 1,
    backgroundColor: palette.card,
    borderWidth: 1,
    borderColor: palette.border,
    color: palette.text,
    borderRadius: 10,
    paddingHorizontal: 12,
    height: 44,
    marginRight: 10,
  },
  primaryBtn: {
    backgroundColor: palette.accent,
    borderRadius: 10,
    paddingHorizontal: 16,
    justifyContent: 'center',
    alignItems: 'center',
    minWidth: 92,
  },
  btnDisabled: {
    opacity: 0.45,
  },
  primaryBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  errorText: {
    color: palette.down,
    marginBottom: 10,
  },
  kpiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  kpiCard: {
    width: '48.5%',
    backgroundColor: palette.card,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  kpiLabel: {
    color: palette.muted,
    fontSize: 12,
  },
  kpiValue: {
    color: palette.text,
    fontSize: 18,
    marginTop: 4,
    fontWeight: '800',
  },
  analysisCard: {
    backgroundColor: palette.cardSoft,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
  },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  analysisTicker: {
    color: palette.text,
    fontSize: 22,
    fontWeight: '800',
  },
  analysisPrice: {
    color: palette.muted,
    marginTop: 2,
  },
  scorePill: {
    backgroundColor: '#0D1422',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: palette.border,
  },
  scoreText: {
    fontSize: 16,
    fontWeight: '800',
  },
  verdictText: {
    color: palette.text,
    marginTop: 12,
    fontSize: 15,
    fontWeight: '700',
  },
  smallMuted: {
    color: palette.muted,
    fontSize: 12,
  },
  blockCard: {
    backgroundColor: palette.card,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
  },
  blockTitle: {
    color: palette.text,
    fontWeight: '700',
    marginBottom: 8,
  },
  probRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 7,
  },
  probLabel: {
    color: palette.muted,
    width: 72,
    fontSize: 12,
  },
  probTrack: {
    flex: 1,
    height: 8,
    borderRadius: 10,
    backgroundColor: '#0F1422',
    overflow: 'hidden',
    marginRight: 10,
  },
  probFill: {
    height: 8,
    borderRadius: 10,
  },
  probValue: {
    color: palette.text,
    width: 42,
    textAlign: 'right',
    fontSize: 12,
    fontWeight: '700',
  },
  riskLevel: {
    fontWeight: '800',
    fontSize: 12,
  },
  warningText: {
    color: '#F8C8C8',
    fontSize: 12,
    marginTop: 6,
  },
  sectionTitle: {
    color: palette.text,
    fontSize: 17,
    fontWeight: '700',
  },
  refreshBtn: {
    backgroundColor: '#182340',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#2A3C69',
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  refreshText: {
    color: '#CFE0FF',
    fontWeight: '700',
    fontSize: 12,
  },
  loaderWrap: {
    backgroundColor: palette.card,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
  },
  stockCard: {
    backgroundColor: palette.card,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 12,
    marginBottom: 8,
    overflow: 'hidden',
  },
  stockAccent: {
    height: 3,
    width: '100%',
  },
  stockBody: {
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  stockTicker: {
    color: palette.text,
    fontWeight: '800',
    fontSize: 15,
  },
  stockScore: {
    fontWeight: '800',
    fontSize: 14,
  },
  stockMeta: {
    color: palette.muted,
    marginTop: 2,
    fontSize: 12,
  },
});
