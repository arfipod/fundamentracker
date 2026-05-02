import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine
} from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface HistoryData {
  date: string;
  value: number;
}

interface MetricChartProps {
  ticker: string;
  metric: string;
  currentValue?: number | null;
  targetValue?: number | null;
  height?: number;
  showPeriodToggle?: boolean;
  showReferenceLineToggle?: boolean;
}

export function MetricChart({ ticker, metric, currentValue, targetValue, height = 400, showPeriodToggle = true, showReferenceLineToggle = true }: MetricChartProps) {
  const [period, setPeriod] = useState('1y');
  const [historyData, setHistoryData] = useState<HistoryData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showMax, setShowMax] = useState(false);
  const [showMin, setShowMin] = useState(false);
  const [showAvg, setShowAvg] = useState(false);
  const [showMedian, setShowMedian] = useState(false);
  const [showCurrent, setShowCurrent] = useState(false);
  const [showTarget, setShowTarget] = useState(false);

  const periods = [
    { label: '1m', value: '1mo' },
    { label: '3m', value: '3mo' },
    { label: '6m', value: '6mo' },
    { label: '1y', value: '1y' },
    { label: '2y', value: '2y' },
    { label: '5y', value: '5y' },
    { label: '10y', value: '10y' },
    { label: 'Max', value: 'max' }
  ];

  useEffect(() => {
    const fetchHistory = async () => {
      if (!ticker || !metric) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const histRes = await fetch(`${API_URL}/history?ticker=${ticker}&metric=${metric}&period=${period}`);
        if (histRes.ok) {
          const histData = await histRes.json();
          setHistoryData(histData);
        } else {
          setHistoryData([]);
          const errorData = await histRes.json();
          setError(errorData.detail || "Failed to fetch historical data");
        }
      } catch (err: any) {
        setError(err.message || "An error occurred");
        setHistoryData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [ticker, metric, period]);

  const values = historyData.map(d => d.value).filter(v => typeof v === 'number' && !isNaN(v));
  const dataMax = values.length ? Math.max(...values) : null;
  const dataMin = values.length ? Math.min(...values) : null;
  const dataAvg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  const sortedValues = [...values].sort((a, b) => a - b);
  const dataMedian = values.length 
    ? (values.length % 2 === 0 
      ? (sortedValues[values.length / 2 - 1] + sortedValues[values.length / 2]) / 2 
      : sortedValues[Math.floor(values.length / 2)]) 
    : null;

  return (
    <div className="metric-chart-container" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      <div className="chart-header" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {showPeriodToggle && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div className="period-selector" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {periods.map(p => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid #334155',
                  background: period === p.value ? '#3b82f6' : '#1e293b',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  fontSize: '0.8rem'
                }}
              >
                {p.label}
              </button>
            ))}
            </div>
          </div>
        )}
        
        {showReferenceLineToggle && (
          <div className="reference-lines-toggles" style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
              <input type="checkbox" checked={showMax} onChange={e => setShowMax(e.target.checked)} /> Max
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
              <input type="checkbox" checked={showMin} onChange={e => setShowMin(e.target.checked)} /> Min
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
              <input type="checkbox" checked={showAvg} onChange={e => setShowAvg(e.target.checked)} /> Avg
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
              <input type="checkbox" checked={showMedian} onChange={e => setShowMedian(e.target.checked)} /> Median
            </label>
            {currentValue !== undefined && currentValue !== null && (
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                <input type="checkbox" checked={showCurrent} onChange={e => setShowCurrent(e.target.checked)} /> Current
              </label>
            )}
            {targetValue !== undefined && targetValue !== null && (
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                <input type="checkbox" checked={showTarget} onChange={e => setShowTarget(e.target.checked)} /> Target
              </label>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading" style={{ height }}>Loading chart data...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : historyData.length > 0 ? (
        <div style={{ width: '100%', height }}>
          <ResponsiveContainer>
            <LineChart data={historyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="date" 
                stroke="#94a3b8" 
                tickFormatter={(val) => {
                  const date = new Date(val);
                  return `${date.getMonth() + 1}/${date.getFullYear().toString().slice(2)}`;
                }}
              />
              <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                itemStyle={{ color: '#60a5fa' }}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="value" 
                name={metric.toUpperCase()} 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 8 }} 
              />
              {showMax && dataMax !== null && <ReferenceLine y={dataMax} label={{ value: "Max", position: 'insideTopLeft', fill: '#ef4444' }} stroke="#ef4444" strokeDasharray="3 3" />}
              {showMin && dataMin !== null && <ReferenceLine y={dataMin} label={{ value: "Min", position: 'insideBottomLeft', fill: '#10b981' }} stroke="#10b981" strokeDasharray="3 3" />}
              {showAvg && dataAvg !== null && <ReferenceLine y={dataAvg} label={{ value: "Avg", position: 'insideBottomLeft', fill: '#f59e0b' }} stroke="#f59e0b" strokeDasharray="3 3" />}
              {showMedian && dataMedian !== null && <ReferenceLine y={dataMedian} label={{ value: "Median", position: 'insideTopLeft', fill: '#8b5cf6' }} stroke="#8b5cf6" strokeDasharray="3 3" />}
              {showCurrent && currentValue !== null && currentValue !== undefined && <ReferenceLine y={currentValue} label={{ value: "Current", position: 'right', fill: '#06b6d4' }} stroke="#06b6d4" strokeDasharray="3 3" />}
              {showTarget && targetValue !== null && targetValue !== undefined && <ReferenceLine y={targetValue} label={{ value: "Target", position: 'left', fill: '#ec4899' }} stroke="#ec4899" strokeDasharray="3 3" />}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-message" style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>No historical data available</div>
      )}
    </div>
  );
}
