# Warehouse Automation System

An intelligent warehouse management system built with Django that automates order processing through email communication and AI-powered response parsing.

## Features

- **RESTful API** for product and order management
- **Automated Email Notifications** to warehouse staff when orders are placed
- **Intelligent Email Parsing** using Google's Gemini AI to process warehouse responses
- **Real-time Order Status Updates** based on email confirmations/rejections
- **Asynchronous Task Processing** with Celery and Redis
- **Docker Support** for easy deployment
- **PostgreSQL Database** for reliable data storage

## Table of Contents

- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Background Tasks](#background-tasks)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## System Architecture

The system works in the following workflow:

1. **Order Creation**: Customer places an order via REST API
2. **Email Notification**: System automatically emails warehouse staff with order details
3. **Warehouse Response**: Warehouse staff responds via email (confirm/reject)
4. **Email Monitoring**: Celery task periodically checks inbox for new emails
5. **AI Parsing**: Gemini AI extracts order ID and status from email content
6. **Status Update**: Order status is automatically updated in the database

##  Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Docker & Docker Compose (optional)
- Gmail account (for IMAP email monitoring)
- Google API Key (for Gemini AI)

##  Installation

### Option 1: Local Setup

1. **Clone the repository**
   
   git clone <repository-url>
   cd warehouse_automation
   

2. **Create virtual environment**
   
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   

3. **Install dependencies**
   
   pip install -r requirements.txt
   

4. **Set up environment variables**
   
   cp env.example .env
   # Edit .env with your configuration
   

5. **Run database migrations**
   
   python manage.py migrate
   

6. **Create superuser (optional)**
   
   python manage.py createsuperuser
   

7. **Start the development server**
  
   python manage.py runserver
   

8. **Start Celery worker** (in a new terminal)
   
   celery -A warehouse_automation worker --loglevel=info
   

9. **Start Celery beat** (in another terminal)
   
   celery -A warehouse_automation beat --loglevel=info
   

### Option 2: Docker Setup

1. **Build and start containers**
   
   docker-compose up --build
   

2. **Run migrations**
   
   docker-compose exec web python manage.py migrate
   

3. **Create superuser**
   
   docker-compose exec web python manage.py createsuperuser
  
##  Configuration

Edit the `.env` file with your settings:

### Database Configuration

DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432


### Django Settings

SECRET_KEY=your-secret-key-here
DEBUG=True


### Celery Configuration

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0


### Email Configuration (Gmail)

EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password


### IMAP Configuration (for monitoring inbox)

CONNECTED_MAILBOX=monitoring-email@gmail.com
WAREHOUSE_EMAIL=warehouse-staff@gmail.com
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_PASSWORD=app-password-for-monitoring-email


### Google Gemini AI

GOOGLE_API_KEY=your-google-api-key


### 📧 Setting up Gmail App Passwords

1. Enable 2-Factor Authentication on your Gmail account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Use this password in `EMAIL_HOST_PASSWORD` and `IMAP_PASSWORD`

##  Usage

### Adding Products

Use Django admin panel or create via API:


python manage.py shell



from orders.models import Product
Product.objects.create(name="Widget A", cost=29.99)
Product.objects.create(name="Gadget B", cost=49.99)


### Creating Orders

Send a POST request to `/api/orders/create/`:


{
  "customer_name": "John Doe",
  "customer_id": "CUST001",
  "user_email": "john@example.com",
  "product": 1,
  "quantity": 5
}


##  API Endpoints

### Products

- **GET** `/api/products/` - List all products
  ```bash
  curl http://localhost:8000/api/products/
  ```

### Orders

- **POST** `/api/orders/create/` - Create a new order
  ```bash
  curl -X POST http://localhost:8000/api/orders/create/ \
    -H "Content-Type: application/json" \
    -d '{
      "customer_name": "John Doe",
      "customer_id": "CUST001",
      "user_email": "john@example.com",
      "product": 1,
      "quantity": 5
    }'
  ```

### Response Format

**Success Response:**
```json
{
  "id": 1,
  "customer_name": "John Doe",
  "customer_id": "CUST001",
  "user_email": "john@example.com",
  "product": 1,
  "quantity": 5,
  "total_cost": "149.95",
  "status": "Order Placed",
  "created_at": "2024-01-15T10:30:00Z"
}
```

##  Background Tasks

### 1. Send Warehouse Confirmation Email

**Task**: `send_warehouse_confirmation_email`
- Triggered automatically when an order is created
- Sends email to warehouse staff with order details
- Includes a "Click to Confirm" button that opens a mailto link

### 2. Check Warehouse Inbox

**Task**: `check_warehouse_inbox`
- Runs periodically (configured in Celery Beat schedule)
- Connects to IMAP server and reads unread emails
- Uses Gemini AI to parse email content
- Updates order status based on warehouse response
- Marks emails as read after processing

**Supported Status Updates:**
- `Confirmed` - Order ready for dispatch
- `Rejected` - Order cannot be fulfilled

**Email Response Format:**
Warehouse staff can reply with simple messages like:
- "Order #123 is confirmed and ready"
- "CONFIRM: Order #123"
- "Cannot fulfill order #123 - out of stock"

##  Deployment

### Docker Compose

The project includes Docker configuration for production deployment:


services:
  - web (Django + Gunicorn)
  - celery_worker
  - celery_beat
  - redis
  - db (PostgreSQL)
  - nginx


**Start all services:**

docker-compose up -d


**View logs:**

docker-compose logs -f


**Stop services:**

docker-compose down


##  Project Structure


warehouse_automation/
├── warehouse_automation/       # Main project settings
│   ├── settings.py            # Django configuration
│   ├── celery.py              # Celery configuration
│   ├── urls.py                # URL routing
│   └── wsgi.py                # WSGI configuration
├── orders/                    # Orders app
│   ├── models.py              # Product & Order models
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # API views
│   ├── tasks.py               # Celery tasks
│   ├── llm_parser.py          # AI email parsing
│   └── urls.py                # App URL routing
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Docker image definition
├── entrypoint.sh              # Docker entrypoint script
├── nginx.conf                 # Nginx configuration
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
└── .env                       # Environment variables


##  Models

### Product
- `name` - Product name
- `cost` - Product price (decimal)

### Order
- `customer_name` - Customer's full name
- `customer_id` - Unique customer identifier
- `user_email` - Customer's email address
- `product` - Foreign key to Product
- `quantity` - Order quantity
- `total_cost` - Auto-calculated (product cost × quantity)
- `status` - Order status (Order Placed, Confirmed, Dispatched, Rejected, Cancelled)
- `created_at` - Timestamp

##  AI Email Parsing

The system uses **Google Gemini 2.0 Flash** model to intelligently parse warehouse email responses:

**Features:**
- Extracts order ID from various formats (#123, Order 123, etc.)
- Determines status from natural language responses
- Handles ambiguous responses
- Falls back to regex parsing if AI fails
- Validates extracted data before updating orders

**Parsed Information:**
- Order ID (numeric)
- Status (Confirmed/Rejected/Unknown)

##  Security Notes

- Never commit `.env` file to version control
- Use strong database passwords
- Keep `SECRET_KEY` secure and unique
- Use app-specific passwords for Gmail
- Restrict API access in production
- Enable HTTPS in production
- Regularly update dependencies

##  Troubleshooting

### Email not sending
- Verify Gmail app password is correct
- Check if 2FA is enabled on Gmail account
- Review Django email settings

### IMAP connection fails
- Confirm IMAP is enabled in Gmail settings
- Check firewall/network settings
- Verify credentials in `.env`

### Celery tasks not running
- Ensure Redis is running: `redis-cli ping`
- Check Celery worker is active
- Review Celery logs for errors

### AI parsing fails
- Verify `GOOGLE_API_KEY` is valid
- Check API quota limits
- Review logs for specific errors
- System falls back to regex parsing automatically

