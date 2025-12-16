// static/app.js
let socket;
let currentInventory = [];
let currentEditingItem = null;
let categoryChart = null;
let stockChart = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
    loadInventory();
    updateTime();
    setInterval(updateTime, 60000); // Update time every minute
});

// Socket.IO connection
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
    });
    
    socket.on('inventory_update', function(inventory) {
        console.log('Inventory updated via socket');
        currentInventory = inventory.items || [];
        renderInventory();
        updateAnalytics();
        updateCharts();
    });
}

// Load inventory from server
function loadInventory() {
    fetch('/api/inventory')
        .then(response => response.json())
        .then(data => {
            currentInventory = data.items || [];
            renderInventory();
            updateAnalytics();
            updateCharts();
        })
        .catch(error => {
            showToast('Error loading inventory', 'error');
            console.error('Error:', error);
        });
}

// Render inventory table
function renderInventory() {
    const tbody = document.getElementById('inventory-body');
    const searchTerm = document.getElementById('search-inventory').value.toLowerCase();
    const categoryFilter = document.getElementById('category-filter').value;
    
    // Filter items
    let filteredItems = currentInventory.filter(item => {
        const matchesSearch = item.name.toLowerCase().includes(searchTerm) ||
                             item.category.toLowerCase().includes(searchTerm) ||
                             item.color.toLowerCase().includes(searchTerm);
        const matchesCategory = !categoryFilter || item.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });
    
    // Update category filter options
    updateCategoryFilter();
    
    if (filteredItems.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center" style="text-align: center; padding: 40px;">
                    <i class="fas fa-box-open" style="font-size: 48px; color: #ccc; margin-bottom: 15px;"></i>
                    <p>No items found. Add your first item!</p>
                </td>
            </tr>
        `;
    } else {
        let html = '';
        let pageTotal = 0;
        let pageValue = 0;
        
        filteredItems.forEach(item => {
            const totalValue = item.price * item.quantity;
            pageTotal += item.quantity;
            pageValue += totalValue;
            
            html += `
                <tr>
                    <td><strong>${escapeHtml(item.name)}</strong></td>
                    <td><span class="category-badge">${escapeHtml(item.category)}</span></td>
                    <td>${escapeHtml(item.size)}</td>
                    <td>
                        <span class="color-indicator" style="background-color: ${getColorCode(item.color)}"></span>
                        ${escapeHtml(item.color)}
                    </td>
                    <td class="price-cell">KSH ${formatNumber(item.price.toFixed(2))}</td>
                    <td>
                        <span class="quantity-badge ${item.quantity < 10 ? 'low-stock' : ''}">
                            ${item.quantity}
                        </span>
                    </td>
                    <td class="value-cell">KSH ${formatNumber(totalValue.toFixed(2))}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-action btn-edit" onclick="editItem('${item.id}')" 
                                    title="Edit Item">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-action btn-qty" onclick="editQuantity('${item.id}')" 
                                    title="Update Quantity">
                                <i class="fas fa-calculator"></i>
                            </button>
                            <button class="btn-action btn-delete" onclick="deleteItem('${item.id}')" 
                                    title="Delete Item">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        tbody.innerHTML = html;
        
        // Update summary
        document.getElementById('showing-count').textContent = filteredItems.length;
        document.getElementById('page-total').textContent = formatNumber(pageTotal);
        document.getElementById('page-value').textContent = formatNumber(pageValue.toFixed(2));
    }
}

// Update category filter dropdown
function updateCategoryFilter() {
    const categories = [...new Set(currentInventory.map(item => item.category))];
    const filterSelect = document.getElementById('category-filter');
    
    // Keep current value
    const currentValue = filterSelect.value;
    
    // Clear options except "All Categories"
    filterSelect.innerHTML = '<option value="">All Categories</option>';
    
    // Add category options
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        filterSelect.appendChild(option);
    });
    
    // Restore previous selection
    filterSelect.value = currentValue;
}

// Filter inventory based on search and category
function filterInventory() {
    renderInventory();
}

// Update analytics dashboard
function updateAnalytics() {
    let totalItems = 0;
    let totalValue = 0;
    let categories = new Set();
    let lowStockCount = 0;
    
    currentInventory.forEach(item => {
        totalItems += item.quantity;
        totalValue += item.price * item.quantity;
        categories.add(item.category);
        if (item.quantity < 10) {
            lowStockCount++;
        }
    });
    
    document.getElementById('total-items').textContent = formatNumber(totalItems);
    document.getElementById('total-value').textContent = `KSH ${formatNumber(totalValue.toFixed(2))}`;
    document.getElementById('category-count').textContent = categories.size;
    document.getElementById('low-stock-count').textContent = lowStockCount;
}

