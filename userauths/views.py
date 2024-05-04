import random
import string

from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from userauths.forms import UserRegisterForm, ProfileForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.conf import settings
from userauths.models import Profile, User, TempUser


# User = settings.AUTH_USER_MODEL

def generate_otp(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def send_verification_email(email, otp):
    subject = 'Email Verification'
    message = f'Dear user,\n\nYour One-Time Password (OTP) for account verification is: {otp}\n\nPlease use this OTP for account verification process.\n\nDo not share this OTP with anyone for security reasons.'
    from_email = 'alicart.eshop@gmail.com'  # Update with your email address
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
        if TempUser.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already exists"})
        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already exists"})
        # Generate OTP
        otp = generate_otp()
        if send_verification_email(email, otp):
            TempUser.objects.create(email=email, otp=otp)
            # Return success response
            return JsonResponse({"success": "OTP has been sent successfully"})
        else:
            return JsonResponse({"error": "OTP not sent, Try again."})
    else:
        return JsonResponse({"error": "Invalid request method"})


def verify_otp_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        # Retrieve TempUser object based on email
        try:
            temp_user = TempUser.objects.get(email=email)
        except TempUser.DoesNotExist:
            return JsonResponse({"error": "No such user found"})
        # Check if OTP matches
        if temp_user.otp == otp:
            # OTP verification successful, delete TempUser and return success response
            temp_user.delete()
            return JsonResponse({"success": "OTP has been verified successfully"})
        else:
            return JsonResponse({"error": "Invalid OTP"})
    else:
        return JsonResponse({"error": "Invalid request method"})


def register_view(request):
    if request.user.is_authenticated:
        messages.warning(request, f"Hey you are already Logged In.")
        return redirect("core:index")
    if request.method == "POST":
        form = UserRegisterForm(request.POST or None)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data['password1'])  # Set password
            new_user.save()
            # Authenticate and login the user
            new_user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password1'])
            login(request, new_user)
            messages.success(request, f"Hey {new_user.username}, Your account was created successfully.")
            return redirect("core:index")
    else:
        form = UserRegisterForm()
    context = {'form': form}
    return render(request, "userauths/sign-up.html", context)


def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, f"Hey you are already Logged In.")
        return redirect("core:index")
    
    if request.method == "POST":
        email = request.POST.get("email") # peanuts@gmail.com
        password = request.POST.get("password") # getmepeanuts
        try:
            user = User.objects.get(email=email)
            user = authenticate(username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "You are logged in.")
                # Clear the session data after login
                if 'wishlist_count' in request.session:
                    if request.session['wishlist_count']:
                        del request.session['wishlist_count']
                if 'cart_data_obj' in request.session:
                    if request.session['cart_data_obj']:
                        del request.session['cart_data_obj']
                return redirect("core:index")
            else:
                messages.warning(request, "User Does Not Exist, create an account.")
    
        except:
            messages.warning(request, f"User with {email} does not exist")
    
    return render(request, "userauths/sign-in.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You logged out.")
    return redirect("userauths:sign-in")


def profile_update(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            new_form.save()
            messages.success(request, "Profile Updated Successfully.")
            return redirect("core:dashboard")
    else:
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
        "profile": profile,
    }

    return render(request, "userauths/profile-edit.html", context)


def forgot_password(request):
    if request.user.is_authenticated:
        messages.warning(request, f"Hey you are already Logged In.")
        return redirect("core:index")
    if request.method == "POST":
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        otp = request.POST.get('otp')

        # Store the form data in a dictionary to pass it back in case of errors
        form_data = {'email': email, 'password1': password1, 'password2': password2, 'otp': otp}

        if email and password1 and password1 == password2:
            try:
                # Get the user object associated with the provided email
                user = User.objects.get(email=email)

                # Set the new password
                user.set_password(password1)
                user.save()

                # Authenticate and login the user with the new password
                user = authenticate(username=email, password=password1)
                login(request, user)

                # Redirect to the index page
                messages.success(request, f"Hey {user.username}, Your password is changed successfully.")
                return redirect("core:index")
            except User.DoesNotExist:
                # Handle case where user with provided email doesn't exist
                messages.error(request, "User with this email doesn't exist.")
        else:
            # Handle case where email or passwords are missing or passwords don't match
            messages.error(request, "Invalid email or passwords don't match.")

        # Pass form_data along with the error message in the context
        context = {'form_data': form_data}
        return render(request, "userauths/forgot-password.html", context)
    else:
        return render(request, "userauths/forgot-password.html")


def send_forgot_otp_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if not User.objects.filter(email=email).exists():
            return JsonResponse({"error": "There is no account associated with this email address."})
        # Generate OTP
        otp = generate_otp()
        if send_verification_email(email, otp):
            TempUser.objects.create(email=email, otp=otp)
            # Return success response
            return JsonResponse({"success": "OTP has been sent successfully"})
        else:
            return JsonResponse({"error": "OTP not sent, Try again."})
    else:
        return JsonResponse({"error": "Invalid request method"})