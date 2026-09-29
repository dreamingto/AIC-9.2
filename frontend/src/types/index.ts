import { z } from 'zod';

export const EvidenceStateSchema = z.enum(["Observed", "Documented", "Inferred", "Verified"]);
export type EvidenceState = z.infer<typeof EvidenceStateSchema>;

export const VerificationStateSchema = z.enum(["pending", "worth_comparing", "rejected", "disputed", "verified", "insufficient_evidence"]);
export type VerificationState = z.infer<typeof VerificationStateSchema>;

export const EvidenceKindSchema = z.enum(["image", "text", "metadata"]);
export type EvidenceKind = z.infer<typeof EvidenceKindSchema>;

export const TextKindSchema = z.enum(["title", "caption", "context", "ocr", "corrected"]);
export type TextKind = z.infer<typeof TextKindSchema>;

export const SearchTypeSchema = z.enum(["text", "image", "region"]);
export type SearchType = z.infer<typeof SearchTypeSchema>;

export const VerificationResponseSchema = z.object({
  id: z.string().uuid(),
  candidate_id: z.string().uuid(),
  state: VerificationStateSchema,
  note: z.string().nullable(),
  created_at: z.string().datetime()
});
export type VerificationResponse = z.infer<typeof VerificationResponseSchema>;

export const AssetRefSchema = z.object({
  id: z.string().uuid(),
  url: z.string(),
  mime_type: z.string(),
  width: z.number().nullable(),
  height: z.number().nullable(),
  license_status: z.string(),
  allow_redistribution: z.boolean(),
});
export type AssetRef = z.infer<typeof AssetRefSchema>;

export const SourceSummarySchema = z.object({
  book_title: z.string(),
  edition: z.string(),
  source_name: z.string().nullable(),
  volume: z.string().nullable(),
  page_or_folio: z.string(),
  source_url: z.string().nullable(),
  license_status: z.string(),
});
export type SourceSummary = z.infer<typeof SourceSummarySchema>;

export const RegionResponseSchema = z.object({
  id: z.string().uuid(),
  label: z.string().nullable(),
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
});
export type RegionResponse = z.infer<typeof RegionResponseSchema>;

export const EvidenceResponseSchema = z.object({
  id: z.string().uuid(),
  evidence_type: EvidenceKindSchema,
  status: EvidenceStateSchema,
  content: z.string(),
  pointer: z.string().nullable(),
  support_confidence: z.number(),
});
export type EvidenceResponse = z.infer<typeof EvidenceResponseSchema>;

export const FunctionalAssertionResponseSchema = z.object({
  id: z.string().uuid(),
  slot: z.string(),
  concept: z.string(),
  confidence: z.number(),
  state: EvidenceStateSchema,
  evidence_pointer: z.string().nullable(),
});
export type FunctionalAssertionResponse = z.infer<typeof FunctionalAssertionResponseSchema>;

export const ScoreComponentsSchema = z.object({
  sv: z.number(),
  st: z.number(),
  sr: z.number(),
  sf: z.number(),
  sg: z.number(),
  se: z.number(),
  u_model: z.number(),
  availability: z.record(z.string(), z.boolean()),
  reliability: z.record(z.string(), z.number()),
  missing_modalities: z.array(z.string()),
  weights: z.record(z.string(), z.number()),
  contributions: z.record(z.string(), z.number()),
});
export type ScoreComponents = z.infer<typeof ScoreComponentsSchema>;

export const SearchResultSchema = z.object({
  candidate_id: z.string().uuid(),
  figure_id: z.string().uuid(),
  source: SourceSummarySchema,
  image_ref: AssetRefSchema.nullable(),
  matched_regions: z.array(RegionResponseSchema),
  score: z.number(),
  score_components: ScoreComponentsSchema,
  cfr_summary: z.object({
    assertions: z.array(FunctionalAssertionResponseSchema),
    uncertainty: z.number(),
  }),
  evidence: z.array(EvidenceResponseSchema),
  uncertainty: z.record(z.string(), z.number()),
  verification_state: VerificationStateSchema,
});
export type SearchResult = z.infer<typeof SearchResultSchema>;

