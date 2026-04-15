# api/router_v1.py
from ninja import Router, File, UploadedFile
from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import cache_page
from api.auth import auth_bearer, token_query_auth
import pandas as pd
import io
import csv
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
import logging

from api.models import Transaction, SystemMetrics, AuditLog, User, OAuthAccount, RefreshToken
from api.jwt_auth import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, verify_token, create_password_reset_token
)
from django.db import IntegrityError
from django.http import JsonResponse
from pydantic import EmailStr, Field
from typing import Optional

logger = logging.getLogger('api')
router = Router()


@router.get("/status", auth=None)
def status(request):
    """Health check endpoint - no authentication required"""
    return {
        "status": "ok",
        "message": "SecurePath API v1 is running",
        "version": "1.0.0",
        "timestamp": timezone.now().isoformat()
    }


@router.get("/dashboard/stats", auth=auth_bearer)
def stats(request):
    """Returns high-level statistics with caching - user-specific"""
    try:
        # Get current user from request (set by auth_bearer)
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # Filter transactions by user
        user_transactions = Transaction.objects.filter(user=current_user)
        total_txns = user_transactions.count()

        aggregation = user_transactions.aggregate(
            total_amount=Sum('amount'),
            fraud_count=Count('pk', filter=Q(is_fraud=True)),
            pending_count=Count('pk', filter=Q(status='pending'))
        )

        return {
            "total_transactions": total_txns,
            "fraud_detected": aggregation['fraud_count'] or 0,
            "pending_review": aggregation['pending_count'] or 0,
            "total_amount": float(aggregation['total_amount'] or 0)
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return JsonResponse({"error": "Failed to fetch statistics"}, status=500)


@router.get("/dashboard/transactions", auth=auth_bearer)
@ratelimit(key='user', rate='100/m', method='GET')
def transactions(request, page: int = 1, page_size: int = 10, status_filter: str = None):
    """Returns paginated transactions with optional filtering - user-specific"""
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # Validate pagination parameters
        page = max(1, page)
        page_size = min(max(1, page_size), 100)  # Max 100 items per page
        
        offset = (page - 1) * page_size
        limit = page_size

        # Build query - filter by user
        query = Transaction.objects.filter(user=current_user)
        
        # Apply filters
        if status_filter and status_filter in ['pending', 'approved', 'rejected']:
            query = query.filter(status=status_filter)

        # Get total count for pagination
        total_count = query.count()
        
        # Get paginated results
        txns = query.order_by('-date')[offset:offset + limit]

        txn_list = [{
            "transaction_id": txn.transaction_id,
            "amount": float(txn.amount),
            "merchant": txn.merchant,
            "status": txn.status,
            "fraud_score": float(txn.fraud_score or 0.0),
            "risk_score": float(txn.risk_score or 0.0),
            "is_fraud": txn.is_fraud,
            "date": txn.date.isoformat() if txn.date else None,
        } for txn in txns]

        return {
            "transactions": txn_list,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    except Exception as e:
        logger.error(f"Error fetching transactions: {str(e)}")
        return JsonResponse({"error": "Failed to fetch transactions"}, status=500)


@router.get("/audit-log", auth=auth_bearer)
@ratelimit(key='user', rate='50/m', method='GET')
def audit_log(request, page: int = 1, page_size: int = 20):
    """Returns paginated audit logs - user-specific"""
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        
        offset = (page - 1) * page_size
        limit = page_size

        # Filter audit logs by user
        user_logs = AuditLog.objects.filter(user=current_user)
        total_count = user_logs.count()
        logs = user_logs.order_by('-timestamp')[offset:offset + limit]

        log_list = [{
            "action": log.action,
            "transaction_id": log.transaction_id,
            "details": log.details,
            "user": log.user.email if log.user else (log.user_string or "SYSTEM"),  # Use email or fallback to user_string
            "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        } for log in logs]

        return {
            "logs": log_list,
            "total": total_count,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"Error fetching audit logs: {str(e)}")
        return JsonResponse({"error": "Failed to fetch audit logs"}, status=500)


@router.post("/detect-fraud", auth=auth_bearer)
@ratelimit(key='user', rate='10/m', method='POST')
def detect_fraud(request):
    """
    Optimized fraud detection with rate limiting - user-specific
    """
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        start_time = timezone.now()
        HIGH_RISK_AMOUNT = Decimal('5000.00')
        HIGH_SCORE = Decimal('0.5')

        # Get all pending transactions for this user (including those that haven't been processed yet)
        transactions_to_process = Transaction.objects.filter(
            user=current_user
        ).filter(
            Q(status='pending') | Q(status='review') | Q(status__isnull=True)
        )
        processed_count = transactions_to_process.count()

        logger.info(f"Found {processed_count} transactions to process for fraud detection (user: {current_user.email})")

        if processed_count == 0:
            # Check if there are any transactions at all for this user
            total_txns = Transaction.objects.filter(user=current_user).count()
            logger.warning(f"No pending transactions found for user {current_user.email}. Total transactions: {total_txns}")
            return {
                "status": "success",
                "message": f"No pending transactions to process. Total transactions: {total_txns}",
                "transactions_processed": 0,
                "fraud_detected": 0,
                "duration_seconds": 0
            }

        # Bulk update high-risk transactions (amount >= $5000)
        high_risk_txns = transactions_to_process.filter(amount__gte=HIGH_RISK_AMOUNT)
        fraud_count = high_risk_txns.count()

        if fraud_count > 0:
            high_risk_txns.update(
                is_fraud=True,
                fraud_score=HIGH_SCORE,
                risk_score=Decimal('80.0'),
                fraud_reasons='High transaction amount (>= $5000).',
                reason_code='R1: High Amount',
                status='rejected'
            )

        # Approve remaining transactions (those not flagged as fraud)
        transactions_to_approve = transactions_to_process.exclude(
            id__in=high_risk_txns.values_list('id', flat=True)
        )
        approved_count = transactions_to_approve.count()
        
        if approved_count > 0:
            transactions_to_approve.update(
                is_fraud=False,
                fraud_score=Decimal('0.0'),
                risk_score=Decimal('10.0'),
                fraud_reasons='',
                reason_code='',
                status='approved'
            )

        # Log the action
        try:
            AuditLog.objects.create(
                user=current_user,  # Associate audit log with user
                action="Fraud Detection Run (Bulk Optimized)",
                details=f"Processed {processed_count} transactions. Detected {fraud_count} fraud attempts. Approved {approved_count} transactions.",
                user_string=current_user.email,  # Legacy field
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception as log_error:
            logger.warning(f"Failed to create audit log: {log_error}")

        duration = (timezone.now() - start_time).total_seconds()

        response_data = {
            "status": "success",
            "message": f"Detection complete. Processed {processed_count} transactions ({fraud_count} fraud, {approved_count} approved) in {round(duration, 3)}s.",
            "transactions_processed": processed_count,
            "fraud_detected": fraud_count,
            "approved_count": approved_count,
            "duration_seconds": round(duration, 3)
        }
        
        logger.info(f"Fraud detection response: {response_data}")
        return response_data
    except Exception as e:
        logger.error(f"Error in fraud detection: {str(e)}")
        return JsonResponse({"error": "Fraud detection failed", "message": str(e)}, status=500)





@router.post("/upload", auth=auth_bearer)
@ratelimit(key='user', rate='10/h', method='POST')
def upload_file(request, file: UploadedFile = File(...)):
    """
    Handles file upload with rate limiting - user-specific
    """
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        file_name = file.name
        file_data = file.read()

        # Read CSV without automatic type conversion to preserve original values
        df = pd.read_csv(io.BytesIO(file_data), dtype=str, keep_default_na=False)
        initial_rows = len(df)

        # Clean column names
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
        df.rename(columns={'txn_id': 'transaction_id', 'txn_date': 'date'}, inplace=True)
        
        # Log column names for debugging
        logger.info(f"CSV columns detected: {list(df.columns)}")
        if len(df) > 0:
            logger.info(f"First row sample: {df.iloc[0].to_dict()}")

        # Prepare bulk insert
        transactions_to_create = []
        logger.info(f"Processing {initial_rows} rows from CSV file: {file_name}")
        
        for index, row in df.iterrows():
            try:
                if 'date' in df.columns:
                    date_raw = row['date']
                    if date_raw and str(date_raw).strip():
                        date_val = pd.to_datetime(date_raw, errors='coerce').to_pydatetime()
                        if pd.isna(date_val):
                            date_val = timezone.now()
                    else:
                        date_val = timezone.now()
                else:
                    date_val = timezone.now()
            except (KeyError, AttributeError, TypeError):
                date_val = timezone.now()

            # Parse amount - handle various formats
            amount_val = Decimal('0.00')
            try:
                if 'amount' in df.columns:
                    amount_raw = row['amount']
                    # Since we read as string, check if it's not empty
                    if amount_raw and str(amount_raw).strip():
                        # Remove currency symbols, commas, and whitespace
                        amount_str = str(amount_raw).replace('$', '').replace(',', '').strip()
                        # Remove all whitespace
                        amount_str = ''.join(amount_str.split())
                        if amount_str:
                            try:
                                amount_val = Decimal(str(float(amount_str)))
                            except (ValueError, TypeError, OverflowError):
                                logger.warning(f"Could not convert amount '{amount_str}' to number for row {index}")
                                amount_val = Decimal('0.00')
                else:
                    logger.warning(f"'amount' column not found in CSV")
            except (ValueError, TypeError, AttributeError, KeyError) as e:
                logger.warning(f"Could not parse amount for row {index}: {e}")
                amount_val = Decimal('0.00')

            # Parse merchant - handle various column names
            merchant_val = 'Unknown Merchant'
            try:
                # Try different possible column names
                merchant_raw = None
                for col_name in ['merchant', 'description', 'merchant_name', 'vendor', 'store']:
                    if col_name in df.columns:
                        raw_value = row[col_name]
                        # Since we read as string, just check if it's not empty
                        if raw_value and str(raw_value).strip():
                            merchant_str = str(raw_value).strip()
                            if merchant_str.lower() not in ['nan', 'none', 'null', '']:
                                merchant_raw = merchant_str
                                break
                
                if merchant_raw:
                    merchant_val = merchant_raw[:200]  # Limit to 200 chars
            except (KeyError, AttributeError, TypeError) as e:
                logger.warning(f"Could not parse merchant for row {index}: {e}")

            # Parse transaction_id
            # Generate a unique ID that includes timestamp and row index to ensure uniqueness
            base_timestamp = timezone.now().timestamp()
            transaction_id = f"AUTO-{base_timestamp}-{index}-{current_user.id}"
            try:
                if 'transaction_id' in df.columns:
                    txn_id_raw = row['transaction_id']
                    if txn_id_raw and str(txn_id_raw).strip():
                        # Use CSV transaction_id but append user ID to make it user-specific
                        csv_txn_id = str(txn_id_raw).strip()[:80]  # Leave room for user suffix
                        transaction_id = f"{csv_txn_id}-U{current_user.id}"
            except (KeyError, AttributeError, TypeError):
                pass
            
            logger.debug(f"Row {index}: transaction_id={transaction_id}, amount={amount_val}, merchant={merchant_val}")

            # Parse card_number
            card_number = 'N/A'
            try:
                for col_name in ['card_number', 'card', 'card_num', 'card_id']:
                    if col_name in df.columns:
                        card_raw = row[col_name]
                        if pd.notna(card_raw) and str(card_raw).strip() and str(card_raw).lower() != 'nan':
                            card_number = str(card_raw).strip()[:20]
                            break
            except (KeyError, AttributeError, TypeError):
                pass

            transactions_to_create.append(
                Transaction(
                    user=current_user,  # Associate transaction with current user
                    transaction_id=transaction_id,
                    amount=amount_val,
                    date=date_val,
                    merchant=merchant_val,
                    card_number=card_number,
                    status='pending',  # Explicitly set status to pending
                    is_fraud=False,
                )
            )
        
        logger.info(f"Created {len(transactions_to_create)} transaction objects from CSV")

        # Bulk insert - check for duplicates within user's transactions
        # Get list of transaction IDs to check
        transaction_ids_to_check = [t.transaction_id for t in transactions_to_create]
        
        # Query existing transactions for this user with these IDs
        existing_ids = set(
            Transaction.objects.filter(
                user=current_user,
                transaction_id__in=transaction_ids_to_check
        ).values_list('transaction_id', flat=True)
        )

        # Filter out duplicates
        new_transactions = [
            t for t in transactions_to_create if t.transaction_id not in existing_ids
        ]

        # Log for debugging
        logger.info(f"Total transactions to create: {len(transactions_to_create)}")
        logger.info(f"Existing transaction IDs found: {len(existing_ids)}")
        logger.info(f"New transactions to insert: {len(new_transactions)}")

        if new_transactions:
            Transaction.objects.bulk_create(new_transactions, ignore_conflicts=True)
            new_rows_added = len(new_transactions)
        else:
            new_rows_added = 0
            logger.warning(f"No new transactions to insert. All {len(transactions_to_create)} transactions already exist for user {current_user.email}")

        # Log success
        AuditLog.objects.create(
            user=current_user,  # Associate audit log with user
            action=f"File Upload Success: {file_name}",
            details=f"Successfully uploaded {new_rows_added} new transaction records.",
            user_string=current_user.email if current_user else "SYSTEM",
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return {
            "message": f"File processed. {new_rows_added} new records added!",
            "rows": new_rows_added,
            "total_rows": initial_rows
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        
        # Log failure
        try:
            # current_user is defined at the start of the function, so it should be available
            AuditLog.objects.create(
                user=current_user,
                action=f"Upload Failed: {file_name}",
                details=str(e),
                user_string=current_user.email if current_user else "SYSTEM",
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return JsonResponse({"error": f"Upload failed: {str(e)}"}, status=500)


# ==========================================
# PLAID INTEGRATION
# ==========================================
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from django.conf import settings
import datetime
from api.schemas import PlaidExchangeRequest
from api.reports import generate_csv_report, generate_pdf_report
from api.cleansing import cleanse_data

def get_plaid_client():
    """Get Plaid client, raising an error if credentials are missing"""
    if not settings.PLAID_CLIENT_ID or not settings.PLAID_SECRET:
        raise ValueError(
            "Plaid credentials not configured. Please set PLAID_CLIENT_ID and PLAID_SECRET environment variables. "
            "Get your keys from https://dashboard.plaid.com/"
        )
    
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox if settings.PLAID_ENV == 'sandbox' else plaid.Environment.Development,
        api_key={
            'clientId': settings.PLAID_CLIENT_ID,
            'secret': settings.PLAID_SECRET,
        }
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)

@router.post("/plaid/create_link_token", auth=auth_bearer)
def create_link_token(request):
    try:
        client = get_plaid_client()
        request_data = LinkTokenCreateRequest(
            products=[Products('transactions')],
            client_name="SecurePath Fraud Detection",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(request.user.id if hasattr(request, 'user') and request.user.is_authenticated else 'guest_user')
            )
        )
        response = client.link_token_create(request_data)
        return {"link_token": response['link_token']}
    except ValueError as e:
        # Missing credentials
        logger.error(f"Plaid Configuration Error: {str(e)}")
        return JsonResponse({"error": str(e), "type": "configuration"}, status=500)
    except Exception as e:
        logger.error(f"Plaid Link Token Error: {str(e)}")
        return JsonResponse({"error": f"Failed to create Plaid link token: {str(e)}", "type": "api_error"}, status=500)

@router.post("/plaid/exchange_public_token", auth=auth_bearer)
def exchange_public_token(request, payload: PlaidExchangeRequest):
    """
    Exchange Plaid public token for access token
    Expects JSON body: {"public_token": "..."}
    """
    try:
        if not payload.public_token:
            return {"error": "public_token is required"}, 400
        
        client = get_plaid_client()
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=payload.public_token
        )
        response = client.item_public_token_exchange(exchange_request)
        return {"access_token": response['access_token']}
    except ValueError as e:
        # Missing credentials
        logger.error(f"Plaid Configuration Error: {str(e)}")
        return JsonResponse({"error": str(e), "type": "configuration"}, status=500)
    except Exception as e:
        logger.error(f"Plaid Exchange Error: {str(e)}")
        return JsonResponse({"error": f"Failed to exchange token: {str(e)}", "type": "api_error"}, status=500)

@router.get("/plaid/transactions", auth=auth_bearer)
def get_plaid_transactions(request, access_token: str):
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        client = get_plaid_client()
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
        end_date = datetime.datetime.now().date()
        
        request_data = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
        )
        response = client.transactions_get(request_data)
        transactions = response['transactions']
        
        # Convert to our format and save - associate with user
        saved_count = 0
        txns_to_create = []
        
        for t in transactions:
            txns_to_create.append(Transaction(
                user=current_user,  # Associate transaction with current user
                transaction_id=t['transaction_id'],
                amount=Decimal(str(t['amount'])),
                date=t['date'],
                merchant=t['name'],
                status='pending'
            ))
            
        Transaction.objects.bulk_create(txns_to_create, ignore_conflicts=True)
        saved_count = len(txns_to_create)
        
        return {
            "message": "Transactions synced",
            "count": saved_count,
            "transactions": [t.to_dict() for t in transactions]
        }
    except Exception as e:
        logger.error(f"Plaid Transactions Error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


# EXPORT REPORTS
# ==========================================
@router.get("/export/{type}", auth=None)  # We'll handle auth manually to support query string token
def export_report(request, type: str):
    """
    Generates and returns a report (CSV or PDF) of all transactions - user-specific.
    Supports both Authorization header and token query parameter for browser downloads.
    """
    try:
        # Try to get user from multiple sources
        current_user = None
        
        # 1. Try Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            from api.jwt_auth import verify_token
            payload = verify_token(token, token_type="access")
            if payload:
                user_id = payload.get("sub")
                current_user = User.objects.filter(id=user_id, is_active=True).first()
                if current_user:
                    logger.info(f"Export authenticated via Authorization header for user: {current_user.email}")
        
        # 2. Try token query parameter (for browser downloads with token in URL)
        if not current_user:
            token = request.GET.get('token')
            if token:
                from api.jwt_auth import verify_token
                payload = verify_token(token, token_type="access")
                if payload:
                    user_id = payload.get("sub")
                    current_user = User.objects.filter(id=user_id, is_active=True).first()
                    if current_user:
                        logger.info(f"Export authenticated via JWT query token for user: {current_user.email}")
        
        # 3. Try httpOnly cookie (access_token cookie)
        if not current_user:
            token = request.COOKIES.get('access_token')
            if token:
                from api.jwt_auth import verify_token
                payload = verify_token(token, token_type="access")
                if payload:
                    user_id = payload.get("sub")
                    current_user = User.objects.filter(id=user_id, is_active=True).first()
                    if current_user:
                        logger.info(f"Export authenticated via httpOnly cookie for user: {current_user.email}")
        
        if not current_user:
            return JsonResponse({"error": "Authentication required. Please log in to export reports."}, status=401)
        
        # Filter transactions by user
        user_transactions = Transaction.objects.filter(user=current_user)
        
        if type == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="transactions_report.csv"'
            
            writer = csv.writer(response)
            # Write header
            writer.writerow(['Transaction ID', 'Date', 'Merchant', 'Amount', 'Status', 'Risk Score', 'Fraud Score', 'Is Fraud', 'Country', 'Currency'])
            
            # Write transaction data - only user's transactions
            for txn in user_transactions.order_by('-date'):
                writer.writerow([
                    txn.transaction_id or '',
                    txn.date.strftime('%Y-%m-%d %H:%M:%S') if txn.date else '',
                    txn.merchant or 'Unknown',
                    float(txn.amount) if txn.amount else 0.0,
                    txn.status or 'pending',
                    float(txn.risk_score) if txn.risk_score else 0.0,
                    float(txn.fraud_score) if txn.fraud_score else 0.0,
                    'YES' if txn.is_fraud else 'NO',
                    txn.country or 'US',
                    txn.currency or 'USD',
                ])
            
            # Log the export
            AuditLog.objects.create(
                user=current_user,
                action="CSV Report Exported",
                details=f"CSV report downloaded with {user_transactions.count()} transactions",
                user_string=current_user.email,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            return response

        elif type == 'pdf':
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.units import inch
            except ImportError:
                logger.error("reportlab not installed. Cannot generate PDF.")
                return JsonResponse({"error": "PDF generation requires reportlab library"}, status=500)

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="transactions_report.pdf"'
            
            p = canvas.Canvas(response, pagesize=letter)
            width, height = letter
            
            # Title
            p.setFont("Helvetica-Bold", 16)
            p.drawString(100, height - 50, "SecurePath Fraud Detection Report")
            
            # Report info - user-specific
            p.setFont("Helvetica", 12)
            total_txns = user_transactions.count()
            fraud_count = user_transactions.filter(is_fraud=True).count()
            pending_count = user_transactions.filter(status='pending').count()
            
            y_pos = height - 100
            p.drawString(100, y_pos, f"Report Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            y_pos -= 20
            p.drawString(100, y_pos, f"Total Transactions: {total_txns}")
            y_pos -= 20
            p.drawString(100, y_pos, f"Fraud Detected: {fraud_count}")
            y_pos -= 20
            p.drawString(100, y_pos, f"Pending Review: {pending_count}")
            
            # Transaction list (first 30 transactions)
            y_pos -= 40
            p.setFont("Helvetica-Bold", 10)
            p.drawString(100, y_pos, "Recent Transactions:")
            y_pos -= 20
            
            p.setFont("Helvetica", 8)
            for txn in user_transactions.order_by('-date')[:30]:
                if y_pos < 50:  # Start new page if needed
                    p.showPage()
                    y_pos = height - 50
                
                line = f"{txn.transaction_id[:15]:15} | {txn.merchant[:20]:20} | ${float(txn.amount):.2f} | {txn.status}"
                p.drawString(100, y_pos, line)
                y_pos -= 15
            
            p.showPage()
            p.save()
            
            # Log the export
            AuditLog.objects.create(
                user=current_user,
                action="PDF Report Exported",
                details=f"PDF report downloaded with {total_txns} transactions",
                user_string=current_user.email,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            return response

        else:
            return {"error": f"Unsupported export type: {type}. Supported types: csv, pdf"}, 400
            
    except Exception as e:
        logger.error(f"Export Error: {str(e)}")
        return JsonResponse({"error": f"Failed to generate report: {str(e)}"}, status=500)


# DATA CLEANSING
# ==========================================
@router.get("/cleansing/stats", auth=auth_bearer)
def cleansing_stats(request):
    """Get statistics about data cleansing - user-specific"""
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # Filter transactions by user
        user_transactions = Transaction.objects.filter(user=current_user)
        total = user_transactions.count()
        
        # Count potential duplicates (same transaction_id) within user's transactions
        from django.db.models import Count
        duplicates = user_transactions.values('transaction_id').annotate(
            count=Count('transaction_id')
        ).filter(count__gt=1).count()
        
        # Get last cleansing time from audit log for this user
        last_cleansing = AuditLog.objects.filter(
            user=current_user,
            action__icontains='cleansing'
        ).order_by('-timestamp').first()
        
        return {
            "total_transactions": total,
            "duplicates_count": duplicates,
            "last_cleansed": last_cleansing.timestamp.isoformat() if last_cleansing else None
        }
    except Exception as e:
        logger.error(f"Cleansing stats error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@router.post("/cleansing/run", auth=auth_bearer)
@ratelimit(key='user', rate='5/h', method='POST')
def run_cleansing(request):
    """
    ATC-02: Run data cleansing on all transactions - user-specific
    - Remove duplicates
    - Normalize data formats
    - Update records in database
    """
    import time
    start_time = time.time()
    
    try:
        # Get current user from request
        current_user = request.auth if isinstance(request.auth, User) else None
        if not current_user:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # Get all transactions for this user
        transactions = Transaction.objects.filter(user=current_user)
        total_count = transactions.count()
        
        if total_count == 0:
            return {
                "message": "No transactions to cleanse",
                "duplicates_removed": 0,
                "records_normalized": 0,
                "duration_seconds": 0
            }
        
        # Step 1: Find and remove duplicates (within user's transactions)
        from django.db.models import Count
        duplicate_groups = transactions.values('transaction_id').annotate(
            count=Count('transaction_id')
        ).filter(count__gt=1)
        
        duplicates_removed = 0
        for group in duplicate_groups:
            txn_id = group['transaction_id']
            # Keep the first one, delete the rest (only within user's transactions)
            duplicates = transactions.filter(transaction_id=txn_id).order_by('created_at')
            if duplicates.count() > 1:
                # Delete all except the first
                to_delete = duplicates[1:]
                duplicates_removed += to_delete.count()
                to_delete.delete()
        
        # Step 2: Normalize existing records (user's transactions only)
        records_normalized = 0
        updates = []
        
        for txn in transactions:
            updated = False
            
            # Normalize country code
            if txn.country:
                normalized_country = str(txn.country).upper().strip()[:2]
                if normalized_country != txn.country:
                    txn.country = normalized_country
                    updated = True
            
            # Normalize currency code
            if txn.currency:
                normalized_currency = str(txn.currency).upper().strip()[:3]
                if normalized_currency != txn.currency:
                    txn.currency = normalized_currency
                    updated = True
            
            # Normalize amount (round to 2 decimals)
            if txn.amount:
                try:
                    normalized_amount = Decimal(str(txn.amount)).quantize(Decimal('0.01'))
                    if normalized_amount != txn.amount:
                        txn.amount = normalized_amount
                        updated = True
                except:
                    pass
            
            # Normalize merchant (trim whitespace)
            if txn.merchant:
                normalized_merchant = str(txn.merchant).strip()[:200]
                if normalized_merchant != txn.merchant:
                    txn.merchant = normalized_merchant
                    updated = True
            
            if updated:
                updates.append(txn)
                records_normalized += 1
        
        # Bulk update normalized records
        if updates:
            Transaction.objects.bulk_update(updates, ['country', 'currency', 'amount', 'merchant'])
        
        duration = time.time() - start_time
        
        # Log the action
        AuditLog.objects.create(
            user=current_user,
            action="Data Cleansing Run (ATC-02)",
            details=f"Processed {total_count} transactions. Removed {duplicates_removed} duplicates. Normalized {records_normalized} records.",
            user_string=current_user.email,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        return {
            "message": f"Data cleansing completed successfully. Removed {duplicates_removed} duplicates and normalized {records_normalized} records.",
            "duplicates_removed": duplicates_removed,
            "records_normalized": records_normalized,
            "total_processed": total_count,
            "duration_seconds": round(duration, 2)
        }
        
    except Exception as e:
        logger.error(f"Cleansing error: {str(e)}")
        
        # Log failure
        try:
            # current_user is defined at the start of the function, so it should be available
            AuditLog.objects.create(
                user=current_user,
                action="Data Cleansing Failed",
                details=str(e),
                user_string=current_user.email if current_user else "SYSTEM",
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except:
            pass
        
        return JsonResponse({"error": f"Data cleansing failed: {str(e)}"}, status=500)


# AUTHENTICATION ROUTES
# ==========================================
from api.schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    TwoFASetupResponse, TwoFAEnableRequest, TwoFAEnableResponse,
    TwoFADisableRequest, TwoFALoginVerifyRequest,
    TwoFAStatusResponse, TwoFABackupCodesResponse,
    ForgotPasswordVerifyRequest, ForgotPasswordVerifyResponse, ForgotPasswordResetRequest,
    ChangePasswordRequest,
)
from api.jwt_auth import create_2fa_pending_token
from api.totp_auth import (
    generate_totp_secret, encrypt_totp_secret, decrypt_totp_secret,
    generate_qr_code_base64,
    verify_totp,
    generate_backup_codes, hash_backup_codes, consume_backup_code,
    check_otp_rate_limit, record_otp_failure, reset_otp_failures,
    generate_device_token, store_device_token, verify_device_token,
    DEVICE_TRUST_DAYS,
)
from django.http import HttpResponse
from datetime import timedelta
import json

@router.post("/auth/register", auth=None)
def register(request, user_data: UserRegister):
    """
    Register a new user account
    - Validates email format
    - Checks password match
    - Hashes password securely
    - Creates user account
    - Returns JWT tokens
    """
    try:
        # Validate password match
        if user_data.password != user_data.confirm_password:
            return JsonResponse({"error": "Passwords do not match"}, status=400)
        
        # Validate password length (bcrypt has 72 byte limit)
        if len(user_data.password.encode('utf-8')) > 72:
            return JsonResponse({"error": "Password cannot be longer than 72 characters"}, status=400)
        
        # Check if user already exists
        if User.objects.filter(email=user_data.email).exists():
            return JsonResponse({"error": "Email already registered"}, status=400)
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User.objects.create(
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        # Create tokens
        token_data = {"sub": new_user.id, "email": new_user.email}
        access_token = create_access_token(token_data)
        refresh_token_str = create_refresh_token(token_data)
        
        # Save refresh token to database
        from datetime import datetime
        refresh_token_expires = timezone.now() + timedelta(days=7)
        RefreshToken.objects.create(
            token=refresh_token_str,
            user=new_user,
            expires_at=refresh_token_expires
        )
        
        # Return response data - Django Ninja will serialize dict to JSON
        # For cookies, we need to use HttpResponse directly
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at.isoformat()
            }
        }
        
        # Create HttpResponse with JSON content and cookies
        response = JsonResponse(response_data)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=30 * 60  # 30 minutes
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        # Django Ninja accepts HttpResponse directly
        return response
        
    except IntegrityError:
        logger.warning(f"Registration attempt with existing email: {user_data.email}")
        return JsonResponse({"error": "Email already registered"}, status=400)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Registration error: {str(e)}\n{error_trace}")
        # Return proper JSON error response
        return JsonResponse({"error": f"Registration failed: {str(e)}"}, status=500)


@router.post("/auth/login", auth=None)
def login(request, user_data: UserLogin):
    """
    Login with email and password
    - Verifies email exists
    - Verifies password
    - Returns JWT tokens in httpOnly cookies
    """
    try:
        # Find user by email
        user = User.objects.filter(email=user_data.email).first()
        
        if not user:
            return JsonResponse({"error": "Incorrect email or password"}, status=401)
        
        # Check if user has a password (OAuth-only users won't have one)
        if not user.hashed_password:
            return JsonResponse({"error": "Please sign in with your OAuth provider"}, status=401)
        
        # Verify password
        if not verify_password(user_data.password, user.hashed_password):
            return JsonResponse({"error": "Incorrect email or password"}, status=401)
        
        # Check if user is active
        if not user.is_active:
            return JsonResponse({"error": "User account is inactive"}, status=403)

        # ── 2FA check ────────────────────────────────────────────────────────
        if user.is_2fa_enabled:
            # Check "remember this device" cookie before demanding OTP
            device_token = request.COOKIES.get("device_token")
            if device_token and verify_device_token(user, device_token):
                # Trusted device — skip OTP, fall through to normal token issuance
                pass
            else:
                # Issue a short-lived pending token; real tokens come after OTP
                pending_token = create_2fa_pending_token({"sub": user.id, "email": user.email})
                logger.info(f"2FA required for user {user.email}")
                return JsonResponse({
                    "requires_2fa": True,
                    "two_fa_token": pending_token,
                    "message": "Please verify your 2FA code.",
                })
        # ─────────────────────────────────────────────────────────────────────

        # Create tokens
        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token_str = create_refresh_token(token_data)

        # Revoke old refresh tokens and save new one
        RefreshToken.objects.filter(user=user).update(is_revoked=True)
        refresh_token_expires = timezone.now() + timedelta(days=7)
        RefreshToken.objects.create(
            token=refresh_token_str,
            user=user,
            expires_at=refresh_token_expires
        )

        # Create response with cookies
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
            }
        }

        response = JsonResponse(response_data)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=30 * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=7 * 24 * 60 * 60
        )

        return response

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({"error": f"Login failed: {str(e)}"}, status=500)


@router.post("/auth/logout", auth=None)
def logout(request):
    """
    Logout user - revoke refresh token and clear cookies
    """
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            RefreshToken.objects.filter(token=refresh_token).update(is_revoked=True)
        
        response = JsonResponse({"message": "Logged out successfully"})
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return JsonResponse({"error": "Logout failed"}, status=500)


@router.get("/auth/me", auth=auth_bearer)
def get_current_user_info(request):
    """
    Get current authenticated user's information
    - Requires valid JWT token in Authorization header
    """
    try:
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Invalid authorization header"}, status=401)
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token, token_type="access")
        
        if not payload:
            return {"error": "Invalid or expired token"}, 401
        
        user_id = payload.get("sub")
        user = User.objects.filter(id=user_id, is_active=True).first()
        
        if not user:
            return {"error": "User not found"}, 404
        
        return {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
    except Exception as e:
        import traceback
        logger.error(f"Get user error: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({"error": "Failed to get user info"}, status=500)


@router.post("/auth/refresh", auth=None)
def refresh_access_token(request):
    """
    Refresh access token using refresh token
    """
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return JsonResponse({"error": "Refresh token required"}, status=401)
        
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            return JsonResponse({"error": "Invalid refresh token"}, status=401)
        
        # Check if token exists in database and is not revoked
        token_record = RefreshToken.objects.filter(
            token=refresh_token,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not token_record:
            return JsonResponse({"error": "Refresh token not found or expired"}, status=401)
        
        user = token_record.user
        if not user.is_active:
            return JsonResponse({"error": "User account is inactive"}, status=403)
        
        # Create new access token
        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)
        
        # Update cookie
        response = JsonResponse({
            "access_token": access_token,
            "token_type": "bearer"
        })
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=30 * 60
        )
        
        return response
        
    except Exception as e:
        import traceback
        logger.error(f"Refresh token error: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({"error": "Failed to refresh token"}, status=500)


# ══════════════════════════════════════════════════════════════════════════════
# FORGOT PASSWORD ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/auth/forgot-password/verify", auth=None)
def forgot_password_verify(request, data: ForgotPasswordVerifyRequest):
    """
    Step 1 of forgot-password flow.
    Verify identity by checking email + TOTP code from the authenticator app.
    Returns a short-lived (10-min) password_reset token on success.
    """
    import traceback
    try:
        user = User.objects.filter(email=data.email, is_active=True).first()
        # Always return the same error shape — don't leak whether the email exists
        if not user or not user.is_2fa_enabled or not user.totp_secret:
            return JsonResponse(
                {"error": "No account with 2FA found for that email address."},
                status=400,
            )

        # Rate-limit OTP attempts
        from api.totp_auth import (
            check_otp_rate_limit, record_otp_failure, reset_otp_failures,
            decrypt_totp_secret, verify_totp,
        )
        allowed, wait_seconds = check_otp_rate_limit(user)
        if not allowed:
            return JsonResponse(
                {"error": f"Too many failed attempts. Try again in {wait_seconds} seconds."},
                status=429,
            )

        plaintext_secret = decrypt_totp_secret(user.totp_secret)
        valid, new_counter = verify_totp(plaintext_secret, data.otp, user.last_otp_counter)
        if not valid:
            record_otp_failure(user)
            return JsonResponse({"error": "Invalid or expired authenticator code."}, status=400)

        user.last_otp_counter = new_counter
        user.otp_failed_attempts = 0
        user.otp_lockout_until = None
        user.save(update_fields=["last_otp_counter", "otp_failed_attempts", "otp_lockout_until"])
        reset_token = create_password_reset_token({"sub": user.id, "email": user.email})
        return {"reset_token": reset_token, "message": "Identity verified. You may now set a new password."}

    except Exception as e:
        logger.error(f"forgot_password_verify error: {e}\n{traceback.format_exc()}")
        return JsonResponse({"error": "Verification failed."}, status=500)


@router.post("/auth/forgot-password/reset", auth=None)
def forgot_password_reset(request, data: ForgotPasswordResetRequest):
    """
    Step 2 of forgot-password flow.
    Accepts the password_reset token from step 1 and sets a new password.
    """
    import traceback
    try:
        payload = verify_token(data.reset_token, token_type="password_reset")
        if not payload:
            return JsonResponse({"error": "Reset link is invalid or has expired."}, status=400)

        if data.new_password != data.confirm_password:
            return JsonResponse({"error": "Passwords do not match."}, status=400)

        if len(data.new_password.encode("utf-8")) > 72:
            return JsonResponse({"error": "Password must be 72 characters or fewer."}, status=400)

        user = User.objects.filter(id=payload["sub"], is_active=True).first()
        if not user:
            return JsonResponse({"error": "User not found."}, status=404)

        user.hashed_password = get_password_hash(data.new_password)
        user.save(update_fields=["hashed_password"])

        # Revoke all existing refresh tokens so old sessions are invalidated
        RefreshToken.objects.filter(user=user).update(is_revoked=True)

        return JsonResponse({"message": "Password updated successfully. Please log in with your new password."})

    except Exception as e:
        logger.error(f"forgot_password_reset error: {e}\n{traceback.format_exc()}")
        return JsonResponse({"error": "Password reset failed."}, status=500)


@router.post("/auth/change-password", auth=auth_bearer)
def change_password(request, data: ChangePasswordRequest):
    """
    Change password while logged in.
    Requires current password + TOTP code + new password.
    """
    import traceback
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Unauthorized."}, status=401)
        token = auth_header.split(' ')[1]
        payload = verify_token(token, token_type="access")
        if not payload:
            return JsonResponse({"error": "Invalid or expired session."}, status=401)

        user = User.objects.filter(id=payload["sub"], is_active=True).first()
        if not user:
            return JsonResponse({"error": "User not found."}, status=404)

        # Verify current password
        if not user.hashed_password or not verify_password(data.current_password, user.hashed_password):
            return JsonResponse({"error": "Current password is incorrect."}, status=400)

        # Verify TOTP (required — all accounts have 2FA)
        if not user.is_2fa_enabled or not user.totp_secret:
            return JsonResponse({"error": "2FA is not enabled on this account."}, status=400)

        allowed, wait_msg = check_otp_rate_limit(user)
        if not allowed:
            return JsonResponse({"error": wait_msg}, status=429)

        plaintext_secret = decrypt_totp_secret(user.totp_secret)
        valid, new_counter = verify_totp(plaintext_secret, data.otp, user.last_otp_counter)
        if not valid:
            record_otp_failure(user)
            return JsonResponse({"error": "Invalid or expired authenticator code."}, status=400)

        if data.new_password != data.confirm_password:
            return JsonResponse({"error": "Passwords do not match."}, status=400)

        if len(data.new_password.encode("utf-8")) > 72:
            return JsonResponse({"error": "Password must be 72 characters or fewer."}, status=400)

        user.hashed_password = get_password_hash(data.new_password)
        user.last_otp_counter = new_counter
        user.otp_failed_attempts = 0
        user.otp_lockout_until = None
        user.save(update_fields=["hashed_password", "last_otp_counter", "otp_failed_attempts", "otp_lockout_until"])

        return JsonResponse({"message": "Password changed successfully."})

    except Exception as e:
        logger.error(f"change_password error: {e}\n{traceback.format_exc()}")
        return JsonResponse({"error": "Password change failed."}, status=500)


# ══════════════════════════════════════════════════════════════════════════════
# 2FA ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
#
# Flow overview
# ─────────────
# SETUP:
#   1. POST /2fa/setup          → generates pending secret + QR (no DB write yet)
#   2. POST /2fa/enable  {otp}  → verifies first OTP, promotes secret, enables 2FA
#                                  returns one-time backup codes
#
# LOGIN (when 2FA is enabled):
#   1. POST /auth/login         → password OK → returns {requires_2fa, two_fa_token}
#   2. POST /2fa/login-verify   → OTP + two_fa_token → returns real JWT tokens
#      (if "remember_device":true, also sets a 30-day device cookie)
#
# MANAGEMENT:
#   GET  /2fa/status            → is_2fa_enabled, backup_codes_remaining
#   POST /2fa/disable           → password + OTP/backup → disables 2FA
#   POST /2fa/backup-codes/regenerate → OTP → new set of backup codes
# ══════════════════════════════════════════════════════════════════════════════


def _resolve_authenticated_user(request) -> Optional[User]:
    """
    Extract the authenticated User from a request bearing a Bearer JWT.
    Returns None if unauthenticated.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token, token_type="access")
    if not payload:
        return None
    return User.objects.filter(id=payload.get("sub"), is_active=True).first()


def _issue_full_tokens(user: User) -> JsonResponse:
    """
    Create access + refresh tokens, persist the refresh token, and return
    a JsonResponse with both tokens in the body and as httpOnly cookies.
    Extracted here so login and 2FA login-verify share identical behaviour.
    """
    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token_str = create_refresh_token(token_data)

    RefreshToken.objects.filter(user=user).update(is_revoked=True)
    RefreshToken.objects.create(
        token=refresh_token_str,
        user=user,
        expires_at=timezone.now() + timedelta(days=7),
    )

    response = JsonResponse({
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        },
    })
    response.set_cookie("access_token", access_token,
                        httponly=True, secure=False, samesite="lax", max_age=30 * 60)
    response.set_cookie("refresh_token", refresh_token_str,
                        httponly=True, secure=False, samesite="lax",
                        max_age=7 * 24 * 60 * 60)
    return response


# ── POST /2fa/setup ───────────────────────────────────────────────────────────

@router.post("/2fa/setup", auth=auth_bearer)
def setup_2fa(request):
    """
    Generate a new TOTP secret and return the QR code + manual key.
    The secret is stored as *pending* (totp_pending_secret) and 2FA is NOT
    enabled yet.  The user must call POST /2fa/enable with a valid OTP first.

    Calling this endpoint again before enabling simply overwrites the pending
    secret, which is safe — the previous pending secret is discarded.

    Response
    --------
    {
      "qr_code":    "<base64 PNG>",
      "manual_key": "<Base32 secret>",
      "message":    "Scan the QR code …"
    }
    """
    user = _resolve_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if user.is_2fa_enabled:
        return JsonResponse(
            {"error": "2FA is already enabled. Disable it first to set up a new authenticator."},
            status=400,
        )

    plaintext_secret = generate_totp_secret()
    user.totp_pending_secret = encrypt_totp_secret(plaintext_secret)
    user.save(update_fields=["totp_pending_secret"])

    qr_code = generate_qr_code_base64(user.email, plaintext_secret)

    logger.info(f"2FA setup initiated for user {user.email}")
    return JsonResponse({
        "qr_code": qr_code,
        "manual_key": plaintext_secret,
        "message": (
            "Scan the QR code with Google Authenticator, Authy, or any TOTP app. "
            "Save the manual key as a fallback. Then call POST /2fa/enable with "
            "the 6-digit code to activate 2FA."
        ),
    })


# ── POST /2fa/enable ──────────────────────────────────────────────────────────

@router.post("/2fa/enable", auth=auth_bearer)
def enable_2fa(request, data: TwoFAEnableRequest):
    """
    Verify the first OTP from the user's authenticator app and enable 2FA.
    Also generates and returns 8 one-time backup codes — shown ONCE.

    The user must have called POST /2fa/setup first.

    Returns
    -------
    { "message": "…", "backup_codes": ["xxxxx-xxxxx", …] }
    """
    user = _resolve_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if user.is_2fa_enabled:
        return JsonResponse({"error": "2FA is already enabled."}, status=400)

    if not user.totp_pending_secret:
        return JsonResponse(
            {"error": "No pending 2FA setup found. Call POST /2fa/setup first."},
            status=400,
        )

    allowed, err = check_otp_rate_limit(user)
    if not allowed:
        return JsonResponse({"error": err}, status=429)

    plaintext_secret = decrypt_totp_secret(user.totp_pending_secret)
    valid, counter = verify_totp(plaintext_secret, data.otp, user.last_otp_counter)

    if not valid:
        record_otp_failure(user)
        logger.warning(f"2FA enable failed (bad OTP) for user {user.email}")
        return JsonResponse({"error": "Invalid OTP. Check your authenticator app and try again."}, status=400)

    # Promote pending secret → active secret
    plaintext_backup_codes = generate_backup_codes()
    user.totp_secret = user.totp_pending_secret
    user.totp_pending_secret = None
    user.is_2fa_enabled = True
    user.last_otp_counter = counter
    user.backup_codes = hash_backup_codes(plaintext_backup_codes)
    user.save(update_fields=[
        "totp_secret", "totp_pending_secret", "is_2fa_enabled",
        "last_otp_counter", "backup_codes",
    ])
    reset_otp_failures(user)

    AuditLog.objects.create(
        user=user,
        action="2FA Enabled",
        details="User enabled two-factor authentication.",
        user_string=user.email,
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    logger.info(f"2FA enabled for user {user.email}")

    return JsonResponse({
        "message": "2FA has been enabled. Save your backup codes — they will not be shown again.",
        "backup_codes": plaintext_backup_codes,
    })


# ── POST /2fa/login-verify ────────────────────────────────────────────────────

@router.post("/2fa/login-verify", auth=None)
def login_verify_2fa(request, data: TwoFALoginVerifyRequest):
    """
    Complete a 2FA login.  Called after POST /auth/login returns requires_2fa=true.

    Accepts either a TOTP code (otp) or a backup code (backup_code).
    If remember_device=true, sets a 30-day httpOnly device cookie so this
    device is trusted on future logins.

    Request body
    ------------
    {
      "two_fa_token": "<pending token from /auth/login>",
      "otp":          "123456",          // OR
      "backup_code":  "ab3f9-xk28p",
      "remember_device": false
    }
    """
    # Validate the pending token
    payload = verify_token(data.two_fa_token, token_type="2fa_pending")
    if not payload:
        return JsonResponse({"error": "Invalid or expired 2FA session. Please log in again."}, status=401)

    user = User.objects.filter(id=payload.get("sub"), is_active=True).first()
    if not user or not user.is_2fa_enabled:
        return JsonResponse({"error": "User not found or 2FA not enabled."}, status=400)

    allowed, err = check_otp_rate_limit(user)
    if not allowed:
        return JsonResponse({"error": err}, status=429)

    verified = False

    if data.otp:
        # TOTP path
        if not user.totp_secret:
            return JsonResponse({"error": "2FA is not configured for this account."}, status=400)
        plaintext_secret = decrypt_totp_secret(user.totp_secret)
        valid, counter = verify_totp(plaintext_secret, data.otp, user.last_otp_counter)
        if valid:
            user.last_otp_counter = counter
            user.save(update_fields=["last_otp_counter"])
            verified = True

    elif data.backup_code:
        # Backup-code path
        if not user.backup_codes:
            return JsonResponse({"error": "No backup codes available."}, status=400)
        ok, updated_json = consume_backup_code(data.backup_code, user.backup_codes)
        if ok:
            user.backup_codes = updated_json
            user.save(update_fields=["backup_codes"])
            verified = True
            AuditLog.objects.create(
                user=user,
                action="2FA Backup Code Used",
                details="User authenticated with a backup code.",
                user_string=user.email,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            logger.warning(f"Backup code used for user {user.email}")

    if not verified:
        record_otp_failure(user)
        logger.warning(f"2FA login-verify failed for user {user.email}")
        return JsonResponse({"error": "Invalid code. Please try again."}, status=401)

    reset_otp_failures(user)
    AuditLog.objects.create(
        user=user,
        action="2FA Login Success",
        details="User completed 2FA login.",
        user_string=user.email,
        ip_address=request.META.get("REMOTE_ADDR"),
    )

    response = _issue_full_tokens(user)

    # "Remember this device" — 30-day device cookie
    if data.remember_device:
        device_token = generate_device_token()
        store_device_token(user, device_token)
        response.set_cookie(
            "device_token",
            device_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=DEVICE_TRUST_DAYS * 24 * 60 * 60,
        )

    return response


# ── GET /2fa/status ───────────────────────────────────────────────────────────

@router.get("/2fa/status", auth=auth_bearer)
def get_2fa_status(request):
    """
    Return the current 2FA status and remaining backup code count for the
    authenticated user.
    """
    user = _resolve_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)

    remaining = None
    if user.backup_codes:
        try:
            remaining = len(json.loads(user.backup_codes))
        except (ValueError, TypeError):
            remaining = 0

    return JsonResponse({
        "is_2fa_enabled": user.is_2fa_enabled,
        "backup_codes_remaining": remaining,
    })


# ── POST /2fa/disable ─────────────────────────────────────────────────────────

@router.post("/2fa/disable", auth=auth_bearer)
def disable_2fa(request, data: TwoFADisableRequest):
    """
    Disable 2FA for the authenticated user.
    Requires the account password AND either a valid OTP or a backup code.

    Request body
    ------------
    { "password": "…", "otp": "123456" }   // or "backup_code": "xxxxx-xxxxx"
    """
    user = _resolve_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if not user.is_2fa_enabled:
        return JsonResponse({"error": "2FA is not enabled on this account."}, status=400)

    # Password check
    if not user.hashed_password or not verify_password(data.password, user.hashed_password):
        return JsonResponse({"error": "Incorrect password."}, status=401)

    allowed, err = check_otp_rate_limit(user)
    if not allowed:
        return JsonResponse({"error": err}, status=429)

    verified = False

    if data.otp and user.totp_secret:
        plaintext_secret = decrypt_totp_secret(user.totp_secret)
        valid, counter = verify_totp(plaintext_secret, data.otp, user.last_otp_counter)
        if valid:
            user.last_otp_counter = counter
            verified = True

    elif data.backup_code and user.backup_codes:
        ok, updated_json = consume_backup_code(data.backup_code, user.backup_codes)
        if ok:
            user.backup_codes = updated_json
            verified = True

    if not verified:
        record_otp_failure(user)
        return JsonResponse({"error": "Invalid OTP or backup code."}, status=401)

    # Clear all 2FA state
    user.is_2fa_enabled = False
    user.totp_secret = None
    user.totp_pending_secret = None
    user.backup_codes = None
    user.last_otp_counter = None
    user.trusted_device_tokens = None
    user.save(update_fields=[
        "is_2fa_enabled", "totp_secret", "totp_pending_secret",
        "backup_codes", "last_otp_counter", "trusted_device_tokens",
    ])
    reset_otp_failures(user)

    AuditLog.objects.create(
        user=user,
        action="2FA Disabled",
        details="User disabled two-factor authentication.",
        user_string=user.email,
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    logger.info(f"2FA disabled for user {user.email}")

    response = JsonResponse({"message": "2FA has been disabled."})
    response.delete_cookie("device_token")
    return response


# ── POST /2fa/backup-codes/regenerate ────────────────────────────────────────

@router.post("/2fa/backup-codes/regenerate", auth=auth_bearer)
def regenerate_backup_codes(request, data: TwoFAEnableRequest):
    """
    Regenerate backup codes.  Requires a valid OTP.
    Old codes are immediately invalidated.

    Request body
    ------------
    { "otp": "123456" }
    """
    user = _resolve_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if not user.is_2fa_enabled or not user.totp_secret:
        return JsonResponse({"error": "2FA is not enabled on this account."}, status=400)

    allowed, err = check_otp_rate_limit(user)
    if not allowed:
        return JsonResponse({"error": err}, status=429)

    plaintext_secret = decrypt_totp_secret(user.totp_secret)
    valid, counter = verify_totp(plaintext_secret, data.otp, user.last_otp_counter)
    if not valid:
        record_otp_failure(user)
        return JsonResponse({"error": "Invalid OTP."}, status=400)

    new_codes = generate_backup_codes()
    user.backup_codes = hash_backup_codes(new_codes)
    user.last_otp_counter = counter
    user.save(update_fields=["backup_codes", "last_otp_counter"])
    reset_otp_failures(user)

    AuditLog.objects.create(
        user=user,
        action="2FA Backup Codes Regenerated",
        details="User regenerated backup codes.",
        user_string=user.email,
        ip_address=request.META.get("REMOTE_ADDR"),
    )

    return JsonResponse({
        "message": "New backup codes generated. Save them — they will not be shown again.",
        "backup_codes": new_codes,
    })

# OAuth routes removed - using simple email/password authentication only
