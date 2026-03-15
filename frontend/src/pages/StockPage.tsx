import { useState } from 'react';
import { AlertTriangle, Package, Filter, ArrowRightLeft, Settings2, Search } from 'lucide-react';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { usePaginatedApi, useMutation } from '@/hooks/useApi';

interface StockLevel {
  id: string;
  product_id: string;
  warehouse_id: string;
  quantity: number;
  low_stock_threshold: number;
  product: {
    id: string;
    name: string;
    sku: string;
    price: number;
  };
  warehouse: {
    id: string;
    name: string;
    code: string;
  };
  updated_at: string;
}

interface Warehouse {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}

interface Product {
  id: string;
  name: string;
  sku: string;
  price: number;
  is_active: boolean;
}

interface StockTransfer {
  id: string;
  product_id: string;
  from_warehouse_id: string;
  to_warehouse_id: string;
  quantity: number;
  notes: string | null;
  product: {
    name: string;
    sku: string;
  };
  from_warehouse: {
    name: string;
    code: string;
  };
  to_warehouse: {
    name: string;
    code: string;
  };
  created_at: string;
}

interface StockTransferFormData {
  product_id: string;
  from_warehouse_id: string;
  to_warehouse_id: string;
  quantity: number;
  notes: string;
}

interface StockAdjustFormData {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  low_stock_threshold: number;
}

