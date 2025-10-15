// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { render, screen } from '../test-utils';
import Monitoring from '../app/monitoring/page';

describe('Monitoring Page', () => {
  it('renders page title and description', () => {
    render(<Monitoring />);
    expect(screen.getByText(/System Monitoring/i)).toBeInTheDocument();
    expect(screen.getByText(/Monitor the PCB design agent's performance/i)).toBeInTheDocument();
  });

  it('shows status overview cards', () => {
    render(<Monitoring />);
    expect(screen.getByText(/Agent Status/i)).toBeInTheDocument();
    expect(screen.getByText(/Online/i)).toBeInTheDocument();
    expect(screen.getByText(/Queue Length/i)).toBeInTheDocument();
    expect(screen.getByText(/Success Rate/i)).toBeInTheDocument();
    expect(screen.getByText(/Avg Response/i)).toBeInTheDocument();
  });

  it('shows current activity section', () => {
    render(<Monitoring />);
    expect(screen.getByText(/Current Activity/i)).toBeInTheDocument();
    expect(screen.getByText(/Component Selection/i)).toBeInTheDocument();
  });
});