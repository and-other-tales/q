// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
import { useState, useEffect } from 'react';
import { api } from '@/utils/api';
import type { ApiResponse } from '@/types';

export function useApiHealth() {
  const [health, setHealth] = useState<{
    status: string;
    version: string;
    timestamp: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setLoading(true);
        const response = await api.health();
        if (response.success) {
          setHealth(response.data);
          setError(null);
        } else {
          setError(response.error || 'Health check failed');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error');
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return { health, loading, error };
}

export function useDesigns() {
  const [designs, setDesigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDesigns = async () => {
    try {
      setLoading(true);
      const response = await api.design.list();
      if (response.success) {
        setDesigns(response.data || []);
        setError(null);
      } else {
        setError(response.error || 'Failed to fetch designs');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDesigns();
  }, []);

  const createDesign = async (designData: {
    name: string;
    description: string;
    requirements: any;
  }) => {
    try {
      const response = await api.design.create(designData);
      if (response.success) {
        fetchDesigns(); // Refresh the list
        return response.data;
      } else {
        throw new Error(response.error || 'Failed to create design');
      }
    } catch (err) {
      throw err;
    }
  };

  const deleteDesign = async (id: string) => {
    try {
      const response = await api.design.delete(id);
      if (response.success) {
        fetchDesigns(); // Refresh the list
      } else {
        throw new Error(response.error || 'Failed to delete design');
      }
    } catch (err) {
      throw err;
    }
  };

  return {
    designs,
    loading,
    error,
    createDesign,
    deleteDesign,
    refresh: fetchDesigns
  };
}

export function useAgentStatus() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await api.agent.status();
        if (response.success) {
          setStatus(response.data);
          setError(null);
        } else {
          setError(response.error || 'Failed to get agent status');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error');
      } finally {
        setLoading(false);
      }
    };

    checkStatus();
    
    // Check status every 10 seconds
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const startAgent = async (designId: string) => {
    try {
      const response = await api.agent.start(designId);
      if (!response.success) {
        throw new Error(response.error || 'Failed to start agent');
      }
      return response.data;
    } catch (err) {
      throw err;
    }
  };

  const stopAgent = async () => {
    try {
      const response = await api.agent.stop();
      if (!response.success) {
        throw new Error(response.error || 'Failed to stop agent');
      }
      return response.data;
    } catch (err) {
      throw err;
    }
  };

  return {
    status,
    loading,
    error,
    startAgent,
    stopAgent
  };
}