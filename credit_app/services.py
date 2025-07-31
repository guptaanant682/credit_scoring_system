from datetime import datetime, date
from django.db.models import Sum, Count, Q
from .models import Customer, Loan, CreditScore
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class CreditScoringService:
    """Service class for calculating credit scores based on historical data"""
    
    MAX_SCORE = 100
    
    @classmethod
    def calculate_credit_score(cls, customer_id):
        """
        Calculate credit score for a customer based on 5 factors:
        1. Past Loans paid on time (30 points)
        2. Number of loans taken in past (20 points)  
        3. Loan activity in current year (20 points)
        4. Loan approved volume (20 points)
        5. Current debt vs approved limit (10 points penalty if exceeded)
        """
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return 0
        
        # Get all loans for this customer
        loans = Loan.objects.filter(customer=customer)
        
        if not loans.exists():
            # New customer with no loan history gets a base score
            return 50
        
        # Factor 1: Past Loans paid on time (30 points max)
        past_loans_score = cls._calculate_past_loans_score(loans)
        
        # Factor 2: Number of loans taken (20 points max)
        num_loans_score = cls._calculate_num_loans_score(loans)
        
        # Factor 3: Loan activity in current year (20 points max)
        current_year_score = cls._calculate_current_year_activity_score(loans)
        
        # Factor 4: Loan approved volume (20 points max)
        volume_score = cls._calculate_approved_volume_score(customer, loans)
        
        # Factor 5: Current debt vs approved limit penalty
        if customer.current_debt > customer.approved_limit:
            # If debt exceeds limit, credit score is 0 as per requirement
            total_score = 0
        else:
            # Calculate total score normally
            total_score = past_loans_score + num_loans_score + current_year_score + volume_score
            total_score = max(0, min(cls.MAX_SCORE, total_score))
        
        # Calculate debt penalty for record keeping
        debt_penalty = 1 if customer.current_debt > customer.approved_limit else 0
        
        # Store or update credit score
        credit_score, created = CreditScore.objects.get_or_create(
            customer=customer,
            defaults={
                'score': total_score,
                'past_loans_paid_on_time_score': past_loans_score,
                'number_of_loans_score': num_loans_score,
                'loan_activity_current_year_score': current_year_score,
                'loan_approved_volume_score': volume_score,
                'debt_to_limit_penalty': debt_penalty,
            }
        )
        
        if not created:
            credit_score.score = total_score
            credit_score.past_loans_paid_on_time_score = past_loans_score
            credit_score.number_of_loans_score = num_loans_score
            credit_score.loan_activity_current_year_score = current_year_score
            credit_score.loan_approved_volume_score = volume_score
            credit_score.debt_to_limit_penalty = debt_penalty
            credit_score.save()
        
        return total_score
    
    @classmethod
    def _calculate_past_loans_score(cls, loans):
        """Calculate score based on EMIs paid on time (30 points max)"""
        total_emis = 0
        emis_paid_on_time = 0
        
        for loan in loans:
            total_emis += loan.tenure
            emis_paid_on_time += loan.emis_paid_on_time
        
        if total_emis == 0:
            return 15  # Base score for no history
        
        payment_ratio = emis_paid_on_time / total_emis
        return min(30, int(payment_ratio * 30))
    
    @classmethod
    def _calculate_num_loans_score(cls, loans):
        """Calculate score based on number of loans (20 points max)"""
        num_loans = loans.count()
        
        if num_loans == 0:
            return 0
        elif num_loans <= 3:
            return 20  # Good - manageable number of loans
        elif num_loans <= 6:
            return 15  # Moderate
        elif num_loans <= 10:
            return 10  # Higher risk
        else:
            return 5   # High risk - too many loans
    
    @classmethod
    def _calculate_current_year_activity_score(cls, loans):
        """Calculate score based on loan activity in current year (20 points max)"""
        current_year = datetime.now().year
        current_year_loans = loans.filter(start_date__year=current_year)
        
        num_current_loans = current_year_loans.count()
        
        if num_current_loans == 0:
            return 20  # No new loans this year is good
        elif num_current_loans <= 2:
            return 15  # Moderate activity
        elif num_current_loans <= 4:
            return 10  # High activity
        else:
            return 5   # Very high activity - risky
    
    @classmethod
    def _calculate_approved_volume_score(cls, customer, loans):
        """Calculate score based on loan approved volume vs limit (20 points max)"""
        total_loan_amount = loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')
        
        # Convert to Decimal for precise calculations
        total_loan_amount = Decimal(str(total_loan_amount))
        approved_limit = Decimal(str(customer.approved_limit))
        
        if approved_limit == 0:
            return 10  # Base score
        
        utilization_ratio = total_loan_amount / approved_limit
        
        if utilization_ratio <= Decimal('0.3'):
            return 20  # Low utilization - excellent
        elif utilization_ratio <= Decimal('0.6'):
            return 15  # Moderate utilization - good
        elif utilization_ratio <= Decimal('0.8'):
            return 10  # High utilization - fair
        else:
            return 5   # Very high utilization - poor
    
    
    @classmethod
    def get_interest_rate_for_score(cls, credit_score, requested_rate=None):
        """
        Determine appropriate interest rate based on credit score
        Returns tuple: (approved, corrected_rate, message)
        """
        if credit_score > 50:
            # Approve loan with any reasonable interest rate
            return True, requested_rate, "Loan approved"
        elif 30 < credit_score <= 50:
            # Approve loans with interest rate > 12%
            min_rate = 12.0
            if requested_rate and requested_rate >= min_rate:
                return True, requested_rate, "Loan approved"
            else:
                return True, min_rate, f"Loan approved with corrected interest rate of {min_rate}%"
        elif 10 < credit_score <= 30:
            # Approve loans with interest rate > 16%
            min_rate = 16.0
            if requested_rate and requested_rate >= min_rate:
                return True, requested_rate, "Loan approved"
            else:
                return True, min_rate, f"Loan approved with corrected interest rate of {min_rate}%"
        else:
            # Don't approve any loans
            return False, requested_rate, "Loan not approved due to low credit score"
    
    @classmethod
    def check_emi_to_salary_ratio(cls, customer, new_emi):
        """Check if total EMIs (including new one) exceed 50% of monthly salary"""
        # Get current active loans EMIs
        current_emis = Loan.objects.filter(
            customer=customer,
            status='ACTIVE'
        ).aggregate(
            total=Sum('monthly_repayment')
        )['total'] or Decimal('0')
        
        # Convert to Decimal for precise calculations
        current_emis = Decimal(str(current_emis))
        new_emi = Decimal(str(new_emi))
        monthly_salary = Decimal(str(customer.monthly_salary))
        
        total_emis = current_emis + new_emi
        emi_ratio = total_emis / monthly_salary if monthly_salary > 0 else Decimal('1')
        
        return emi_ratio <= Decimal('0.5'), float(emi_ratio)


