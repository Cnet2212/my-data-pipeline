import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            'SUPABASE_URL / SUPABASE_KEY environment variables are not set. '
            'See the setup guide for how to configure them.'
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def save_products_to_db(products: list):
    try:
        supabase = get_supabase_client()
        response = supabase.table('products').upsert(products).execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning: {e}')
        return None
