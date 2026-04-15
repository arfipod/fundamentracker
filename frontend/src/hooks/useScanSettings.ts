import { useState, useCallback, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useScanSettings(onScanComplete?: () => void) {
  const [scanInterval, setScanInterval] = useState<number>(0);
  const [lastScanTime, setLastScanTime] = useState<number>(0);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  const [serverTimeOffset, setServerTimeOffset] = useState<number>(0);
  const [currentServerTime, setCurrentServerTime] = useState<number>(0);

  const fetchScanSettings = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/scan-settings`);
      if (response.ok) {
        const data = await response.json();
        setScanInterval(data.interval_seconds || 0);
        setLastScanTime(data.last_scan_time || 0);
      }
      
      const timeRes = await fetch(`${API_URL}/server-time`);
      if (timeRes.ok) {
        const timeData = await timeRes.json();
        const offset = timeData.server_time - (Date.now() / 1000);
        setServerTimeOffset(offset);
      }
    } catch (err) {
      console.error("Error loading scan settings", err);
    }
  }, []);

  const handleUpdateInterval = async (newInterval: number) => {
    setScanInterval(newInterval);
    try {
      await fetch(`${API_URL}/scan-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_seconds: newInterval })
      });
    } catch (err) {
      console.error("Error saving scan settings", err);
    }
  };

  const handleScan = async () => {
    try {
      setIsScanning(true);
      const response = await fetch(`${API_URL}/scan`, { method: 'POST' });
      if (!response.ok) throw new Error('Error scanning');
      await fetchScanSettings();
      if (onScanComplete) onScanComplete();
    } catch (err: unknown) {
       if (err instanceof Error) {
        setScanError(err.message);
      }
    } finally {
      setIsScanning(false);
    }
  };

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentServerTime((Date.now() / 1000) + serverTimeOffset);
    }, 1000);
    return () => clearInterval(timer);
  }, [serverTimeOffset]);

  const nextScanTime = (scanInterval > 0 && lastScanTime > 0) ? lastScanTime + scanInterval : 0;

  return {
    scanInterval,
    lastScanTime,
    isScanning,
    scanError,
    currentServerTime,
    nextScanTime,
    fetchScanSettings,
    handleUpdateInterval,
    handleScan
  };
}
