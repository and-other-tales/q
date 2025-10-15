// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { render, screen } from '../test-utils';
import Configuration from '../app/configuration/page';

describe('Configuration Page', () => {
  it('renders page title and description', () => {
    render(<Configuration />);
    expect(screen.getByText(/Configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/Configure the PCB design agent settings/i)).toBeInTheDocument();
  });

  it('shows agent settings section', () => {
    render(<Configuration />);
    expect(screen.getByRole('heading', { name: /Agent Settings/i })).toBeInTheDocument(); // More specific
    expect(screen.getByText(/Model Temperature/i)).toBeInTheDocument();
    expect(screen.getByText(/Max Tokens/i)).toBeInTheDocument();
  });

  it('shows component database section', () => {
    render(<Configuration />);
    expect(screen.getByText(/Component Database/i)).toBeInTheDocument();
    expect(screen.getByText(/Preferred Suppliers/i)).toBeInTheDocument();
    expect(screen.getByText(/Digi-Key/i)).toBeInTheDocument();
    expect(screen.getByText(/Mouser/i)).toBeInTheDocument();
  });

  it('shows integrations section', () => {
    render(<Configuration />);
    expect(screen.getByRole('heading', { name: /Integrations/i })).toBeInTheDocument(); // More specific
    expect(screen.getByText(/KiCad Integration/i)).toBeInTheDocument();
  });
});