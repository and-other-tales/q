// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { render, screen } from '../test-utils';
import APIIntegration from '../app/api/page';

describe('API Integration Page', () => {
  it('renders page title and description', () => {
    render(<APIIntegration />);
    expect(screen.getByText(/API Integration/i)).toBeInTheDocument();
    expect(screen.getByText(/Test and manage API connections to the FastAPI backend/i)).toBeInTheDocument();
  });

  it('shows backend status section', () => {
    render(<APIIntegration />);
    expect(screen.getByText(/Backend Status/i)).toBeInTheDocument();
    expect(screen.getByText(/Checking API status/i)).toBeInTheDocument();
  });

  it('shows API endpoint tester section', () => {
    render(<APIIntegration />);
    expect(screen.getByText(/API Endpoint Tester/i)).toBeInTheDocument();
    expect(screen.getByText(/GET \/health/i)).toBeInTheDocument();
    expect(screen.getByText(/Check API health status/i)).toBeInTheDocument();
    expect(screen.getByText(/GET \/api\/design\/jobs/i)).toBeInTheDocument();
    expect(screen.getByText(/List all design jobs/i)).toBeInTheDocument();
  });

  it('shows API documentation section', async () => {
    render(<APIIntegration />);
    expect(await screen.findByRole('heading', { name: /API Documentation/i })).toBeInTheDocument();
    expect(await screen.findByText(/Access comprehensive API documentation/i)).toBeInTheDocument();
  });
});