class LoanEligibilityService:
    """Service for checking loan eligibility"""
    
    @classmethod
    def check_eligibility(cls, customer_id, loan_amount, interest_rate, tenure):
        """
        Check loan eligibility for a customer
        Returns dict with eligibility details
        """
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return {
                'eligible': False,
                'message': 'Customer not found',
                'credit_score': 0,
                'corrected_interest_rate': interest_rate,
                'monthly_installment': 0
            }
        
        # Calculate credit score
        credit_score = CreditScoringService.calculate_credit_score(customer_id)
        
        # Check if current debt exceeds approved limit
        if customer.current_debt > customer.approved_limit:
            return {
                'eligible': False,
                'message': 'Current debt exceeds approved limit',
                'credit_score': 0,
                'corrected_interest_rate': interest_rate,
                'monthly_installment': 0
            }
        
        # Get interest rate based on credit score
        approved, corrected_rate, message = CreditScoringService.get_interest_rate_for_score(
            credit_score, interest_rate
        )
        
        if not approved:
            return {
                'eligible': False,
                'message': message,
                'credit_score': credit_score,
                'corrected_interest_rate': corrected_rate,
                'monthly_installment': 0
            }
        
        # Calculate EMI with corrected interest rate
        monthly_installment = Loan.calculate_emi(loan_amount, corrected_rate, tenure)
        
        # Check EMI to salary ratio
        emi_ok, emi_ratio = CreditScoringService.check_emi_to_salary_ratio(
            customer, monthly_installment
        )
        
        if not emi_ok:
            return {
                'eligible': False,
                'message': f'EMI exceeds 50% of monthly salary (current ratio: {emi_ratio:.1%})',
                'credit_score': credit_score,
                'corrected_interest_rate': corrected_rate,
                'monthly_installment': monthly_installment
            }
        
        return {
            'eligible': True,
            'message': 'Loan approved',
            'credit_score': credit_score,
            'corrected_interest_rate': corrected_rate,
            'monthly_installment': monthly_installment
        }