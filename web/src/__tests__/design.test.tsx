// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.

import { render, screen } from '../test-utils';
import DesignControl from '../app/design/page';
import * as apiHooks from '@/hooks/useApi';

describe('Design Control Page', () => {
  beforeEach(() => {
    jest.spyOn(apiHooks, 'useDesigns').mockReturnValue({
      designs: [
        { id: '1', name: 'Test Design', description: 'A test design', status: 'draft', created_at: new Date().toISOString() }
      ],
      loading: false,
      error: null,
      createDesign: jest.fn(),
      deleteDesign: jest.fn(),
      refresh: jest.fn(),
    });
    jest.spyOn(apiHooks, 'useAgentStatus').mockReturnValue({
      status: { agent_status: 'idle', current_task: null },
      loading: false,
      error: null,
      startAgent: jest.fn(),
      stopAgent: jest.fn(),
    });
  });
  it('renders page title and description', () => {
    render(<DesignControl />);
    expect(screen.getByText(/Design Control/i)).toBeInTheDocument();
    expect(screen.getByText(/Create and manage PCB design projects/i)).toBeInTheDocument();
  });

  it('shows create new design form', () => {
    render(<DesignControl />);
    expect(screen.getByText(/Create New Design/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter project name/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create Design/i })).toBeInTheDocument();
  });

  it('shows your designs section', async () => {
    render(<DesignControl />);
    expect(await screen.findByText(/Your Designs\s*\(\d+\)/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Test Design/i })).toBeInTheDocument();
  });
});