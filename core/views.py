from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from taggit.models import Tag
from core.models import Product, Vendor, CartOrderProducts, ProductReview, wishlist_model, Address
from userauths.models import ContactUs, Profile
from core.forms import ProductReviewForm
from django.contrib import messages

from django.urls import reverse
from django.conf import settings
from paypal.standard.forms import PayPalPaymentsForm
from django.contrib.auth.decorators import login_required

import calendar
from django.db.models import Count, Avg, Q, Sum
from django.db.models.functions import ExtractMonth
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist


def index(request):
    products = Product.objects.filter(product_status="published", featured=True).order_by("-id")

    # Fetch the top selling products based on the sum of quantities sold
    top_selling_products = Product.objects.annotate(total_qty_sold=Sum('cartorderproducts__qty')).order_by(
        '-total_qty_sold')[:3]

    # Fetch the trending products
    trending_products = Product.objects.filter(product_status="published").order_by('-date')[:3]

    # Fetching recently added products
    recently_added_products = Product.objects.filter(product_status="published").order_by("-date")[:3]

    # Fetch the top-rated products
    top_rated_products = Product.objects.filter(product_status="published").annotate(average_rating=Avg('reviews__rating')).order_by('-average_rating')[:3]

    # Calculate average rating for each product
    for product in top_selling_products:
        product.total_qty_sold = product.cartorderproducts_set.aggregate(Sum('qty'))['qty__sum']
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        adjusted_rating = avg_rating * 20
        product.average_rating = adjusted_rating
        product.display_rating = avg_rating

    for product in trending_products:
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        adjusted_rating = avg_rating * 20
        product.average_rating = adjusted_rating
        product.display_rating = avg_rating

    for product in recently_added_products:
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        adjusted_rating = avg_rating * 20
        product.average_rating = adjusted_rating
        product.display_rating = avg_rating

    for product in top_rated_products:
        avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        adjusted_rating = avg_rating * 20
        product.average_rating = adjusted_rating
        product.display_rating = avg_rating

    context = {
        'products': products,
        'top_selling_products': top_selling_products,
        'recently_added_products': recently_added_products,
        'top_rated_products': top_rated_products,
        'trending_products': trending_products
    }

    return render(request, 'core/index.html', context)


def product_list_view(request):
    products = Product.objects.filter(product_status="published").order_by("-id")
    tags = Tag.objects.all().order_by("-id")[:6]

    context = {
        "products":products,
        "tags":tags,
    }

    return render(request, 'core/product-list.html', context)


def category_list_view(request):
    categories = Category.objects.all()

    context = {
        "categories":categories
    }
    return render(request, 'core/category-list.html', context)


def category_product_list__view(request, cid):

    category = Category.objects.get(cid=cid) # food, Cosmetics
    products = Product.objects.filter(product_status="published", category=category)

    context = {
        "category":category,
        "products":products,
    }
    return render(request, "core/category-product-list.html", context)


def vendor_list_view(request):
    vendors = Vendor.objects.all()
    context = {
        "vendors": vendors,
    }
    return render(request, "core/vendor-list.html", context)


def vendor_detail_view(request, vid):
    vendor = Vendor.objects.get(vid=vid)
    products = Product.objects.filter(vendor=vendor, product_status="published").order_by("-id")

    context = {
        "vendor": vendor,
        "products": products,
    }
    return render(request, "core/vendor-detail.html", context)


def product_detail_view(request, pid):
    product = Product.objects.get(pid=pid)
    products = Product.objects.filter(category=product.category).exclude(pid=pid)

    # Getting all reviews related to a product
    reviews = ProductReview.objects.filter(product=product).order_by("-date")

    # Getting average review
    average_rating = ProductReview.objects.filter(product=product).aggregate(rating=Avg('rating'))

    # Product Review form
    review_form = ProductReviewForm()

    make_review = True 

    if request.user.is_authenticated:
        try:
            address = Address.objects.get(status=True, user=request.user)
            user_review_count = ProductReview.objects.filter(user=request.user, product=product).count()
            if user_review_count > 0:
                make_review = False
        except ObjectDoesNotExist:
            address = None
            make_review = False
            messages.warning(request, "No active address found. Please add an address.")

    else:
        address = "Login To Continue"

    p_image = product.p_images.all()

    context = {
        "p": product,
        "address": address,
        "make_review": make_review,
        "review_form": review_form,
        "p_image": p_image,
        "average_rating": average_rating,
        "reviews": reviews,
        "products": products,
    }

    return render(request, "core/product-detail.html", context)


