from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerRegistrationResponseSerializer,
    LoanEligibilityRequestSerializer,
    LoanEligibilityResponseSerializer,
    LoanCreationRequestSerializer,
    LoanCreationResponseSerializer,
    LoanDetailResponseSerializer,
    CustomerLoanResponseSerializer
)
from .services import LoanEligibilityService


@api_view(['GET'])
def api_root(request):
    """
    Credit Approval System API Root
    Welcome to the Credit Approval System API
    """
    return Response({
        'message': 'Welcome to Credit Approval System API',
        'version': '1.0',
        'endpoints': {
            'register': request.build_absolute_uri('/register/'),
            'check_eligibility': request.build_absolute_uri('/check-eligibility/'),
            'create_loan': request.build_absolute_uri('/create-loan/'),
            'view_loan': request.build_absolute_uri('/view-loan/{loan_id}/'),
            'view_customer_loans': request.build_absolute_uri('/view-loans/{customer_id}/'),
            'admin': request.build_absolute_uri('/admin/'),
            'rq_dashboard': request.build_absolute_uri('/django-rq/')
        },
        'documentation': {
            'register': {
                'method': 'POST',
                'description': 'Register a new customer',
                'required_fields': ['first_name', 'last_name', 'age', 'monthly_income', 'phone_number']
            },
            'check_eligibility': {
                'method': 'POST', 
                'description': 'Check loan eligibility for a customer',
                'required_fields': ['customer_id', 'loan_amount', 'interest_rate', 'tenure']
            },
            'create_loan': {
                'method': 'POST',
                'description': 'Create a new loan if eligible',
                'required_fields': ['customer_id', 'loan_amount', 'interest_rate', 'tenure']
            },
            'view_loan': {
                'method': 'GET',
                'description': 'View loan details by loan ID'
            },
            'view_customer_loans': {
                'method': 'GET',
                'description': 'View all active loans for a customer'
            }
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def register_customer(request):
    """
    Register a new customer with approved limit based on salary
    approved_limit = 36 * monthly_salary (rounded to nearest lakh)
    """
    serializer = CustomerRegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # Calculate approved limit
            approved_limit = Customer.calculate_approved_limit(data['monthly_income'])
            
            # Create customer
            customer = Customer.objects.create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                age=data['age'],
                monthly_salary=data['monthly_income'],
                phone_number=data['phone_number'],
                approved_limit=approved_limit,
                current_debt=0
            )
            
            # Serialize response
            response_serializer = CustomerRegistrationResponseSerializer(customer)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {'error': 'Failed to create customer', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def check_loan_eligibility(request):
    """
    Check loan eligibility based on credit score and other factors
    """
    serializer = LoanEligibilityRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    
    try:
        # Check eligibility using the service
        eligibility_result = LoanEligibilityService.check_eligibility(
            customer_id=data['customer_id'],
            loan_amount=data['loan_amount'],
            interest_rate=data['interest_rate'],
            tenure=data['tenure']
        )
        
        response_data = {
            'customer_id': data['customer_id'],
            'approval': eligibility_result['eligible'],
            'interest_rate': data['interest_rate'],
            'corrected_interest_rate': eligibility_result['corrected_interest_rate'],
            'tenure': data['tenure'],
            'monthly_installment': eligibility_result['monthly_installment']
        }
        
        response_serializer = LoanEligibilityResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': 'Failed to check eligibility', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_loan(request):
    """
    Process a new loan based on eligibility
    """
    serializer = LoanCreationRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # Check eligibility first
            eligibility_result = LoanEligibilityService.check_eligibility(
                customer_id=data['customer_id'],
                loan_amount=data['loan_amount'],
                interest_rate=data['interest_rate'],
                tenure=data['tenure']
            )
            
            if not eligibility_result['eligible']:
                response_data = {
                    'loan_id': None,
                    'customer_id': data['customer_id'],
                    'loan_approved': False,
                    'message': eligibility_result['message'],
                    'monthly_installment': eligibility_result['monthly_installment']
                }
                response_serializer = LoanCreationResponseSerializer(response_data)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            
            # Get customer
            customer = get_object_or_404(Customer, customer_id=data['customer_id'])
            
            # Create loan with corrected interest rate
            start_date = date.today()
            end_date = start_date + relativedelta(months=data['tenure'])
            
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=data['loan_amount'],
                tenure=data['tenure'],
                interest_rate=eligibility_result['corrected_interest_rate'],
                monthly_repayment=eligibility_result['monthly_installment'],
                start_date=start_date,
                end_date=end_date,
                status='ACTIVE'
            )
            
            # Update customer's current debt with remaining loan amount
            # Current debt should reflect the outstanding principal amount, not total EMI payments
            customer.current_debt += data['loan_amount']
            customer.save()
            
            response_data = {
                'loan_id': loan.loan_id,
                'customer_id': data['customer_id'],
                'loan_approved': True,
                'message': 'Loan approved successfully',
                'monthly_installment': eligibility_result['monthly_installment']
            }
            
            response_serializer = LoanCreationResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to create loan', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def view_loan(request, loan_id):
    """
    View loan details and customer details
    """
    try:
        loan = get_object_or_404(Loan, loan_id=loan_id)
        serializer = LoanDetailResponseSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': 'Failed to retrieve loan details', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def view_customer_loans(request, customer_id):
    """
    View all current loan details by customer id
    """
    try:
        customer = get_object_or_404(Customer, customer_id=customer_id)
        loans = Loan.objects.filter(customer=customer, status='ACTIVE')
        serializer = CustomerLoanResponseSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to retrieve customer loans', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )