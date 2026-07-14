def applydiscount(price, customertype, coupon_code):

    if price < 0:
        raise ValueError("Invalid Error: price should be greater than 0")
    discount = 0

    if (customertype == "vip"):
        discount = 0.15

    elif (customertype == "regular"):
        discount = 0.05


    if (coupon_code == "SAVE20"):  
        discount = max(discount, 0.20)

    elif (coupon_code == "SAVE10"):
        discount = max(discount, 0.10)
    
    final_price = price * (1 - discount)
    return round(final_price * 100) / 100