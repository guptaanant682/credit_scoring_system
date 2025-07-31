import pandas as pd
from django.db import transaction
from django_rq import job
from .models import Customer, Loan
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


@job('default')
def load_customer_data_async(file_path='customer_data.xlsx'):
    """Background task to load customer data from Excel file"""
    logger.info(f'Starting async customer data loading from {file_path}')
    
    if not os.path.exists(file_path):
        logger.warning(f'Customer file {file_path} not found. Skipping.')
        return {'status': 'error', 'message': f'File {file_path} not found'}
    
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        customers_created = 0
        customers_updated = 0
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    customer_id = int(row.get('customer_id', 0))
                    if customer_id == 0:
                        continue
                        
                    customer, created = Customer.objects.get_or_create(
                        customer_id=customer_id,
                        defaults={
                            'first_name': str(row.get('first_name', '')).strip(),
                            'last_name': str(row.get('last_name', '')).strip(),
                            'phone_number': int(row.get('phone_number', 0)),
                            'monthly_salary': float(row.get('monthly_salary', 0)),
                            'approved_limit': float(row.get('approved_limit', 0)),
                            'current_debt': float(row.get('current_debt', 0)),
                            'age': int(row.get('age', 25)),
                        }
                    )
                    
                    if created:
                        customers_created += 1
                    else:
                        customer.first_name = str(row.get('first_name', customer.first_name)).strip()
                        customer.last_name = str(row.get('last_name', customer.last_name)).strip()
                        customer.phone_number = int(row.get('phone_number', customer.phone_number))
                        customer.monthly_salary = float(row.get('monthly_salary', customer.monthly_salary))
                        customer.approved_limit = float(row.get('approved_limit', customer.approved_limit))
                        customer.current_debt = float(row.get('current_debt', customer.current_debt))
                        customer.age = int(row.get('age', customer.age))
                        customer.save()
                        customers_updated += 1
                        
                except Exception as e:
                    logger.error(f'Error processing customer row: {e}')
                    continue
        
        result = {
            'status': 'success',
            'customers_created': customers_created,
            'customers_updated': customers_updated
        }
        logger.info(f'Customer data loading completed: {result}')
        return result
        
    except Exception as e:
        logger.error(f'Error loading customer data: {e}')
        return {'status': 'error', 'message': str(e)}


@job('default')
def load_loan_data_async(file_path='loan_data.xlsx'):
    """Background task to load loan data from Excel file"""
    logger.info(f'Starting async loan data loading from {file_path}')
    
    if not os.path.exists(file_path):
        logger.warning(f'Loan file {file_path} not found. Skipping.')
        return {'status': 'error', 'message': f'File {file_path} not found'}
    
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        loans_created = 0
        loans_updated = 0
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    customer_id = int(row.get('customer_id', 0))
                    loan_id = int(row.get('loan_id', 0))
                    
                    if customer_id == 0 or loan_id == 0:
                        continue
                    
                    try:
                        customer = Customer.objects.get(customer_id=customer_id)
                    except Customer.DoesNotExist:
                        logger.warning(f'Customer {customer_id} not found for loan {loan_id}. Skipping.')
                        continue
                    
                    # Parse dates with null handling
                    start_date_val = row.get('start_date')
                    end_date_val = row.get('end_date')
                    
                    if pd.isna(start_date_val) or start_date_val is None:
                        logger.warning(f'Loan {loan_id}: Missing start_date, skipping.')
                        continue
                    
                    if pd.isna(end_date_val) or end_date_val is None:
                        logger.warning(f'Loan {loan_id}: Missing end_date, skipping.')
                        continue
                    
                    try:
                        start_date = pd.to_datetime(start_date_val).date()
                        end_date = pd.to_datetime(end_date_val).date()
                    except (ValueError, TypeError) as e:
                        logger.warning(f'Loan {loan_id}: Invalid date format - {e}, skipping.')
                        continue
                    
                    loan, created = Loan.objects.get_or_create(
                        loan_id=loan_id,
                        defaults={
                            'customer': customer,
                            'loan_amount': float(row.get('loan_amount', 0)),
                            'tenure': int(row.get('tenure', 12)),
                            'interest_rate': float(row.get('interest_rate', 10)),
                            'monthly_repayment': float(row.get('monthly_repayment', 0)),
                            'emis_paid_on_time': int(row.get('emis_paid_on_time', 0)),
                            'start_date': start_date,
                            'end_date': end_date,
                            'status': 'ACTIVE' if end_date > datetime.now().date() else 'CLOSED'
                        }
                    )
                    
                    if created:
                        loans_created += 1
                    else:
                        loan.customer = customer
                        loan.loan_amount = float(row.get('loan_amount', loan.loan_amount))
                        loan.tenure = int(row.get('tenure', loan.tenure))
                        loan.interest_rate = float(row.get('interest_rate', loan.interest_rate))
                        loan.monthly_repayment = float(row.get('monthly_repayment', loan.monthly_repayment))
                        loan.emis_paid_on_time = int(row.get('emis_paid_on_time', loan.emis_paid_on_time))
                        loan.start_date = start_date
                        loan.end_date = end_date
                        loan.status = 'ACTIVE' if end_date > datetime.now().date() else 'CLOSED'
                        loan.save()
                        loans_updated += 1
                        
                except Exception as e:
                    logger.error(f'Error processing loan row: {e}')
                    continue
        
        result = {
            'status': 'success',
            'loans_created': loans_created,
            'loans_updated': loans_updated
        }
        logger.info(f'Loan data loading completed: {result}')
        return result
        
    except Exception as e:
        logger.error(f'Error loading loan data: {e}')
        return {'status': 'error', 'message': str(e)}


def load_initial_data_async():
    """Function to start background data loading tasks"""
    logger.info('Starting async initial data loading')
    
    try:
        # Enqueue customer data loading task
        import django_rq
        queue = django_rq.get_queue('default')
        
        customer_job = queue.enqueue(load_customer_data_async, 'customer_data.xlsx')
        loan_job = queue.enqueue(load_loan_data_async, 'loan_data.xlsx')
        
        return {
            'status': 'started',
            'customer_job_id': customer_job.id if customer_job else None,
            'loan_job_id': loan_job.id if loan_job else None
        }
    except Exception as e:
        logger.error(f'Error starting background tasks: {e}')
        # Fallback to synchronous loading
        customer_result = load_customer_data_async('customer_data.xlsx')
        loan_result = load_loan_data_async('loan_data.xlsx')
        
        return {
            'status': 'completed_sync',
            'customer_result': customer_result,
            'loan_result': loan_result
        }