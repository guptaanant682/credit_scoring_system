# Credit Approval System Documentation

## Overview

The Credit Approval System is a Django-based REST API that evaluates loan applications using historical customer data and sophisticated credit scoring algorithms. The system processes large datasets asynchronously and provides real-time loan eligibility decisions.

## Architecture

### Technology Stack
- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15 with custom indexing
- **Cache & Queue**: Redis 7 + Django-RQ for background processing
- **Data Processing**: Pandas + OpenPyXL for Excel file handling
- **Deployment**: Docker + Docker Compose

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Django API    │    │   PostgreSQL    │
│                 │◄──►│                 │◄──►│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis Queue   │◄──►│  Background     │
                       │                 │    │  Workers        │
                       └─────────────────┘    └─────────────────┘
```

## Core Features

### 1. Customer Management
- Automated customer registration
- Credit limit calculation based on salary
- Customer profile management

### 2. Credit Scoring Engine
The system evaluates customers using a comprehensive 100-point scoring system:

**Scoring Components:**
- **Payment History (30 points)**: Percentage of EMIs paid on time
- **Credit Mix (20 points)**: Optimal number of loans for risk assessment
- **Recent Activity (20 points)**: Current year loan activity patterns
- **Credit Utilization (20 points)**: Total borrowed amount vs approved limit
- **Debt Management (10 points)**: Current debt within approved limits

### 3. Loan Processing Pipeline
1. **Eligibility Check**: Real-time credit assessment
2. **Interest Rate Adjustment**: Automatic rate correction based on credit score
3. **EMI Calculation**: Compound interest formula implementation
4. **Risk Assessment**: Debt-to-income ratio validation

### 4. Background Data Processing
- Asynchronous Excel file ingestion
- Historical data processing for credit scoring
- Automatic database migrations and seeding

## API Endpoints

### Authentication
No authentication required for this implementation (development setup).

### Core Endpoints

#### 1. Customer Registration
```http
POST /register/
```

Registers a new customer with automatic credit limit calculation.

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 30,
  "monthly_income": 50000,
  "phone_number": 9876543210
}
```

**Response:**
```json
{
  "customer_id": 101,
  "name": "John Doe",
  "age": 30,
  "monthly_income": "50000.00",
  "approved_limit": 1800000,
  "phone_number": 9876543210
}
```

**Business Logic:**
- `approved_limit = 36 × monthly_income` (rounded to nearest lakh)

#### 2. Loan Eligibility Check
```http
POST /check-eligibility/
```

Evaluates loan eligibility using the credit scoring engine.

**Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 200000,
  "interest_rate": 10.5,
  "tenure": 24
}
```

**Response:**
```json
{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 10.5,
  "corrected_interest_rate": 12.0,
  "tenure": 24,
  "monthly_installment": 9439.07
}
```

#### 3. Loan Creation
```http
POST /create-loan/
```

Creates a new loan if the customer passes eligibility requirements.

**Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 200000,
  "interest_rate": 10.5,
  "tenure": 24
}
```

**Response:**
```json
{
  "loan_id": 501,
  "customer_id": 1,
  "loan_approved": true,
  "message": "Loan approved successfully",
  "monthly_installment": 9439.07
}
```

#### 4. Loan Details
```http
GET /view-loan/{loan_id}/
```

Retrieves detailed information about a specific loan.

**Response:**
```json
{
  "loan_id": 501,
  "customer": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": 9876543210,
    "age": 30
  },
  "loan_amount": "200000.00",
  "interest_rate": "12.00",
  "monthly_installment": "9439.07",
  "tenure": 24
}
```

#### 5. Customer Loans
```http
GET /view-loans/{customer_id}/
```

Lists all active loans for a specific customer.

**Response:**
```json
[
  {
    "loan_id": 501,
    "loan_amount": "200000.00",
    "interest_rate": "12.00",
    "monthly_installment": "9439.07",
    "repayments_left": 24
  }
]
```

## Business Logic Implementation

### Credit Scoring Algorithm

The credit scoring system implements industry-standard risk assessment:

```python
def calculate_credit_score(customer_id):
    # Payment History (30 points)
    payment_score = calculate_payment_reliability()
    
    # Credit Mix (20 points)  
    loan_portfolio_score = evaluate_loan_diversity()
    
    # Recent Activity (20 points)
    current_activity_score = assess_recent_patterns()
    
    # Utilization (20 points)
    utilization_score = calculate_credit_utilization()
    
    # Debt Management (10 points penalty)
    debt_penalty = check_debt_limits()
    
    return min(100, payment_score + loan_portfolio_score + 
               current_activity_score + utilization_score - debt_penalty)
```

### Interest Rate Matrix

| Credit Score Range | Interest Rate Policy |
|-------------------|---------------------|
| > 50 | Approve with requested rate |
| 30-50 | Approve with minimum 12% rate |
| 10-30 | Approve with minimum 16% rate |
| < 10 | Reject application |

### EMI Calculation

The system uses compound interest formula for accurate EMI calculation:

