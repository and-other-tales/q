// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { ApiStatus, ApiEndpointTester } from '@/components/ApiStatus';

export default function APIIntegration() {
  return (
    <div className="space-y-6">
      <div className="bg-card p-6 rounded-lg border border-border">
        <h1 className="text-2xl font-bold mb-2">API Integration</h1>
        <p className="text-muted-foreground">
          Test and manage API connections to the FastAPI backend. Monitor endpoint health and test functionality.
        </p>
      </div>

      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">Backend Status</h2>
        <ApiStatus />
      </div>

      <div className="bg-card p-6 rounded-lg border border-border">
        <h2 className="text-lg font-semibold mb-4">API Endpoint Tester</h2>
        <ApiEndpointTester />
      </div>

      <div className="bg-card p-6 rounded-lg border border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">API Documentation</h2>
          <button className="px-4 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80">
            View Full Docs
          </button>
        </div>
        <p className="text-muted-foreground">
          Access comprehensive API documentation including request/response schemas, authentication details, and usage examples.
        </p>
      </div>
    </div>
  );
}
