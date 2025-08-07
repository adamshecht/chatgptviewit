"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import { PropertyCard } from "@/components/property-card";
import { PropertyForm } from "@/components/property-form";
import { Plus, Loader2 } from "lucide-react";
import { useSession } from "next-auth/react";

export default function PropertiesPage() {
  const { data: session } = useSession();
  const [showAddForm, setShowAddForm] = useState(false);
  const queryClient = useQueryClient();

  const { data: properties, isLoading, error } = useQuery({
    queryKey: ["properties"],
    queryFn: () => apiClient.properties.list(),
  });

  const createProperty = useMutation({
    mutationFn: (data: any) => apiClient.properties.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["properties"] });
      setShowAddForm(false);
    },
  });

  const isAdmin = session?.user?.role === "admin";

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
        Error loading properties. Please try again.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Properties</h1>
          <p className="mt-2 text-gray-600">
            Manage your monitored properties and their settings
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Property
          </button>
        )}
      </div>

      {showAddForm && (
        <div className="mb-6">
          <PropertyForm
            onSubmit={(data) => createProperty.mutate(data)}
            onCancel={() => setShowAddForm(false)}
            isLoading={createProperty.isPending}
          />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {properties?.length === 0 ? (
          <div className="col-span-full bg-white border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-500">No properties added yet</p>
            {isAdmin && (
              <button
                onClick={() => setShowAddForm(true)}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add Your First Property
              </button>
            )}
          </div>
        ) : (
          properties?.map((property: any) => (
            <PropertyCard 
              key={property.id} 
              property={property}
              isAdmin={isAdmin}
            />
          ))
        )}
      </div>
    </div>
  );
}