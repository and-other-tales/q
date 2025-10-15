<!-- Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved. -->
# PCB Design Agent - Web Interface

A modern, responsive web application built with Next.js 15.5 that provides a user-friendly interface for the AI-powered PCB design agent. This frontend connects to a FastAPI backend to enable comprehensive PCB design automation and control.

## Features

- **Dashboard**: Overview of active projects, performance metrics, and quick actions
- **Design Control**: Create new PCB designs, manage active projects, and import existing files
- **Configuration**: Customize agent settings, component database preferences, and design rules
- **Monitoring**: Real-time system status, performance metrics, and activity logs
- **API Integration**: Test backend connectivity and explore available endpoints

## Tech Stack

- **Framework**: Next.js 15.5 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom design system
- **Icons**: Heroicons (via inline SVG)
- **Backend**: FastAPI integration via REST API

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with navigation
│   ├── page.tsx           # Dashboard page
│   ├── design/            # Design control page
│   ├── configuration/     # Configuration page
│   ├── monitoring/        # System monitoring page
│   └── api/               # API integration page
├── components/            # Reusable UI components
├── features/              # Feature-specific components
├── hooks/                 # Custom React hooks
├── types/                 # TypeScript type definitions
└── utils/                 # Utility functions and API client
```

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm, yarn, pnpm, or bun
- PCB Design Agent backend running (default: http://localhost:8000)

### Installation

1. Clone the repository and navigate to the web directory:
```bash
cd /path/to/pcb-design-agent/web
```

2. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. Set up environment variables (optional):
```bash
# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### Development

Run the development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to access the application.

The page auto-updates as you edit files. Start by modifying `src/app/page.tsx`.

### Building for Production

Build the application:
```bash
npm run build
```

Start the production server:
```bash
npm start
```

## API Integration

The frontend communicates with the FastAPI backend through a comprehensive API client located in `src/utils/api.ts`. Key features include:

- **Type-safe requests**: Full TypeScript support with proper error handling
- **Authentication ready**: Extensible for future auth implementations  
- **File operations**: Upload/download support for design files
- **Real-time data**: Integration points for WebSocket connections

### Environment Configuration

Configure the backend URL using environment variables:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000  # Development
# NEXT_PUBLIC_API_URL=https://your-api.com  # Production
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler

## Design System

The application uses a custom design system built on Tailwind CSS with:

- **HSL-based color palette**: Consistent theming across light/dark modes
- **CSS custom properties**: Dynamic theme switching
- **Responsive design**: Mobile-first approach with breakpoint utilities
- **Component patterns**: Consistent spacing, typography, and interaction states

## Development Guidelines

### Adding New Pages

1. Create a new directory in `src/app/`
2. Add a `page.tsx` file with your component
3. Update navigation in `src/app/layout.tsx`

### API Integration

Use the centralized API client:
```typescript
import { api } from '@/utils/api';

// Example usage
const response = await api.design.create({
  name: "My Project",
  description: "Example PCB design",
  requirements: { /* ... */ }
});

if (response.success) {
  console.log(response.data);
} else {
  console.error(response.error);
}
```

### Type Safety

All API responses and data structures are typed. Add new types to `src/types/index.ts`.

## Deployment

### Vercel (Recommended)

1. Connect your repository to Vercel
2. Set environment variables in the dashboard
3. Deploy automatically on git push

### Other Platforms

The application is a standard Next.js app and can be deployed to any platform supporting Node.js:

- Netlify
- AWS Amplify  
- Docker containers
- Traditional hosting with PM2

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for new features
3. Test API integrations thoroughly
4. Update documentation for new features

## License

This project is part of the PCB Design Agent system. See the main project repository for license information.
