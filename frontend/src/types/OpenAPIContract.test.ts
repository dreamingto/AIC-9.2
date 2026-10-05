import { expect, test } from 'vitest';
import { z } from 'zod';
import contract from './openapi.json';
import * as dto from './index';

type Definition = { properties?: Record<string, unknown>; title?: string };

test('实际后端OpenAPI与前端响应Schema字段保持同步', () => {
  const names = ['CapabilitiesResponse', 'ProviderStatus', 'BookSummary', 'EditionSummary',
    'FigureResponse', 'TextChunkResponse', 'RegionResponse', 'RelationResponse',
    'FunctionalAssertionResponse', 'EvidenceResponse', 'SourceSummary', 'AssetRef',
    'SearchResponse', 'SearchResult', 'CandidateResponse', 'VerificationResponse', 'DataStatus'];
  const backend: Record<string, Definition> = contract.components.schemas;
  const frontend: Record<string, unknown> = dto;
  for (const name of names) {
    const schema = frontend[`${name}Schema`];
    expect(schema, name).toBeInstanceOf(z.ZodType);
    if (!(schema instanceof z.ZodType)) throw new Error(`Missing schema: ${name}`);
    const json = z.toJSONSchema(schema);
    expect(Object.keys(json.properties ?? {}).sort(), name)
      .toEqual(Object.keys(backend[name].properties ?? {}).sort());
  }
});
