# Credit Approval System

A Django-based credit approval system that evaluates loan applications based on historical data and calculates credit scores using multiple factors.

## Features

- **Customer Registration**: Register new customers with automatic approved limit calculation
- **Credit Scoring**: Calculate credit scores based on 5 factors:
  - Past loans paid on time
  - Number of loans taken
  - Loan activity in current year
  - Total approved loan volume
  - Current debt vs approved limit ratio
- **Loan Eligibility**: Check loan eligibility with interest rate corrections
- **Loan Management**: Create, view, and manage loans
- **Background Processing**: Automatic data ingestion from Excel files
- **Dockerized Deployment**: Single-command deployment with Docker Compose

## Tech Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Task Queue**: Redis + Django-RQ
- **Data Processing**: Pandas + OpenPyXL
- **Deployment**: Docker + Docker Compose

## Quick Start

1. **Clone and Setup**:
   ```bash
   cd alemeno
   cp .env.example .env  # Optional: customize environment variables
   ```

2. **Single Command Deployment**:
   ```bash
   docker-compose up --build
   ```

3. **Access the Application**:
   - API Base URL: `http://localhost:8000`
   - Admin Panel: `http://localhost:8000/admin` (admin/admin123)

## API Endpoints

### 1. Register Customer
**POST** `/register/`

Register a new customer with auto-calculated approved limit.

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 30,
  "monthly_income": 50000,
  "phone_number": 9876543210
}
```

### 2. Check Loan Eligibility
**POST** `/check-eligibility/`

Check if a customer is eligible for a loan with credit score-based interest rate corrections.

```json
{
  "customer_id": 1,
  "loan_amount": 200000,
  "interest_rate": 10.5,
  "tenure": 24
}
```

### 3. Create Loan
**POST** `/create-loan/`

Process and create a new loan if eligible.

```json
{
  "customer_id": 1,
  "loan_amount": 200000,
  "interest_rate": 10.5,
  "tenure": 24
}
```

### 4. View Loan Details
**GET** `/view-loan/{loan_id}/`

Get detailed information about a specific loan.

### 5. View Customer Loans
**GET** `/view-loans/{customer_id}/`

Get all active loans for a specific customer.

## Credit Scoring Algorithm

The system calculates credit scores (0-100) based on:

1. **Payment History (30 points)**: Percentage of EMIs paid on time
2. **Number of Loans (20 points)**: Optimal number of loans for credit building
3. **Current Year Activity (20 points)**: Loan activity in the current year
4. **Approved Volume (20 points)**: Total loan amount vs approved limit ratio
5. **Debt Penalty (up to 100 points)**: Penalty if current debt exceeds approved limit

## Interest Rate Determination

- **Credit Score > 50**: Approve with requested rate
- **30 < Credit Score ≤ 50**: Approve with minimum 12% interest rate
- **10 < Credit Score ≤ 30**: Approve with minimum 16% interest rate
- **Credit Score ≤ 10**: Reject loan application

## Data Ingestion

The system automatically loads data from Excel files on startup:

- `customer_data.xlsx`: Customer information
- `loan_data.xlsx`: Historical loan data

Place these files in the project root directory for automatic ingestion.

## Development

### Running Tests
```bash
docker-compose exec web python manage.py test
```

### Database Migrations
```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Loading Sample Data
```bash
docker-compose exec web python manage.py load_initial_data
```

### Accessing Django Shell
```bash
docker-compose exec web python manage.py shell
```

## Project Structure

```
alemeno/
├── credit_approval_system/     # Django project settings
├── credit_app/                 # Main application
│   ├── models.py              # Customer, Loan, CreditScore models
│   ├── views.py               # API endpoints
│   ├── serializers.py         # DRF serializers
│   ├── services.py            # Business logic (credit scoring)
│   ├── admin.py               # Django admin configuration
│   └── tests.py               # Unit tests
├── docker-compose.yml         # Multi-container deployment
├── Dockerfile                 # Application container
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Business Logic

### Approved Limit Calculation
```
approved_limit = 36 × monthly_salary (rounded to nearest lakh)
```

### EMI Calculation (Compound Interest)
```
EMI = P × [r(1+r)^n] / [(1+r)^n - 1]
Where: P = Principal, r = Monthly rate, n = Tenure in months
```

### Loan Approval Criteria
- Credit score determines minimum interest rate
- Total EMIs must not exceed 50% of monthly salary
- Current debt must not exceed approved limit

## Environment Variables

- `DEBUG`: Enable debug mode (default: True)
- `DATABASE_NAME`: PostgreSQL database name
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password
- `DATABASE_HOST`: Database host
- `REDIS_HOST`: Redis host for task queue

## License

This project is developed as part of an internship assignment for Alemeno.