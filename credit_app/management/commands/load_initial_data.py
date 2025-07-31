import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from credit_app.models import Customer, Loan
from credit_app.tasks import load_initial_data_async
from datetime import datetime
import os


class Command(BaseCommand):
    help = 'Load initial data from Excel files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer-file',
            type=str,
            default='customer_data.xlsx',
            help='Path to customer data Excel file'
        )
        parser.add_argument(
            '--loan-file',
            type=str,
            default='loan_data.xlsx',
            help='Path to loan data Excel file'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Load data using background tasks (requires Redis)'
        )

    def handle(self, *args, **options):
        customer_file = options['customer_file']
        loan_file = options['loan_file']
        use_async = options['async']

        self.stdout.write(
            self.style.SUCCESS('Starting data loading process...')
        )

        if use_async:
            # Use background tasks
            try:
                result = load_initial_data_async()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Background data loading started. Job IDs: {result}'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to start background tasks: {e}')
                )
        else:
            # Load synchronously
            # Load customer data
            if os.path.exists(customer_file):
                self.load_customer_data(customer_file)
            else:
                self.stdout.write(
                    self.style.WARNING(f'Customer file {customer_file} not found. Skipping customer data loading.')
                )

            # Load loan data
            if os.path.exists(loan_file):
                self.load_loan_data(loan_file)
            else:
                self.stdout.write(
                    self.style.WARNING(f'Loan file {loan_file} not found. Skipping loan data loading.')
                )

            self.stdout.write(
                self.style.SUCCESS('Data loading completed successfully!')
            )

    @transaction.atomic
    def load_customer_data(self, file_path):
        """Load customer data from Excel file"""
        self.stdout.write(f'Loading customer data from {file_path}...')
        
        try:
            df = pd.read_excel(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            customers_created = 0
            customers_updated = 0
            
            for _, row in df.iterrows():
                try:
                    customer_id = int(row.get('customer_id', 0))
                    if customer_id == 0:
                        continue
                        
                    # Get or create customer
                    customer, created = Customer.objects.get_or_create(
                        customer_id=customer_id,
                        defaults={
                            'first_name': str(row.get('first_name', '')).strip(),
                            'last_name': str(row.get('last_name', '')).strip(),
                            'phone_number': int(row.get('phone_number', 0)),
                            'monthly_salary': float(row.get('monthly_salary', 0)),
                            'approved_limit': float(row.get('approved_limit', 0)),
                            'current_debt': float(row.get('current_debt', 0)),
                            'age': int(row.get('age', 25)),  # Default age if not provided
                        }
                    )
                    
                    if created:
                        customers_created += 1
                    else:
                        # Update existing customer
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
                    self.stdout.write(
                        self.style.ERROR(f'Error processing customer row: {e}')
                    )
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Customer data loaded: {customers_created} created, {customers_updated} updated'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading customer data: {e}')
            )

    @transaction.atomic
    def load_loan_data(self, file_path):
        """Load loan data from Excel file"""
        self.stdout.write(f'Loading loan data from {file_path}...')
        
        try:
            df = pd.read_excel(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            loans_created = 0
            loans_updated = 0
            
            for _, row in df.iterrows():
                try:
                    customer_id = int(row.get('customer_id', 0))
                    loan_id = int(row.get('loan_id', 0))
                    
                    if customer_id == 0 or loan_id == 0:
                        continue
                    
                    try:
                        customer = Customer.objects.get(customer_id=customer_id)
                    except Customer.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Customer {customer_id} not found for loan {loan_id}. Skipping.')
                        )
                        continue
                    
                    # Parse dates with null handling
                    start_date_val = row.get('start_date')
                    end_date_val = row.get('end_date')
                    
                    if pd.isna(start_date_val) or start_date_val is None:
                        self.stdout.write(
                            self.style.WARNING(f'Loan {loan_id}: Missing start_date, skipping.')
                        )
                        continue
                    
                    if pd.isna(end_date_val) or end_date_val is None:
                        self.stdout.write(
                            self.style.WARNING(f'Loan {loan_id}: Missing end_date, skipping.')
                        )
                        continue
                    
                    try:
                        start_date = pd.to_datetime(start_date_val).date()
                        end_date = pd.to_datetime(end_date_val).date()
                    except (ValueError, TypeError) as e:
                        self.stdout.write(
                            self.style.WARNING(f'Loan {loan_id}: Invalid date format - {e}, skipping.')
                        )
                        continue
                    
                    # Get or create loan
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
                        # Update existing loan
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
                    self.stdout.write(
                        self.style.ERROR(f'Error processing loan row: {e}')
                    )
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Loan data loaded: {loans_created} created, {loans_updated} updated'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading loan data: {e}')
            )