def tag_list(request, tag_slug=None):

    products = Product.objects.filter(product_status="published").order_by("-id")

    tag = None 
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        products = products.filter(tags__in=[tag])

    context = {
        "products": products,
        "tag": tag
    }

    return render(request, "core/tag.html", context)


def ajax_add_review(request, pid):
    product = Product.objects.get(pk=pid)
    user = request.user 

    review = ProductReview.objects.create(
        user=user,
        product=product,
        review = request.POST['review'],
        rating = request.POST['rating'],
    )

    context = {
        'user': user.username,
        'review': request.POST['review'],
        'rating': request.POST['rating'],
    }

    average_reviews = ProductReview.objects.filter(product=product).aggregate(rating=Avg("rating"))

    return JsonResponse(
       {
         'bool': True,
        'context': context,
        'average_reviews': average_reviews
       }
    )


def search_view(request):
    query = request.GET.get("q")

    # Search across multiple fields using Q objects
    products = Product.objects.filter(
        Q(title__icontains=query) |  # Search in title
        Q(description__icontains=query) |  # Search in description
        Q(specifications__icontains=query) |  # Search in specifications
        Q(tags__name__icontains=query)  # Search in tags
    ).distinct().order_by("-date")

    context = {
        "products": products,
        "query": query,
    }
    return render(request, "core/search.html", context)


def search_characters(request):
    query = request.GET.get('q', '')
    suggestions = []
    if query:
        products = Product.objects.filter(
            Q(title__icontains=query) |  # Search in title
            Q(description__icontains=query) |  # Search in description
            Q(specifications__icontains=query) |  # Search in specifications
            Q(tags__name__icontains=query)  # Search in tags
        ).order_by('title').values_list('title', flat=True).distinct()
        suggestions = list(products)
    return JsonResponse(suggestions, safe=False)


def filter_product(request):
    categories = request.GET.getlist("category[]")
    vendors = request.GET.getlist("vendor[]")
    min_price = request.GET['min_price']
    max_price = request.GET['max_price']

    products = Product.objects.filter(product_status="published").order_by("-id").distinct()

    products = products.filter(price__gte=min_price)
    products = products.filter(price__lte=max_price)

    if len(categories) > 0:
        products = products.filter(category__id__in=categories).distinct() 
    else:
        products = Product.objects.filter(product_status="published").order_by("-id").distinct()
    if len(vendors) > 0:
        products = products.filter(vendor__id__in=vendors).distinct() 
    else:
        products = Product.objects.filter(product_status="published").order_by("-id").distinct()    

    data = render_to_string("core/async/product-list.html", {"products": products})
    return JsonResponse({"data": data})


# def add_to_cart(request):
#     cart_product = {}
#     cart_product[str(request.GET['id'])] = {
#         'title': request.GET['title'],
#         'qty': request.GET['qty'],
#         'price': request.GET['price'],
#         'image': request.GET['image'],
#         'pid': request.GET['pid'],
#     }
#
#     if 'cart_data_obj' in request.session:
#         if str(request.GET['id']) in request.session['cart_data_obj']:
#             cart_data = request.session['cart_data_obj']
#             cart_data[str(request.GET['id'])]['qty'] = int(cart_product[str(request.GET['id'])]['qty'])
#             cart_data.update(cart_data)
#             request.session['cart_data_obj'] = cart_data
#         else:
#             cart_data = request.session['cart_data_obj']
#             cart_data.update(cart_product)
#             request.session['cart_data_obj'] = cart_data
#
#     else:
#         request.session['cart_data_obj'] = cart_product
#     return JsonResponse({"data":request.session['cart_data_obj'], 'totalcartitems': len(request.session['cart_data_obj'])})

