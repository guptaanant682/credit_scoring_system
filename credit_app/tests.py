from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from .models import Customer, Loan
from .services import CreditScoringService, LoanEligibilityService


class CustomerModelTest(TestCase):
    def test_calculate_approved_limit(self):
        """Test approved limit calculation"""
        # Test with 50000 monthly salary
        limit = Customer.calculate_approved_limit(50000)
        expected = round(36 * 50000 / 100000) * 100000  # Should be 1800000
        self.assertEqual(limit, expected)
        
        # Test with 30000 monthly salary
        limit = Customer.calculate_approved_limit(30000)
        expected = round(36 * 30000 / 100000) * 100000  # Should be 1100000
        self.assertEqual(limit, expected)


class LoanModelTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            phone_number=9876543210,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
    
    def test_emi_calculation(self):
        """Test EMI calculation with compound interest"""
        # Test with principal=100000, rate=12%, tenure=12 months
        emi = Loan.calculate_emi(100000, 12, 12)
        # Expected EMI should be around 8884.88
        self.assertAlmostEqual(float(emi), 8884.88, places=2)
    
    def test_loan_creation(self):
        """Test loan creation and EMI auto-calculation"""
        loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=12,
            start_date=date.today(),
            end_date=date.today() + relativedelta(months=12)
        )
        
        # EMI should be auto-calculated
        self.assertGreater(loan.monthly_repayment, 0)
        self.assertAlmostEqual(float(loan.monthly_repayment), 8884.88, places=2)


class CreditScoringServiceTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Jane",
            last_name="Smith",
            phone_number=9876543211,
            monthly_salary=60000,
            approved_limit=2160000,
            current_debt=0,
            age=28
        )
    
    def test_new_customer_score(self):
        """Test credit score for new customer with no loan history"""
        score = CreditScoringService.calculate_credit_score(self.customer.customer_id)
        self.assertEqual(score, 50)  # Base score for new customers
    
    def test_customer_with_good_payment_history(self):
        """Test credit score for customer with good payment history"""
        # Create a loan with good payment history
        Loan.objects.create(
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=8791,
            emis_paid_on_time=12,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            status='CLOSED'
        )
        
        score = CreditScoringService.calculate_credit_score(self.customer.customer_id)
        self.assertGreater(score, 50)
    
    def test_debt_exceeds_limit_penalty(self):
        """Test credit score when debt exceeds approved limit"""
        self.customer.current_debt = 2500000  # Exceeds approved limit
        self.customer.save()
        
        score = CreditScoringService.calculate_credit_score(self.customer.customer_id)
        self.assertEqual(score, 0)  # Should be 0 due to penalty


class CustomerRegistrationAPITest(APITestCase):
    def test_register_customer_success(self):
        """Test successful customer registration"""
        url = reverse('register_customer')
        data = {
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'age': 25,
            'monthly_income': 45000,
            'phone_number': 9876543212
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Alice Johnson')
        self.assertEqual(float(response.data['approved_limit']), 1600000.00)
    
    def test_register_customer_invalid_data(self):
        """Test customer registration with invalid data"""
        url = reverse('register_customer')
        data = {
            'first_name': '',  # Invalid: empty first name
            'last_name': 'Johnson',
            'age': 17,  # Invalid: under 18
            'monthly_income': -5000,  # Invalid: negative income
            'phone_number': 123  # Invalid: too short
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoanEligibilityAPITest(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            phone_number=9876543213,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
    
    def test_check_eligibility_new_customer(self):
        """Test loan eligibility for new customer"""
        url = reverse('check_loan_eligibility')
        data = {
            'customer_id': self.customer.customer_id,
            'loan_amount': 200000,
            'interest_rate': 10,
            'tenure': 24
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['approval'])
    
    def test_check_eligibility_nonexistent_customer(self):
        """Test loan eligibility for non-existent customer"""
        url = reverse('check_loan_eligibility')
        data = {
            'customer_id': 99999,  # Non-existent customer
            'loan_amount': 200000,
            'interest_rate': 10,
            'tenure': 24
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['approval'])


class LoanCreationAPITest(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Loan",
            last_name="Tester",
            phone_number=9876543214,
            monthly_salary=60000,
            approved_limit=2160000,
            age=35
        )
    
    def test_create_loan_success(self):
        """Test successful loan creation"""
        url = reverse('create_loan')
        data = {
            'customer_id': self.customer.customer_id,
            'loan_amount': 150000,
            'interest_rate': 12,
            'tenure': 18
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['loan_approved'])
        self.assertIsNotNone(response.data['loan_id'])
    
    def test_create_loan_ineligible_customer(self):
        """Test loan creation for ineligible customer"""
        # Set customer debt higher than approved limit
        self.customer.current_debt = 2500000
        self.customer.save()
        
        url = reverse('create_loan')
        data = {
            'customer_id': self.customer.customer_id,
            'loan_amount': 100000,
            'interest_rate': 10,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['loan_approved'])
        self.assertIsNone(response.data['loan_id'])


class LoanViewAPITest(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="View",
            last_name="Tester",
            phone_number=9876543215,
            monthly_salary=55000,
            approved_limit=1980000,
            age=32
        )
        
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=120000,
            tenure=15,
            interest_rate=11,
            start_date=date.today(),
            end_date=date.today() + relativedelta(months=15),
            status='ACTIVE'
        )
    
    def test_view_loan_details(self):
        """Test viewing loan details"""
        url = reverse('view_loan', kwargs={'loan_id': self.loan.loan_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loan_id'], self.loan.loan_id)
        self.assertEqual(response.data['customer']['first_name'], 'View')
    
    def test_view_customer_loans(self):
        """Test viewing all loans for a customer"""
        url = reverse('view_customer_loans', kwargs={'customer_id': self.customer.customer_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['loan_id'], self.loan.loan_id)
    
    def test_view_nonexistent_loan(self):
        """Test viewing non-existent loan"""
        url = reverse('view_loan', kwargs={'loan_id': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)