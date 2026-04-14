import { useEffect, useState } from 'react';

function App() {
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWatchlist = async () => {
      try {
        const response = await fetch('http://localhost:8000/watchlist');
        const result = await response.json();
        setData(result);
      } finally {
        setLoading(false);
      }
    };

    fetchWatchlist();
  }, []);

  return (
    <main>
      <h1>FundamenTracker UI</h1>
      {loading ? <p>Cargando...</p> : <pre>{JSON.stringify(data, null, 2)}</pre>}
    </main>
  );
}

export default App;
