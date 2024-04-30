import datetime
import string
import random
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from taggit.models import Tag

from core.models import CartOrder, Product, Category, CartOrderProducts
from django.db.models import Sum, Count
from userauths.models import User, TempUser
from useradmin.forms import AddProductForm


@login_required
def dashboard(request):
    user = request.user
    all_products = user.product_set.all()
    distinct_categories = all_products.values('category').distinct()

    user_products = Product.objects.filter(user=user)

    # Calculate total revenue for the user's products
    revenue = user_products.aggregate(total=Sum('cartorderproducts__total'))['total']

    # Calculate total number of orders for the user's products
    total_orders_count = user_products.aggregate(total_orders=Count('cartorderproducts__order', distinct=True))['total_orders']

    # Retrieve all CartOrderProducts related to user's products
    cart_order_products = CartOrderProducts.objects.filter(product__in=user_products)

    # Grouping cart_order_products by order ID and calculating total price for each order
    orders_data = {}
    for cart_order_product in cart_order_products:
        order_id = cart_order_product.order_id
        if order_id in orders_data:
            orders_data[order_id]['total_price'] += cart_order_product.total
        else:
            orders_data[order_id] = {
                'order_date': cart_order_product.order.order_date,
                'payment_method': cart_order_product.order.payment_method,
                'payment_status': cart_order_product.order.paid_status,
                'sku': cart_order_product.order.sku,
                'total_price': cart_order_product.total,
                'username': cart_order_product.order.user
            }

    # Sort orders_data by order_date in descending order
    ordered_orders_data = dict(sorted(orders_data.items(), key=lambda item: item[1]['order_date'], reverse=True))

    # Calculate total monthly revenue for the currently logged-in user
    this_month = datetime.datetime.now().month
    monthly_revenue = sum(order_info['total_price'] for order_info in orders_data.values() if order_info['order_date'].month == this_month)

    context = {
        "monthly_revenue": monthly_revenue,
        "revenue": revenue,
        "all_products": all_products,
        "distinct_categories": distinct_categories,
        "orders_data": ordered_orders_data,
        "total_orders_count": total_orders_count,
    }
    return render(request, "useradmin/dashboard.html", context)


@login_required
def dashboard_products(request):
    user = request.user
    all_products = user.product_set.all()
    all_categories = Category.objects.all()
    
    context = {
        "all_products": all_products,
        "all_categories": all_categories,
    }
    return render(request, "useradmin/dashboard-products.html", context)


@login_required
def dashboard_add_product(request):
    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            # Ensure old_price is None if it's empty or contains invalid data
            old_price = form.cleaned_data.get('old_price')
            if old_price == '':
                new_form.old_price = None
            else:
                try:
                    new_form.old_price = float(old_price)
                except ValueError:
                    new_form.old_price = None
            # Save the product first to assign a primary key
            new_form.save()
            # Process tags input and save them properly
            tags = form.cleaned_data.get('tags')
            if tags:
                # Split the tags string by comma, filter out empty strings and duplicates
                tag_list = list(set(filter(None, (tag.strip() for tag in tags.split(',')))))
                # Create or retrieve Tag objects for each tag in the list
                tag_objects = [Tag.objects.get_or_create(name=tag)[0] for tag in tag_list]
                # Set the tags for the product
                new_form.tags.set(tag_objects)

            return redirect("useradmin:dashboard-products")
    else:
        form = AddProductForm()
    context = {
        'form':form
    }
    return render(request, "useradmin/dashboard-add-products.html", context)


@login_required
def dashboard_edit_product(request, pid):
    product = Product.objects.get(pid=pid)

    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            new_form = form.save(commit=False)
            old_price = form.cleaned_data.get('old_price')
            if old_price == '':
                new_form.old_price = None
            else:
                try:
                    new_form.old_price = float(old_price)
                except ValueError:
                    new_form.old_price = None
            new_form.save()
            # Process tags input and save them properly
            tags = form.cleaned_data.get('tags')
            if tags:
                # Split the tags string by comma, filter out empty strings and duplicates
                tag_list = list(set(filter(None, (tag.strip() for tag in tags.split(',')))))
                # Create or retrieve Tag objects for each tag in the list
                tag_objects = [Tag.objects.get_or_create(name=tag)[0] for tag in tag_list]
                # Set the tags for the product
                new_form.tags.set(tag_objects)
            # form.save_m2m()
            return redirect("useradmin:dashboard-products")
    else:
        form = AddProductForm(instance=product)
    context = {
        'form':form,
        'product':product,
    }
    return render(request, "useradmin/dashboard-edit-products.html", context)


@login_required
def dashboard_delete_product(request, pid):
    product = Product.objects.get(pid=pid)
    product.delete()
    return redirect("useradmin:dashboard-products")


def generate_otp(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def send_verification_email(email, otp):
    subject = 'Email Verification'
    message = f'Dear user,\n Your One-Time Password (OTP) for account verification is: {otp}\nDo not share this OTP with anyone for security reasons.'
    from_email = 'advertise.website0994@gmail.com'  # Update with your email address
    to_email = email
    try:
        send_mail(subject, message, from_email, [to_email])
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False


def send_otp_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if User.objects.filter(email=email, is_superuser=1).exists():
            # Generate OTP
            otp = generate_otp()
            if send_verification_email(email, otp):
                TempUser.objects.create(email=email, otp=otp)
                # Return success response
                return JsonResponse({"success": "OTP has been sent successfully"})
            else:
                return JsonResponse({"error": "OTP not sent, Try again."})
        else:
            return JsonResponse({"error": "Email does not exists"})
    else:
        return JsonResponse({"error": "Invalid request method"})


@login_required
def dashboard_statistics_superuser(request):
    revenue = CartOrder.objects.aggregate(price=Sum("price"))
    total_orders_count = CartOrder.objects.all()
    all_products = Product.objects.all()
    all_categories = Category.objects.all()

    this_month = datetime.datetime.now().month
    monthly_revenue = CartOrder.objects.filter(order_date__month=this_month).aggregate(price=Sum("price"))

    context = {
        "monthly_revenue": monthly_revenue,
        "revenue": revenue,
        "all_products": all_products,
        "all_categories": all_categories,
        "total_orders_count": total_orders_count,
    }
    return render(request, "useradmin/dashboard_statistics.html", context)
