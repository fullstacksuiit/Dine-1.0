# DinePay 🍽️

**DinePay** - A comprehensive restaurant management system built with Django, designed to streamline restaurant operations from order management to billing and reporting.

## 📖 Project Overview

Restaurant-365 is a complete restaurant management solution that handles:

- **Multi-Platform Order Management** - Dine-in, takeaway, and delivery orders
- **Digital Menu Management** - Create and organize menu items with course categorization
- **Kitchen Order Tickets (KOT)** - Real-time order tracking with status updates
- **Smart Billing System** - GST/CGST compliant invoicing with tax calculations
- **Public Menu & QR Codes** - Generate QR codes for contactless menu viewing
- **Role-Based Access Control** - Owner, Manager, and Waiter roles with permissions
- **Multi-Platform Pricing** - Different pricing for Restaurant, Zomato, and Swiggy
- **WhatsApp Bill Sharing** - Share bills with payment links/QR codes
- **Reporting & Analytics** - Sales reports and GST compliance

## 🛠️ Technology Stack

- **Backend**: Django 5.2, Django REST Framework
- **Database**: SQLite (development), PostgreSQL-ready
- **Frontend**: Vue.js 2, Bootstrap, Feather Icons
- **Authentication**: Django Auth with custom middleware
- **APIs**: RESTful APIs with dj-rest-auth

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Git

### Clone and Setup

1. **Clone the Repository**

```bash
git clone https://github.com/strix-inc/Restaurant-365.git
cd Restaurant-365
```

1. **Set up Virtual Environment**

**Using venv:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Using conda:**

```bash
conda create -n restaurant365 python=3.8
conda activate restaurant365
```

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

1. **Database Setup**

```bash
python manage.py migrate
```

1. **Create Superuser (Optional)**

```bash
python manage.py createsuperuser
```

1. **Run Development Server**

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

### Initial Setup Commands

**Onboard a Restaurant:**

```bash
python manage.py onboard_restaurant "Your Restaurant Name"
```

**Add Staff Members:**

```bash
python manage.py add_staff <username> <role> <restaurant_id> --password <password>
```

**Roles available:** `owner`, `manager`, `waiter`

## 📝 License

This project is developed by [Strix](https://strix.co.in) as DinePay restaurant management solution.

**DinePay** - Streamlining restaurant operations, one order at a time. 🍽️ ✨
