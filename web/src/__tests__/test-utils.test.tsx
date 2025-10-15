// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { render, screen } from '@testing-library/react';
import { ReactElement } from 'react';

// Test the test utilities themselves
describe('Test Utils', () => {
  it('renders components correctly', () => {
    const TestComponent = () => <div>Test Component</div>;
    
    const customRender = (ui: ReactElement, options = {}) =>
      render(ui, { wrapper: ({ children }) => children, ...options });

    customRender(<TestComponent />);
    expect(screen.getByText('Test Component')).toBeInTheDocument();
  });

  it('provides access to testing library utilities', () => {
    expect(screen).toBeDefined();
    expect(render).toBeDefined();
  });
});