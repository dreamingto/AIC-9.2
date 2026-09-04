import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { fetchAPI, APIError } from '../api/client';
import { FigureResponseSchema } from '../types';
import type { FigureResponse } from '../types';

export default function FigurePage() {
  const { figureId } = useParams();
  const [data, setData] = useState<FigureResponse | null>(null);
  const [error, setError] = useState<APIError | null>(null);
  const [loading, setLoading] = useState(true);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();

    if (!figureId) {
      // eslint-disable-next-line react/set-state-in-effect
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    // eslint-disable-next-line react/set-state-in-effect
    setData(null);
    // eslint-disable-next-line react/set-state-in-effect
    setError(null);
    // eslint-disable-next-line react/set-state-in-effect
    setLoading(true);

    fetchAPI<FigureResponse>(`/api/v1/figures/${figureId}`, {
      signal: controller.signal,
      schema: FigureResponseSchema
    })
      .then(res => {
         if (!controller.signal.aborted) setData(res);
      })
      .catch(err => {
        if (!controller.signal.aborted) setError(err);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [figureId]);

  if (loading) return <div aria-live="polite">加载中...</div>;
  if (error) return <div className="text-red-600">加载错误: {error.message}</div>;
  if (!data) return null;

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">技术图详情：{data.title || data.id}</h2>
      <p className="text-sm text-gray-500 mb-4">来源 Page ID: {data.page_id}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 flex flex-col items-center justify-center relative min-h-[24rem]">
          {!data.asset ? (
            <span className="text-gray-500">无图片资料</span>
          ) : data.asset.allow_redistribution ? (
            <img src={data.asset.url} alt="Figure" className="w-full h-full object-contain" />
          ) : (
            <div className="text-center">
              <span className="text-gray-500 block">图片受限</span>
              <span className="text-xs text-gray-400">{data.asset.license_status}</span>
            </div>
          )}
          {data.bbox && (
            <div className="mt-4 text-xs text-gray-400 text-center">
              归一化坐标: x={data.bbox.x}, y={data.bbox.y}, w={data.bbox.width}, h={data.bbox.height}
            </div>
          )}
        </div>
        <div className="space-y-4 max-h-[80vh] overflow-y-auto">
          <div>
            <h3 className="font-medium text-gray-900 border-b pb-2">图题与文本 (Text)</h3>
            <ul className="mt-2 text-sm text-gray-600 list-disc pl-5">
              {data.text_chunks.length === 0 && <li>无文本</li>}
              {data.text_chunks.map((txt) => <li key={txt.id}>{txt.corrected_text ?? txt.text}</li>)}
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 border-b pb-2">局部区域 (Regions)</h3>
            <ul className="mt-2 text-sm text-gray-600 space-y-1">
              {data.regions.length === 0 && <li>无局部区域</li>}
              {data.regions.map(r => (
                <li key={r.id}>
                  {r.label || r.id} <span className="text-xs text-gray-400">({r.width.toFixed(2)}x{r.height.toFixed(2)})</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 border-b pb-2">功能槽推断 (CFR Assertions)</h3>
            <ul className="mt-2 text-sm text-gray-600 space-y-1">
              {data.assertions.length === 0 && <li>无推断槽</li>}
              {data.assertions.map(a => (
                <li key={a.id}>
                  <span className="font-medium">{a.slot}:</span> {a.concept}{' '}
                  <span className="text-xs text-blue-600 border border-blue-200 px-1 rounded">{a.state}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 border-b pb-2">关联网络 (Relations)</h3>
            <ul className="mt-2 text-sm text-gray-600 space-y-1">
              {data.relations.length === 0 && <li>无关联网络</li>}
              {data.relations.map((rel) => (
                <li key={rel.id}>
                  {rel.subject} <span className="text-blue-500 font-medium">{rel.predicate}</span> {rel.object}
                  <span className="text-xs text-gray-400 ml-2">(wt: {rel.weight}, conf: {rel.confidence})</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
             <h3 className="font-medium text-gray-900 border-b pb-2">证据记录 (Evidences)</h3>
             <ul className="mt-2 text-sm text-gray-600 space-y-1">
              {data.evidences.length === 0 && <li>无明确证据记录</li>}
              {data.evidences.map(e => (
                <li key={e.id}>
                  <span className="text-xs border px-1 rounded text-gray-600">{e.status}</span> {e.content}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
