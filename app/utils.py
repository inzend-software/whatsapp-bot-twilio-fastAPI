# Utility helpers (expand as needed)
def normalize_phone(phone: str) -> str:
    # Basic normalization: remove spaces and keep +
    return phone.replace(' ', '').replace('-', '')
