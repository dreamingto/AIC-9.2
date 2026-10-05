import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { DemoCasesSchema, SearchResponseSchema } from '../types';
import type { CapabilitiesResponse, DemoCase, SearchResponse } from '../types';
import { fetchAPI, getErrorMessage, isAbortError } from '../api/client';
import DataStatusNotice from '../components/DataStatusNotice';

const MODEL_ROLES: Record<string, string> = {
  bge_zh: '中文文本语义', chinese_clip_image: '视觉与局部', chinese_clip_text: '中文图文语义',
  deterministic_text_embedding: '离线文本基线', deterministic_image_embedding: '离线视觉基线',
};

export default function DemoPage({ capabilities }: { capabilities: CapabilitiesResponse }) {
  const [cases, setCases] = useState<DemoCase[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState('');
  const [result, setResult] = useState<SearchResponse | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchAPI('/api/v1/demo/cases', { schema: DemoCasesSchema, signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setCases(data); })
      .catch(err => { if (!controller.signal.aborted) setError(getErrorMessage(err, '案例加载失败')); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); controllerRef.current?.abort(); };
  }, []);

  async function run(caseId: string, mode: 'text' | 'region') {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setActive(`${caseId}:${mode}`); setResult(null); setError('');
    try {
      const response = await fetchAPI(`/api/v1/demo/cases/${caseId}/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }), signal: controller.signal, schema: SearchResponseSchema,
      });
      if (!controller.signal.aborted) setResult(response);
    } catch (err) {
      if (!controller.signal.aborted && !isAbortError(err)) setError(getErrorMessage(err, '检索失败'));
    } finally {
      if (!controller.signal.aborted) setActive('');
    }
  }

  return <div className="space-y-6">
    <div>
      <h1 className="text-2xl font-bold">国内古籍固定演示案例</h1>
      <p className="text-gray-600 mt-2">固定查询、真实数据库检索与可追溯扫描。AI 整理暂不人工审核，研究指标未评测。</p>
    </div>
    <div className="bg-white p-4 rounded border text-sm" aria-label="当前检索模型">
      <h2 className="font-semibold">当前检索模型</h2>
      {capabilities.providers.filter(p => p.provider in MODEL_ROLES).map(p =>
        <p key={p.name} className="mt-1 break-all">{MODEL_ROLES[p.provider]}：{p.model} · {p.dimension} 维 · {p.available ? '可用' : '不可用'} · {p.version.slice(0, 12)}</p>)}
    </div>
    {loading && <p role="status">正在读取案例来源…</p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {cases.map(item => <article key={item.id} className="bg-white rounded border p-5 space-y-4">
        <h2 className="text-xl font-semibold">{item.title}</h2>
        <p>{item.description}</p><p className="text-sm text-gray-600">{item.source_note}</p>
        {!item.ready && <p role="status">该案例扫描尚未导入，请先准备国内古籍语料。</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {item.figures.map(figure => <div key={figure.id}>
            {figure.asset?.allow_redistribution && <div className="relative">
              <img src={figure.asset.url} alt={figure.title ?? '古籍扫描'} className="w-full border" />
              {figure.bbox && <div aria-label="AI 建议图区" className="absolute border-2 border-blue-500 pointer-events-none" style={{
                left: `${figure.bbox.x * 100}%`, top: `${figure.bbox.y * 100}%`,
                width: `${figure.bbox.width * 100}%`, height: `${figure.bbox.height * 100}%`,
              }} />}
              {figure.id === item.region_query?.figure_id && <div aria-label="固定区域查询框" className="absolute border-2 border-orange-500 pointer-events-none" style={{
                left: `${item.region_query.bbox.x * 100}%`, top: `${item.region_query.bbox.y * 100}%`,
                width: `${item.region_query.bbox.width * 100}%`, height: `${item.region_query.bbox.height * 100}%`,
              }} />}
            </div>}
            <Link to={`/figures/${figure.id}`} className="text-blue-700 underline block mt-2">{figure.title}</Link>
            <p className="text-xs text-gray-600">PDF 页码 / 页叶：{figure.source?.page_or_folio}</p>
            <DataStatusNotice status={figure.data_status} />
          </div>)}
        </div>
        <p className="text-sm">固定文本查询：{item.text_query}；蓝框为 AI 建议图区，橙框为固定区域查询，检索时排除来源图本身。</p>
        <div className="flex flex-wrap gap-3">
          <button className="bg-blue-700 text-white px-3 py-2 rounded disabled:opacity-50" disabled={!item.ready || !capabilities.search_types.includes('text')}
            onClick={() => run(item.id, 'text')}>运行文本检索</button>
          <button className="border border-blue-700 text-blue-700 px-3 py-2 rounded disabled:opacity-50" disabled={!item.ready || !capabilities.search_types.includes('region')}
            onClick={() => run(item.id, 'region')}>运行区域检索</button>
        </div>
        {item.limitations.map(note => <p key={note} className="text-xs text-amber-800">{note}</p>)}
      </article>)}
    </div>
    {active && <p role="status" aria-live="polite">正在运行 {active.endsWith('text') ? '文本' : '区域'} 检索…</p>}
    {result && <section className="bg-white rounded border p-5 space-y-3" aria-label="真实检索结果">
      <h2 className="text-xl font-semibold">实时检索结果</h2>
      <p className="text-sm">耗时 {result.latency_ms.toFixed(0)} ms · 会话 {result.search_id} · 按真实分数排序，固定图对不保证名次。</p>
      {!result.results.length && <p>当前查询没有候选。</p>}
      <ol className="space-y-3">{result.results.map((r, index) => <li key={r.candidate_id} className="border-t pt-3">
        <p>{index + 1}. {r.title} · {r.score.toFixed(4)}</p>
        <p className="text-xs text-gray-600">视觉 {r.score_components.sv?.toFixed(4) ?? '缺失'} · 文本 {r.score_components.st?.toFixed(4) ?? '缺失'} · 局部 {r.score_components.sr?.toFixed(4) ?? '缺失'} · 状态 {r.verification_state}</p>
        <Link className="text-blue-700 underline mr-4" to={`/figures/${r.figure_id}`}>查看扫描与文本</Link>
        <Link className="text-blue-700 underline" to={`/compare/${r.candidate_id}`}>查看候选与证据</Link>
      </li>)}</ol>
    </section>}
  </div>;
}
