import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { QuerySummarySchema } from '../types';
import App from '../App';
import SearchPage from './SearchPage';
import FigurePage from './FigurePage';
import ComparePage from './ComparePage';
import SourcesPage from './SourcesPage';
import { mockCapabilities, server } from '../setupTests';
import { http, HttpResponse } from 'msw';

// Mock matchMedia for jsdom
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('Comprehensive Frontend Scenarios', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('1. App fetches capabilities', async () => {
    render(<App />);
    expect(await screen.findByText(/机图索隐/i)).toBeInTheDocument();
    expect(await screen.findByText(/可用/i)).toBeInTheDocument();
  });

  it('2. SearchPage: image multipart form data pure test via spy', async () => {
    render(<MemoryRouter><SearchPage capabilities={mockCapabilities} /></MemoryRouter>);
    fireEvent.click(screen.getByRole('tab', { name: /图片/i }));

    const file = new File(['123'], 'test.png', { type: 'image/png' });
    Object.defineProperty(file, 'size', { value: 100 });

    const originalImage = window.Image;
    // @ts-expect-error Mocking Image for jsdom
    window.Image = class {
       onload: () => void = () => {};
       src: string = '';
       width: number = 10;
       height: number = 10;
       constructor() { setTimeout(() => { if (this.onload) this.onload(); }, 5); }
    };

    const fetchSpy = vi.spyOn(window, 'fetch');

    const input = screen.getByLabelText(/上传检索图/i);
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /图片检索/i }));

    await waitFor(() => {
       const calls = fetchSpy.mock.calls.filter(c => c[0].toString().includes('/api/v1/search/image'));
       expect(calls.length).toBeGreaterThan(0);
    });

    const imageCall = fetchSpy.mock.calls.find(c => c[0].toString().includes('/api/v1/search/image'))!;
    const body = imageCall[1]!.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('file')).toBeTruthy();
    expect(body.get('top_k')).toBe('10');
    expect(body.get('filters')).toBeTruthy();

    fetchSpy.mockRestore();
    window.Image = originalImage;
  });

  it('3. SearchPage: image pixel and byte limits prevent network', async () => {
    const fetchSpy = vi.spyOn(window, 'fetch');
    render(<MemoryRouter><SearchPage capabilities={mockCapabilities} /></MemoryRouter>);
    fireEvent.click(screen.getByRole('tab', { name: /图片/i }));

    // 1. Byte limit
    const largeFile = new File([''], 'test.png', { type: 'image/png' });
    Object.defineProperty(largeFile, 'size', { value: 999999999 });
    const input = screen.getByLabelText(/上传检索图/i);
    fireEvent.change(input, { target: { files: [largeFile] } });
    fireEvent.click(screen.getByRole('button', { name: /图片检索/i }));
    expect(await screen.findByText(/图片大小不能超过/i)).toBeInTheDocument();

    // 2. Pixel limit
    const normalFile = new File([''], 'test2.png', { type: 'image/png' });
    Object.defineProperty(normalFile, 'size', { value: 100 });
    const originalImage = window.Image;
    // @ts-expect-error
    window.Image = class {
       onload: () => void = () => {};
       src: string = '';
       width: number = 3000;
       height: number = 3000;
       constructor() { setTimeout(() => { if (this.onload) this.onload(); }, 5); }
    };
    fireEvent.change(input, { target: { files: [normalFile] } });
    fireEvent.click(screen.getByRole('button', { name: /图片检索/i }));
    expect(await screen.findByText(/图片像素数超过上限/i)).toBeInTheDocument();

    const imageCalls = fetchSpy.mock.calls.filter(c => c[0].toString().includes('/api/v1/search/image'));
    expect(imageCalls.length).toBe(0); // No network calls should be made

    fetchSpy.mockRestore();
    window.Image = originalImage;
  });

  it('4. SearchPage: Race condition switching mode', async () => {
    render(<MemoryRouter><SearchPage capabilities={mockCapabilities} /></MemoryRouter>);
    fireEvent.click(screen.getByRole('tab', { name: /文本/i }));
    fireEvent.change(screen.getByPlaceholderText(/例如/i), { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: /搜索/i }));

    fireEvent.click(screen.getByRole('tab', { name: /图片/i }));
    await new Promise(r => setTimeout(r, 150));

    expect(screen.queryByText(/候选关联/i)).not.toBeInTheDocument();
  });

  it('5. FigurePage: real slow -> fast route switch', async () => {
    const TestComponent = () => {
       const nav = useNavigate();
       return (
          <div>
            <button onClick={() => nav('/figures/123e4567-e89b-12d3-a456-426614174088')}>Load Slow</button>
            <button onClick={() => nav('/figures/123e4567-e89b-12d3-a456-426614174099')}>Load Fast</button>
            <Routes><Route path="/figures/:figureId" element={<FigurePage />} /></Routes>
          </div>
       );
    };

    server.use(
       http.get('/api/v1/figures/123e4567-e89b-12d3-a456-426614174088', async () => {
          await new Promise(r => setTimeout(r, 200));
          return HttpResponse.json({
            id: '123e4567-e89b-12d3-a456-426614174088', title: 'Figure A', page_id: '123e4567-e89b-12d3-a456-426614174003',
            asset: null, bbox: null, regions: [], text_chunks: [], assertions: [], relations: [], evidences: []
          });
       }),
       http.get('/api/v1/figures/123e4567-e89b-12d3-a456-426614174099', () => {
          return HttpResponse.json({
            id: '123e4567-e89b-12d3-a456-426614174099', title: 'Fast Fig', page_id: '123e4567-e89b-12d3-a456-426614174003',
            asset: null, bbox: null, regions: [], text_chunks: [], assertions: [], relations: [], evidences: []
          });
       })
    );

    render(<MemoryRouter><TestComponent /></MemoryRouter>);
    fireEvent.click(screen.getByText('Load Slow'));
    fireEvent.click(screen.getByText('Load Fast'));

    expect(await screen.findByText(/Fast Fig/i)).toBeInTheDocument();
    await new Promise(r => setTimeout(r, 250));
    expect(screen.queryByText(/Figure A/i)).not.toBeInTheDocument();
  });

  it('6. ComparePage: real verify race condition', async () => {
    let resolveVerifyA: () => void;
    const verifyPromise = new Promise<void>(res => { resolveVerifyA = res; });
    let capturedReq: Request | null = null;
    let capturedBody: any = null;

    server.use(
       http.post('/api/v1/associations/123e4567-e89b-12d3-a456-426614174009/verify', async ({ request }) => {
          capturedReq = request;
          capturedBody = await request.clone().json();
          await verifyPromise;
          return HttpResponse.json({
             id: '123e4567-e89b-12d3-a456-426614174099', candidate_id: '123e4567-e89b-12d3-a456-426614174009', state: 'verified', note: 'my note', created_at: '2023-01-01T00:00:00.000Z'
          });
       }),
       http.get('/api/v1/associations/123e4567-e89b-12d3-a456-426614174099', () => {
          return HttpResponse.json({
            search_id: '123e4567-e89b-12d3-a456-426614174000', created_at: '2023-01-01T00:00:00.000Z', candidate_id: '123e4567-e89b-12d3-a456-426614174099', figure_id: '123e4567-e89b-12d3-a456-426614174000',
            source: { book_title: 'FastBook', edition: 'Ed 1', source_name: null, volume: null, page_or_folio: '1', source_url: null, license_status: 'public' },
            image_ref: null, matched_regions: [], score: 0.8,
            score_components: { sv: 1, st: 1, sr: 1, sf: 1, sg: 1, se: 1, u_model: 1, availability: {}, reliability: {}, missing_modalities: [], weights: {}, contributions: {} },
            cfr_summary: { assertions: [], uncertainty: 0 }, evidence: [], uncertainty: {}, verification_state: 'pending'
          });
       })
    );

    const TestComponent = () => {
       const nav = useNavigate();
       return (
          <div>
            <button onClick={() => nav('/compare/123e4567-e89b-12d3-a456-426614174009')}>Load Slow C</button>
            <button onClick={() => nav('/compare/123e4567-e89b-12d3-a456-426614174099')}>Load Fast C</button>
            <Routes><Route path="/compare/:candidateId" element={<ComparePage capabilities={mockCapabilities} />} /></Routes>
          </div>
       );
    };

    render(<MemoryRouter><TestComponent /></MemoryRouter>);
    fireEvent.click(screen.getByText('Load Slow C'));

    await waitFor(() => {
       expect(screen.getByPlaceholderText(/请输入核验依据/i)).toBeInTheDocument();
    }, { timeout: 1000 });

    const textarea = screen.getByPlaceholderText(/请输入核验依据/i);
    fireEvent.change(textarea, { target: { value: 'my note' } });
    fireEvent.click(screen.getByRole('button', { name: /提交 verified/i }));

    // While verify A is pending, navigate to B
    fireEvent.click(screen.getByText('Load Fast C'));
    expect(await screen.findByText(/FastBook/i)).toBeInTheDocument();

    // Release verify A
    resolveVerifyA!();
    await new Promise(r => setTimeout(r, 50));

    // Fast candidate UI should remain clean
    const fastTextarea = screen.getByPlaceholderText(/请输入核验依据/i) as HTMLTextAreaElement;
    expect(fastTextarea.value).toBe('');
    expect(screen.queryByText(/已更新核验状态/i)).not.toBeInTheDocument();

    // Assert request A payload
    expect(capturedReq).not.toBeNull();
    expect(capturedBody.state).toBe('verified');
    expect(capturedBody.note).toBe('my note');
  });

  it('7. Zod Schema tests (QuerySummary)', () => {
    expect(() => QuerySummarySchema.parse({ type: 'text', query: 'a' })).not.toThrow();
    expect(() => QuerySummarySchema.parse({ type: 'image', filename: 'a.png', mime_type: 'image/png' })).toThrow();
  });

  it('8. SourcesPage: partial failure', async () => {
    server.use(
      http.get('/api/v1/books/:id/editions', ({ params }) => {
        if (params.id === '123e4567-e89b-12d3-a456-426614174008') {
           return HttpResponse.json([{ id: '123e4567-e89b-12d3-a456-426614174009', name: 'E1', source_name: null, license_status: 'public', allow_redistribution: true, book_id: '123e4567-e89b-12d3-a456-426614174008', edition_note: null }]);
        }
        return new HttpResponse(JSON.stringify({ error: { code: 'FAIL', message: 'fail', request_id: '123' } }), { status: 500, headers: {'Content-Type': 'application/json'} });
      })
    );
    render(<MemoryRouter><SourcesPage /></MemoryRouter>);
    expect(await screen.findByText('B1')).toBeInTheDocument();
    expect(screen.getByText(/部分书籍版本加载失败/i)).toBeInTheDocument();
  });

  it('9. SearchPage: region search request format', async () => {
    let capturedBody: any = null;
    server.use(
      http.post('/api/v1/search/region', async ({ request }) => {
         capturedBody = await request.clone().json();
         return HttpResponse.json({
           search_id: '123e4567-e89b-12d3-a456-426614174001',
           query_summary: { type: 'region', source_figure_id: '123e4567-e89b-12d3-a456-426614174000', bbox: {x:0.1, y:0.1, width:0.5, height:0.5} },
           results: [], latency_ms: 10, model_versions: {}
         });
      })
    );

    render(<MemoryRouter><SearchPage capabilities={mockCapabilities} /></MemoryRouter>);
    fireEvent.click(screen.getByRole('tab', { name: /区域/i }));

    // Choose page_id
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'page_id' } });
    fireEvent.change(screen.getByPlaceholderText(/输入UUID/i), { target: { value: '123e4567-e89b-12d3-a456-426614174000' } });
    fireEvent.change(screen.getByLabelText('X'), { target: { value: '0.1' } });
    fireEvent.change(screen.getByLabelText('Y'), { target: { value: '0.1' } });
    fireEvent.change(screen.getByLabelText('Width'), { target: { value: '0.5' } });
    fireEvent.change(screen.getByLabelText('Height'), { target: { value: '0.5' } });
    fireEvent.click(screen.getByRole('button', { name: /区域检索/i }));

    await waitFor(() => {
       expect(capturedBody).not.toBeNull();
    });

    expect(capturedBody.page_id).toBe('123e4567-e89b-12d3-a456-426614174000');
    expect(capturedBody.figure_id).toBeUndefined();
    expect(capturedBody.coordinate_space).toBe('normalized');
    expect(capturedBody.top_k).toBe(10);
    expect(capturedBody.bbox).toEqual({ x: 0.1, y: 0.1, width: 0.5, height: 0.5 });
  });
});