export const QuerySummaryTextSchema = z.object({
  type: z.literal("text"),
  query: z.string(),
});
export type QuerySummaryText = z.infer<typeof QuerySummaryTextSchema>;

export const QuerySummaryImageSchema = z.object({
  type: z.literal("image"),
  filename: z.string().nullable(),
  mime_type: z.string(),
  byte_size: z.number(),
});
export type QuerySummaryImage = z.infer<typeof QuerySummaryImageSchema>;

export const QuerySummaryRegionSchema = z.object({
  type: z.literal("region"),
  source_figure_id: z.string().uuid(),
  bbox: z.object({ x: z.number(), y: z.number(), width: z.number(), height: z.number() }),
});
export type QuerySummaryRegion = z.infer<typeof QuerySummaryRegionSchema>;

export const QuerySummarySchema = z.discriminatedUnion("type", [
  QuerySummaryTextSchema,
  QuerySummaryImageSchema,
  QuerySummaryRegionSchema
]);
export type QuerySummary = z.infer<typeof QuerySummarySchema>;

export const SearchResponseSchema = z.object({
  search_id: z.string().uuid(),
  query_summary: QuerySummarySchema,
  results: z.array(SearchResultSchema),
  latency_ms: z.number(),
  model_versions: z.record(z.string(), z.unknown()),
});
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

export const ProviderStatusSchema = z.object({
  name: z.string(),
  available: z.boolean(),
  provider: z.string(),
  model: z.string(),
  version: z.string(),
  dimension: z.number().nullable(),
  detail: z.string().nullable(),
});
export type ProviderStatus = z.infer<typeof ProviderStatusSchema>;

export const CapabilitiesResponseSchema = z.object({
  search_types: z.array(SearchTypeSchema),
  verification_states: z.array(VerificationStateSchema),
  evidence_states: z.array(EvidenceStateSchema),
  providers: z.array(ProviderStatusSchema),
  upload_limits: z.object({
    max_upload_bytes: z.number(),
    max_image_pixels: z.number(),
  }),
});
export type CapabilitiesResponse = z.infer<typeof CapabilitiesResponseSchema>;

export const TextChunkResponseSchema = z.object({
  id: z.string().uuid(),
  chunk_type: TextKindSchema,
  text: z.string(),
  corrected_text: z.string().nullable(),
  source_pointer: z.string().nullable(),
  state: EvidenceStateSchema,
});
export type TextChunkResponse = z.infer<typeof TextChunkResponseSchema>;

export const RelationResponseSchema = z.object({
  id: z.string().uuid(),
  subject: z.string(),
  predicate: z.string(),
  object: z.string(),
  weight: z.number(),
  confidence: z.number(),
});
export type RelationResponse = z.infer<typeof RelationResponseSchema>;

export const FigureResponseSchema = z.object({
  id: z.string().uuid(),
  title: z.string().nullable(),
  page_id: z.string().uuid(),
  asset: AssetRefSchema.nullable(),
  bbox: z.object({ x: z.number(), y: z.number(), width: z.number(), height: z.number() }).nullable(),
  regions: z.array(RegionResponseSchema),
  text_chunks: z.array(TextChunkResponseSchema),
  assertions: z.array(FunctionalAssertionResponseSchema),
  relations: z.array(RelationResponseSchema),
  evidences: z.array(EvidenceResponseSchema),
});
export type FigureResponse = z.infer<typeof FigureResponseSchema>;

export const CandidateResponseSchema = SearchResultSchema.extend({
  search_id: z.string().uuid(),
  created_at: z.string().datetime(),
});
export type CandidateResponse = z.infer<typeof CandidateResponseSchema>;

export const BookSummarySchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  author: z.string().nullable(),
  era: z.string().nullable(),
  description: z.string().nullable(),
});
export type BookSummary = z.infer<typeof BookSummarySchema>;

export const EditionSummarySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  book_id: z.string().uuid(),
  edition_note: z.string().nullable(),
  source_name: z.string().nullable(),
  license_status: z.string(),
  allow_redistribution: z.boolean(),
});
export type EditionSummary = z.infer<typeof EditionSummarySchema>;

export const APIErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string(),
    details: z.record(z.string(), z.unknown()),
  })
});
export type APIErrorEnvelope = z.infer<typeof APIErrorEnvelopeSchema>;
