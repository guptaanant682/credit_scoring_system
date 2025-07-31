from django.contrib import admin
from .models import Customer, Loan, CreditScore


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'first_name', 'last_name', 'phone_number', 'monthly_salary', 'approved_limit', 'current_debt', 'age']
    list_filter = ['age', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone_number']
    readonly_fields = ['customer_id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_id', 'customer', 'loan_amount', 'tenure', 'interest_rate', 'monthly_repayment', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'start_date', 'interest_rate']
    search_fields = ['customer__first_name', 'customer__last_name', 'loan_id']
    readonly_fields = ['loan_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def customer(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"


@admin.register(CreditScore)
class CreditScoreAdmin(admin.ModelAdmin):
    list_display = ['customer', 'score', 'calculated_at']
    list_filter = ['score', 'calculated_at']
    search_fields = ['customer__first_name', 'customer__last_name']
    readonly_fields = ['calculated_at']
    ordering = ['-calculated_at']