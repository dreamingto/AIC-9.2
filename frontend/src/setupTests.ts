import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { http, HttpResponse, delay } from 'msw';
import { beforeAll, afterEach, afterAll } from 'vitest';
import type { CapabilitiesResponse, SearchResponse, CandidateResponse, BookSummary, EditionSummary } from './types';

export const mockCapabilities = {
  search_types: ['text', 'image', 'region'],
  verification_states: ['worth_comparing', 'verified', 'pending', 'insufficient_evidence'],
  evidence_states: ['Observed'],
  providers: [{ name: 'test_provider', available: true, provider: 'aws', model: 'v1', version: '1.0', dimension: 1024, detail: null }],
  upload_limits: { max_upload_bytes: 5242880, max_image_pixels: 4000000 }
} satisfies CapabilitiesResponse;

export const handlers = [
  http.get('/api/v1/capabilities', async () => {
    return HttpResponse.json(mockCapabilities);
  }),
  http.post('/api/v1/search/text', async () => {
    await delay(100);
    return HttpResponse.json({
      search_id: '123e4567-e89b-12d3-a456-426614174000',
      query_summary: { type: 'text', query: 'test' },
      results: [{
         candidate_id: '123e4567-e89b-12d3-a456-426614174000',
         figure_id: '123e4567-e89b-12d3-a456-426614174000',
         source: { book_title: 'Book A', edition: 'Ed 1', source_name: null, volume: null, page_or_folio: '1', source_url: null, license_status: 'public' },
         image_ref: null,
         matched_regions: [],
         score: 0.9,
         score_components: { sv: 1, st: 1, sr: 1, sf: 1, sg: 1, se: 1, u_model: 1, availability: {}, reliability: {}, missing_modalities: [], weights: {}, contributions: {} },
         cfr_summary: { assertions: [], uncertainty: 0 },
         evidence: [],
         uncertainty: {},
         verification_state: 'pending'
      }],
      latency_ms: 10,
      model_versions: {}
    } satisfies SearchResponse);
  }),
  http.post('/api/v1/search/region', async ({ request }) => {
    const data = await request.json() as Record<string, unknown>;
    if (!data.bbox) return new HttpResponse(null, { status: 400 });
    return HttpResponse.json({
      search_id: '123e4567-e89b-12d3-a456-426614174001',
      query_summary: { type: 'region', source_figure_id: '123e4567-e89b-12d3-a456-426614174000', bbox: {x:0, y:0, width:1, height:1} },
      results: [],
      latency_ms: 10,
      model_versions: {}
    } satisfies SearchResponse);
  }),
  http.post('/api/v1/search/image', async () => {
    await delay(100);
    return HttpResponse.json({
      search_id: '123e4567-e89b-12d3-a456-426614174002',
      query_summary: { type: 'image', filename: 'test.png', mime_type: 'image/png', byte_size: 100 },
      results: [],
      latency_ms: 10,
      model_versions: {}
    } satisfies SearchResponse);
  }),
  http.get('/api/v1/associations/:id', async ({ params }) => {
    if (params.id === '123e4567-e89b-12d3-a456-426614174009') await delay(200); // slow cand
    return HttpResponse.json({
      search_id: '123e4567-e89b-12d3-a456-426614174000',
      created_at: '2023-01-01T00:00:00.000Z',
      candidate_id: params.id as string,
      figure_id: '123e4567-e89b-12d3-a456-426614174000',
      source: { book_title: 'Book A', edition: 'Ed 1', source_name: null, volume: null, page_or_folio: '1', source_url: null, license_status: 'public' },
      image_ref: { id: '123e4567-e89b-12d3-a456-426614174006', url: '/img.jpg', mime_type: 'image/jpeg', width: 100, height: 100, license_status: 'restricted', allow_redistribution: false },
      matched_regions: [],
      score: 0.8,
      score_components: { sv: 1, st: 1, sr: 1, sf: 1, sg: 1, se: 1, u_model: 1, availability: {}, reliability: {}, missing_modalities: ['image'], weights: {}, contributions: {} },
      cfr_summary: { assertions: [], uncertainty: 0 },
      evidence: [{ id: '123e4567-e89b-12d3-a456-426614174007', evidence_type: 'text', status: 'Observed', content: 'ev text', pointer: null, support_confidence: 1 }],
      uncertainty: { 'some': 0.1 },
      verification_state: 'pending'
    } satisfies CandidateResponse);
  }),
  http.get('/api/v1/search/:id', async () => {
    return HttpResponse.json({
      search_id: '123e4567-e89b-12d3-a456-426614174000',
      query_summary: { type: 'text', query: 'mock query' },
      results: [],
      latency_ms: 10,
      model_versions: {}
    } satisfies SearchResponse);
  }),
  http.get('/api/v1/books', async () => {
    return HttpResponse.json([
       { id: '123e4567-e89b-12d3-a456-426614174008', title: 'B1', author: null, era: null, description: null },
       { id: '123e4567-e89b-12d3-a456-426614174010', title: 'B2', author: null, era: null, description: null }
    ] satisfies BookSummary[]);
  }),
  http.get('/api/v1/books/:id/editions', async ({ params }) => {
    if (params.id === '123e4567-e89b-12d3-a456-426614174008') {
       return HttpResponse.json([{ id: '123e4567-e89b-12d3-a456-426614174009', name: 'E1', source_name: null, license_status: 'public', allow_redistribution: true, book_id: '123e4567-e89b-12d3-a456-426614174008', edition_note: null }] satisfies EditionSummary[]);
    }
    return HttpResponse.json([]);
  }),
  http.post('/api/v1/associations/:id/verify', async ({ params, request }) => {
    const data = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
       id: '123e4567-e89b-12d3-a456-426614174099',
       candidate_id: params.id,
       state: data.state,
       note: (data.note as string) || null,
       created_at: '2023-01-01T00:00:00.000Z'
    });
  })
];

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
