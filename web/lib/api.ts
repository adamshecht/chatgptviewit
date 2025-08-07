/**
 * API Client for CityScrape
 */

import axios from 'axios';
import { getSession } from 'next-auth/react';

// Use backend URL directly
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  // Development mode: use test token
  if (process.env.NODE_ENV === 'development') {
    config.headers.Authorization = 'Bearer test-token';
  } else {
    const session = await getSession();
    if (session?.accessToken) {
      config.headers.Authorization = `Bearer ${session.accessToken}`;
    }
  }
  return config;
});

// API methods
export const apiClient = {
  // Auth
  auth: {
    login: async (email: string, auth0Token: string) => {
      const response = await api.post('/api/auth/login', { email, auth0_token: auth0Token });
      return response.data;
    },
    me: async () => {
      const response = await api.get('/api/auth/me');
      return response.data;
    },
  },

  // Properties
  properties: {
    list: async () => {
      const response = await api.get('/api/properties/');
      return response.data;
    },
    get: async (id: number) => {
      const response = await api.get(`/api/properties/${id}`);
      return response.data;
    },
    create: async (data: any) => {
      const response = await api.post('/api/properties', data);
      return response.data;
    },
    update: async (id: number, data: any) => {
      const response = await api.put(`/api/properties/${id}`, data);
      return response.data;
    },
    delete: async (id: number) => {
      const response = await api.delete(`/api/properties/${id}`);
      return response.data;
    },
  },

  // Alerts
  alerts: {
    list: async (params?: any) => {
      const response = await api.get('/api/alerts/', { params });
      return response.data;
    },
    get: async (id: number) => {
      const response = await api.get(`/api/alerts/${id}`);
      return response.data;
    },
    updateStatus: async (id: number, status: string) => {
      const response = await api.patch(`/api/alerts/${id}/status`, { status });
      return response.data;
    },
    addComment: async (id: number, comment: string) => {
      const response = await api.post(`/api/alerts/${id}/comments`, { comment });
      return response.data;
    },
    getComments: async (id: number) => {
      const response = await api.get(`/api/alerts/${id}/comments`);
      return response.data;
    },
  },

  // Documents
  documents: {
    get: async (documentId: string) => {
      const response = await api.get(`/api/documents/${documentId}`);
      return response.data;
    },
    getContent: async (documentId: string) => {
      const response = await api.get(`/api/documents/${documentId}/content`);
      return response.data;
    },
    download: async (documentId: string) => {
      const response = await api.get(`/api/documents/${documentId}/download`, {
        responseType: 'blob',
      });
      return response.data;
    },
    getAnalysis: async (documentId: string) => {
      const response = await api.get(`/api/documents/${documentId}/analysis`);
      return response.data;
    },
    reanalyze: async (documentId: string) => {
      const response = await api.post(`/api/documents/${documentId}/reanalyze`);
      return response.data;
    },
  },

  // Companies
  companies: {
    getInfo: async () => {
      const response = await api.get('/api/companies/me');
      return response.data;
    },
    updateSettings: async (settings: any) => {
      const response = await api.put('/api/companies/settings', settings);
      return response.data;
    },
    uploadToR: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('/api/companies/terms-of-reference', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    getUsers: async () => {
      const response = await api.get('/api/companies/users');
      return response.data;
    },
    inviteUser: async (data: any) => {
      const response = await api.post('/api/companies/users', data);
      return response.data;
    },
    removeUser: async (userId: number) => {
      const response = await api.delete(`/api/companies/users/${userId}`);
      return response.data;
    },
    getMunicipalities: async () => {
      const response = await api.get('/api/companies/municipalities');
      return response.data;
    },
    updateMunicipalities: async (municipalities: string[]) => {
      const response = await api.put('/api/companies/municipalities', municipalities);
      return response.data;
    },
  },

  // Ingest
  ingest: {
    submit: async (data: any) => {
      const response = await api.post('/api/ingest', data);
      return response.data;
    },
    batchSubmit: async (data: any[]) => {
      const response = await api.post('/api/ingest/batch', data);
      return response.data;
    },
    getStatus: async (documentId: string) => {
      const response = await api.get(`/api/ingest/status/${documentId}`);
      return response.data;
    },
  },
};

export default apiClient;