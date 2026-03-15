import { useState, useEffect } from 'react';
import { Filter, Calendar, Search, ChevronDown, ChevronRight } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
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
import { Separator } from '@/components/ui/separator';
import { usePaginatedApi } from '@/hooks/useApi';

interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
  user?: {
    id: string;
    email: string;
    username: string;
  };
}

export default function AuditPage() {
  // State management
  const [selectedAction, setSelectedAction] = useState<string>('');
  const [selectedEntityType, setSelectedEntityType] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage] = useState(50);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Build filters
  const filters: Record<string, unknown> = {
    ...(searchTerm && { search: searchTerm }),
    ...(selectedAction && { action: selectedAction }),
    ...(selectedEntityType && { resource_type: selectedEntityType }),
    ...(dateFrom && { date_from: dateFrom }),
    ...(dateTo && { date_to: dateTo }),
  };

  // API hook
  const {
    data: auditResponse,
    isLoading: isLoadingAudit,
    error: auditError,
    refetch: refetchAudit,
  } = usePaginatedApi<AuditLog>('/audit', currentPage, perPage, filters);

  // Handle search with debouncing
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setCurrentPage(1);
      refetchAudit();
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, selectedAction, selectedEntityType, dateFrom, dateTo, refetchAudit]);

  // Handle pagination
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Toggle row expansion
  const toggleRowExpansion = (id: string) => {
    const newExpandedRows = new Set(expandedRows);
    if (newExpandedRows.has(id)) {
      newExpandedRows.delete(id);
    } else {
      newExpandedRows.add(id);
    }
    setExpandedRows(newExpandedRows);
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Format JSON details
  const formatDetails = (details: Record<string, unknown>) => {
    return JSON.stringify(details, null, 2);
  };

  // Get action color
  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'create':
        return 'default';
      case 'update':
        return 'secondary';
      case 'delete':
        return 'destructive';
      case 'transfer':
        return 'outline';
      default:
        return 'outline';
    }
  };

  // Clear all filters
  const clearFilters = () => {
    setSelectedAction('');
    setSelectedEntityType('');
    setDateFrom('');
    setDateTo('');
    setSearchTerm('');
    setCurrentPage(1);
  };

  const totalPages = Math.ceil((auditResponse?.total || 0) / perPage);
  const hasActiveFilters = selectedAction || selectedEntityType || dateFrom || dateTo || searchTerm;

  return (
    <div className="container mx-auto px-4 py-6">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-2xl">Audit Log</CardTitle>
              <CardDescription>
                View system activity and changes
              </CardDescription>
            </div>
            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>

            <Select value={selectedAction} onValueChange={setSelectedAction}>
              <SelectTrigger>
                <SelectValue placeholder="All actions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All actions</SelectItem>
                <SelectItem value="create">Create</SelectItem>
                <SelectItem value="update">Update</SelectItem>
                <SelectItem value="delete">Delete</SelectItem>
                <SelectItem value="transfer">Transfer</SelectItem>
                <SelectItem value="login">Login</SelectItem>
                <SelectItem value="logout">Logout</SelectItem>
              </SelectContent>
            </Select>

            <Select value={selectedEntityType} onValueChange={setSelectedEntityType}>
              <SelectTrigger>
                <SelectValue placeholder="All entity types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All entity types</SelectItem>
                <SelectItem value="product">Product</SelectItem>
                <SelectItem value="category">Category</SelectItem>
                <SelectItem value="warehouse">Warehouse</SelectItem>
                <SelectItem value="stock_level">Stock Level</SelectItem>
                <SelectItem value="stock_transfer">Stock Transfer</SelectItem>
                <SelectItem value="user">User</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex flex-col gap-1">
              <Label htmlFor="date-from" className="text-xs text-gray-500">
                From Date
              </Label>
              <Input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-1">
              <Label htmlFor="date-to" className="text-xs text-gray-500">
                To Date
              </Label>
              <Input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>

          {/* Error state */}
          {auditError && (
            <div className="text-center py-8">
              <p className="text-red-500">Failed to load audit log: {auditError}</p>
              <Button onClick={refetchAudit} variant="outline" className="mt-2">
                Retry
              </Button>
            </div>
          )}

          {/* Loading state */}
          {isLoadingAudit && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}

          {/* Data table */}
          {!isLoadingAudit && !auditError && (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Entity Type</TableHead>
                    <TableHead>Entity ID</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>IP Address</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditResponse?.items?.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        No audit logs found. Try adjusting your filters.
                      </TableCell>
                    </TableRow>
                  ) : (
                    <>
                      {auditResponse?.items?.map((log) => (
                        <>
                          <TableRow key={log.id} className="cursor-pointer hover:bg-muted/50">
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => toggleRowExpansion(log.id)}
                                className="p-1"
                              >
                                {expandedRows.has(log.id) ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </Button>
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {formatDate(log.created_at)}
                            </TableCell>
                            <TableCell>
                              <Badge variant={getActionColor(log.action)}>
                                {log.action}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {log.resource_type}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {log.resource_id.slice(0, 8)}...
                            </TableCell>
                            <TableCell>
                              {log.user ? (
                                <div className="flex flex-col">
                                  <span className="font-medium">{log.user.username}</span>
                                  <span className="text-sm text-gray-500">{log.user.email}</span>
                                </div>
                              ) : (
                                <span className="text-gray-400">System</span>
                              )}
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {log.ip_address || 'N/A'}
                            </TableCell>
                          </TableRow>

                          {/* Expandable details row */}
                          {expandedRows.has(log.id) && (
                            <TableRow>
                              <TableCell></TableCell>
                              <TableCell colSpan={6}>
                                <div className="py-4">
                                  <div className="mb-2">
                                    <h4 className="font-semibold text-sm mb-2">Details:</h4>
                                  </div>
                                  <div className="bg-muted rounded-md p-3 overflow-x-auto">
                                    <pre className="text-xs whitespace-pre-wrap font-mono">
                                      {formatDetails(log.details)}
                                    </pre>
                                  </div>
                                  <Separator className="mt-4" />
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </>
                      ))}
                    </>
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-600">
                    Showing {((currentPage - 1) * perPage) + 1} to{' '}
                    {Math.min(currentPage * perPage, auditResponse?.total || 0)} of{' '}
                    {auditResponse?.total || 0} audit logs
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <span className="text-sm">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
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
    </div>
  );
}