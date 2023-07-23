import json
import datetime
import random
import string

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django_otp.plugins.otp_email.models import EmailDevice


from cart.models import CartItem, Cart
from cart.views import _cart_id
from django.core.exceptions import ObjectDoesNotExist
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from shop.models import Product





@login_required(login_url = 'accounts:login')
def payment_method(request):
    return render(request, 'shop/orders/payment_method.html',)


@login_required(login_url = 'accounts:login')
def checkout(request,total=0, total_price=0, quantity=0, cart_items=None):
    tax = 0.00
    handing = 0.00
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total_price += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        total = total_price + 10

    except ObjectDoesNotExist:
        pass # just ignore

    
    tax = round(((2 * total_price)/100), 2)
    grand_total = total_price + tax
    handing = 15.00
    total = float(grand_total) + handing
    
    context = {
        'total_price': total_price,
        'quantity': quantity,
        'cart_items':cart_items,
        'handing': handing,
        'vat' : tax,
        'order_total': total,
    }
    return render(request, 'shop/orders/checkout/checkout.html', context)


@login_required(login_url = 'accounts:login')
def payment(request, total=0, quantity=0):
    current_user = request.user
    handing = 15.0
    # if the cart cout less than 0 , redirect to shop page 
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0 :
        return redirect('shop:shop')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = round(((2 * total)/100), 2)

    grand_total = total + tax
    handing = 15.00
    total = float(grand_total) + handing
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # shop all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address = form.cleaned_data['address']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20210305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()


            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'handing': handing,
                'vat': tax,
                'order_total': total,
            }
            return render(request, 'shop/orders/checkout/payment.html', context)
        else:
            messages.error(request, 'Your information not Valid')
            return redirect('orders:checkout')
            
    else:
        return redirect('orders:otp_verification')


def payments(request):
    try:
        body = json.loads(request.body)
    
        order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
        
        # Store transation details inside payment model 
        payment = Payment(
            user = request.user,
            payment_id = body['transID'],
            payment_method = body['payment_method'],
            status = body['status'],
            amount_paid = order.order_total,
        )
        
        payment.save()

        order.payment = payment
        order.is_ordered = True
        order.save()
        
        # Move the cart item to OrderProduct table 
        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.quantity = item.quantity
            orderproduct.product_price = item.product.price
            orderproduct.ordered = True
            orderproduct.save()
            
            # add variation to OrderProduct table
            cart_item = CartItem.objects.get(id=item.id)
            product_variation = cart_item.variation.all()
            orderproduct = OrderProduct.objects.get(id=orderproduct.id)
            orderproduct.variations.set(product_variation)
            orderproduct.save()

            
            # Reduce the quantity of the sold products
            product = Product.objects.get(id=item.product_id)
            product.stock -= item.quantity
            product.save()

        # Clear Cart 
        CartItem.objects.filter(user=request.user).delete()

        
        # Send order recieved email to cutomer 
        #subject = 'Thank you for your order!'
        #message = render_to_string('shop/orders/checkout/payment_recieved_email.html', {
        #    'user': request.user,
        #    'order':order,
        #})
        #to_email = request.user.email
        #send_email = EmailMessage(subject, message, to=[to_email])
        #send_email.send()
    #
        #
        ## Send order recieved email to admin account 
        #subject = 'Thank you for your order!'
        #message = render_to_string('shop/orders/checkout/payment_recieved_email.html', {
        #    'user': request.user,
        #    'order':order,
        #})
        #to_email = request.user.email
        #send_email = EmailMessage(subject, message, to=['eshopsuppo@gmail.com'])
        #send_email.send()

        # Send order number and transation id back to sendDate method via JavaResponse
        data = {
                'order_number': order.order_number,
                'transID': payment.payment_id,
            }
        return JsonResponse(data)
    except json.JSONDecodeError:
        # Handle the error gracefully, such as returning an error response
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    #This function generates the OTP codes for payment validation 
def generate_otp(length=6):
    digits = string.digits
    print("digits......" + digits)
    return ''.join(random.choices(digits, k=length))

#This function send emails of the OTP codes for payment validation
def send_otp_email(email, otp):
    subject = 'Payment OTP'
    message = f'Your OTP for Payment is: {otp}'
    from_email = 'noreply@example.com'  # Replace with your desired sender email address
    recipient_list = [email]
    # recipient_list = 'mukurutracey@gmail.com'
    print("message.../...." + message)

    send_mail(subject, message, from_email, recipient_list)

#This function verifies the OTP codes for payment validation

@login_required(login_url='accounts:login')
def otp_verification(request):
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        user_id = request.session.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                # email_device = EmailDevice.objects.get(user=user)
                otp_generated = generate_otp(length=6)  # Generate a 6-digit OTP

                # Send the generated OTP via email
                send_otp_email(user.email, otp_generated)

                # For demonstration purposes, we're printing the OTP, but you should send it via email
                print("Generated OTP: ", otp_generated)

                # Compares the value entered by the user to the one generated by the system.
                if otp_input == otp_generated:
                    del request.session['user_id']
                    auth_login(request, user)
                    return redirect('orders:order_complete')
                else:
                    messages.error(request, 'Invalid OTP. Please try again.')
            except (User.DoesNotExist, EmailDevice.DoesNotExist):
                messages.error(request, 'OTP verification failed. Please contact support.')
                return redirect('accounts:login')

    return render(request, 'shop/orders/checkout/otp_verification.html')

# def otp_verification(request):
#     if request.method == 'POST':
#         otp = request.POST.get('otp')
#         # Geth the OTP code before it is sent to the email.
#         print("otp...." + otp)
#         user_id = request.session.get('user_id')
#         if user_id:
#             try:
#                 # Checks if the user information is correct and redirects to order complete page
#                 user = User.objects.get(id=user_id)
#                 email_device = EmailDevice.objects.get(user=user)
#                 if email_device.verify_token(otp):
#                     del request.session['user_id']  # Remove the user ID from the session after successful verification
#                     auth.login(request, user)
#                     return redirect('orders:order_complete')

#                 messages.error(request, 'Invalid OTP. Please try again.')
#             except (User.DoesNotExist, EmailDevice.DoesNotExist):
#                 messages.error(request, 'OTP verification failed. Please contact support.')
#                 return redirect('accounts:login')

#     return render(request, 'shop/orders/checkout/otp_verification.html')



# Completed order and details shared.

@login_required(login_url = 'accounts:login')
def order_completed(request):
    # data = payments(request)
    # print("Data is This" + str(data))
    # order_number = data.get('order_number')
    # transID = data.get('payment_id')

    # try:
    #     order = Order.objects.get(order_number=order_number, is_ordered=True)
        
    #     ordered_products = OrderProduct.objects.filter(order_id=order.order_number)

    #     subtotal = 0
    #     for i in ordered_products:
    #         subtotal += i.product_price * i.quantity
    #     subtotal = round(subtotal, 2)
    #     payment = Payment.objects.get(payment_id=transID)

    #     context = {
    #         'order': order,
    #         'ordered_products': ordered_products,
    #         'order_number': order.order_number,
    #         'transID': payment.payment_id,
    #         'payment': payment,
    #         'subtotal': subtotal,
    #     }
    # return render(request, 'shop/orders/order_completed/order_completed.html', context)
    return render(request, 'shop/orders/order_completed/order_completed.html')

    # except (Payment.DoesNotExist, Order.DoesNotExist):
    #     return redirect('shop:shop')
    