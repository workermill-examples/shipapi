import { useState } from 'react';
import { Plus, MapPin, Package, Edit, Trash2, Warehouse } from 'lucide-react';
import { toast } from 'sonner';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { usePaginatedApi, useMutation } from '@/hooks/useApi';

interface WarehouseResponse {
  id: string;
  name: string;
  code: string;
  address: string | null;
  is_active: boolean;
  stock_summary?: {
    total_items: number;
    total_quantity: number;
  };
  created_at: string;
  updated_at: string;
}

interface WarehouseFormData {
  name: string;
  code: string;
  address: string;
  is_active: boolean;
}

export default function WarehousesPage() {
  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedWarehouse, setSelectedWarehouse] = useState<WarehouseResponse | null>(null);

  // Form state
  const [formData, setFormData] = useState<WarehouseFormData>({
    name: '',
    code: '',
    address: '',
    is_active: true,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // API hooks
  const {
    data: warehousesData,
    isLoading: isLoadingWarehouses,
    error: warehousesError,
    refetch: refetchWarehouses,
  } = usePaginatedApi<WarehouseResponse>('/warehouses');
  const warehouses = warehousesData?.items ?? null;

  const { mutate, isLoading: isMutating } = useMutation<WarehouseResponse, WarehouseFormData>();

  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      address: '',
      is_active: true,
    });
    setFormErrors({});
  };

  // Validation
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Warehouse name is required';
    }

    if (!formData.code.trim()) {
      errors.code = 'Warehouse code is required';
    }

    // Check for duplicate codes (only during creation or when changing code)
    if (warehouses && (!selectedWarehouse || formData.code !== selectedWarehouse.code)) {
      const isDuplicate = warehouses.some(w => w.code.toLowerCase() === formData.code.toLowerCase());
      if (isDuplicate) {
        errors.code = 'Warehouse code must be unique';
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (isEdit = false) => {
    if (!validateForm()) return;

    try {
      if (isEdit && selectedWarehouse) {
        await mutate('PUT', `/warehouses/${selectedWarehouse.id}`, formData);
        toast.success('Warehouse updated successfully');
        setIsEditDialogOpen(false);
      } else {
        await mutate('POST', '/warehouses', formData);
        toast.success('Warehouse created successfully');
        setIsCreateDialogOpen(false);
      }

      resetForm();
      setSelectedWarehouse(null);
      refetchWarehouses();
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'An error occurred';
      toast.error(message);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!selectedWarehouse) return;

    try {
      await mutate('DELETE', `/warehouses/${selectedWarehouse.id}`);
      toast.success('Warehouse deleted successfully');
      setIsDeleteDialogOpen(false);
      setSelectedWarehouse(null);
      refetchWarehouses();
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'Failed to delete warehouse';
      toast.error(message);
    }
  };

  // Handle edit
  const handleEdit = (warehouse: WarehouseResponse) => {
    setSelectedWarehouse(warehouse);
    setFormData({
      name: warehouse.name,
      code: warehouse.code,
      address: warehouse.address || '',
      is_active: warehouse.is_active,
    });
    setIsEditDialogOpen(true);
  };

  // Handle delete confirmation
  const handleDeleteConfirm = (warehouse: WarehouseResponse) => {
    setSelectedWarehouse(warehouse);
    setIsDeleteDialogOpen(true);
  };

  // Handle click for stock detail
  const handleViewStock = (warehouseId: string) => {
    // Navigate to stock page with warehouse filter
    window.location.href = `/stock?warehouse_id=${warehouseId}`;
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-2xl">Warehouses</CardTitle>
              <CardDescription>
                Manage your warehouse locations and view stock summaries
              </CardDescription>
            </div>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Warehouse
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Create Warehouse</DialogTitle>
                  <DialogDescription>
                    Add a new warehouse location to your inventory system.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="name">Warehouse Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Enter warehouse name"
                    />
                    {formErrors.name && <p className="text-sm text-red-500">{formErrors.name}</p>}
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="code">Warehouse Code</Label>
                    <Input
                      id="code"
                      value={formData.code}
                      onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                      placeholder="Enter unique warehouse code"
                    />
                    {formErrors.code && <p className="text-sm text-red-500">{formErrors.code}</p>}
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="address">Address</Label>
                    <Textarea
                      id="address"
                      value={formData.address}
                      onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                      placeholder="Enter warehouse address"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => {
                    setIsCreateDialogOpen(false);
                    resetForm();
                  }}>
                    Cancel
                  </Button>
                  <Button onClick={() => handleSubmit(false)} disabled={isMutating}>
                    {isMutating ? 'Creating...' : 'Create Warehouse'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {/* Error state */}
          {warehousesError && (
            <div className="text-center py-8">
              <p className="text-red-500">Failed to load warehouses: {warehousesError}</p>
              <Button onClick={refetchWarehouses} variant="outline" className="mt-2">
                Retry
              </Button>
            </div>
          )}

          {/* Loading state */}
          {isLoadingWarehouses && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-48 w-full" />
              ))}
            </div>
          )}

          {/* Card grid layout */}
          {!isLoadingWarehouses && !warehousesError && (
            <>
              {warehouses?.length === 0 ? (
                <div className="text-center py-8">
                  <Warehouse className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <p className="text-gray-500 mb-4">
                    No warehouses found. Create your first warehouse to get started.
                  </p>
                  <Button onClick={() => setIsCreateDialogOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add First Warehouse
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {warehouses?.map((warehouse) => (
                    <Card
                      key={warehouse.id}
                      className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => handleViewStock(warehouse.id)}
                    >
                      <CardHeader className="pb-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <CardTitle className="text-lg flex items-center gap-2">
                              <Warehouse className="h-5 w-5" />
                              {warehouse.name}
                            </CardTitle>
                            <CardDescription className="mt-1">
                              <code className="text-sm bg-gray-100 px-1 rounded">
                                {warehouse.code}
                              </code>
                            </CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={warehouse.is_active ? "default" : "secondary"}>
                              {warehouse.is_active ? "Active" : "Inactive"}
                            </Badge>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                <Button variant="ghost" size="sm">
                                  •••
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent>
                                <DropdownMenuItem onClick={(e) => {
                                  e.stopPropagation();
                                  handleEdit(warehouse);
                                }}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteConfirm(warehouse);
                                  }}
                                  className="text-red-600"
                                >
                                  <Trash2 className="mr-2 h-4 w-4" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-0">
                        {/* Address */}
                        {warehouse.address && (
                          <div className="flex items-start gap-2 mb-4">
                            <MapPin className="h-4 w-4 mt-0.5 text-gray-500 flex-shrink-0" />
                            <p className="text-sm text-gray-600">{warehouse.address}</p>
                          </div>
                        )}

                        {/* Stock Summary */}
                        <div className="space-y-3">
                          <h4 className="text-sm font-medium flex items-center gap-2">
                            <Package className="h-4 w-4" />
                            Stock Summary
                          </h4>
                          {warehouse.stock_summary ? (
                            <div className="grid grid-cols-2 gap-4">
                              <div className="text-center p-3 bg-blue-50 rounded-lg">
                                <p className="text-2xl font-bold text-blue-600">
                                  {warehouse.stock_summary.total_items}
                                </p>
                                <p className="text-xs text-blue-600">Unique Items</p>
                              </div>
                              <div className="text-center p-3 bg-green-50 rounded-lg">
                                <p className="text-2xl font-bold text-green-600">
                                  {warehouse.stock_summary.total_quantity}
                                </p>
                                <p className="text-xs text-green-600">Total Quantity</p>
                              </div>
                            </div>
                          ) : (
                            <div className="text-center p-4 text-gray-500">
                              <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
                              <p className="text-sm">No stock data</p>
                            </div>
                          )}
                          <p className="text-xs text-gray-500">
                            Created {formatDate(warehouse.created_at)}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Warehouse</DialogTitle>
            <DialogDescription>
              Make changes to the warehouse information.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Warehouse Name</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter warehouse name"
              />
              {formErrors.name && <p className="text-sm text-red-500">{formErrors.name}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-code">Warehouse Code</Label>
              <Input
                id="edit-code"
                value={formData.code}
                onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                placeholder="Enter unique warehouse code"
              />
              {formErrors.code && <p className="text-sm text-red-500">{formErrors.code}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-address">Address</Label>
              <Textarea
                id="edit-address"
                value={formData.address}
                onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                placeholder="Enter warehouse address"
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="edit-active"
                checked={formData.is_active}
                onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                className="rounded"
              />
              <Label htmlFor="edit-active">Active warehouse</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsEditDialogOpen(false);
              resetForm();
              setSelectedWarehouse(null);
            }}>
              Cancel
            </Button>
            <Button onClick={() => handleSubmit(true)} disabled={isMutating}>
              {isMutating ? 'Updating...' : 'Update Warehouse'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Warehouse</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedWarehouse?.name}"? This action cannot be undone.
              {selectedWarehouse?.stock_summary && selectedWarehouse.stock_summary.total_items > 0 && (
                <span className="block mt-2 font-medium text-red-600">
                  This warehouse contains {selectedWarehouse.stock_summary.total_items} items and cannot be deleted.
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsDeleteDialogOpen(false);
              setSelectedWarehouse(null);
            }}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isMutating || Boolean(selectedWarehouse?.stock_summary && selectedWarehouse.stock_summary.total_items > 0)}
            >
              {isMutating ? 'Deleting...' : 'Delete Warehouse'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}