def add_to_cart(request):
    product_id = str(request.GET.get('id'))
    cart_product = {
        'title': request.GET.get('title'),
        'qty': int(request.GET.get('qty')),
        'price': request.GET.get('price'),
        'image': request.GET.get('image'),
        'pid': request.GET.get('pid'),
    }

    if 'cart_data_obj' in request.session:
        cart_data = request.session['cart_data_obj']
        if product_id in cart_data:
            # If product already exists in cart, remove it
            del cart_data[product_id]
        else:
            cart_data[product_id] = cart_product
        request.session['cart_data_obj'] = cart_data
    else:
        request.session['cart_data_obj'] = {product_id: cart_product}

    return JsonResponse({"data": request.session['cart_data_obj'], 'totalcartitems': len(request.session['cart_data_obj'])})


def cart_view(request):
    cart_total_amount = 0
    if 'cart_data_obj' in request.session:
        for p_id, item in request.session['cart_data_obj'].items():
            cart_total_amount += int(item['qty']) * float(item['price'])
        return render(request, "core/cart.html", {"cart_data":request.session['cart_data_obj'], 'totalcartitems': len(request.session['cart_data_obj']), 'cart_total_amount':cart_total_amount})
    else:
        messages.warning(request, "Your cart is empty")
        return redirect("core:index")


def delete_item_from_cart(request):
    product_id = str(request.GET['id'])
    if 'cart_data_obj' in request.session:
        if product_id in request.session['cart_data_obj']:
            cart_data = request.session['cart_data_obj']
            del request.session['cart_data_obj'][product_id]
            request.session['cart_data_obj'] = cart_data
    
    cart_total_amount = 0
    if 'cart_data_obj' in request.session:
        for p_id, item in request.session['cart_data_obj'].items():
            cart_total_amount += int(item['qty']) * float(item['price'])

    context = render_to_string("core/async/cart-list.html", {"cart_data":request.session['cart_data_obj'], 'totalcartitems': len(request.session['cart_data_obj']), 'cart_total_amount':cart_total_amount})
    return JsonResponse({"data": context, 'totalcartitems': len(request.session['cart_data_obj'])})


def update_cart(request):
    product_id = str(request.GET['id'])
    product_qty = request.GET['qty']

    if 'cart_data_obj' in request.session:
        if product_id in request.session['cart_data_obj']:
            cart_data = request.session['cart_data_obj']
            cart_data[str(request.GET['id'])]['qty'] = product_qty
            request.session['cart_data_obj'] = cart_data
    
    cart_total_amount = 0
    if 'cart_data_obj' in request.session:
        for p_id, item in request.session['cart_data_obj'].items():
            cart_total_amount += int(item['qty']) * float(item['price'])

    context = render_to_string("core/async/cart-list.html", {"cart_data":request.session['cart_data_obj'], 'totalcartitems': len(request.session['cart_data_obj']), 'cart_total_amount':cart_total_amount})
    return JsonResponse({"data": context, 'totalcartitems': len(request.session['cart_data_obj'])})


