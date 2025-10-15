// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

const customRender = (ui: ReactElement, options = {}) =>
  render(ui, { wrapper: ({ children }) => children, ...options });

export * from '@testing-library/react';
export { customRender as render };