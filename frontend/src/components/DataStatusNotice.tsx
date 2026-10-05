import type { DataStatus } from '../types';

export default function DataStatusNotice({ status }: { status?: DataStatus }) {
  if (!status || status.dataset_kind === 'unclassified') return null;
  const category = status.source_category === 'domestic_publication'
    ? '国内出版来源'
    : status.source_category === 'domestic_holding' ? '国内馆藏来源' : '来源记录';
  if (status.review_origin === 'ai_assisted') {
    return <p className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded p-2 my-2">
      {category} · AI 辅助整理 · 暂不人工审核 · 未评测。场景名、转录与功能描述均为待核实建议。
    </p>;
  }
  if (status.review_origin === 'synthetic_fixture') {
    return <p className="text-xs text-gray-600 bg-gray-100 rounded p-2 my-2">合成工程示例 · 未评测</p>;
  }
  return <p className="text-xs text-gray-600 my-2">已审核图题及范围 · 历史关联仍需独立核实 · 未评测</p>;
}