# @login_required
def checkout_view(request):
    cart_total_amount = 0
    total_amount = 0

    # Checking if cart_data_obj session exists
    if 'cart_data_obj' in request.session:
        # Getting total amount for Paypal Amount
        for p_id, item in request.session['cart_data_obj'].items():
            total_amount += int(item['qty']) * float(item['price'])

        if request.user.is_authenticated:
            # User is authenticated, use the current user for the order
            user = request.user
        else:
            # User is not authenticated, use a placeholder user object
            user = None

        # Save the CartOrder instance with cheque_picture and comments
        order = CartOrder.objects.create(
            user=user,
            price=total_amount,
        )

        # Getting total amount for The Cart
        for p_id, item in request.session['cart_data_obj'].items():
            cart_total_amount += int(item['qty']) * float(item['price'])

            # Fetch the Product instance corresponding to the product ID (pid)
            product = get_object_or_404(Product, pid=item['pid'])

            cart_order_products = CartOrderProducts.objects.create(
                order=order,
                invoice_no="INVOICE_NO-" + str(order.id),  # INVOICE_NO-5,
                item=item['title'],
                image=item['image'],
                qty=item['qty'],
                price=item['price'],
                product=product,
                total=float(item['qty']) * float(item['price'])
            )

        host = request.get_host()
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': cart_total_amount,
            'item_name': "Order-Item-No-" + str(order.id),
            'invoice': "INVOICE_NO-" + str(order.id),
            'currency_code': "USD",
            'notify_url': 'http://{}{}'.format(host, reverse("core:paypal-ipn")),
            'return_url': 'http://{}{}'.format(host, reverse("core:payment-completed")),
            'cancel_url': 'http://{}{}'.format(host, reverse("core:payment-failed")),
        }

        paypal_payment_button = PayPalPaymentsForm(initial=paypal_dict)

        # cart_total_amount = 0
        # if 'cart_data_obj' in request.session:
        #     for p_id, item in request.session['cart_data_obj'].items():
        #         cart_total_amount += int(item['qty']) * float(item['price'])

        try:
            active_address = Address.objects.get(user=request.user, status=True)
        except:
            if request.user.is_authenticated:
                messages.warning(request, "There are multiple addresses, only one should be activated.")
                active_address = None
            else:
                messages.warning(request, "")
                active_address = None

        return render(request, "core/checkout.html", {"cart_data":request.session['cart_data_obj'], 'totalcartitems': len(request.session['cart_data_obj']), 'cart_total_amount':cart_total_amount, 'paypal_payment_button':paypal_payment_button, "active_address":active_address})


def payment_completed_view(request):
    payment_option = request.POST.get('payment_option')
    if payment_option == 'cart_and_check':
        # User has selected "Pay with cart and upload the check"
        name = request.POST.get('fname')
        lname = request.POST.get('lname')
        address = request.POST.get('billing_address')
        cheque_picture = request.FILES.get('cheque_picture')
        comments = request.POST.get('comments')

        # Check if any required field is empty
        if not (name and lname and address and cheque_picture and comments):
            messages.error(request, 'Please fill out all required fields.')
            return redirect('core:checkout')

        cart_total_amount = 0
        cart_data = request.session.get('cart_data_obj', {})

        for p_id, item in cart_data.items():
            cart_total_amount += int(item['qty']) * float(item['price'])

        if request.user.is_authenticated:
            cart_order = CartOrder.objects.get(user=request.user, price=cart_total_amount, paid_status=False)
            cart_order.comments = comments
            cart_order.payment_method = "Cheque"
            cart_order.cheque_picture = cheque_picture
            cart_order.save()
        else:
            cart_order = CartOrder.objects.get(price=cart_total_amount, paid_status=False)
            cart_order.comments = comments
            cart_order.payment_method = "Cheque"
            cart_order.cheque_picture = cheque_picture
            cart_order.save()
    else:
        name = request.POST.get('fname')
        lname = request.POST.get('lname')
        address = request.POST.get('billing_address')

        # Check if any required field is empty
        if not (name and lname and address):
            messages.error(request, 'Please fill out all required fields.')
            return redirect('core:checkout')

        cart_total_amount = 0
        cart_data = request.session.get('cart_data_obj', {})

        for p_id, item in cart_data.items():
            cart_total_amount += int(item['qty']) * float(item['price'])

        if request.user.is_authenticated:
            cart_order = CartOrder.objects.get(user=request.user, price=cart_total_amount, paid_status=False)
            cart_order.payment_method = "COD"
            cart_order.save()
        else:
            cart_order = CartOrder.objects.get(price=cart_total_amount, paid_status=False)
            cart_order.payment_method = "COD"
            cart_order.save()

    return render(request, 'core/payment-completed.html',
                  {'name': name, 'cart_data': cart_data, 'totalcartitems': len(cart_data),
                   'cart_total_amount': cart_total_amount})


