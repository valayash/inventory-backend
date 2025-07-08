# Inventory Management System - Backend

This is the backend for the Inventory Management System, built with Django and Django REST Framework. It provides a robust API for managing shops, products, inventory, sales, and analytics for a multi-shop eyewear distribution business.

## Key Features

*   **User Roles**: JWT-based authentication with two distinct user roles: `DISTRIBUTOR` and `SHOP_OWNER`.
*   **Product Catalog**: Manage a detailed catalog of eyeglass frames, including brands, colors, materials, and types.
*   **Shop Management**: Distributors can create, view, edit, and delete shops for their clients.
*   **Quantity-Based Inventory**: A comprehensive inventory system that tracks stock levels (`quantity_received`, `quantity_sold`, `quantity_remaining`) for each frame in each shop.
*   **Inventory Transactions**: A complete audit trail for all stock movements, including `STOCK_IN`, `SALE`, and `ADJUSTMENT`.
*   **Bulk Operations**:
    *   **CSV Upload**: Distributors can upload CSV files to add new frame types and update stock levels.
    *   **Inventory Distribution**: A powerful interface for distributors to send specific quantities of frames to multiple shops in a single operation.
*   **Financial Summaries**: The system automatically generates monthly financial summaries for each shop, tracking revenue, costs, and profit.
*   **Analytics Dashboards**: A suite of powerful API endpoints to drive analytics for both distributors and shop owners, including:
    *   Sales trends (daily, weekly, monthly)
    *   Top-selling products and frame-lens combinations
    *   Slow-moving inventory
    *   Shop performance comparisons
    *   Low-stock alerts

## Technology Stack

*   **Framework**: Django
*   **API**: Django REST Framework (DRF)
*   **Authentication**: Simple JWT for token-based authentication
*   **Database**: PostgresQL (default, configurable in `settings.py`)
*   **CORS**: `django-cors-headers` for handling cross-origin requests

## Setup and Installation

Follow these steps to get the backend server up and running on your local machine.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd inventory-management-system/inventory-backend
```

### 2. Create a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows, use:
```bash
venv\Scripts\activate
```

### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations

Run the Django `migrate` command to apply all database migrations and create the necessary tables.

```bash
python3 manage.py migrate
```

### 5. Create a Superuser (Optional)

To access the Django admin panel, you'll need a superuser account.

```bash
python3 manage.py createsuperuser
```

Follow the prompts to create your admin account.

### 6. Run the Development Server

Start the Django development server. By default, it runs on port 8000, but we'll specify port 8001 to avoid conflicts with a frontend server.

```bash
python3 manage.py runserver 8001
```

The backend API will now be accessible at `http://127.0.0.1:8001/`.

## API Endpoints

The API is browsable via DRF's interface. Below is a summary of the main endpoints available, categorized by functionality.

### Authentication
- `POST /api/token/`: Obtain a JWT token pair (access and refresh) by providing user credentials.
- `POST /api/token/refresh/`: Refresh an expired access token using a valid refresh token.

### Distributor Portal: Shop Management
- `GET /api/shops/`: Retrieve a list of all shops.
- `POST /api/shops/`: Create a new shop.
- `GET /api/shops/{id}/`: Retrieve details for a specific shop.
- `PUT /api/shops/{id}/`: Update a specific shop's information.
- `DELETE /api/shops/{id}/`: Delete a specific shop.

### Distributor Portal: Product & Inventory Management
- `GET /api/frames/`: List all product frames in the catalog. Supports searching and filtering.
- `POST /api/frames/`: Add a new frame to the product catalog.
- `POST /api/stock-in/`: Add new stock to a specific shop's inventory.
- `POST /api/inventory-csv-upload/`: Bulk upload new inventory items from a CSV file.
- `GET /api/distribution/`: Get all necessary data for the inventory distribution dashboard (shops, frames, etc.).
- `POST /api/distribution/bulk/`: Distribute specified quantities of frames to multiple shops in a single bulk transaction.

### Distributor Portal: Billing & Reporting
- `GET /api/shops/{id}/inventory/`: View detailed inventory for a specific shop.
- `GET /api/shops/{id}/billing-report/`: Generate a detailed monthly billing report for a specific shop, including itemized sales.

### Shop Owner Portal: Operations
- `GET /api/shop-inventory/`: Get the inventory for the authenticated shop owner's shop. Supports searching and filtering.
- `POST /api/process-sale/`: Record a sale for a specific inventory item, which updates stock levels and financial summaries.

### Analytics Dashboards
Both Distributor and Shop Owner dashboards are powered by a suite of analytics endpoints.

**Distributor Analytics (`/api/dashboard/`)**
- `GET sales-trends/`: Get sales trends over time (day, week, month).
- `GET top-products/`: List top-selling products by sales count.
- `GET top-products-with-lens/`: List top-selling frame and lens combinations.
- `GET slow-moving-inventory/`: Identify items that have been in stock for an extended period (e.g., >90 days).
- `GET shop-performance/`: Compare performance metrics across all shops.
- `GET revenue-summary/`: View overall and per-shop revenue summaries.
- `GET low-stock-alerts/`: Get alerts for items with low stock levels across all shops.
- `GET sales-report/`: Generate monthly or quarterly sales reports.

**Shop Owner Analytics (`/api/dashboard/shop/`)**
- `GET summary/`: Get key performance indicators (sales, revenue, stock count) for the shop's dashboard.
- `GET sales-trends/`: Get sales trends for the specific shop.
- `GET top-products/`: List top-selling products for the shop.
- `GET top-products-with-lens/`: List top-selling combinations for the shop.
- `GET slow-moving-inventory/`: Identify slow-moving items for the shop.
- `GET low-stock-alerts/`: Get low-stock alerts for the shop.
- `GET sales-report/`: Generate monthly or quarterly sales reports for the shop.
