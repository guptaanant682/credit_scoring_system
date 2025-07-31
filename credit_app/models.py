from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import math


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.BigIntegerField()
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    approved_limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    age = models.IntegerField(validators=[MinValueValidator(18), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['customer_id']),
            models.Index(fields=['phone_number']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.customer_id})"

    @staticmethod
    def calculate_approved_limit(monthly_salary):
        """Calculate approved credit limit based on salary"""
        limit = 36 * monthly_salary
        return round(limit / 100000) * 100000


class Loan(models.Model):
    LOAN_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('DEFAULTED', 'Defaulted'),
    ]

    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    tenure = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(360)])  # in months
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    monthly_repayment = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    emis_paid_on_time = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=LOAN_STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        indexes = [
            models.Index(fields=['loan_id']),
            models.Index(fields=['customer']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Loan {self.loan_id} - {self.customer.first_name} {self.customer.last_name}"

    @property
    def total_emis(self):
        return self.tenure

    @property
    def emis_remaining(self):
        return max(0, self.tenure - self.emis_paid_on_time)

    @staticmethod
    def calculate_emi(principal, annual_interest_rate, tenure_months):
        """Calculate EMI using compound interest formula"""
        # Convert to Decimal for precise calculations
        principal = Decimal(str(principal))
        annual_interest_rate = Decimal(str(annual_interest_rate))
        tenure_months = int(tenure_months)
        
        if annual_interest_rate == 0:
            return principal / tenure_months
        
        monthly_interest_rate = annual_interest_rate / (Decimal('12') * Decimal('100'))
        one_plus_r = Decimal('1') + monthly_interest_rate
        one_plus_r_power_n = one_plus_r ** tenure_months
        
        emi = principal * (monthly_interest_rate * one_plus_r_power_n) / (one_plus_r_power_n - Decimal('1'))
        return emi.quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        # Calculate monthly repayment if not provided
        if not self.monthly_repayment:
            self.monthly_repayment = self.calculate_emi(
                self.loan_amount, 
                self.interest_rate, 
                self.tenure
            )
        super().save(*args, **kwargs)


class CreditScore(models.Model):
    """Model to store calculated credit scores for customers"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='credit_score')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    calculated_at = models.DateTimeField(auto_now=True)
    
    # Credit score components for transparency
    past_loans_paid_on_time_score = models.IntegerField(default=0)
    number_of_loans_score = models.IntegerField(default=0)
    loan_activity_current_year_score = models.IntegerField(default=0)
    loan_approved_volume_score = models.IntegerField(default=0)
    debt_to_limit_penalty = models.IntegerField(default=0)

    class Meta:
        db_table = 'credit_scores'

    def __str__(self):
        return f"Credit Score: {self.score} for {self.customer.first_name} {self.customer.last_name}"