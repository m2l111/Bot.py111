# Placeholder for Mhd Store integration
# Replace this function with actual API call
def buy_product(product_code, quantity=1):
    """
    Connect to Mahd Store API, purchase the product, and return the coupon code.
    product_code: e.g., 'PUBG_UC', 'FF_DIAMOND'
    quantity: e.g., number of codes to buy (usually 1)
    Returns: a coupon code string.
    """
    # TODO: Implement real HTTP request to Mahd Store API
    # Example: response = requests.post(https://mhd-game.com/store.html', json={...})
    # For now, simulate a coupon
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))