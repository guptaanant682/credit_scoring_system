# API Reference Guide

## Base URL
```
http://localhost:8000
```

## Response Format
All API responses are in JSON format with consistent structure:

```json
{
  "status": "success|error",
  "data": {},
  "message": "Optional message"
}
```

## Error Handling
The API uses standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `404` - Not Found
- `500` - Internal Server Error

Error responses include detailed information:
```json
{
  "error": "Error description",
  "details": "Specific error details"
}
```

## Endpoints

### 1. API Root
```http
GET /
```

Returns API information and available endpoints.

**Response:**
```json
{
  "message": "Welcome to Credit Approval System API",
  "version": "1.0",
  "endpoints": {
    "register": "http://localhost:8000/register/",
    "check_eligibility": "http://localhost:8000/check-eligibility/",
    "create_loan": "http://localhost:8000/create-loan/",
    "view_loan": "http://localhost:8000/view-loan/{loan_id}/",
    "view_customer_loans": "http://localhost:8000/view-loans/{customer_id}/"
  }
}
```

### 2. Customer Registration
```http
POST /register/
Content-Type: application/json
```

Creates a new customer account with automatic credit limit calculation.

**Request Body:**
```json
{
  "first_name": "string (required, max 100 chars)",
  "last_name": "string (required, max 100 chars)", 
  "age": "integer (required, 18-100)",
  "monthly_income": "decimal (required, min 0)",
  "phone_number": "integer (required, 10-15 digits)"
}
```

**Example Request:**
```json
{
  "first_name": "Priya",
  "last_name": "Sharma",
  "age": 28,
  "monthly_income": 65000,
  "phone_number": 9876543210
}
```

**Success Response (201):**
```json
{
  "customer_id": 102,
  "name": "Priya Sharma",
  "age": 28,
  "monthly_income": "65000.00",
  "approved_limit": 2300000,
  "phone_number": 9876543210
}
```

**Validation Rules:**
- Phone number must be 10-15 digits
- Age must be between 18-100
- Monthly income must be positive
- Names cannot be empty

### 3. Loan Eligibility Check
```http
POST /check-eligibility/
Content-Type: application/json
```

Evaluates loan eligibility using credit scoring algorithm without creating a loan.

**Request Body:**
```json
{
  "customer_id": "integer (required)",
  "loan_amount": "decimal (required, min 0)",
  "interest_rate": "decimal (required, 0-100)",
  "tenure": "integer (required, 1-360 months)"
}
```

**Example Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 500000,
  "interest_rate": 9.5,
  "tenure": 36
}
```

**Success Response (200):**
```json
{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 9.5,
  "corrected_interest_rate": 12.0,
  "tenure": 36,
  "monthly_installment": 16607.97
}
```

**Business Logic:**
- Credit score calculated based on payment history
- Interest rate adjusted based on credit score ranges
- EMI-to-salary ratio must be ≤ 50%
- Current debt must not exceed approved limit

### 4. Loan Creation
```http
POST /create-loan/
Content-Type: application/json
```

Creates a new loan after eligibility verification.

**Request Body:**
```json
{
  "customer_id": "integer (required)",
  "loan_amount": "decimal (required, min 0)",
  "interest_rate": "decimal (required, 0-100)",
  "tenure": "integer (required, 1-360 months)"
}
```

**Example Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 300000,
  "interest_rate": 11.0,
  "tenure": 24
}
```

**Success Response (201):**
```json
{
  "loan_id": 205,
  "customer_id": 1,
  "loan_approved": true,
  "message": "Loan approved successfully",
  "monthly_installment": 14069.29
}
```

**Rejection Response (200):**
```json
{
  "loan_id": null,
  "customer_id": 1,
  "loan_approved": false,
  "message": "EMI exceeds 50% of monthly salary",
  "monthly_installment": 0
}
```

### 5. View Loan Details
```http
GET /view-loan/{loan_id}/
```

Retrieves comprehensive loan information including customer details.

**Path Parameters:**
- `loan_id`: Integer (required) - Unique loan identifier

**Example Request:**
```http
GET /view-loan/205/
```

**Success Response (200):**
```json
{
  "loan_id": 205,
  "customer": {
    "id": 1,
    "first_name": "Rahul",
    "last_name": "Kumar",
    "phone_number": 9123456789,
    "age": 32
  },
  "loan_amount": "300000.00",
  "interest_rate": "12.00",
  "monthly_installment": "14069.29",
  "tenure": 24
}
```

**Error Response (404):**
```json
{
  "error": "Loan not found"
}
```

### 6. View Customer Loans
```http
GET /view-loans/{customer_id}/
```

Lists all active loans for a specific customer.

**Path Parameters:**
- `customer_id`: Integer (required) - Customer identifier

**Example Request:**
```http
GET /view-loans/1/
```

**Success Response (200):**
```json
[
  {
    "loan_id": 205,
    "loan_amount": "300000.00",
    "interest_rate": "12.00",
    "monthly_installment": "14069.29",
    "repayments_left": 24
  },
  {
    "loan_id": 178,
    "loan_amount": "150000.00",
    "interest_rate": "14.50",
    "monthly_installment": "7234.56",
    "repayments_left": 18
  }
]
```

