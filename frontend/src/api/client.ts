import { z } from 'zod';
import { APIErrorEnvelopeSchema } from '../types';

export class APIError extends Error {
  code: string;
  request_id: string;
  details: Record<string, unknown>;

  constructor(code: string, message: string, request_id: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.request_id = request_id;
    this.details = details;
  }
}

export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && (error.name === 'AbortError' || error.message === 'aborted');
}

export function toAPIError(error: unknown, fallback: string): APIError {
  return error instanceof APIError
    ? error
    : new APIError('CLIENT_ERROR', getErrorMessage(error, fallback), '');
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
    if (isAbortError(err)) throw err;
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
  let data: unknown = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new APIError('API_CONTRACT_ERROR', 'API 契约校验失败: 后端返回了无效 JSON', '');
    }
  }

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
