import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

# If you already have a Product model, import it
# from .models import Product

# Demo product lookup (replace with your actual ORM query)
FAKE_DB = {
    "4902430780003": {"name": "Coca-Cola 1L", "price": 65.00, "sku": "CC-1L"},
    "9556041602119": {"name": "Milo 24g", "price": 12.00, "sku": "ML-24"},
}

@require_POST
@csrf_protect
def scan_product(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        barcode = (body.get("barcode") or "").strip()
        if not barcode:
            return JsonResponse({"ok": False, "error": "No barcode provided"}, status=400)
        

        try:
            product = Product.objects.get(barcode=barcode)
            data = {"name": product.name, "price": float(product.price), "sku": product.sku}
        except Product.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Product not found"}, status=404)
        

        product = FAKE_DB.get(barcode)
        if not product:
            return JsonResponse({"ok": False, "error": "Product not found"}, status=404)
        
        return JsonResponse({"ok": True, "barcode": barcode, "product": product})
    
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)