**Empty Response (200):**
```json
[]
```

## Credit Scoring Details

### Scoring Components (Total: 100 points)

1. **Payment History (30 points)**
   - Excellent (26-30): 95%+ EMIs paid on time
   - Good (21-25): 80-94% EMIs paid on time
   - Fair (15-20): 60-79% EMIs paid on time
   - Poor (0-14): <60% EMIs paid on time

2. **Credit Mix (20 points)**
   - Optimal (20): 1-3 active loans
   - Good (15): 4-6 active loans
   - Moderate (10): 7-10 active loans
   - Risky (5): 10+ active loans

3. **Recent Activity (20 points)**
   - Excellent (20): No new loans this year
   - Good (15): 1-2 new loans this year
   - Moderate (10): 3-4 new loans this year
   - High Risk (5): 5+ new loans this year

4. **Credit Utilization (20 points)**
   - Excellent (20): ≤30% of approved limit
   - Good (15): 31-60% of approved limit
   - Fair (10): 61-80% of approved limit
   - Poor (5): >80% of approved limit

5. **Debt Management (Penalty)**
   - If current debt > approved limit: Score = 0

### Interest Rate Matrix

| Credit Score | Policy | Minimum Rate |
|-------------|---------|-------------|
| 51-100 | Approve with requested rate | No minimum |
| 31-50 | Approve with rate adjustment | 12.0% |
| 11-30 | Approve with high rate | 16.0% |
| 0-10 | Reject application | N/A |

## EMI Calculation Formula

The system uses compound interest for precise EMI calculation:

```
EMI = P × [r × (1+r)^n] / [(1+r)^n - 1]

Where:
P = Principal amount (loan_amount)
r = Monthly interest rate (annual_rate ÷ 12 ÷ 100)
n = Number of months (tenure)
```

**Example Calculation:**
- Principal: ₹300,000
- Annual Rate: 12%
- Tenure: 24 months
- Monthly Rate: 12 ÷ 12 ÷ 100 = 0.01
- EMI: ₹14,069.29

## Rate Limiting

Currently no rate limiting is implemented. For production deployment, consider:
- 100 requests per minute per IP
- 1000 requests per hour per customer
- Exponential backoff for repeated failures

## Data Validation

### Phone Number Validation
- Must be numeric only
- Length between 10-15 digits
- No special characters or spaces

### Amount Validation
- All monetary values use Decimal precision
- Minimum loan amount: ₹1,000
- Maximum loan amount: Based on approved limit
- Currency: Indian Rupees (₹)

### Date Handling
- All dates in ISO format (YYYY-MM-DD)
- Timezone: UTC
- Loan start date: Current date
- Loan end date: Calculated based on tenure

## Sample Workflows

### Complete Loan Application Process

1. **Register Customer**
```bash
curl -X POST http://localhost:8000/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Amit",
    "last_name": "Patel", 
    "age": 35,
    "monthly_income": 80000,
    "phone_number": 9988776655
  }'
```

2. **Check Eligibility**
```bash
curl -X POST http://localhost:8000/check-eligibility/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 103,
    "loan_amount": 400000,
    "interest_rate": 10.0,
    "tenure": 30
  }'
```

3. **Create Loan**
```bash
curl -X POST http://localhost:8000/create-loan/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 103,
    "loan_amount": 400000,
    "interest_rate": 12.0,
    "tenure": 30
  }'
```

4. **View Loan Details**
```bash
curl http://localhost:8000/view-loan/206/
```

### Loan Portfolio Management

**Check Customer's Current Loans:**
```bash
curl http://localhost:8000/view-loans/103/
```

**Verify Customer Credit Status:**
```bash
# Check in admin panel
open http://localhost:8000/admin/credit_app/creditscore/
```

## Integration Examples

### Python Integration
```python
import requests

# Register customer
response = requests.post('http://localhost:8000/register/', json={
    'first_name': 'Sneha',
    'last_name': 'Reddy',
    'age': 29,
    'monthly_income': 70000,
    'phone_number': 9876543210
})

customer_data = response.json()
customer_id = customer_data['customer_id']

# Apply for loan
loan_response = requests.post('http://localhost:8000/create-loan/', json={
    'customer_id': customer_id,
    'loan_amount': 250000,
    'interest_rate': 11.5,
    'tenure': 24
})

print(loan_response.json())
```

### JavaScript Integration
```javascript
// Register customer
const registerCustomer = async (customerData) => {
  const response = await fetch('http://localhost:8000/register/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(customerData)
  });
  
  return await response.json();
};

// Check loan eligibility  
const checkEligibility = async (loanRequest) => {
  const response = await fetch('http://localhost:8000/check-eligibility/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(loanRequest)
  });
  
  return await response.json();
};
```

---

**API Version**: 1.0  
**Documentation Updated**: July 2025  
**Support**: Contact development team for technical assistance