export default function StockPage() {
  // Filter state
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Dialog states
  const [isTransferDialogOpen, setIsTransferDialogOpen] = useState(false);
  const [isAdjustDialogOpen, setIsAdjustDialogOpen] = useState(false);

  // Form states
  const [transferFormData, setTransferFormData] = useState<StockTransferFormData>({
    product_id: '',
    from_warehouse_id: '',
    to_warehouse_id: '',
    quantity: 0,
    notes: '',
  });
  const [adjustFormData, setAdjustFormData] = useState<StockAdjustFormData>({
    product_id: '',
    warehouse_id: '',
    quantity: 0,
    low_stock_threshold: 10,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Build filters for API
  const filters = {
    ...(selectedWarehouse && { warehouse_id: selectedWarehouse }),
    ...(selectedProduct && { product_id: selectedProduct }),
    ...(searchQuery && { search: searchQuery }),
  };

  // API hooks
  const {
    data: stockData,
    isLoading: isLoadingStock,
    error: stockError,
    refetch: refetchStock,
  } = usePaginatedApi<StockLevel>('/stock', currentPage, 50, filters);

  const {
    data: lowStockResponse,
    isLoading: isLoadingLowStock,
    error: lowStockError,
    refetch: refetchLowStock,
  } = usePaginatedApi<StockLevel>('/stock/alerts');
  const lowStockData = lowStockResponse?.items ?? null;

  const {
    data: transfersData,
    isLoading: isLoadingTransfers,
    error: transfersError,
    refetch: refetchTransfers,
  } = usePaginatedApi<StockTransfer>('/stock/transfers', 1, 20, {});

  const {
    data: warehousesData,
  } = usePaginatedApi<Warehouse>('/warehouses');
  const warehouses = warehousesData?.items ?? null;

  const {
    data: productsData,
  } = usePaginatedApi<Product>('/products');
  const products = productsData?.items ?? null;

  const { mutate: transferMutate, isLoading: isTransferring } = useMutation();
  const { mutate: adjustMutate, isLoading: isAdjusting } = useMutation();

  // Reset forms
  const resetTransferForm = () => {
    setTransferFormData({
      product_id: '',
      from_warehouse_id: '',
      to_warehouse_id: '',
      quantity: 0,
      notes: '',
    });
    setFormErrors({});
  };

  const resetAdjustForm = () => {
    setAdjustFormData({
      product_id: '',
      warehouse_id: '',
      quantity: 0,
      low_stock_threshold: 10,
    });
    setFormErrors({});
  };

  // Validation
  const validateTransferForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!transferFormData.product_id) {
      errors.product_id = 'Product is required';
    }
    if (!transferFormData.from_warehouse_id) {
      errors.from_warehouse_id = 'Source warehouse is required';
    }
    if (!transferFormData.to_warehouse_id) {
      errors.to_warehouse_id = 'Destination warehouse is required';
    }
    if (transferFormData.from_warehouse_id === transferFormData.to_warehouse_id) {
      errors.to_warehouse_id = 'Source and destination warehouses must be different';
    }
    if (transferFormData.quantity <= 0) {
      errors.quantity = 'Quantity must be greater than 0';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const validateAdjustForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!adjustFormData.product_id) {
      errors.product_id = 'Product is required';
    }
    if (!adjustFormData.warehouse_id) {
      errors.warehouse_id = 'Warehouse is required';
    }
    if (adjustFormData.quantity < 0) {
      errors.quantity = 'Quantity cannot be negative';
    }
    if (adjustFormData.low_stock_threshold < 0) {
      errors.low_stock_threshold = 'Low stock threshold cannot be negative';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle transfer submission
  const handleTransferSubmit = async () => {
    if (!validateTransferForm()) return;

    try {
      await transferMutate('POST', '/stock/transfers', transferFormData);
      toast.success('Stock transfer completed successfully');
      setIsTransferDialogOpen(false);
      resetTransferForm();
      refetchStock();
      refetchTransfers();
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'Failed to transfer stock';
      toast.error(message);
    }
  };

  // Handle stock adjustment submission
  const handleAdjustSubmit = async () => {
    if (!validateAdjustForm()) return;

    try {
      await adjustMutate('PUT', '/stock/adjust', adjustFormData);
      toast.success('Stock level adjusted successfully');
      setIsAdjustDialogOpen(false);
      resetAdjustForm();
      refetchStock();
      refetchLowStock();
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'Failed to adjust stock level';
      toast.error(message);
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Check if stock is low
  const isLowStock = (stockLevel: StockLevel) => {
    return stockLevel.quantity < stockLevel.low_stock_threshold;
  };

  // Get available warehouses for transfer (exclude source warehouse)
  const getAvailableDestinations = () => {
    if (!warehouses) return [];
    return warehouses.filter(w =>
      w.is_active && w.id !== transferFormData.from_warehouse_id
    );
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-2xl">Stock Management</CardTitle>
              <CardDescription>
                Monitor stock levels, transfer inventory, and manage stock adjustments
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Dialog open={isAdjustDialogOpen} onOpenChange={setIsAdjustDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Settings2 className="mr-2 h-4 w-4" />
                    Adjust Stock
                  </Button>
                </DialogTrigger>
              </Dialog>
              <Dialog open={isTransferDialogOpen} onOpenChange={setIsTransferDialogOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <ArrowRightLeft className="mr-2 h-4 w-4" />
                    Transfer Stock
                  </Button>
                </DialogTrigger>
              </Dialog>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label htmlFor="search">Search Product</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
                <Input
                  id="search"
                  placeholder="Search by name or SKU..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="warehouse-filter">Warehouse</Label>
              <Select value={selectedWarehouse || "__all__"} onValueChange={(val) => setSelectedWarehouse(val === '__all__' ? '' : val)}>
                <SelectTrigger>
                  <SelectValue placeholder="All warehouses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All warehouses</SelectItem>
                  {warehouses?.map((warehouse) => (
                    <SelectItem key={warehouse.id} value={warehouse.id}>
                      {warehouse.name} ({warehouse.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="product-filter">Product</Label>
              <Select value={selectedProduct || "__all__"} onValueChange={(val) => setSelectedProduct(val === '__all__' ? '' : val)}>
                <SelectTrigger>
                  <SelectValue placeholder="All products" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All products</SelectItem>
                  {products?.filter(p => p.is_active).map((product) => (
                    <SelectItem key={product.id} value={product.id}>
                      {product.name} ({product.sku})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button variant="outline" onClick={() => {
                setSelectedWarehouse('');
                setSelectedProduct('');
                setSearchQuery('');
                setCurrentPage(1);
              }}>
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Content Tabs */}
      <Tabs defaultValue="stock-levels" className="space-y-4">
        <TabsList>
          <TabsTrigger value="stock-levels">
            Stock Levels
            {stockData?.total && <Badge variant="secondary" className="ml-2">{stockData.total}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="low-stock">
            Low Stock Alerts
            {lowStockData && <Badge variant="destructive" className="ml-2">{lowStockData.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="transfers">
            Transfer History
            {transfersData?.total && <Badge variant="secondary" className="ml-2">{transfersData.total}</Badge>}
          </TabsTrigger>
        </TabsList>

        {/* Stock Levels Tab */}
        <TabsContent value="stock-levels">
          <Card>
            <CardHeader>
              <CardTitle>Current Stock Levels</CardTitle>
            </CardHeader>
            <CardContent>
              {stockError && (
                <div className="text-center py-8">
                  <p className="text-red-500">Failed to load stock levels: {stockError}</p>
                  <Button onClick={refetchStock} variant="outline" className="mt-2">
                    Retry
                  </Button>
                </div>
              )}

              {isLoadingStock && (
                <div className="space-y-3">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              )}

              {!isLoadingStock && !stockError && (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product</TableHead>
                        <TableHead>SKU</TableHead>
                        <TableHead>Warehouse</TableHead>
                        <TableHead>Quantity</TableHead>
                        <TableHead>Threshold</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Last Updated</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {stockData?.items.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} className="text-center py-8">
                            No stock levels found. Adjust stock levels for products to see them here.
                          </TableCell>
                        </TableRow>
                      ) : (
                        stockData?.items.map((stock) => (
                          <TableRow key={stock.id} className={isLowStock(stock) ? 'bg-red-50' : ''}>
                            <TableCell className="font-medium">
                              {stock.product.name}
                            </TableCell>
                            <TableCell>
                              <code className="text-sm bg-gray-100 px-1 rounded">
                                {stock.product.sku}
                              </code>
                            </TableCell>
                            <TableCell>
                              {stock.warehouse.name}
                              <span className="text-gray-500 text-sm ml-1">
                                ({stock.warehouse.code})
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className={isLowStock(stock) ? 'font-bold text-red-600' : 'font-medium'}>
                                {stock.quantity}
                              </span>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {stock.low_stock_threshold}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {isLowStock(stock) ? (
                                <Badge variant="destructive" className="flex items-center gap-1 w-fit">
                                  <AlertTriangle className="h-3 w-3" />
                                  Low Stock
                                </Badge>
                              ) : (
                                <Badge variant="default">
                                  Normal
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-sm text-gray-500">
                              {formatDate(stock.updated_at)}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  {stockData && stockData.total > 50 && (
                    <div className="flex justify-between items-center mt-4">
                      <p className="text-sm text-gray-500">
                        Showing {((stockData.page - 1) * stockData.per_page) + 1} to{' '}
                        {Math.min(stockData.page * stockData.per_page, stockData.total)} of{' '}
                        {stockData.total} entries
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={currentPage === 1}
                          onClick={() => setCurrentPage(currentPage - 1)}
                        >
                          Previous
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={currentPage * 50 >= stockData.total}
                          onClick={() => setCurrentPage(currentPage + 1)}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Low Stock Alerts Tab */}
        <TabsContent value="low-stock">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                Low Stock Alerts
              </CardTitle>
              <CardDescription>
                Items that have fallen below their low stock threshold
              </CardDescription>
            </CardHeader>
            <CardContent>
              {lowStockError && (
                <div className="text-center py-8">
                  <p className="text-red-500">Failed to load low stock alerts: {lowStockError}</p>
                  <Button onClick={refetchLowStock} variant="outline" className="mt-2">
                    Retry
                  </Button>
                </div>
              )}

              {isLoadingLowStock && (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              )}

              {!isLoadingLowStock && !lowStockError && (
                <>
                  {lowStockData?.length === 0 ? (
                    <div className="text-center py-8">
                      <Package className="mx-auto h-12 w-12 text-green-500 mb-4" />
                      <p className="text-green-600 font-medium mb-2">All stock levels are healthy!</p>
                      <p className="text-gray-500">No items are below their low stock threshold.</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Product</TableHead>
                          <TableHead>SKU</TableHead>
                          <TableHead>Warehouse</TableHead>
                          <TableHead>Current Stock</TableHead>
                          <TableHead>Threshold</TableHead>
                          <TableHead>Shortage</TableHead>
                          <TableHead>Last Updated</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {lowStockData?.map((stock) => (
                          <TableRow key={stock.id} className="bg-red-50">
                            <TableCell className="font-medium">
                              {stock.product.name}
                            </TableCell>
                            <TableCell>
                              <code className="text-sm bg-gray-100 px-1 rounded">
                                {stock.product.sku}
                              </code>
                            </TableCell>
                            <TableCell>
                              {stock.warehouse.name}
                              <span className="text-gray-500 text-sm ml-1">
                                ({stock.warehouse.code})
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className="font-bold text-red-600">
                                {stock.quantity}
                              </span>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {stock.low_stock_threshold}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant="destructive">
                                {stock.low_stock_threshold - stock.quantity} needed
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm text-gray-500">
                              {formatDate(stock.updated_at)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transfer History Tab */}
        <TabsContent value="transfers">
          <Card>
            <CardHeader>
              <CardTitle>Transfer History</CardTitle>
              <CardDescription>
                Recent stock transfers between warehouses
              </CardDescription>
            </CardHeader>
            <CardContent>
              {transfersError && (
                <div className="text-center py-8">
                  <p className="text-red-500">Failed to load transfers: {transfersError}</p>
                  <Button onClick={refetchTransfers} variant="outline" className="mt-2">
                    Retry
                  </Button>
                </div>
              )}

              {isLoadingTransfers && (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              )}

              {!isLoadingTransfers && !transfersError && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Product</TableHead>
                      <TableHead>SKU</TableHead>
                      <TableHead>From</TableHead>
                      <TableHead>To</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Notes</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transfersData?.items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8">
                          No stock transfers found. Create a transfer to see it here.
                        </TableCell>
                      </TableRow>
                    ) : (
                      transfersData?.items.map((transfer) => (
                        <TableRow key={transfer.id}>
                          <TableCell className="font-medium">
                            {transfer.product.name}
                          </TableCell>
                          <TableCell>
                            <code className="text-sm bg-gray-100 px-1 rounded">
                              {transfer.product.sku}
                            </code>
                          </TableCell>
                          <TableCell>
                            {transfer.from_warehouse.name}
                            <span className="text-gray-500 text-sm ml-1">
                              ({transfer.from_warehouse.code})
                            </span>
                          </TableCell>
                          <TableCell>
                            {transfer.to_warehouse.name}
                            <span className="text-gray-500 text-sm ml-1">
                              ({transfer.to_warehouse.code})
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {transfer.quantity}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {transfer.notes ? (
                              <span className="text-sm">{transfer.notes}</span>
                            ) : (
                              <span className="text-gray-400 text-sm">No notes</span>
                            )}
                          </TableCell>
                          <TableCell className="text-sm text-gray-500">
                            {formatDate(transfer.created_at)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Transfer Dialog */}
      <Dialog open={isTransferDialogOpen} onOpenChange={setIsTransferDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Transfer Stock</DialogTitle>
            <DialogDescription>
              Move inventory from one warehouse to another. This operation is atomic and will update both warehouses instantly.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="transfer-product">Product</Label>
              <Select
                value={transferFormData.product_id}
                onValueChange={(value) => setTransferFormData(prev => ({ ...prev, product_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select product" />
                </SelectTrigger>
                <SelectContent>
                  {products?.filter(p => p.is_active).map((product) => (
                    <SelectItem key={product.id} value={product.id}>
                      {product.name} ({product.sku})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.product_id && <p className="text-sm text-red-500">{formErrors.product_id}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="transfer-from">From Warehouse</Label>
              <Select
                value={transferFormData.from_warehouse_id}
                onValueChange={(value) => setTransferFormData(prev => ({ ...prev, from_warehouse_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select source warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses?.filter(w => w.is_active).map((warehouse) => (
                    <SelectItem key={warehouse.id} value={warehouse.id}>
                      {warehouse.name} ({warehouse.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.from_warehouse_id && <p className="text-sm text-red-500">{formErrors.from_warehouse_id}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="transfer-to">To Warehouse</Label>
              <Select
                value={transferFormData.to_warehouse_id}
                onValueChange={(value) => setTransferFormData(prev => ({ ...prev, to_warehouse_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select destination warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {getAvailableDestinations().map((warehouse) => (
                    <SelectItem key={warehouse.id} value={warehouse.id}>
                      {warehouse.name} ({warehouse.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.to_warehouse_id && <p className="text-sm text-red-500">{formErrors.to_warehouse_id}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="transfer-quantity">Quantity</Label>
              <Input
                id="transfer-quantity"
                type="number"
                min="1"
                value={transferFormData.quantity || ''}
                onChange={(e) => setTransferFormData(prev => ({ ...prev, quantity: parseInt(e.target.value) || 0 }))}
                placeholder="Enter quantity to transfer"
              />
              {formErrors.quantity && <p className="text-sm text-red-500">{formErrors.quantity}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="transfer-notes">Notes (Optional)</Label>
              <Input
                id="transfer-notes"
                value={transferFormData.notes}
                onChange={(e) => setTransferFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Add notes about this transfer"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsTransferDialogOpen(false);
              resetTransferForm();
            }}>
              Cancel
            </Button>
            <Button onClick={handleTransferSubmit} disabled={isTransferring}>
              {isTransferring ? 'Transferring...' : 'Transfer Stock'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Adjust Stock Dialog */}
      <Dialog open={isAdjustDialogOpen} onOpenChange={setIsAdjustDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Adjust Stock Level</DialogTitle>
            <DialogDescription>
              Set the exact stock level for a product at a specific warehouse. This will override the current quantity.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="adjust-product">Product</Label>
              <Select
                value={adjustFormData.product_id}
                onValueChange={(value) => setAdjustFormData(prev => ({ ...prev, product_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select product" />
                </SelectTrigger>
                <SelectContent>
                  {products?.filter(p => p.is_active).map((product) => (
                    <SelectItem key={product.id} value={product.id}>
                      {product.name} ({product.sku})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.product_id && <p className="text-sm text-red-500">{formErrors.product_id}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="adjust-warehouse">Warehouse</Label>
              <Select
                value={adjustFormData.warehouse_id}
                onValueChange={(value) => setAdjustFormData(prev => ({ ...prev, warehouse_id: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {warehouses?.filter(w => w.is_active).map((warehouse) => (
                    <SelectItem key={warehouse.id} value={warehouse.id}>
                      {warehouse.name} ({warehouse.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.warehouse_id && <p className="text-sm text-red-500">{formErrors.warehouse_id}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="adjust-quantity">New Quantity</Label>
              <Input
                id="adjust-quantity"
                type="number"
                min="0"
                value={adjustFormData.quantity || ''}
                onChange={(e) => setAdjustFormData(prev => ({ ...prev, quantity: parseInt(e.target.value) || 0 }))}
                placeholder="Enter new quantity"
              />
              {formErrors.quantity && <p className="text-sm text-red-500">{formErrors.quantity}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="adjust-threshold">Low Stock Threshold</Label>
              <Input
                id="adjust-threshold"
                type="number"
                min="0"
                value={adjustFormData.low_stock_threshold || ''}
                onChange={(e) => setAdjustFormData(prev => ({ ...prev, low_stock_threshold: parseInt(e.target.value) || 0 }))}
                placeholder="Enter low stock threshold"
              />
              {formErrors.low_stock_threshold && <p className="text-sm text-red-500">{formErrors.low_stock_threshold}</p>}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsAdjustDialogOpen(false);
              resetAdjustForm();
            }}>
              Cancel
            </Button>
            <Button onClick={handleAdjustSubmit} disabled={isAdjusting}>
              {isAdjusting ? 'Adjusting...' : 'Adjust Stock'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}