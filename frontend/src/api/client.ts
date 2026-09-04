import { z } from 'zod';
import { APIErrorEnvelopeSchema } from '../types';

export class APIError extends Error {
  code: string;
  request_id: string;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, request_id: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.request_id = request_id;
    this.details = details;
  }
}

export async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit & { schema: { parse: (data: unknown) => T } }
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : endpoint;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      },
    });
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') throw err;
    throw new APIError('NETWORK_ERROR', 'Network request failed', '');
  }

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      const requestId = response.headers.get('X-Request-ID') || '';
      throw new APIError('UNKNOWN_ERROR', `HTTP ${response.status}`, requestId);
    }

    const parsedError = APIErrorEnvelopeSchema.safeParse(errorData);
    if (parsedError.success) {
      throw new APIError(
        parsedError.data.error.code,
        parsedError.data.error.message,
        parsedError.data.error.request_id,
        parsedError.data.error.details
      );
    } else {
      throw new APIError('UNKNOWN_ERROR', `HTTP ${response.status} (invalid error format)`, '');
    }
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  try {
    return options.schema.parse(data);
  } catch (err) {
    if (err instanceof z.ZodError) {
      // Do not expose stack trace
      throw new APIError('API_CONTRACT_ERROR', 'API 契约校验失败: 后端返回数据结构异常', '');
    }
    throw err;
  }
}
