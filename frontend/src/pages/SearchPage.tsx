import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { SearchResponseSchema } from '../types';
import type { SearchResponse, CapabilitiesResponse } from '../types';
import { fetchAPI, APIError, isAbortError, toAPIError } from '../api/client';
import DataStatusNotice from '../components/DataStatusNotice';

const SCORE_COMPONENT_KEYS = ['sv', 'st', 'sr', 'sf', 'sg', 'se', 'u_model'] as const;

export default function SearchPage({ capabilities }: { capabilities: CapabilitiesResponse }) {
  const [mode, setMode] = useState<'text' | 'image' | 'region'>('text');
  const [query, setQuery] = useState('');
  const [corpus, setCorpus] = useState('all');

  const [file, setFile] = useState<File | null>(null);

  const [regionIdType, setRegionIdType] = useState<'figure_id' | 'page_id'>('figure_id');
  const [regionId, setRegionId] = useState('');
  const [bbox, setBbox] = useState({ x: 0, y: 0, width: 0, height: 0 });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);

  const navigate = useNavigate();
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  const handleModeChange = (newMode: 'text' | 'image' | 'region') => {
    if (abortRef.current) abortRef.current.abort();
    setMode(newMode);
    setLoading(false);
    setError(null);
    setData(null);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (abortRef.current) abortRef.current.abort();

    setLoading(true);
    setError(null);
    setData(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const filters = { book_ids: [], edition_ids: [],
        ...(corpus === 'all' ? {} : { dataset_kinds: [corpus] }) };
      if (mode === 'text') {
        if (!query.trim()) throw new Error('请输入检索词');
        const res = await fetchAPI<SearchResponse>('/api/v1/search/text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, top_k: 10, filters }),
          signal: controller.signal,
          schema: SearchResponseSchema
        });
        if (!controller.signal.aborted) setData(res);
      } else if (mode === 'image') {
        if (!file) throw new Error('请选择图片');
        if (file.size > capabilities.upload_limits.max_upload_bytes) {
           throw new Error(`图片大小不能超过 ${capabilities.upload_limits.max_upload_bytes} 字节`);
        }

        await new Promise<void>((resolve, reject) => {
           const img = new Image();
           const objectUrl = URL.createObjectURL(file);
           let settled = false;

           const cleanup = () => {
              controller.signal.removeEventListener('abort', handleAbort);
              img.onload = null;
              img.onerror = null;
              URL.revokeObjectURL(objectUrl);
              img.src = '';
           };
           const settle = (callback: () => void) => {
              if (settled) return;
              settled = true;
              cleanup();
              callback();
           };
           const handleAbort = () => {
              settle(() => reject(new DOMException('Request aborted', 'AbortError')));
           };

           controller.signal.addEventListener('abort', handleAbort, { once: true });

           img.onload = () => {
              if (controller.signal.aborted) {
                 handleAbort();
              } else if (img.width * img.height > capabilities.upload_limits.max_image_pixels) {
                 settle(() => reject(new Error(`图片像素数超过上限 ${capabilities.upload_limits.max_image_pixels}`)));
              } else {
                 settle(resolve);
              }
           };
           img.onerror = () => {
              if (controller.signal.aborted) {
                 handleAbort();
              } else {
                 settle(() => reject(new Error('无法读取图片尺寸')));
              }
           };
           img.src = objectUrl;
        });

        if (controller.signal.aborted) throw new DOMException('Request aborted', 'AbortError');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('top_k', '10');
        formData.append('filters', JSON.stringify(filters));

        const res = await fetchAPI<SearchResponse>('/api/v1/search/image', {
          method: 'POST',
          body: formData,
          signal: controller.signal,
          schema: SearchResponseSchema
        });
        if (!controller.signal.aborted) setData(res);
      } else if (mode === 'region') {
        if (!regionId.trim()) throw new Error('请输入正确的ID');
        if (!Number.isFinite(bbox.x) || !Number.isFinite(bbox.y) || !Number.isFinite(bbox.width) || !Number.isFinite(bbox.height)) {
           throw new Error('坐标必须是有效数值');
        }
        if (bbox.width <= 0 || bbox.height <= 0 || bbox.x < 0 || bbox.y < 0 || bbox.x + bbox.width > 1 || bbox.y + bbox.height > 1) {
           throw new Error('无效的归一化坐标');
        }

        const payload: Record<string, unknown> = {
           bbox,
           filters,
           top_k: 10,
           coordinate_space: 'normalized'
        };
        payload[regionIdType] = regionId;

        const res = await fetchAPI<SearchResponse>('/api/v1/search/region', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal,
          schema: SearchResponseSchema
        });
        if (!controller.signal.aborted) setData(res);
      }
    } catch (err: unknown) {
      if (isAbortError(err)) return;
      if (!controller.signal.aborted) {
        setError(toAPIError(err, '检索失败'));
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">跨文献关联检索</h2>
        <div className="mb-4">
          <label htmlFor="corpus-filter" className="text-sm mr-2">检索数据</label>
          <select id="corpus-filter" className="border rounded p-2 text-sm" value={corpus}
            onChange={e => { abortRef.current?.abort(); setCorpus(e.target.value); setData(null); setError(null); setLoading(false); }}>
            <option value="all">全部数据</option>
            <option value="ai_assisted_real_pilot">真实古籍 · AI 辅助比赛版</option>
            <option value="synthetic_fixture">合成工程示例</option>
            <option value="human_reviewed_real_pilot">已独立审核的图题与范围</option>
          </select>
          <p className="text-xs text-gray-500 mt-2">比赛版暂不人工审核；AI 场景描述与原始 OCR 均保留待核实标记，检索分数用于候选排序。</p>
        </div>
        <div className="flex space-x-2 sm:space-x-4 mb-4" role="tablist">
          {capabilities.search_types.includes('text') && (
            <button role="tab" aria-selected={mode === 'text'} onClick={() => handleModeChange('text')} className={`px-4 py-2 rounded-md ${mode === 'text' ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-gray-100 text-gray-700'}`}>文本</button>
          )}
          {capabilities.search_types.includes('image') && (
            <button role="tab" aria-selected={mode === 'image'} onClick={() => handleModeChange('image')} className={`px-4 py-2 rounded-md ${mode === 'image' ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-gray-100 text-gray-700'}`}>图片</button>
          )}
          {capabilities.search_types.includes('region') && (
            <button role="tab" aria-selected={mode === 'region'} onClick={() => handleModeChange('region')} className={`px-4 py-2 rounded-md ${mode === 'region' ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-gray-100 text-gray-700'}`}>区域</button>
          )}
        </div>

        {mode === 'text' && (
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
            <label className="sr-only" htmlFor="text-search">检索词</label>
            <input id="text-search" type="text" value={query} onChange={(e) => setQuery(e.target.value)} disabled={loading} className="flex-1 rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-blue-500" placeholder="例如：水轮提水灌溉" />
            <button type="submit" disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50">
              {loading ? '搜索中...' : '搜索'}
            </button>
          </form>
        )}

        {mode === 'image' && (
          <form onSubmit={handleSearch} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="image-upload">上传检索图 (最大 {Math.floor(capabilities.upload_limits.max_upload_bytes / 1024 / 1024)}MB)</label>
              <input id="image-upload" type="file" accept="image/*" onChange={(e) => {
                 const f = e.target.files?.[0] || null;
                 setFile(f);
              }} disabled={loading} className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
            </div>
            <button type="submit" disabled={loading || !file} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 self-start">
              {loading ? '搜索中...' : '图片检索'}
            </button>
          </form>
        )}

        {mode === 'region' && (
          <form onSubmit={handleSearch} className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-2 items-center">
              <label htmlFor="region-id-type" className="sr-only">来源类型</label>
              <select id="region-id-type" value={regionIdType} onChange={(e) => setRegionIdType(e.target.value as 'figure_id'|'page_id')} className="rounded-md border-gray-300 border p-2 focus:border-blue-500">
                <option value="figure_id">Figure ID</option>
                <option value="page_id">Page ID</option>
              </select>
              <label htmlFor="region-id-val" className="sr-only">UUID</label>
              <input id="region-id-val" type="text" value={regionId} onChange={(e) => setRegionId(e.target.value)} placeholder={`输入UUID...`} className="flex-1 rounded-md border-gray-300 border p-2 w-full" />
            </div>
            <fieldset className="grid grid-cols-4 gap-2">
               <legend className="text-sm font-medium text-gray-700 mb-1">归一化坐标 (0-1)</legend>
               <div><label htmlFor="bbox-x" className="text-xs block">X</label><input id="bbox-x" type="number" step="any" value={bbox.x} onChange={e => setBbox({...bbox, x: parseFloat(e.target.value)})} className="w-full border p-1 rounded" /></div>
               <div><label htmlFor="bbox-y" className="text-xs block">Y</label><input id="bbox-y" type="number" step="any" value={bbox.y} onChange={e => setBbox({...bbox, y: parseFloat(e.target.value)})} className="w-full border p-1 rounded" /></div>
               <div><label htmlFor="bbox-w" className="text-xs block">Width</label><input id="bbox-w" type="number" step="any" value={bbox.width} onChange={e => setBbox({...bbox, width: parseFloat(e.target.value)})} className="w-full border p-1 rounded" /></div>
               <div><label htmlFor="bbox-h" className="text-xs block">Height</label><input id="bbox-h" type="number" step="any" value={bbox.height} onChange={e => setBbox({...bbox, height: parseFloat(e.target.value)})} className="w-full border p-1 rounded" /></div>
            </fieldset>
            <button type="submit" disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 self-start">
              {loading ? '搜索中...' : '区域检索'}
            </button>
          </form>
        )}
      </div>

      <div aria-live="polite">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md mt-4" role="alert">
            <p className="font-bold">错误 [{error.code}]</p>
            <p>{error.message}</p>
            {error.request_id && <p className="text-sm mt-1 text-red-500">Request ID: {error.request_id}</p>}
          </div>
        )}
      </div>

      {!loading && !error && data && data.results.length === 0 && (
        <div className="text-center py-12 bg-white shadow rounded-lg text-gray-500 mt-4">
          没有找到满足当前条件的候选，请尝试修改查询或过滤条件。
        </div>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-4 mt-4">
          <div className="text-sm text-gray-500">
            耗时: {data.latency_ms}ms
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.results.map((result) => (
              <div key={result.candidate_id} className="bg-white shadow rounded-lg overflow-hidden border border-gray-200 flex flex-col">
                <div className="h-48 bg-gray-100 relative">
                  {!result.image_ref ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400 p-4 text-center">无可用图像</div>
                  ) : result.image_ref.allow_redistribution ? (
                    <img src={result.image_ref.url} alt={`Candidate ${result.candidate_id}`} loading="lazy" decoding="async" className="w-full h-full object-contain" />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400 p-4 text-center">
                      <span>图片受限</span>
                      <span className="text-xs">{result.image_ref.license_status}</span>
                    </div>
                  )}
                </div>
                <div className="p-4 flex-1 flex flex-col">
                  <h3 className="font-medium text-gray-900 mb-2" title={result.title || result.candidate_id}>{result.title || `候选关联: ${result.candidate_id}`}</h3>
                  <p className="text-xs text-gray-600">{result.source.book_title} · {result.source.page_or_folio}</p>
                  <p className="text-xs text-gray-500">{result.source.source_name}</p>
                  <DataStatusNotice status={result.data_status} />
                  <div className="text-xs text-gray-500 mb-2">
                    <span className="block mb-1">缺失模态: {result.score_components.missing_modalities?.length > 0 ? result.score_components.missing_modalities.join(', ') : '无'}</span>
                    <div className="grid grid-cols-4 gap-1">
                      {SCORE_COMPONENT_KEYS.map(key => {
                        const val = result.score_components[key];
                        return (
                          <span key={key} className="bg-gray-100 px-1 py-0.5 rounded truncate" title={key}>
                             {key}: {typeof val === 'number' ? val.toFixed(2) : 'N/A'}
                          </span>
                        );
                      })}
                    </div>

                    <div className="mt-2 text-xs text-gray-400 truncate border-t pt-1">
                      <span className="mr-2" title="availability">A:{Object.keys(result.score_components.availability || {}).join(',')}</span>
                      <span className="mr-2" title="reliability">R:{Object.keys(result.score_components.reliability || {}).join(',')}</span>
                      <span className="mr-2" title="weights">W:{Object.keys(result.score_components.weights || {}).join(',')}</span>
                      <span title="contributions">C:{Object.keys(result.score_components.contributions || {}).join(',')}</span>
                    </div>
                  </div>
                  <div className="mt-auto pt-4 flex justify-between items-center">
                    <span className="text-xs font-medium px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                      {result.verification_state}
                    </span>
                    <button onClick={() => navigate(`/compare/${result.candidate_id}`)} className="text-sm text-blue-600 hover:text-blue-800 font-medium">对照与核验 &rarr;</button>
                  </div>
                  <button onClick={() => navigate(`/figures/${result.figure_id}`)} className="text-sm text-blue-600 text-left mt-2">查看原图与文本 &rarr;</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
