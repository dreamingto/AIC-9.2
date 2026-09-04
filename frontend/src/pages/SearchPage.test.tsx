import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import SearchPage from './SearchPage';
import type { CapabilitiesResponse } from '../types';

const mockCapabilities: CapabilitiesResponse = {
  search_types: ['text', 'image', 'region'],
  verification_states: ['worth_comparing', 'verified', 'pending', 'insufficient_evidence'],
  evidence_states: ['Observed'],
  providers: [{ name: 'test_provider', available: true, provider: 'aws', model: 'v1', version: '1.0', dimension: null, detail: null }],
  upload_limits: { max_upload_bytes: 5242880, max_image_pixels: 4000000 }
};

describe('SearchPage', () => {
  it('renders tabs based on capabilities', () => {
    render(
      <BrowserRouter>
        <SearchPage capabilities={mockCapabilities} />
      </BrowserRouter>
    );
    expect(screen.getByRole('tab', { name: /文本/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /图片/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /区域/i })).toBeInTheDocument();
  });

  it('can submit a text search', async () => {
    render(
      <BrowserRouter>
        <SearchPage capabilities={mockCapabilities} />
      </BrowserRouter>
    );
    const input = screen.getByPlaceholderText(/例如：水轮提水灌溉/i);
    fireEvent.change(input, { target: { value: 'test query' } });
    const button = screen.getByRole('button', { name: /搜索/i });
    fireEvent.click(button);
    expect(await screen.findByText(/候选关联/i)).toBeInTheDocument();
  });
});
