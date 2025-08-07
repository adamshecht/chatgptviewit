"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import { AlertCard } from "@/components/alert-card";
import { AlertFilters } from "@/components/alert-filters";
import { Loader2 } from "lucide-react";

export default function AlertsPage() {
  const [filters, setFilters] = useState({
    status: null,
    municipality: null,
    property_id: null,
    start_date: null,
    end_date: null,
  });

  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ["alerts", filters],
    queryFn: () => apiClient.alerts.list(filters),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        Error loading alerts. Please try again.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
        <p className="mt-2 text-gray-600">
          Review flagged municipal documents that may impact your properties
        </p>
      </div>

      <AlertFilters filters={filters} onFiltersChange={setFilters} />

      <div className="mt-6 space-y-4">
        {alerts?.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-500">No alerts found matching your filters</p>
          </div>
        ) : (
          alerts?.map((alert: any) => (
            <AlertCard key={alert.id} alert={alert} />
          ))
        )}
      </div>
    </div>
  );
}