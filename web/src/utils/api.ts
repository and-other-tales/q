// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import type { ApiResponse, ComponentData, PCBDesignState, AgentConfiguration, MonitoringData } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...defaultHeaders,
          ...options.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.detail || `HTTP ${response.status}: ${response.statusText}`,
          timestamp: new Date().toISOString(),
        };
      }

      return {
        success: true,
        data,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error',
        timestamp: new Date().toISOString(),
      };
    }
  }

  // Health check
  async checkHealth(): Promise<ApiResponse<{ status: string; version: string }>> {
    return this.request('/health');
  }

  // Design management
  async createDesign(designData: {
    name: string;
    description: string;
    requirements: any;
  }): Promise<ApiResponse<PCBDesignState>> {
    return this.request('/design/create', {
      method: 'POST',
      body: JSON.stringify(designData),
    });
  }

  async getDesign(id: string): Promise<ApiResponse<PCBDesignState>> {
    return this.request(`/design/${id}`);
  }

  async listDesigns(): Promise<ApiResponse<PCBDesignState[]>> {
    return this.request('/design/list');
  }

  async deleteDesign(id: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/design/${id}`, {
      method: 'DELETE',
    });
  }

  // Agent control
  async startAgent(designId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request('/agent/start', {
      method: 'POST',
      body: JSON.stringify({ design_id: designId }),
    });
  }

  async stopAgent(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/agent/stop', {
      method: 'POST',
    });
  }

  async getAgentStatus(): Promise<ApiResponse<MonitoringData>> {
    return this.request('/agent/status');
  }

  // Component database
  async searchComponents(query: {
    search_term?: string;
    category?: string;
    manufacturer?: string;
    max_results?: number;
  }): Promise<ApiResponse<ComponentData[]>> {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });

    return this.request(`/components/search?${params.toString()}`);
  }

  // Configuration
  async getConfiguration(): Promise<ApiResponse<AgentConfiguration>> {
    return this.request('/configuration');
  }

  async updateConfiguration(
    config: Partial<AgentConfiguration>
  ): Promise<ApiResponse<AgentConfiguration>> {
    return this.request('/configuration', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  // File operations
  async uploadFile(file: File, designId: string): Promise<ApiResponse<{ file_path: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('design_id', designId);

    return this.request('/files/upload', {
      method: 'POST',
      headers: {}, // Don't set Content-Type for FormData
      body: formData,
    });
  }

  async downloadFile(filePath: string): Promise<Blob | null> {
    try {
      const response = await fetch(`${this.baseURL}/files/download?path=${encodeURIComponent(filePath)}`);
      if (response.ok) {
        return await response.blob();
      }
      return null;
    } catch (error) {
      console.error('Download error:', error);
      return null;
    }
  }

  // Utility methods
  async testEndpoint(
    method: string,
    endpoint: string,
    body?: any
  ): Promise<ApiResponse<any>> {
    const options: RequestInit = { method };
    
    if (body && (method === 'POST' || method === 'PUT')) {
      options.body = JSON.stringify(body);
    }

    return this.request(endpoint, options);
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();

// Export utility functions for common operations
export const api = {
  health: () => apiClient.checkHealth(),
  
  design: {
    create: (data: Parameters<typeof apiClient.createDesign>[0]) => 
      apiClient.createDesign(data),
    get: (id: string) => apiClient.getDesign(id),
    list: () => apiClient.listDesigns(),
    delete: (id: string) => apiClient.deleteDesign(id),
  },

  agent: {
    start: (designId: string) => apiClient.startAgent(designId),
    stop: () => apiClient.stopAgent(),
    status: () => apiClient.getAgentStatus(),
  },

  components: {
    search: (query: Parameters<typeof apiClient.searchComponents>[0]) =>
      apiClient.searchComponents(query),
  },

  config: {
    get: () => apiClient.getConfiguration(),
    update: (config: Parameters<typeof apiClient.updateConfiguration>[0]) =>
      apiClient.updateConfiguration(config),
  },

  files: {
    upload: (file: File, designId: string) => apiClient.uploadFile(file, designId),
    download: (filePath: string) => apiClient.downloadFile(filePath),
  },

  test: (method: string, endpoint: string, body?: any) =>
    apiClient.testEndpoint(method, endpoint, body),
};

export default apiClient;