// Update charts
function updateCharts() {
    // Category distribution
    const categoryData = {};
    currentInventory.forEach(item => {
        categoryData[item.category] = (categoryData[item.category] || 0) + item.quantity;
    });
    
    const ctx1 = document.getElementById('categoryChart').getContext('2d');
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    categoryChart = new Chart(ctx1, {
        type: 'pie',
        data: {
            labels: Object.keys(categoryData),
            datasets: [{
                data: Object.values(categoryData),
                backgroundColor: [
                    '#4a4a9c', '#6c63ff', '#28a745', '#dc3545', 
                    '#ffc107', '#17a2b8', '#6610f2', '#fd7e14'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    // Stock levels (top 10 items)
    const sortedByStock = [...currentInventory]
        .sort((a, b) => b.quantity - a.quantity)
        .slice(0, 10);
    
    const ctx2 = document.getElementById('stockChart').getContext('2d');
    if (stockChart) {
        stockChart.destroy();
    }
    
    stockChart = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: sortedByStock.map(item => item.name.substring(0, 15) + (item.name.length > 15 ? '...' : '')),
            datasets: [{
                label: 'Quantity in Stock',
                data: sortedByStock.map(item => item.quantity),
                backgroundColor: sortedByStock.map(item => 
                    item.quantity < 10 ? '#dc3545' : '#28a745'
                )
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Show add item modal
function showAddItemModal() {
    currentEditingItem = null;
    document.getElementById('modal-title').textContent = 'Add New Clothing Item';
    document.getElementById('submit-btn-text').textContent = 'Add Item';
    document.getElementById('itemForm').reset();
    document.getElementById('item-id').value = '';
    document.getElementById('itemModal').style.display = 'block';
}

// Show edit item modal
function editItem(itemId) {
    const item = currentInventory.find(i => i.id === itemId);
    if (!item) return;
    
    currentEditingItem = item;
    document.getElementById('modal-title').textContent = 'Edit Clothing Item';
    document.getElementById('submit-btn-text').textContent = 'Update Item';
    document.getElementById('item-id').value = item.id;
    document.getElementById('item-name').value = item.name;
    document.getElementById('item-category').value = item.category;
    document.getElementById('item-size').value = item.size;
    document.getElementById('item-color').value = item.color;
    document.getElementById('item-price').value = item.price;
    document.getElementById('item-quantity').value = item.quantity;
    document.getElementById('itemModal').style.display = 'block';
}

// Handle form submission
document.getElementById('itemForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('item-name').value.trim(),
        category: document.getElementById('item-category').value,
        size: document.getElementById('item-size').value.trim(),
        color: document.getElementById('item-color').value.trim(),
        price: parseFloat(document.getElementById('item-price').value),
        quantity: parseInt(document.getElementById('item-quantity').value)
    };
    
    // Validate
    if (!formData.name || !formData.category || !formData.size || !formData.color || 
        isNaN(formData.price) || isNaN(formData.quantity)) {
        showToast('Please fill all required fields correctly', 'error');
        return;
    }
    
    const itemId = document.getElementById('item-id').value;
    const url = itemId ? '/api/update_item' : '/api/add_item';
    
    if (itemId) {
        formData.id = itemId;
    }
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(itemId ? 'Item updated successfully!' : 'Item added successfully!', 'success');
            closeModal();
            loadInventory(); // Reload to get updated data
        } else {
            showToast(data.error || 'Operation failed', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Network error. Please try again.', 'error');
    });
});

// Show edit quantity modal
function editQuantity(itemId) {
    const item = currentInventory.find(i => i.id === itemId);
    if (!item) return;
    
    currentEditingItem = item;
    document.getElementById('edit-item-name').textContent = item.name;
    document.getElementById('current-quantity').textContent = item.quantity;
    document.getElementById('new-quantity').value = item.quantity;
    document.getElementById('quantityModal').style.display = 'block';
}

// Adjust quantity buttons
function adjustQuantity(change) {
    const input = document.getElementById('new-quantity');
    let newValue = parseInt(input.value) + change;
    if (newValue < 0) newValue = 0;
    input.value = newValue;
}

// Save quantity update
function saveQuantity() {
    if (!currentEditingItem) return;
    
    const newQuantity = parseInt(document.getElementById('new-quantity').value);
    
    if (isNaN(newQuantity) || newQuantity < 0) {
        showToast('Please enter a valid quantity', 'error');
        return;
    }
    
    fetch('/api/update_quantity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            item_id: currentEditingItem.id,
            quantity: newQuantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const change = newQuantity - data.old_quantity;
            const changeText = change >= 0 ? `+${change}` : change;
            showToast(`Quantity updated: ${changeText} items`, 'success');
            closeQuantityModal();
            loadInventory();
        } else {
            showToast(data.error || 'Failed to update quantity', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Network error. Please try again.', 'error');
    });
}

// Delete item
function deleteItem(itemId) {
    if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
        return;
    }
    
    fetch('/api/delete_item', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: itemId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Item deleted successfully', 'success');
            loadInventory();
        } else {
            showToast(data.error || 'Failed to delete item', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Network error. Please try again.', 'error');
    });
}

// Close modals
function closeModal() {
    document.getElementById('itemModal').style.display = 'none';
}

function closeQuantityModal() {
    document.getElementById('quantityModal').style.display = 'none';
    currentEditingItem = null;
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function getColorCode(colorName) {
    const colorMap = {
        'red': '#dc3545',
        'blue': '#007bff',
        'green': '#28a745',
        'yellow': '#ffc107',
        'black': '#343a40',
        'white': '#f8f9fa',
        'purple': '#6f42c1',
        'pink': '#e83e8c',
        'orange': '#fd7e14',
        'brown': '#8b4513',
        'gray': '#6c757d'
    };
    
    return colorMap[colorName.toLowerCase()] || '#6c757d';
}

function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
    });
    const dateString = now.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    document.getElementById('current-time').textContent = 
        `${dateString} | ${timeString}`;
}

// Close modal when clicking outside
window.onclick = function(event) {
    const itemModal = document.getElementById('itemModal');
    const quantityModal = document.getElementById('quantityModal');
    
    if (event.target === itemModal) {
        closeModal();
    }
    if (event.target === quantityModal) {
        closeQuantityModal();
    }
};
