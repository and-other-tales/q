// Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
// Type definitions for the PCB design agent
export interface ComponentData {
  id: string;
  name: string;
  manufacturer: string;
  category: string;
  description: string;
  specifications: Record<string, any>;
  footprint: string;
  symbol: string;
  datasheet_url?: string;
  price?: number;
  availability?: boolean;
}

export interface PCBDesignState {
  id: string;
  name: string;
  status: 'draft' | 'in-progress' | 'review' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  requirements: DesignRequirements;
  components: ComponentData[];
  schematic_file?: string;
  layout_file?: string;
  gerber_files?: string[];
  progress: {
    component_selection: number;
    schematic_design: number;
    layout_design: number;
    validation: number;
  };
}

export interface DesignRequirements {
  description: string;
  specifications: {
    voltage?: string;
    current?: string;
    frequency?: string;
    board_size?: string;
    layer_count?: number;
    special_requirements?: string[];
  };
  constraints: {
    cost_target?: number;
    timeline?: string;
    manufacturing_requirements?: string[];
  };
}

export interface AgentConfiguration {
  model_settings: {
    temperature: number;
    max_tokens: number;
    model_name: string;
  };
  component_database: {
    preferred_suppliers: string[];
    search_timeout: number;
    max_results: number;
  };
  design_rules: {
    trace_width_min: number;
    via_size_min: number;
    clearance_min: number;
  };
}

export interface MonitoringData {
  agent_status: 'idle' | 'running' | 'error';
  current_task?: string;
  queue_length: number;
  last_activity: string;
  performance_metrics: {
    average_response_time: number;
    success_rate: number;
    error_count: number;
  };
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}