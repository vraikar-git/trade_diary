import logging

def validate_symbol(value):
    if value is None or value == "" :
        return "Stock Ticker is required."
    return None  

def validate_price(value):

    if value is None or value == "" or value <= 0:
        return "Price cannot be zero."
    try:
        float(value)
    except ValueError:
        return "Price must be a number."
    return None  

def validate_qty(value):
    
    if value is None or value == "" or value <= 0:
        return "Quantity cannot be zero."
    try:
        int(value)
    except ValueError:
        return "Quantity must be a integer."
    return None  

def validate_exit_qty(total_open_position, exit_quantity):
    if exit_quantity > total_open_position:
        return "Quantity cannot exceed total open position."
    return None  

def validate_stoploss(value):

    if value is None or value == "" or value == 0 :
        return "Stoploss is required and cannot exceed entry price."
    try:
        float(value)
    except ValueError:
        return "Input must be a number."
    return None  

def validate_risk_percentage(value):
    if value is None or value == "" or value <= 0 or value > 100:
        return "Risk percentage is required and must be between 0 and 100."
    try:
        float(value)
    except ValueError:
        return "Risk percentage must be a number."
    return None



def validate_add_position(symbol, entry_price, entry_quantity, entry_date, risk_percentage, setup, entry_type , stop_loss):

    logging.info("Validating add position inputs...")
    errors = []
    symbol_error = validate_symbol(symbol)
    if symbol_error:
        errors.append(symbol_error)
    
    entry_price_error = validate_price(entry_price)
    if entry_price_error:
        errors.append(entry_price_error)
    
    qty_error = validate_qty(entry_quantity)
    if qty_error:
        errors.append(qty_error)

    risk_percentage_error = validate_risk_percentage(risk_percentage)
    if risk_percentage_error:
        errors.append(risk_percentage_error)
    
    stop_loss_error = validate_stoploss(stop_loss)
    if stop_loss_error:
        errors.append(stop_loss_error)

    
    if  errors:
        logging.error(f"Validation errors: {errors}")
    return errors if errors else None  


def validate_exit_position(total_open_position, exit_price, exit_quantity, exit_date):
    logging.info("Validating exit position inputs...")
    errors = []

    exit_price_error = validate_price(exit_price)
    if exit_price_error:
        errors.append(f"Exit Price: {exit_price_error}")

    qty_error = validate_qty(exit_quantity)
    if qty_error:
        errors.append(f"Exit Quantity: {qty_error}")

    total_open_position_error = validate_exit_qty(total_open_position, exit_quantity)
    if total_open_position_error:
        errors.append(f"Exit Quantity: {total_open_position_error}")

    if errors:
        logging.error(f"Validation errors: {errors}")
    return errors if errors else None  

def validate_pyramid_position(pyramid_price, pyramid_quantity, pyramid_date, risk_percentage, stop_loss):
    logging.info("Validating pyramid inputs...")
    errors = []

    pyramid_price_error = validate_price(pyramid_price)
    if pyramid_price_error:
        errors.append(f"Pyramid Price: {pyramid_price_error}")

    qty_error = validate_qty(pyramid_quantity)
    if qty_error:
        errors.append(f"Pyramid Quantity: {qty_error}")

    risk_percentage_error = validate_risk_percentage(risk_percentage)
    if risk_percentage_error:
        errors.append(f"Risk Percentage: {risk_percentage_error}")

    stop_loss_error = validate_stoploss(stop_loss)
    if stop_loss_error:
        errors.append(f"Stop Loss: {stop_loss_error}")

    if errors:
        logging.error(f"Validation errors: {errors}")
    return errors if errors else None


