from django.shortcuts import render,redirect
from django.http import HttpResponse,JsonResponse
from cart.models import CartItem
from store.models import Product
import datetime
from .models import Order,Payment,OrderProduct
from .forms import OrderForm
import json
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

# Create your views here.


def payments(request):
    body=json.loads(request.body)
    order=Order.objects.get(user=request.user,is_ordered=False,order_number=body['orderID'])
    payment=Payment(user=request.user,payment_id=body['transID'],payment_method=body['payment_method'],
    amount_paid=order.order_total,
    status=body['status'])
    payment.save()
    order.payment=payment
    order.is_ordered=True
    order.save()
   

    #move the cart items to Order Product table
    cart_items=CartItem.objects.filter(user=request.user)
    for item in cart_items:
        order_product=OrderProduct()
        order_product.order_id=order.id
        order_product.payment=payment
        order_product.user_id=request.user.id
        order_product.product_id=item.product_id
        order_product.quantity=item.quantity
        order_product.product_price=item.product.price
        order_product.ordered=True
        order_product.save()
        cart_item=CartItem.objects.get(id=item.id)
        product_variation=cart_item.variations.all()
        order_product=OrderProduct.objects.get(id=order_product.id)
        order_product.variations.set(product_variation)
        order_product.save()

        #reduce the quantity of the sold products

        product=Product.objects.get(id=item.product.id)
        product.stock-=item.quantity
        product.save()





   
    
    

    #clear cart
    CartItem.objects.filter(user=request.user).delete()


    #send order received email to customer

    mail_subject='Thank you for your order'
    message=render_to_string('orders/order_recived_email.html',{
                'user':request.user,
                 'order':order
                
               
            })
    to_email=request.user.email
    send_email=EmailMessage(mail_subject,message,to=[to_email])
    send_email.send()


    #send order number and transaction id back to SendData method via json response
    data={
        'order_number':order.order_number,
        'transID':payment.payment_id
    }
    return JsonResponse(data)
def place_order(request,total=0,quantity=0):
    current_user=request.user
    #If the cart count is less than or  equal to 0 then redirect back to shop
    cart_items=CartItem.objects.filter(user=current_user)
    cart_count=cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    tax=0
    grand_total=0
    for cart_item in cart_items:
        total+=(cart_item.product.price*cart_item.quantity)
        quantity+=cart_item.quantity
    tax=(2*total)/100
    grand_total=total+tax

    if request.method == 'POST':
        form=OrderForm(request.POST)
        if form.is_valid():
            #store all the billing information inside OPrder tables
            data=Order()
            data.user=current_user
            data.first_name=form.cleaned_data['first_name']
            data.last_name=form.cleaned_data['last_name']
            data.email=form.cleaned_data['email']
            data.phone=form.cleaned_data['phone']
            data.address_line_1=form.cleaned_data['address_line_1']
            data.address_line_2=form.cleaned_data['address_line_2']
            data.city=form.cleaned_data['city']
            data.state=form.cleaned_data['state']
            data.country=form.cleaned_data['country']
            data.order_note=form.cleaned_data['order_note']
            data.order_total=grand_total
            data.tax=tax
            data.ip=request.META.get('REMOTE_ADDR')
            data.save()
            #Generate order number 
            yr=int(datetime.date.today().strftime("%Y"))
            dt=int(datetime.date.today().strftime("%d"))
            mt=int(datetime.date.today().strftime("%m"))
            d=datetime.date(yr,mt,dt)
            current_date=d.strftime("%Y%m%d")
            order_number=current_date+str(data.id)
            data.order_number=order_number
            data.save()
            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')

def order_complete(request):
    order_number=request.GET.get('order_number')
    transID=request.GET.get('payment_id')
    try:
        order=Order.objects.get(order_number=order_number,is_ordered=True)
        ordered_product=OrderProduct.objects.filter(order_id=order.id)
        context={
            'order':order,
            'ordered_products':ordered_product
        }
        return render(request,'orders/order_complete.html',context)
    except(Payment.DoesNotExist,Order.DoesNotExist):
        return redirect('home')