@login_required
def payment_failed_view(request):
    return render(request, 'core/payment-failed.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        # Retrieve password fields from the request
        current_password = request.POST.get('password')
        new_password = request.POST.get('npassword')
        confirm_password = request.POST.get('cpassword')

        # Check if the current password is correct
        if not request.user.check_password(current_password):
            messages.error(request, 'Your current password is incorrect.')
            return redirect('core:dashboard')

        # Check if the new password and confirm password match
        if new_password != confirm_password:
            messages.error(request, 'New password and confirm password do not match.')
            return redirect('core:dashboard')

        # Update the user's password
        user = request.user
        user.password = make_password(new_password)
        user.save()

        # Update the session authentication hash
        update_session_auth_hash(request, user)

        # Redirect back to the dashboard with a success message
        messages.success(request, 'Your password was successfully updated!')
        return redirect('core:dashboard')
    else:
        # If the request method is not POST, redirect back to dashboard page
        return redirect('core:dashboard')


@login_required
def customer_dashboard(request):
    orders_list = CartOrder.objects.filter(user=request.user).order_by("-id")
    address = Address.objects.filter(user=request.user)

    orders = CartOrder.objects.annotate(month=ExtractMonth("order_date")).values("month").annotate(count=Count("id")).values("month", "count")
    month = []
    total_orders = []

    for i in orders:
        month.append(calendar.month_name[i["month"]])
        total_orders.append(i["count"])

    # If the user has no addresses yet, set the first address as default
    if not address.exists():
        if request.method == "POST":
            address_text = request.POST.get("address")
            mobile = request.POST.get("mobile")

            # Create a new address
            new_address = Address.objects.create(
                user=request.user,
                address=address_text,
                mobile=mobile,
                status=True
            )
            messages.success(request, "Address Added Successfully.")
            return redirect("core:dashboard")
        else:
            print("Error")
    # If the user already has addresses, continue as usual
    else:
        if request.method == "POST":
            address = request.POST.get("address")
            mobile = request.POST.get("mobile")

            new_address = Address.objects.create(
                user=request.user,
                address=address,
                mobile=mobile,
            )
            messages.success(request, "Address Added Successfully.")
            return redirect("core:dashboard")
        else:
            print("Error")
    
    user_profile = Profile.objects.get(user=request.user)
    # print("user profile is: #########################",  user_profile)

    context = {
        "user_profile": user_profile,
        "orders": orders,
        "orders_list": orders_list,
        "address": address,
        "month": month,
        "total_orders": total_orders,
    }
    return render(request, 'core/dashboard.html', context)


def order_detail(request, id):
    order = CartOrder.objects.get(user=request.user, id=id)
    order_items = CartOrderProducts.objects.filter(order=order)
    
    context = {
        "order_items": order_items,
    }
    return render(request, 'core/order-detail.html', context)


def make_address_default(request):
    id = request.GET['id']
    Address.objects.update(status=False)
    Address.objects.filter(id=id).update(status=True)
    return JsonResponse({"boolean": True})


@login_required
def wishlist_view(request):
    wishlist = wishlist_model.objects.filter(user=request.user)
    context = {
        "w":wishlist
    }
    return render(request, "core/wishlist.html", context)


def add_to_wishlist(request):
    product_id = request.GET.get('id')
    product = Product.objects.get(id=product_id)

    context = {}

    # Check if the product is already in the wishlist
    wishlist_item = wishlist_model.objects.filter(product=product, user=request.user).first()

    if wishlist_item:
        # If the product is already in the wishlist, remove it
        wishlist_item.delete()
        context = {
            "bool": False  # Indicate that the product is removed from the wishlist
        }
    else:
        # If the product is not in the wishlist, add it
        new_wishlist = wishlist_model.objects.create(
            user=request.user,
            product=product,
        )
        context = {
            "bool": True  # Indicate that the product is added to the wishlist
        }

    return JsonResponse(context)



# def remove_wishlist(request):
#     pid = request.GET['id']
#     wishlist = wishlist_model.objects.filter(user=request.user).values()

#     product = wishlist_model.objects.get(id=pid)
#     h = product.delete()

#     context = {
#         "bool": True,
#         "wishlist":wishlist
#     }
#     t = render_to_string("core/async/wishlist-list.html", context)
#     return JsonResponse({"data": t, "w":wishlist})

def remove_wishlist(request):
    pid = request.GET['id']
    wishlist = wishlist_model.objects.filter(user=request.user)
    wishlist_d = wishlist_model.objects.get(id=pid)
    delete_product = wishlist_d.delete()
    
    context = {
        "bool":True,
        "w":wishlist
    }
    wishlist_json = serializers.serialize('json', wishlist)
    t = render_to_string('core/async/wishlist-list.html', context)
    return JsonResponse({'data':t,'w':wishlist_json})


from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .forms import ContactForm


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save the form data to the database
            form.save()

            # Get cleaned data from the form
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Construct email message
            email_message = f"Name: {full_name}\nEmail: {email}\nPhone: {phone}\nSubject: {subject}\nMessage: {message}"

            try:
                # Send email
                send_mail(
                    'Contact Form Submission',
                    email_message,
                    'sender@example.com',  # Sender's email
                    ['your@gmail.com'],  # Recipient's email
                    fail_silently=False,
                )
                return render(request, 'core/contact.html', {'success_message': 'Message sent successfully!'})
            except Exception as e:
                return render(request, 'core/contact.html', {'error_message': str(e)})
    else:
        form = ContactForm()

    return render(request, 'core/contact.html', {'form': form})


def ajax_contact_form(request):
    full_name = request.GET['full_name']
    email = request.GET['email']
    phone = request.GET['phone']
    subject = request.GET['subject']
    message = request.GET['message']

    contact = ContactUs.objects.create(
        full_name=full_name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
    )

    data = {
        "bool": True,
        "message": "Message Sent Successfully"
    }

    return JsonResponse({"data":data})


def about_us(request):
    return render(request, "core/about_us.html")



def privacy_policy(request):
    return render(request, "core/privacy_policy.html")

def terms_of_service(request):
    return render(request, "core/terms_of_service.html")

def sign_in(request):
    return render(request, "userauths/sign-in.html")

def sign_up(request):
    return render(request, "userauths/sign-up.html")




from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from core.models import CartOrder, Category  # Import your models

def generate_report(request):
    # Your logic to fetch data for the report
    revenue = 13500.50
    total_orders_count = 50
    all_categories = Category.objects.all()
    latest_orders = CartOrder.objects.all().order_by('-order_date')[:10]

    # Define the styles for the report
    styles = getSampleStyleSheet()
    style_heading = styles["Heading1"]
    style_body = styles["BodyText"]

    # Create the elements for the PDF report
    report_elements = []

    # Add a heading
    report_elements.append(Paragraph("Report", style_heading))
    report_elements.append(Spacer(1, 12))

    # Add revenue and total orders count
    report_elements.append(Paragraph(f"Total Revenue: ${revenue}", style_body))
    report_elements.append(Paragraph(f"Total Orders: {total_orders_count}", style_body))
    report_elements.append(Spacer(1, 12))

    # Add a table of categories
    category_table_data = [["Category ID", "Category Name"]]
    for category in all_categories:
        category_table_data.append([category.id, category.title])  # Use title attribute for category name
    category_table = Table(category_table_data)
    category_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                         ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                         ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    report_elements.append(Paragraph("Categories:", style_body))
    report_elements.append(category_table)
    report_elements.append(Spacer(1, 12))

    # Add a table of latest orders
    order_table_data = [["Order ID", "User", "Date", "Price"]]
    for order in latest_orders:
        order_table_data.append([order.id, order.user.username, order.order_date, order.price])
    order_table = Table(order_table_data)
    order_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                      ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                      ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                      ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                      ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    report_elements.append(Paragraph("Latest Orders:", style_body))
    report_elements.append(order_table)
    report_elements.append(Spacer(1, 12))

    # Create a PDF document
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)

    # Add elements to the PDF document and generate the PDF
    doc.build(report_elements)

    return response