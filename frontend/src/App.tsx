import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import SearchPage from './pages/SearchPage';
import FigurePage from './pages/FigurePage';
import ComparePage from './pages/ComparePage';
import SourcesPage from './pages/SourcesPage';
import NotFoundPage from './pages/NotFoundPage';
import DemoPage from './pages/DemoPage';
import { fetchAPI, getErrorMessage } from './api/client';
import type { CapabilitiesResponse } from './types';
import { CapabilitiesResponseSchema } from './types';

function App() {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAPI<CapabilitiesResponse>('/api/v1/capabilities', { schema: CapabilitiesResponseSchema })
      .then(setCapabilities)
      .catch((error: unknown) => setError(getErrorMessage(error, '获取配置失败')));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 text-red-600" role="alert">
        <p>初始化失败: {error}</p>
        <button onClick={() => window.location.reload()} className="ml-4 underline">重试</button>
      </div>
    );
  }

  if (!capabilities) {
    return <div className="min-h-screen flex items-center justify-center" aria-live="polite">加载中...</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout capabilities={capabilities} />}>
          <Route index element={<Navigate to="/search" replace />} />
          <Route path="search" element={<SearchPage capabilities={capabilities} />} />
          <Route path="figures/:figureId" element={<FigurePage />} />
          <Route path="compare/:candidateId" element={<ComparePage capabilities={capabilities} />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="demo" element={<DemoPage capabilities={capabilities} />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