```
EMI = P × [r(1+r)^n] / [(1+r)^n - 1]

Where:
P = Principal loan amount
r = Monthly interest rate (annual rate / 12 / 100)
n = Tenure in months
```

### Risk Management

**Automatic Rejection Criteria:**
- Current debt exceeds approved credit limit
- Total EMIs exceed 50% of monthly salary
- Credit score below 10 points

## Data Models

### Customer Model
```python
class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.BigIntegerField()
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    approved_limit = models.DecimalField(max_digits=12, decimal_places=2)
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    age = models.IntegerField()
```

### Loan Model
```python
class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.IntegerField()  # in months
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_repayment = models.DecimalField(max_digits=12, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=LOAN_STATUS_CHOICES)
```

### Credit Score Model
```python
class CreditScore(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    score = models.IntegerField()
    past_loans_paid_on_time_score = models.IntegerField()
    number_of_loans_score = models.IntegerField()
    loan_activity_current_year_score = models.IntegerField()
    loan_approved_volume_score = models.IntegerField()
    debt_to_limit_penalty = models.IntegerField()
```

## Background Processing

### Data Ingestion Pipeline

The system processes large Excel datasets using background workers:

1. **Customer Data Processing**: Validates and imports customer profiles
2. **Loan History Processing**: Imports historical loan data for credit scoring
3. **Data Validation**: Handles missing values and data type conversions
4. **Error Handling**: Logs issues without stopping the process

### Queue Management

```python
# Background job decorator
@job('default')
def load_customer_data_async(file_path):
    """Process customer data in background"""
    # Implementation handles large datasets efficiently
```

## Deployment Guide

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Quick Start
```bash
# Clone project
git clone <repository-url>
cd alemeno

# Start all services
docker-compose up --build

# Access application
open http://localhost:8000
```

### Service Architecture
```yaml
# docker-compose.yml
services:
  db:        # PostgreSQL database
  redis:     # Cache and job queue
  web:       # Django application server
  worker:    # Background job processor
```

### Environment Configuration
```bash
# .env file
DEBUG=True
DATABASE_NAME=credit_approval_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
REDIS_HOST=redis
```

## Testing

### API Testing with curl

**Register Customer:**
```bash
curl -X POST http://localhost:8000/register/ \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Jane","last_name":"Smith","age":28,"monthly_income":75000,"phone_number":9123456789}'
```

**Check Eligibility:**
```bash
curl -X POST http://localhost:8000/check-eligibility/ \
  -H "Content-Type: application/json" \
  -d '{"customer_id":1,"loan_amount":300000,"interest_rate":11.0,"tenure":36}'
```

### Database Testing
```bash
# Access PostgreSQL
docker-compose exec db psql -U postgres -d credit_approval_db

# Check data
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM loans;
```

## Monitoring and Administration

### Admin Panel
- **URL**: http://localhost:8000/admin/
- **Credentials**: admin / admin123
- **Features**: Customer management, loan tracking, system monitoring

### Queue Dashboard
- **URL**: http://localhost:8000/django-rq/
- **Features**: Job monitoring, queue statistics, worker status

### Database Indices
Optimized queries with strategic indexing:
- Customer ID lookups
- Loan status filtering
- Date range queries
- Phone number searches

## Performance Considerations

### Scalability Features
- **Connection Pooling**: Efficient database connections
- **Background Processing**: Non-blocking data operations
- **Decimal Precision**: Financial accuracy with proper rounding
- **Query Optimization**: Indexed fields for fast lookups

### Monitoring Metrics
- API response times
- Background job completion rates
- Database query performance
- Memory and CPU utilization

## Security Implementation

### Data Protection
- Input validation on all endpoints
- SQL injection prevention through ORM
- Decimal precision for financial calculations
- Error handling without data exposure

### Production Considerations
- Environment variable configuration
- Debug mode disabled in production
- Database credential rotation
- HTTPS certificate installation

## Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check database status
docker-compose logs db

# Restart database
docker-compose restart db
```

**Background Job Failures:**
```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker
```

**Data Loading Issues:**
```bash
# Manual data load
docker-compose exec web python manage.py load_initial_data

# Check Excel files
ls -la *.xlsx
```

## Development Setup

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Code Quality
- PEP 8 compliance
- Comprehensive error handling
- Modular service architecture
- Clear variable naming conventions

## Contributing

### Code Standards
- Follow Django best practices
- Write descriptive commit messages
- Add docstrings for complex functions
- Test API endpoints before committing

### Project Structure
```
alemeno/
├── credit_approval_system/     # Django project configuration
├── credit_app/                 # Main application logic
│   ├── models.py              # Database models
│   ├── views.py               # API endpoint handlers
│   ├── serializers.py         # Data validation and serialization
│   ├── services.py            # Business logic implementation
│   └── tasks.py               # Background job definitions
├── docker-compose.yml         # Multi-container orchestration
├── Dockerfile                 # Application container definition
└── requirements.txt           # Python dependencies
```

---

**Documentation Version**: 1.0  
**Last Updated**: July 2025  
**Maintainer**: Backend Development Team