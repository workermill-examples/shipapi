import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

interface ApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

interface UseApiOptions {
  immediate?: boolean;
  dependencies?: unknown[];
}

// Generic API hook for GET requests
export const useApi = <T>(
  url: string | null,
  options: UseApiOptions = {}
): ApiState<T> & { refetch: () => Promise<void> } => {
  const { immediate = true, dependencies = [] } = options;
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    isLoading: false,
    error: null,
  });

  const fetchData = useCallback(async () => {
    if (!url) return;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await api.get<T>(url);
      setState({
        data: response.data,
        isLoading: false,
        error: null,
      });
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : error instanceof Error
          ? error.message
          : 'An error occurred';
      setState({
        data: null,
        isLoading: false,
        error: message,
      });
    }
  }, [url]);

  useEffect(() => {
    if (immediate) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchData, immediate, ...dependencies]);

  return {
    ...state,
    refetch: fetchData,
  };
};

// Hook for paginated data fetching
export const usePaginatedApi = <T>(
  baseUrl: string | null,
  page: number = 1,
  perPage: number = 50,
  filters: Record<string, unknown> = {}
): ApiState<PaginatedResponse<T>> & { refetch: () => Promise<void> } => {
  const [state, setState] = useState<ApiState<PaginatedResponse<T>>>({
    data: null,
    isLoading: false,
    error: null,
  });

  const fetchData = useCallback(async () => {
    if (!baseUrl) return;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Build query parameters
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });

      // Add filters to params
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, value.toString());
        }
      });

      const url = `${baseUrl}?${params.toString()}`;
      const response = await api.get<PaginatedResponse<T>>(url);
      setState({
        data: response.data,
        isLoading: false,
        error: null,
      });
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : error instanceof Error
          ? error.message
          : 'An error occurred';
      setState({
        data: null,
        isLoading: false,
        error: message,
      });
    }
  }, [baseUrl, page, perPage, filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    ...state,
    refetch: fetchData,
  };
};

// Hook for API mutations (POST, PUT, DELETE)
export const useMutation = <TData, TVariables = unknown>() => {
  const [state, setState] = useState({
    isLoading: false,
    error: null as string | null,
  });

  const mutate = useCallback(
    async (
      method: 'POST' | 'PUT' | 'DELETE',
      url: string,
      data?: TVariables
    ): Promise<TData> => {
      setState({ isLoading: true, error: null });

      try {
        const response = await api.request<TData>({
          method,
          url,
          data,
        });

        setState({ isLoading: false, error: null });
        return response.data;
      } catch (error: unknown) {
        const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
          ? String(error.response.data.detail)
          : error instanceof Error
            ? error.message
            : 'An error occurred';
        setState({ isLoading: false, error: message });
        throw error;
      }
    },
    []
  );

  return {
    mutate,
    isLoading: state.isLoading,
    error: state.error,
  };
};

// Specific hooks for common operations
export const useProducts = (filters: Record<string, unknown> = {}, page: number = 1) => {
  return usePaginatedApi('/products', page, 50, filters);
};

export const useCategories = () => {
  return useApi<unknown[]>('/categories');
};

export const useWarehouses = () => {
  return useApi<unknown[]>('/warehouses');
};

export const useStockLevels = (filters: Record<string, unknown> = {}, page: number = 1) => {
  return usePaginatedApi('/stock', page, 50, filters);
};

export const useAuditLog = (filters: Record<string, unknown> = {}, page: number = 1) => {
  return usePaginatedApi('/audit', page, 50, filters);
};

export const useShowcaseStats = () => {
  return useApi<{
    total_products: number;
    total_categories: number;
    total_warehouses: number;
    total_stock_transfers: number;
    low_stock_alerts: number;
  }>('/showcase/stats');
};