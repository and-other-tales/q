// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
'use client';

import { useApiHealth } from '@/hooks/useApi';

export function ApiStatus() {
  const { health, loading, error } = useApiHealth();

  if (loading) {
    return (
      <div className="p-4 bg-muted/50 rounded-lg">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-gray-400 rounded-full animate-pulse"></div>
          <span className="text-sm text-muted-foreground">Checking API status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-red-500 rounded-full"></div>
          <span className="text-sm text-red-700">API Error: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-sm text-green-700">API Healthy</span>
        </div>
        <div className="text-xs text-muted-foreground">
          v{health?.version} - {new Date(health?.timestamp || '').toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

export function ApiEndpointTester() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-muted/50 rounded-lg">
          <h3 className="font-medium mb-2">GET /health</h3>
          <p className="text-sm text-muted-foreground mb-2">Check API health status</p>
          <div className="flex space-x-2">
            <button 
              onClick={async () => {
                try {
                  const response = await fetch('http://localhost:8000/health');
                  const data = await response.json();
                  alert(JSON.stringify(data, null, 2));
                } catch (err) {
                  alert('Error: ' + (err instanceof Error ? err.message : 'Unknown error'));
                }
              }}
              className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            >
              Test
            </button>
            <span className="px-2 py-1 bg-green-100 text-green-600 text-xs rounded">GET</span>
          </div>
        </div>

        <div className="p-4 bg-muted/50 rounded-lg">
          <h3 className="font-medium mb-2">GET /</h3>
          <p className="text-sm text-muted-foreground mb-2">Root API information</p>
          <div className="flex space-x-2">
            <button 
              onClick={async () => {
                try {
                  const response = await fetch('http://localhost:8000/');
                  const data = await response.json();
                  alert(JSON.stringify(data, null, 2));
                } catch (err) {
                  alert('Error: ' + (err instanceof Error ? err.message : 'Unknown error'));
                }
              }}
              className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            >
              Test
            </button>
            <span className="px-2 py-1 bg-green-100 text-green-600 text-xs rounded">GET</span>
          </div>
        </div>

        <div className="p-4 bg-muted/50 rounded-lg">
          <h3 className="font-medium mb-2">GET /api/design/jobs</h3>
          <p className="text-sm text-muted-foreground mb-2">List all design jobs</p>
          <div className="flex space-x-2">
            <button 
              onClick={async () => {
                try {
                  const response = await fetch('http://localhost:8000/api/design/jobs');
                  const data = await response.json();
                  alert(JSON.stringify(data, null, 2));
                } catch (err) {
                  alert('Error: ' + (err instanceof Error ? err.message : 'Unknown error'));
                }
              }}
              className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            >
              Test
            </button>
            <span className="px-2 py-1 bg-green-100 text-green-600 text-xs rounded">GET</span>
          </div>
        </div>

        <div className="p-4 bg-muted/50 rounded-lg">
          <h3 className="font-medium mb-2">GET /api/components/categories</h3>
          <p className="text-sm text-muted-foreground mb-2">Get component categories</p>
          <div className="flex space-x-2">
            <button 
              onClick={async () => {
                try {
                  const response = await fetch('http://localhost:8000/api/components/categories');
                  const data = await response.json();
                  alert(JSON.stringify(data, null, 2));
                } catch (err) {
                  alert('Error: ' + (err instanceof Error ? err.message : 'Unknown error'));
                }
              }}
              className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            >
              Test
            </button>
            <span className="px-2 py-1 bg-green-100 text-green-600 text-xs rounded">GET</span>
          </div>
        </div>
      </div>
    </div>
  );
}