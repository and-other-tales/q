// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { render, screen } from '../test-utils';
import Dashboard from '../app/page';

describe('Dashboard Page', () => {
  it('renders welcome message', () => {
    render(<Dashboard />);
    expect(screen.getByText(/Welcome to PCB Design Agent/i)).toBeInTheDocument();
  });
  it('shows quick actions', () => {
    render(<Dashboard />);
    expect(screen.getByText(/New Design/i)).toBeInTheDocument();
    expect(screen.getByText(/Import Design/i)).toBeInTheDocument();
    expect(screen.getByText(/View Analytics/i)).toBeInTheDocument();
  });
});
