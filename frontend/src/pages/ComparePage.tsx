import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchAPI, APIError, toAPIError } from '../api/client';
import { CandidateResponseSchema, SearchResponseSchema, VerificationResponseSchema } from '../types';
import type { CandidateResponse, CapabilitiesResponse, SearchResponse, VerificationState } from '../types';

const SCORE_COMPONENT_KEYS = ['sv', 'st', 'sr', 'sf', 'sg', 'se', 'u_model'] as const;

export default function ComparePage({ capabilities }: { capabilities: CapabilitiesResponse }) {
  const { candidateId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<CandidateResponse | null>(null);
  const [searchData, setSearchData] = useState<SearchResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError] = useState<APIError | null>(null);
  const [note, setNote] = useState('');

  const abortRef = useRef<AbortController | null>(null);
  const verifyAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    if (verifyAbortRef.current) verifyAbortRef.current.abort();

    if (!candidateId) return;

    const controller = new AbortController();
    abortRef.current = controller;

    // eslint-disable-next-line react/set-state-in-effect
    setData(null);
    // eslint-disable-next-line react/set-state-in-effect
    setSearchData(null);
    // eslint-disable-next-line react/set-state-in-effect
    setError(null);
    // eslint-disable-next-line react/set-state-in-effect
    setStatusMsg('');
    // eslint-disable-next-line react/set-state-in-effect
    setNote('');
    // eslint-disable-next-line react/set-state-in-effect
    setSubmitting(false);

    fetchAPI<CandidateResponse>(`/api/v1/associations/${candidateId}`, {
       signal: controller.signal,
       schema: CandidateResponseSchema
    })
      .then(res => {
         if (!controller.signal.aborted && candidateId === res.candidate_id) {
           setData(res);
           return fetchAPI<SearchResponse>(`/api/v1/search/${res.search_id}`, {
              signal: controller.signal,
              schema: SearchResponseSchema
           });
         }
      })
      .then(searchRes => {
         if (searchRes && !controller.signal.aborted) {
           setSearchData(searchRes);
         }
      })
      .catch((err: unknown) => {
         if (!controller.signal.aborted) setError(toAPIError(err, '加载候选关联失败'));
      });

    return () => {
       controller.abort();
       if (verifyAbortRef.current) verifyAbortRef.current.abort();
    }
  }, [candidateId]);

  const handleVerify = async (state: VerificationState) => {
    if (verifyAbortRef.current) verifyAbortRef.current.abort();
    const controller = new AbortController();
    verifyAbortRef.current = controller;

    setSubmitting(true);
    setStatusMsg('');
    setError(null);
    try {
      await fetchAPI(`/api/v1/associations/${candidateId}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state, note: note.trim() || undefined }),
        signal: controller.signal,
        schema: VerificationResponseSchema
      });

      if (!controller.signal.aborted) {
         setStatusMsg(`已更新核验状态为: ${state}`);
         const res = await fetchAPI<CandidateResponse>(`/api/v1/associations/${candidateId}`, {
            signal: controller.signal,
            schema: CandidateResponseSchema
         });
         if (!controller.signal.aborted && candidateId === res.candidate_id) setData(res);
      }
    } catch (err: unknown) {
      if (!controller.signal.aborted) {
         setError(toAPIError(err, '提交核验失败'));
      }
    } finally {
      if (!controller.signal.aborted) setSubmitting(false);
    }
  };

  if (error && !data) return <div className="text-red-500 p-4">加载错误: {error.message}</div>;
  if (!data) return <div className="p-4" aria-live="polite">加载中...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold truncate">候选对照：{candidateId}</h2>
        <button onClick={() => navigate(-1)} className="text-sm text-gray-500 hover:text-gray-900">&larr; 返回</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-4">
           <h3 className="font-medium mb-4 text-center">查询背景 (Search ID: {data.search_id})</h3>
           <div className="text-sm text-gray-600 bg-gray-50 p-4 rounded min-h-[16rem]">
             {!searchData ? (
                <p>查询详情加载中...</p>
             ) : (
                <>
                  <p className="mb-2"><span className="font-semibold">查询方式：</span> {searchData.query_summary.type}</p>

                  {searchData.query_summary.type === 'text' && (
                    <p><span className="font-semibold">检索词：</span> {searchData.query_summary.query}</p>
                  )}
                  {searchData.query_summary.type === 'region' && (
                    <div>
                      <p><span className="font-semibold">来源页面/图片ID：</span> {searchData.query_summary.source_figure_id}</p>
                      <p><span className="font-semibold">坐标空间：</span> V1 固定为 normalized (接口约定)</p>
                      <p><span className="font-semibold">框选区域：</span> {JSON.stringify(searchData.query_summary.bbox)}</p>
                    </div>
                  )}
                  {searchData.query_summary.type === 'image' && (
                    <div>
                       <p><span className="font-semibold">上传图片：</span> 原始图片无法恢复预览，文件属性：</p>
                       <p>文件名: {searchData.query_summary.filename ?? '未提供'}</p>
                       <p>MIME: {searchData.query_summary.mime_type}</p>
                       <p>字节大小: {searchData.query_summary.byte_size}</p>
                    </div>
                  )}
                </>
             )}
           </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
           <h3 className="font-medium mb-4 text-center">候选图详情 (Figure ID: {data.figure_id})</h3>
           <div className="h-64 bg-gray-50 flex items-center justify-center border">
              {!data.image_ref ? (
                <span className="text-gray-400">无可用图像</span>
              ) : data.image_ref.allow_redistribution ? (
                <img src={data.image_ref.url} alt="Candidate" className="max-h-full object-contain" />
              ) : (
                <div className="text-center">
                  <span className="text-gray-500 block">图片受限</span>
                  <span className="text-xs text-gray-400">{data.image_ref.license_status}</span>
                </div>
              )}
           </div>
           <p className="text-xs text-gray-500 mt-2">来源: {data.source.book_title} - {data.source.edition} (页/叶: {data.source.page_or_folio})</p>
           {data.source.source_url && <a href={data.source.source_url} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:underline">查看外部资料源</a>}
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-4 space-y-6">
        <div>
           <h3 className="font-medium mb-2 border-b">匹配得分与组件贡献 (Score: {data.score.toFixed(2)})</h3>
           <p className="text-xs text-gray-500 mb-2">缺失模态: {data.score_components.missing_modalities?.join(', ') || '无'}</p>
           <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-600">
             <div>
               <p className="font-medium">基础分值:</p>
               {SCORE_COMPONENT_KEYS.map(key => {
                  const val = data.score_components[key];
                  return <div key={key}>{key}: {typeof val === 'number' ? val.toFixed(2) : 'N/A'}</div>;
               })}
             </div>
             <div>
               <p className="font-medium">可用性 (Availability):</p>
               {Object.entries(data.score_components.availability || {}).map(([k, v]) => (
                 <div key={k}>{k}: {v ? '是' : '否'}</div>
               ))}
             </div>
             <div>
               <p className="font-medium">可靠性 & 权重 (Reliability/Weights):</p>
               {Object.entries(data.score_components.reliability || {}).map(([k, v]) => (
                 <div key={k}>{k} 可靠性: {v.toFixed(2)}</div>
               ))}
               {Object.entries(data.score_components.weights || {}).map(([k, v]) => (
                 <div key={k}>{k} 权重: {v.toFixed(2)}</div>
               ))}
             </div>
             <div>
               <p className="font-medium">贡献值 (Contributions):</p>
               {Object.entries(data.score_components.contributions || {}).map(([k, v]) => (
                 <div key={k}>{k}: {v.toFixed(2)}</div>
               ))}
             </div>
           </div>
           {data.matched_regions.length > 0 && (
             <div className="mt-2 text-xs">
               <span className="font-medium">匹配区域: </span>
               {data.matched_regions.map(r => r.label || r.id).join(', ')}
             </div>
           )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
           <div>
              <h3 className="font-medium mb-2 border-b">功能槽推断 (CFR)</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                 {data.cfr_summary.assertions.length === 0 && <li>无相关推断</li>}
                 {data.cfr_summary.assertions.map(a => (
                   <li key={a.id}>{a.slot}: {a.concept} <span className="text-xs bg-gray-100 rounded px-1">{a.state}</span></li>
                 ))}
              </ul>
              <p className="text-xs mt-1 text-gray-400">推断不确定度: {data.cfr_summary.uncertainty.toFixed(2)} | 全局不确定度: {JSON.stringify(data.uncertainty)}</p>
           </div>
           <div>
              <h3 className="font-medium mb-2 border-b">证据记录 (Evidence)</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                 {data.evidence.length === 0 && <li>无充足证据</li>}
                 {data.evidence.map(e => (
                   <li key={e.id}><span className="text-xs border rounded px-1">{e.status}</span> {e.content}</li>
                 ))}
              </ul>
           </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6 border-t-4 border-blue-500">
        <h3 className="font-medium mb-4">人工核验操作 (Manual Verification)</h3>
        <p className="text-sm text-gray-500 mb-4">当前状态：<span className="font-medium text-gray-900">{data.verification_state}</span>。请注意，核验对象仅为“候选关联”，不作为历史事实成立的自动证明。</p>

        {error && <div className="mb-4 text-red-600 text-sm">{error.message}</div>}

        <div className="mb-4">
           <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="verification-note">核验备注 (可选)</label>
           <textarea
              id="verification-note"
              className="w-full border-gray-300 border rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
              rows={3}
              maxLength={2000}
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="请输入核验依据或疑问..."
           ></textarea>
        </div>

        <div className="flex flex-wrap gap-3">
          {capabilities.verification_states.map(state => (
            <button
              key={state}
              disabled={submitting || !searchData}
              onClick={() => handleVerify(state)}
              className="px-4 py-2 bg-gray-50 text-gray-700 rounded border border-gray-200 hover:bg-gray-100 disabled:opacity-50"
            >
              提交 {state}
            </button>
          ))}
        </div>
        {statusMsg && <p className="mt-4 text-sm font-medium text-green-700" aria-live="polite">{statusMsg}</p>}
      </div>
    </div>
  );
}
