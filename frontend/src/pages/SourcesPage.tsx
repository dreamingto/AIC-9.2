import { useState, useEffect } from 'react';
import { fetchAPI, getErrorMessage } from '../api/client';
import { BookSummarySchema, EditionSummarySchema } from '../types';
import type { BookSummary, EditionSummary } from '../types';
import { z } from 'zod';

export default function SourcesPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [booksWithEditions, setBooksWithEditions] = useState<{book: BookSummary, editions: EditionSummary[]}[]>([]);
  const [partialFailure, setPartialFailure] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchSources() {
      setError('');
      setPartialFailure(false);
      try {
        const books = await fetchAPI<BookSummary[]>('/api/v1/books', {
           signal: controller.signal,
           schema: z.array(BookSummarySchema)
        });

        const results = await Promise.allSettled(
          books.map(async (book) => {
             const editions = await fetchAPI<EditionSummary[]>(`/api/v1/books/${book.id}/editions`, {
                signal: controller.signal,
                schema: z.array(EditionSummarySchema)
             });
             return { book, editions };
          })
        );

        if (controller.signal.aborted) return;

        const validResults = results
           .filter((res): res is PromiseFulfilledResult<{book: BookSummary, editions: EditionSummary[]}> => res.status === 'fulfilled')
           .map(res => res.value);

        setBooksWithEditions(validResults);

        if (validResults.length < books.length && books.length > 0) {
           if (validResults.length === 0) {
              setError('所有版本的加载都失败了，请稍后重试。');
           } else {
              setPartialFailure(true);
           }
        }
      } catch (err: unknown) {
        if (!controller.signal.aborted) {
          setError(getErrorMessage(err, '获取文献来源错误'));
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    fetchSources();
    return () => controller.abort();
  }, []);

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">文献来源 (Sources)</h2>
      <p className="text-sm text-gray-500 mb-6">受限于许可展示（LICENSE_RESTRICTED），本系统仅展示公开可用的古籍信息。</p>

      {loading && <p aria-live="polite">加载中...</p>}
      {error && <p className="text-red-500" role="alert">{error}</p>}
      {partialFailure && <p className="text-yellow-600 bg-yellow-50 p-2 rounded mb-4" role="alert">提示：部分书籍版本加载失败，当前展示为不完整数据 (Partial data)。</p>}

      {!loading && booksWithEditions.length === 0 && !error && (
         <p className="text-gray-500">暂无文献来源数据</p>
      )}

      {!loading && booksWithEditions.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">书名 (Book)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">作者/时代</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">版本 (Edition Name)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">许可 (License)</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {booksWithEditions.map(({ book, editions }) => (
                editions.map(ed => (
                  <tr key={`${book.id}-${ed.id}`}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{book.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{book.author || '未知'} ({book.era || '未知'})</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{ed.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${ed.allow_redistribution ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                        {ed.allow_redistribution ? '允许再分发 ' : '禁止再分发 '}
                        ({ed.license_status === 'synthetic_fixture' ? '工程数据' : ed.license_status})
                      </span>
                    </td>
                  </tr>
                ))
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
