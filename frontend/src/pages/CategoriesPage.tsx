import { useState } from 'react';
import { Plus, Edit, Trash2 } from 'lucide-react';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { usePaginatedApi, useMutation } from '@/hooks/useApi';

interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  parent_id: string | null;
  product_count?: number;
  parent?: {
    id: string;
    name: string;
    slug: string;
  };
  created_at: string;
  updated_at: string;
}

interface CategoryFormData {
  name: string;
  description: string;
  parent_id: string | null;
}

export default function CategoriesPage() {
  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);

  // Form state
  const [formData, setFormData] = useState<CategoryFormData>({
    name: '',
    description: '',
    parent_id: null,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // API hooks
  const {
    data: categoriesData,
    isLoading: isLoadingCategories,
    error: categoriesError,
    refetch: refetchCategories,
  } = usePaginatedApi<Category>('/categories');
  const categories = categoriesData?.items ?? null;

  const { mutate, isLoading: isMutating } = useMutation<Category, CategoryFormData>();

  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      parent_id: null,
    });
    setFormErrors({});
  };

  // Validation
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Category name is required';
    }

    // Prevent self-referencing
    if (selectedCategory && formData.parent_id === selectedCategory.id) {
      errors.parent_id = 'A category cannot be its own parent';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (isEdit = false) => {
    if (!validateForm()) return;

    try {
      const submitData = {
        ...formData,
        parent_id: formData.parent_id || null,
      };

      if (isEdit && selectedCategory) {
        await mutate('PUT', `/categories/${selectedCategory.id}`, submitData);
        toast.success('Category updated successfully');
        setIsEditDialogOpen(false);
      } else {
        await mutate('POST', '/categories', submitData);
        toast.success('Category created successfully');
        setIsCreateDialogOpen(false);
      }

      resetForm();
      setSelectedCategory(null);
      refetchCategories();
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'An error occurred';
      toast.error(message);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!selectedCategory) return;

    try {
      await mutate('DELETE', `/categories/${selectedCategory.id}`);
      toast.success('Category deleted successfully');
      setIsDeleteDialogOpen(false);
      setSelectedCategory(null);
      refetchCategories();
    } catch (error: unknown) {
      const message = error && typeof error === 'object' && 'response' in error && error.response && typeof error.response === 'object' && 'data' in error.response && error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'Failed to delete category';
      toast.error(message);
    }
  };

  // Handle edit
  const handleEdit = (category: Category) => {
    setSelectedCategory(category);
    setFormData({
      name: category.name,
      description: category.description || '',
      parent_id: category.parent_id || null,
    });
    setIsEditDialogOpen(true);
  };

  // Handle delete confirmation
  const handleDeleteConfirm = (category: Category) => {
    setSelectedCategory(category);
    setIsDeleteDialogOpen(true);
  };

  // Handle navigate to filtered products
  const handleViewProducts = (categoryId: string) => {
    // Navigate to products page with category filter
    window.location.href = `/products?category_id=${categoryId}`;
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  // Get available parent categories (excluding current category and its descendants)
  const getAvailableParents = () => {
    if (!categories) return [];

    return categories.filter(category => {
      // Exclude current category when editing
      if (selectedCategory && category.id === selectedCategory.id) {
        return false;
      }

      // Exclude categories that are children of the current category
      if (selectedCategory && category.parent_id === selectedCategory.id) {
        return false;
      }

      return true;
    });
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-2xl">Categories</CardTitle>
              <CardDescription>
                Organize your products into categories and subcategories
              </CardDescription>
            </div>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Category
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Create Category</DialogTitle>
                  <DialogDescription>
                    Add a new category to organize your products.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="name">Category Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Enter category name"
                    />
                    {formErrors.name && <p className="text-sm text-red-500">{formErrors.name}</p>}
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Enter category description"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="parent">Parent Category</Label>
                    <Select
                      value={formData.parent_id || ""}
                      onValueChange={(value) => setFormData(prev => ({ ...prev, parent_id: value || null }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select parent category (optional)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">No parent category</SelectItem>
                        {getAvailableParents().map((category) => (
                          <SelectItem key={category.id} value={category.id}>
                            {category.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {formErrors.parent_id && <p className="text-sm text-red-500">{formErrors.parent_id}</p>}
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
                    {isMutating ? 'Creating...' : 'Create Category'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {/* Error state */}
          {categoriesError && (
            <div className="text-center py-8">
              <p className="text-red-500">Failed to load categories: {categoriesError}</p>
              <Button onClick={refetchCategories} variant="outline" className="mt-2">
                Retry
              </Button>
            </div>
          )}

          {/* Loading state */}
          {isLoadingCategories && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          )}

          {/* Data table */}
          {!isLoadingCategories && !categoriesError && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Parent Category</TableHead>
                  <TableHead>Product Count</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {categories?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      No categories found. Create your first category to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  categories?.map((category) => (
                    <TableRow key={category.id}>
                      <TableCell className="font-medium">
                        <div
                          className="cursor-pointer hover:text-blue-600"
                          onClick={() => handleViewProducts(category.id)}
                          title="Click to view products in this category"
                        >
                          {category.name}
                        </div>
                      </TableCell>
                      <TableCell>
                        {category.description ? (
                          <div className="max-w-xs truncate" title={category.description}>
                            {category.description}
                          </div>
                        ) : (
                          <span className="text-gray-400">No description</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {category.parent ? (
                          <Badge variant="outline">{category.parent.name}</Badge>
                        ) : (
                          <span className="text-gray-400">Root category</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div
                          className="cursor-pointer hover:text-blue-600"
                          onClick={() => handleViewProducts(category.id)}
                        >
                          <Badge variant="secondary">
                            {category.product_count || 0} products
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <code className="text-sm bg-gray-100 px-1 rounded">
                          {category.slug}
                        </code>
                      </TableCell>
                      <TableCell>{formatDate(category.created_at)}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              •••
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem onClick={() => handleEdit(category)}>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleDeleteConfirm(category)}
                              className="text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
            <DialogDescription>
              Make changes to the category information.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Category Name</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter category name"
              />
              {formErrors.name && <p className="text-sm text-red-500">{formErrors.name}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Enter category description"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-parent">Parent Category</Label>
              <Select
                value={formData.parent_id || ""}
                onValueChange={(value) => setFormData(prev => ({ ...prev, parent_id: value || null }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select parent category (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No parent category</SelectItem>
                  {getAvailableParents().map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.parent_id && <p className="text-sm text-red-500">{formErrors.parent_id}</p>}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsEditDialogOpen(false);
              resetForm();
              setSelectedCategory(null);
            }}>
              Cancel
            </Button>
            <Button onClick={() => handleSubmit(true)} disabled={isMutating}>
              {isMutating ? 'Updating...' : 'Update Category'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Category</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedCategory?.name}"? This action cannot be undone.
              {selectedCategory?.product_count && selectedCategory.product_count > 0 && (
                <span className="block mt-2 font-medium text-red-600">
                  This category contains {selectedCategory.product_count} products and cannot be deleted.
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsDeleteDialogOpen(false);
              setSelectedCategory(null);
            }}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isMutating || Boolean(selectedCategory?.product_count && selectedCategory.product_count > 0)}
            >
              {isMutating ? 'Deleting...' : 'Delete Category'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}